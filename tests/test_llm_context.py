"""build_llm_context (CLAUDE.md bản 2, mục 3.3): LLM chỉ thấy đúng mức dữ liệu của nguồn, không bao giờ thấy dòng thật."""

import csv
import json
import re
import secrets as pysecrets
import uuid
from pathlib import Path

import pytest

from src.agents.nodes.ingest import ingest_node  # noqa: F401  (đảm bảo node nạp được import trước khi dựng hồ sơ)
from src.agents.nodes.profiler import profiler_node
from src.agents.tools.duckdb_tools import SourceInfo, ingest_sources
from src.config import get_settings
from src.models.sources import CreateSourceBody
from src.services import auth, secrets
from src.services import source_registry as registry
from src.services.llm_context import build_llm_context, context_for_state

REPO = Path(__file__).resolve().parent.parent
NAMES = ["Nguyễn Canary Một", "Trần Canary Hai", "Lê Canary Ba", "Phạm Canary Bốn"]
EMAILS = [f"canary.{i}@secret-corp.vn" for i in range(1, 5)]
PHONES = ["0987654321", "0912345678", "0933333333", "0944444444"]
AMOUNTS = ["1.234.567", "2.345.678", "3.456.789", "4.567.891"]  # khác ví dụ cố định trong nhãn định dạng tiền
ORDER_IDS = [f"CANARY-ORD-{i}" for i in range(1, 13)]
SECRETS = NAMES + EMAILS + PHONES + AMOUNTS + ORDER_IDS


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def make_canary_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sensitivity: str, llm_access: str | None
) -> dict:
    """Nguồn `file` chứa chuỗi bí mật mẫu (tên, email, điện thoại, tiền, mã đơn) + người dùng cùng phòng ban."""
    directory = tmp_path / "canary"
    directory.mkdir()
    with (directory / "canary_orders.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "order_id",
                "order_date",
                "customer_name",
                "customer_email",
                "customer_phone",
                "total_amount",
                "qty",
                "status",
                "contact_note",
            ]
        )
        for i in range(12):
            date = "15/03/2026" if i % 6 else "2026-03-16"
            status = ("completed", "cancelled", "refunded")[i % 3]
            note = f"liên hệ {EMAILS[i % 4]}"  # email nằm trong cột có tên bình thường: giá trị vẫn bị che
            writer.writerow(
                [ORDER_IDS[i], date, NAMES[i % 4], EMAILS[i % 4], PHONES[i % 4], AMOUNTS[i % 4], i + 1, status, note]
            )
    ref = _unique("canary").replace("-", "_")
    monkeypatch.setenv(secrets.env_name(ref), str(directory))
    dept = registry.create_department(_unique("phong"))
    source = registry.create_source(
        CreateSourceBody(
            name=_unique("canary-src"), department_id=dept.id, kind="file", secret_ref=ref, allowed_tables=["*"],
            sensitivity=sensitivity, llm_access=llm_access,
        ),
        "adm",
    )  # fmt: skip
    username = _unique("eng")
    auth.create_user(username, username, "engineer", pysecrets.token_urlsafe(16), dept.id)
    return {"source": source, "user": registry.user_context(username), "directory": directory}


def node_profile(items: list[dict], workspace: Path) -> dict:
    """Hồ sơ của bước P (Soi dữ liệu) trên sandbox vừa nạp: đầu vào của Codegen/Testgen."""
    workspace.mkdir(parents=True, exist_ok=True)
    ingest_sources(workspace / "sandbox.duckdb", [SourceInfo.model_validate(i) for i in items])
    return profiler_node({"workspace": str(workspace)})["profile"]


def everything_llm_sees(ctx, profile: dict) -> str:
    return json.dumps([ctx.planner_catalog(), ctx.build_profile(profile)], ensure_ascii=False)


def assert_no_secret(text: str, allowed: tuple[str, ...] = ()) -> None:
    for secret in SECRETS:
        if secret not in allowed:
            assert secret not in text, f"{secret!r} lọt vào ngữ cảnh LLM"


# ---------- Ba mức ----------


def test_schema_only_has_names_and_types_but_no_stats_and_no_values(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="high", llm_access=None)  # high → schema_only
    ctx = build_llm_context(world["user"])
    assert [t.access for t in ctx.tables] == ["schema_only"] and not ctx.tables[0].profile and not ctx.tables[0].sample
    profile = node_profile(ctx.catalog, tmp_path / "ws")
    seen = everything_llm_sees(ctx, profile)
    assert_no_secret(seen)
    catalog = ctx.planner_catalog()[0]
    assert set(catalog) == {"name", "kind", "columns"} and "customer_email" in catalog["columns"]  # có tên cột
    built = ctx.build_profile(profile)["canary_orders"]
    assert set(built) == {"columns"} and set(built["columns"]["qty"]) == {"type"}  # chỉ kiểu, không null_pct/distinct
    assert not re.search(r"null_pct|distinct|rows|shapes|min|max", json.dumps(built))


def test_profile_level_has_counts_and_shapes_but_no_real_values(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="medium", llm_access="profile")
    ctx = build_llm_context(world["user"])
    table = ctx.tables[0]
    assert table.access == "profile" and not table.sample
    profile = node_profile(ctx.catalog, tmp_path / "ws")
    assert_no_secret(everything_llm_sees(ctx, profile))
    stats = ctx.planner_catalog()[0]["stats"]
    assert stats["rows"] == 12 and stats["few_values"]["status"] == 3
    # ngày lẫn hai định dạng, tiền có dấu chấm: LLM thấy DẠNG, không thấy giá trị
    assert set(stats["formats"]["order_date"]) == {"99/99/9999", "9999-99-99"}
    assert "9.999.999" in stats["formats"]["total_amount"]
    columns = table.profile["columns"]
    assert columns["status"]["distinct"] == 3 and columns["order_id"]["shapes"]
    # cột nhạy cảm: chỉ số đếm + dạng giá trị
    for name in ("customer_name", "customer_email", "customer_phone"):
        info = columns[name]
        assert info["sensitive"] is True and info["shapes"]
        assert not ({"min", "max", "top_values"} & set(info)), name
    assert columns["qty"]["min"] == "1" and columns["qty"]["max"] == "12"  # cột số không nhạy cảm có khoảng giá trị
    assert "top_values" not in columns["status"]  # medium: không đưa danh sách giá trị phổ biến


def test_profile_of_low_sensitivity_source_lists_values_of_small_categorical_columns_only(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="low", llm_access="profile")
    columns = build_llm_context(world["user"]).tables[0].profile["columns"]
    assert set(columns["status"]["top_values"]) == {"completed", "cancelled", "refunded"}  # ≤ 10 giá trị, lặp lại
    for name in ("customer_name", "customer_email", "customer_phone", "order_id", "total_amount"):
        assert "top_values" not in columns[name], name  # nhạy cảm hoặc quá nhiều giá trị khác nhau
    assert_no_secret(json.dumps(columns, ensure_ascii=False))


def test_masked_sample_only_low_sensitivity_and_everything_masked(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="low", llm_access="masked_sample")
    ctx = build_llm_context(world["user"])
    table = ctx.tables[0]
    assert table.access == "masked_sample" and len(table.sample) == get_settings().llm_sample_max_rows == 5
    profile = node_profile(ctx.catalog, tmp_path / "ws")
    seen = everything_llm_sees(ctx, profile)
    assert_no_secret(
        seen, allowed=tuple(ORDER_IDS + AMOUNTS)
    )  # mã đơn, số tiền không nhạy cảm: được hiện (đã qua pii) ở mức này
    row = table.sample[0]
    assert re.fullmatch(r"[a9.@-]+", row["customer_email"]) and re.fullmatch(
        r"9+", row["customer_phone"]
    )  # cột nhạy cảm: dạng giá trị
    assert re.fullmatch(r"[Aa ]+", row["customer_name"])
    assert "***@" in row["contact_note"] and "canary." not in row["contact_note"]  # email trong cột thường: pii che
    assert ctx.build_profile(profile)["canary_orders"]["sample"] == table.sample


def test_sample_row_limit_follows_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_SAMPLE_MAX_ROWS", "2")
    get_settings.cache_clear()
    try:
        world = make_canary_source(tmp_path, monkeypatch, sensitivity="low", llm_access="masked_sample")
        assert len(build_llm_context(world["user"]).tables[0].sample) == 2
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


# ---------- Ràng buộc theo độ nhạy cảm ----------


def test_high_sensitivity_source_can_never_be_raised(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="high", llm_access=None)
    item = {
        **registry.visible_catalog(world["user"])[0],
        "llm_access": "masked_sample",
    }  # giả lập cấu hình bị sửa trực tiếp
    ctx = build_llm_context(world["user"], catalog=[item], run_id="run-nang-quyen")
    assert ctx.tables[0].access == "schema_only" and not ctx.tables[0].sample and not ctx.tables[0].profile
    assert ctx.downgraded == ["canary_orders"]
    actions = [(e.action, e.actor_name, e.detail.get("run_id")) for e in auth.recent_audit(50)]
    assert ("llm_access.downgraded", world["user"].name, "run-nang-quyen") in actions  # vượt mức thì hạ và ghi AuditLog


def test_medium_source_cannot_be_given_samples(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="medium", llm_access="profile")
    item = {**registry.visible_catalog(world["user"])[0], "llm_access": "masked_sample"}
    assert build_llm_context(world["user"], catalog=[item]).tables[0].access == "profile"


def test_catalog_without_registry_metadata_defaults_to_schema_only():
    item = {"name": "t", "kind": "csv", "columns": {"a": "VARCHAR"}, "path": "/khong/co.csv"}
    ctx = build_llm_context("alice", catalog=[item])
    assert (
        ctx.tables[0].access == "schema_only"
        and ctx.level_of("t") == "schema_only"
        and ctx.level_of("khac") == "schema_only"
    )


def test_context_only_contains_tables_the_user_may_see(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="medium", llm_access="profile")
    outsider = registry.user_context("nguoi-ngoai-phong-ban")
    assert [t.name for t in build_llm_context(world["user"]).tables] == ["canary_orders"]
    assert "canary_orders" not in {t.name for t in build_llm_context(outsider).tables}
    assert build_llm_context(world["user"], tables=["khong-co"]).tables == []


def test_code_catalog_keeps_paths_but_llm_view_never_has_them(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="medium", llm_access="profile")
    ctx = build_llm_context(world["user"], audit=True)
    assert ctx.catalog[0]["path"].endswith("canary_orders.csv") and ctx.catalog[0]["llm_access"] == "profile"
    llm_view = json.dumps([ctx.planner_catalog(), [t.model_dump() for t in ctx.tables]], ensure_ascii=False)
    assert "canary_orders.csv" not in llm_view and str(tmp_path) not in llm_view
    assert "sample" not in ctx.catalog[0]  # danh mục cho code cũng không giữ dòng mẫu


def test_context_for_state_uses_state_catalog_and_requester(tmp_path, monkeypatch):
    world = make_canary_source(tmp_path, monkeypatch, sensitivity="medium", llm_access="profile")
    state = {"requester": world["user"].name, "run_id": "r1"}
    ctx = context_for_state(state)
    assert [t.name for t in ctx.tables] == ["canary_orders"]
    again = context_for_state({**state, "source_catalog": ctx.catalog})
    assert [t.access for t in again.tables] == ["profile"]


# ---------- Mọi đường vào prompt đều qua cửa duy nhất ----------

ONLY_CONTEXT_MAY_USE = (
    "compact_profile(",
    "compact_catalog(",
    "referenced_schema(",
    "table_profile(",
    "masked_sample(",
)
ALLOWED = {
    "src/services/llm_context.py",
    "src/services/prompt_context.py",
    "src/services/profiling.py",
    # bộ nạp cài `get_profile`/`sample` của giao diện chung: chỉ llm_context được GỌI chúng để dựng ngữ cảnh cho prompt
    "src/services/connectors/file.py",
    "src/services/connectors/duckdb_conn.py",
    "src/services/connectors/postgres.py",
}


def test_no_node_builds_data_context_by_itself():
    offenders = []
    for path in sorted((REPO / "src").rglob("*.py")):
        relative = path.relative_to(REPO).as_posix()
        text = path.read_text(encoding="utf-8")
        if relative not in ALLOWED and any(token in text for token in ONLY_CONTEXT_MAY_USE):
            offenders.append(relative)
    assert not offenders, f"Chỉ llm_context được dựng ngữ cảnh dữ liệu cho prompt: {offenders}"


@pytest.mark.slow
def test_every_prompt_of_a_full_run_is_free_of_real_values(seeded_sources: Path, monkeypatch: pytest.MonkeyPatch):
    """Quét TOÀN BỘ prompt (system + user) gửi tới LLM trong một lần chạy thử: không có email/điện thoại/mã đơn thật của nguồn."""
    from src.agents import runner
    from src.agents.runner import ResumeRequest
    from src.services.llm_mock import MockProvider

    prompts: list[str] = []
    real = MockProvider.complete

    def spy(self, request, prompt):
        prompts.append("\n".join(prompt))
        return real(self, request, prompt)

    monkeypatch.setattr(MockProvider, "complete", spy)
    outcome = runner.start_run("Gộp đơn hàng 3 nguồn, tính doanh thu ngày", "alice-quet-prompt")
    answers = {q["id"]: q["options"][0] for q in outcome.pending["questions"]}
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="clarify", value={"answers": answers}))
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="plan", value={"decision": "approve"}))
    assert outcome.status == "waiting_review", outcome.error
    assert len(prompts) >= 4  # input_gate không gọi LLM; planner ×2, codegen, testgen, optimizer
    values: set[str] = set()
    for file in seeded_sources.glob("*.csv"):
        with file.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                values |= {
                    v for k, v in row.items() if k and re.search(r"email|phone|order_id|customer", k) and len(v) > 6
                }
    assert len(values) > 50
    text = "\n".join(prompts)
    leaked = sorted(v for v in values if v in text)
    assert not leaked, f"Giá trị thật lọt vào prompt: {leaked[:5]}"

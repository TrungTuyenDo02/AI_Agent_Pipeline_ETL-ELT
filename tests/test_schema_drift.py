"""Phát hiện thay đổi cấu trúc nguồn (CLAUDE.md bản 2, giai đoạn 5): phân loại, chặn run, xác nhận, J2, bản vá, kiểm tra định kỳ."""

import csv
import secrets as pysecrets
import shutil
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.models.sources import CreateSourceBody
from src.services import auth, schema_drift, secrets
from src.services import source_registry as registry
from src.services.jobs import get_jobs
from src.services.store import get_store
from tests.conftest import CSRF

API = "/api/v1"
REQUEST = {"request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày"}


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def col(type_: str, position: int, nullable: bool = True) -> dict:
    return {"type": type_, "nullable": nullable, "position": position}


BASE = {
    "orders": {
        "order_id": col("string", 0, False),
        "order_date": col("string", 1),
        "amount": col("integer", 2),
        "status": col("string", 3),
    }
}


def changed(new_orders: dict, depended: set | None = None, old: dict | None = None) -> dict[str, tuple[str, str]]:
    """{loại thay đổi + cột: (mức, loại)} để khẳng định gọn."""
    drafts = schema_drift.diff(old or BASE, {"orders": new_orders}, depended or set())
    return {f"{d.change_type}:{d.column}": (d.severity, d.change_type) for d in drafts}


# ---------- Phân loại thay đổi (code thuần) ----------


def test_added_column_is_info_only():
    result = changed({**BASE["orders"], "channel": col("string", 4)})
    assert result == {"column_added:channel": ("info", "column_added")}


@pytest.mark.parametrize(
    ("before", "after", "severity"),
    [
        ("integer", "decimal", "warning"),  # mở rộng an toàn
        ("integer", "float", "warning"),
        ("date", "timestamp", "warning"),
        ("string", "integer", "breaking"),
        ("decimal", "string", "breaking"),
        ("timestamp", "date", "breaking"),
        ("integer", "boolean", "breaking"),  # chưa có trong bảng "an toàn" → coi là breaking
    ],
)
def test_type_change_severity(before: str, after: str, severity: str):
    old = {"orders": {"x": col(before, 0)}}
    result = schema_drift.diff(old, {"orders": {"x": col(after, 0)}}, set())
    assert [d.severity for d in result] == [severity]


def test_removed_column_is_breaking_only_when_a_pipeline_uses_it():
    without = {k: v for k, v in BASE["orders"].items() if k != "status"}
    assert changed(without)["column_removed:status"][0] == "warning"
    assert changed(without, depended={("orders", "status")})["column_removed:status"][0] == "breaking"


def test_removed_table_is_breaking():
    drafts = schema_drift.diff(BASE, {}, set())
    assert [(d.change_type, d.severity) for d in drafts] == [("table_removed", "breaking")]


def test_not_null_to_nullable_is_warning():
    result = changed({**BASE["orders"], "order_id": col("string", 0, True)})
    assert result["nullable_changed:order_id"][0] == "warning"


def test_rename_is_suggested_as_possible_rename():
    renamed = {("ordered_at" if k == "order_date" else k): v for k, v in BASE["orders"].items()}
    drafts = schema_drift.diff(BASE, {"orders": renamed}, set())
    assert [(d.change_type, d.severity) for d in drafts] == [("possible_rename", "breaking")]
    assert "order_date → ordered_at" in drafts[0].hint


def test_unrelated_removed_and_added_columns_are_not_a_rename():
    """Khác kiểu, khác vị trí, tên không giống: xóa một cột + thêm một cột chứ không phải đổi tên."""
    new = {k: v for k, v in BASE["orders"].items() if k != "amount"}
    new["tags"] = col("json", 9)
    types = {d.change_type for d in schema_drift.diff(BASE, {"orders": new}, set())}
    assert types == {"column_removed", "column_added"}


def test_identical_structure_has_no_changes_and_same_fingerprint():
    assert schema_drift.diff(BASE, BASE, set()) == []
    shuffled = dict(reversed(list(BASE["orders"].items())))
    assert schema_drift.fingerprint_of(shuffled) == schema_drift.fingerprint_of(BASE["orders"])
    assert schema_drift.fingerprint_of({**BASE["orders"], "x": col("string", 9)}) != schema_drift.fingerprint_of(
        BASE["orders"]
    )


def test_safe_widening_list_lives_in_config_file():
    rules = schema_drift.load_rules()
    assert ("integer", "decimal") in rules["safe"] and ("string", "integer") not in rules["safe"]


# ---------- Cảnh báo thống kê (chỉ cảnh báo, không chặn) ----------


def _profile(rows: int, null_pct: float = 0.0, shapes: dict | None = None, maximum: str = "100") -> dict:
    return {
        "rows": rows,
        "columns": {"amount": {"null_pct": null_pct, "shapes": shapes or {"9.999": 100.0}, "min": "1", "max": maximum}},
    }


def test_profile_warnings_never_block():
    base = _profile(100)
    kinds = {
        "stat_null_increase": _profile(100, null_pct=60.0),
        "stat_rowcount": _profile(1000),
        "stat_new_shape": _profile(100, shapes={"9.999": 80.0, "9.999.999": 20.0}),
        "stat_range_shift": _profile(100, maximum="100000"),
    }
    for kind, current in kinds.items():
        drafts = schema_drift.compare_profiles("orders", base, current)
        assert kind in {d.change_type for d in drafts}, kind
        assert all(d.severity == "warning" for d in drafts)
    assert schema_drift.compare_profiles("orders", base, _profile(120, null_pct=5.0)) == []


def test_sensitive_columns_get_no_range_warning():
    base, current = _profile(100), _profile(100, maximum="999999")
    for profile in (base, current):
        profile["columns"]["amount"]["sensitive"] = True
    kinds = {d.change_type for d in schema_drift.compare_profiles("orders", base, current)}
    assert "stat_range_shift" not in kinds


# ---------- Phụ thuộc pipeline và yêu cầu bản vá ----------


def test_dependencies_come_from_generated_sql():
    catalog = [
        {"name": "orders", "source_id": 7, "source_name": "S", "columns": {"order_id": "VARCHAR", "status": "VARCHAR"}}
    ]
    files = {"models/staging/stg_orders.sql": "select order_id from {{ source('raw', 'orders') }}"}
    found = schema_drift.extract_dependencies(files, catalog)
    assert found == [(7, "S", "orders", "order_id")]  # `status` không được dùng thì không phải phụ thuộc


def test_patch_request_has_structure_only():
    change = schema_drift.SchemaChangeView(
        id=1, source_id=1, source_name="S", table="orders", from_version=1, to_version=2, change_type="possible_rename",
        severity="breaking", detail="Cột orders.order_date biến mất", hint="possible_rename: order_date → ordered_at",
        detected_at=schema_drift._now(), status="open",
    )  # fmt: skip
    text = schema_drift.patch_request_text("Gộp đơn hàng", {"target": "fct", "sources": [{"name": "orders"}]}, [change])
    assert "Gộp đơn hàng" in text and "order_date → ordered_at" in text and len(text) <= schema_drift.MAX_PATCH_TEXT


# ---------- Có cơ sở dữ liệu: chụp, so, ghi, xác nhận ----------


@pytest.fixture
def world(tmp_path: Path, seeded_sources: Path, monkeypatch: pytest.MonkeyPatch):
    """Một phòng ban riêng có một nguồn `file` là bản sao dữ liệu giả lập (sửa được mà không đụng nguồn của test khác)."""
    directory = tmp_path / "src"
    shutil.copytree(seeded_sources, directory)
    ref = f"drift_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv(secrets.env_name(ref), str(directory))
    dept = registry.create_department(_unique("phong-drift"))
    source = registry.create_source(
        CreateSourceBody(
            name=_unique("nguon-drift"), department_id=dept.id, kind="file", secret_ref=ref, allowed_tables=["*"],
            sensitivity="medium",
        ),
        "admin-test",
    )  # fmt: skip
    schema_drift.forget_recent()
    schema_drift.forget_rechecks()
    return {"dir": directory, "dept": dept, "source": source}


def rename_header(path: Path, old: str, new: str) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    rows[0] = [new if name == old else name for name in rows[0]]
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def test_first_check_is_baseline_then_rename_is_recorded_once(world):
    source = world["source"]
    created, tables = schema_drift.check_source(source)
    assert created == [] and "shopee_orders" in tables  # lần đầu: chỉ đặt bản chuẩn
    rename_header(world["dir"] / "shopee_orders.csv", "order_date", "ordered_at")
    created, _ = schema_drift.check_source(source)
    assert [(c.change_type, c.severity) for c in created] == [("possible_rename", "breaking")]
    assert schema_drift.check_source(source)[0] == []  # đã `open` y hệt thì không ghi trùng
    assert len(schema_drift.list_changes([source.id], status="open")) == 1


def test_acknowledge_sets_new_baseline_and_audits(world):
    source = world["source"]
    schema_drift.check_source(source)
    rename_header(world["dir"] / "shopee_orders.csv", "order_date", "ordered_at")
    created, _ = schema_drift.check_source(source)
    assert schema_drift.acknowledge(source.id, "an", change_id=created[0].id) == 1
    acknowledged = schema_drift.list_changes([source.id], status="acknowledged")
    assert [c.acknowledged_by for c in acknowledged] == ["an"]
    assert schema_drift.check_source(source)[0] == []  # cấu trúc mới là bản chuẩn
    assert schema_drift.check_sources([source]).open_breaking == []


def test_change_resolves_itself_when_source_is_restored(world):
    source = world["source"]
    schema_drift.check_source(source)
    path = world["dir"] / "shopee_orders.csv"
    rename_header(path, "order_date", "ordered_at")
    schema_drift.check_source(source)
    rename_header(path, "ordered_at", "order_date")
    schema_drift.check_source(source)
    assert schema_drift.list_changes([source.id], status="open") == []
    assert [c.status for c in schema_drift.list_changes([source.id])] == ["resolved"]


def test_added_column_does_not_block(world):
    source = world["source"]
    schema_drift.check_source(source)
    path = world["dir"] / "shopee_orders.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    rows[0].append("channel")
    rows[1:] = [row + ["web"] for row in rows[1:]]
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    report = schema_drift.check_sources([source])
    assert report.open_breaking == [] and [c.severity for c in report.new_changes] == ["info"]


def test_unreachable_source_is_reported_not_raised(world, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(secrets.env_name(world["source"].secret_ref))
    report = schema_drift.check_sources([world["source"]])
    assert report.unreachable == [world["source"].name] and report.checked_sources == 0


# ---------- Qua API: chặn run, J2, bản vá, kiểm tra định kỳ ----------


async def client_for(role: str, department_id: int) -> AsyncClient:
    from src.main import app

    name, password = _unique(role[:3]), pysecrets.token_urlsafe(16)
    auth.create_user(name, name, role, password, department_id)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="https://test", headers=CSRF)
    response = await client.post(f"{API}/auth/login", json={"username": name, "password": password})
    assert response.status_code == 200, response.text
    client.username = name  # type: ignore[attr-defined]
    return client


@pytest.fixture
def drift_on(monkeypatch: pytest.MonkeyPatch):
    """Bật cửa G1 (test mặc định tắt) và tắt lại khi xong."""
    monkeypatch.setenv("DRIFT_GATE_ENABLED", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def _run_until(client: AsyncClient, status: str, **kwargs) -> str:
    created = await client.post(f"{API}/runs", json=kwargs.get("body", REQUEST))
    assert created.status_code == 202, created.text
    run_id = created.json()["run_id"]
    get_jobs().wait(run_id)
    detail = (await client.get(f"{API}/runs/{run_id}")).json()
    assert detail["record"]["status"] == status, detail["record"]
    return run_id


async def _to_review(client: AsyncClient) -> str:
    run_id = await _run_until(client, "waiting_clarification")
    pending = (await client.get(f"{API}/runs/{run_id}")).json()["pending"]
    answers = {q["id"]: q["options"][0] for q in pending["questions"]}
    assert (await client.post(f"{API}/runs/{run_id}/answers", json={"answers": answers})).status_code == 202
    get_jobs().wait(run_id)
    assert (await client.post(f"{API}/runs/{run_id}/plan", json={"decision": "approve"})).status_code == 202
    get_jobs().wait(run_id)
    assert (await client.get(f"{API}/runs/{run_id}")).json()["record"]["status"] == "waiting_review"
    return run_id


@pytest.mark.slow
async def test_breaking_change_blocks_run_until_engineer_confirms(world, drift_on):
    engineer = await client_for("engineer", world["dept"].id)
    schema_drift.check_source(world["source"])  # bản chuẩn
    rename_header(world["dir"] / "shopee_orders.csv", "order_date", "ordered_at")
    runs_before = len(get_store().list_runs(limit=500))
    run_id = await _run_until(engineer, "waiting_drift")
    pending = (await engineer.get(f"{API}/runs/{run_id}")).json()["pending"]
    assert pending["kind"] == "drift" and "order_date" in pending["message"] and "ordered_at" in pending["message"]
    assert any(c["change_type"] == "possible_rename" for c in pending["changes"])
    assert len(get_store().list_runs(limit=500)) == runs_before + 1  # chỉ run do người tạo; không có run tự sinh
    reviewer = await client_for("reviewer", world["dept"].id)
    assert (await reviewer.post(f"{API}/runs/{run_id}/drift", json={"action": "continue"})).status_code == 403
    done = await engineer.post(f"{API}/runs/{run_id}/drift", json={"action": "continue"})
    assert done.status_code == 202
    get_jobs().wait(run_id)
    status = (await engineer.get(f"{API}/runs/{run_id}")).json()["record"]["status"]
    assert status == "waiting_clarification"  # đã qua G1 sang Planner
    assert [c.acknowledged_by for c in schema_drift.list_changes([world["source"].id], status="acknowledged")] == [
        engineer.username
    ]
    await engineer.aclose()
    await reviewer.aclose()


@pytest.mark.slow
async def test_engineer_can_stop_instead_of_confirming(world, drift_on):
    engineer = await client_for("engineer", world["dept"].id)
    schema_drift.check_source(world["source"])
    rename_header(world["dir"] / "shopee_orders.csv", "order_date", "ordered_at")
    run_id = await _run_until(engineer, "waiting_drift")
    assert (await engineer.post(f"{API}/runs/{run_id}/drift", json={"action": "abort"})).status_code == 202
    get_jobs().wait(run_id)
    detail = (await engineer.get(f"{API}/runs/{run_id}")).json()
    assert detail["record"]["status"] == "failed" and "đổi cấu trúc" in detail["record"]["summary"]["error"]
    assert schema_drift.list_changes([world["source"].id], status="open")  # chưa xác nhận: thay đổi vẫn mở
    await engineer.aclose()


@pytest.mark.slow
async def test_review_blocked_when_structure_changes_after_codegen_then_patch(world, drift_on, monkeypatch):
    engineer = await client_for("engineer", world["dept"].id)
    reviewer = await client_for("reviewer", world["dept"].id)
    run_id = await _to_review(engineer)
    # backend đổi cấu trúc SAU khi agent sinh code: cảnh báo đỏ ở màn duyệt và chặn nút duyệt
    rename_header(world["dir"] / "shopee_orders.csv", "order_date", "ordered_at")
    schema_drift.forget_rechecks()
    detail = (await engineer.get(f"{API}/runs/{run_id}")).json()
    assert detail["drift"]["recheck"]["blocked"] is True
    blocked = await reviewer.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})
    assert blocked.status_code == 409 and "Cấu trúc nguồn đã đổi" in blocked.json()["detail"]
    # kiểm tra lại cấu trúc ghi thay đổi và chỉ ra pipeline bị ảnh hưởng; việc này không tự tạo run
    runs_before = len(get_store().list_runs(limit=500))
    checked = await engineer.post(f"{API}/sources/{world['source'].id}/check-drift")
    assert checked.status_code == 200 and checked.json()["open_breaking"]
    changes = (await engineer.get(f"{API}/schema-changes?status=open")).json()
    assert changes and run_id in [p["run_id"] for p in changes[0]["affected_pipelines"]]
    assert len(get_store().list_runs(limit=500)) == runs_before
    assert (await reviewer.post(f"{API}/sources/{world['source'].id}/check-drift")).status_code == 403
    # chỉ người bấm "Đề xuất bản vá" mới tạo run mới, và run đó đi qua luồng chuẩn (bắt đầu từ cửa G1)
    assert (await reviewer.post(f"{API}/runs/{run_id}/patch")).status_code == 403
    patch = await engineer.post(f"{API}/runs/{run_id}/patch")
    assert patch.status_code == 202
    patch_id = patch.json()["run_id"]
    get_jobs().wait(patch_id)
    assert patch_id != run_id
    assert (await engineer.get(f"{API}/runs/{patch_id}")).json()["record"]["status"] == "waiting_drift"
    await engineer.aclose()
    await reviewer.aclose()


async def test_patch_needs_open_changes(world, drift_on):
    engineer = await client_for("engineer", world["dept"].id)
    run_id = await _run_until(engineer, "waiting_clarification")
    rejected = await engineer.post(f"{API}/runs/{run_id}/patch")
    assert rejected.status_code == 409 and "Không có thay đổi" in rejected.json()["detail"]
    await engineer.aclose()


async def test_scheduled_check_needs_internal_token(anon: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DRIFT_CHECK_TOKEN", "")
    get_settings.cache_clear()
    try:
        assert (await anon.post(f"{API}/sources/check-drift")).status_code == 503  # chưa cấu hình → tắt
        monkeypatch.setenv("DRIFT_CHECK_TOKEN", "token-thu-nghiem-dai-du-dung")
        get_settings.cache_clear()
        wrong = await anon.post(f"{API}/sources/check-drift", headers={"X-Drift-Token": "sai"})
        assert wrong.status_code == 403
        assert (await anon.post(f"{API}/sources/check-drift")).status_code == 403
        right = await anon.post(f"{API}/sources/check-drift", headers={"X-Drift-Token": "token-thu-nghiem-dai-du-dung"})
        assert right.status_code == 200
        assert {"checked", "new_changes", "open_breaking", "open_warnings", "unreachable"} <= set(right.json())
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


async def test_schema_changes_hidden_from_other_departments(world, login):
    schema_drift.check_source(world["source"])
    rename_header(world["dir"] / "shopee_orders.csv", "order_date", "ordered_at")
    schema_drift.check_source(world["source"])
    outsider = await login("engineer")  # phòng mặc định, không thấy nguồn của phòng riêng
    assert (await outsider.get(f"{API}/schema-changes?source_id={world['source'].id}")).json() == []
    assert (await outsider.post(f"{API}/sources/{world['source'].id}/check-drift")).status_code == 404
    insider = await client_for("engineer", world["dept"].id)
    assert len((await insider.get(f"{API}/schema-changes?source_id={world['source'].id}")).json()) == 1
    await insider.aclose()


# ---------- Thêm nhiều ca, hình trước/sau, đề xuất sửa pipeline ----------


def test_narrowing_and_tightening_cases():
    narrowed = schema_drift.diff({"t": {"x": col("float", 0)}}, {"t": {"x": col("decimal", 0)}}, set())
    assert [(d.change_type, d.severity) for d in narrowed] == [("type_narrowed", "breaking")]
    tightened = schema_drift.diff({"t": {"x": col("string", 0, True)}}, {"t": {"x": col("string", 0, False)}}, set())
    assert [(d.change_type, d.severity) for d in tightened] == [("nullable_tightened", "info")]


def _view(change_type: str, detail: str, hint: str = "", table: str = "shopee_orders"):
    return schema_drift.SchemaChangeView(
        id=1, source_id=1, source_name="S", table=table, from_version=1, to_version=2, change_type=change_type,
        severity="breaking", detail=detail, hint=hint, detected_at=schema_drift._now(), status="open",
    )  # fmt: skip


def test_diff_rows_pair_rename_and_mark_changes():
    from src.services import drift_advice

    before = {"order_id": col("string", 0), "order_date": col("string", 1), "amount": col("string", 2)}
    after = {"order_id": col("string", 0), "ordered_at": col("string", 1), "amount": col("integer", 2)}
    view = _view("possible_rename", "x", "possible_rename: order_date → ordered_at")
    rows = {r.name: r for r in drift_advice.build_rows(before, after, view)}
    assert rows["order_id"].status == "same"
    assert rows["order_date"].status == "renamed_from" and rows["ordered_at"].status == "renamed_to"
    assert rows["amount"].status == "changed" and "string → integer" in rows["amount"].note


CODE = {
    "models/staging/stg_shopee_orders.sql": "select cast(order_id as varchar) as order_id, order_date from {{ source('raw', 'shopee_orders') }}",
    "models/staging/stg_tiki_orders.sql": "select id from {{ source('raw', 'tiki_orders') }}",
    "models/marts/fct.sql": "select order_date from {{ ref('stg_shopee_orders') }}",
}


def test_advice_points_to_files_and_actions_without_llm():
    from src.services import drift_advice

    view = _view("possible_rename", "Cột shopee_orders.order_date biến mất", "possible_rename: order_date → ordered_at")
    files = drift_advice.affected_files(CODE, {}, view, "order_date")
    assert [(f.path, f.impact) for f in files if f.role in ("staging", "mart")] == [
        ("models/staging/stg_shopee_orders.sql", "direct"),
        ("models/marts/fct.sql", "indirect"),
    ]  # tiki không bị ảnh hưởng
    actions = drift_advice.build_actions(view, "order_date", files)
    assert any("ordered_at" in a.what and a.where.endswith("stg_shopee_orders.sql") for a in actions)
    nothing = drift_advice.affected_files(CODE, {}, _view("column_removed", "x", table="website_orders"), "x")
    assert nothing == []


def test_added_column_needs_no_pipeline_change():
    from src.services import drift_advice

    view = _view("column_added", "Cột mới shopee_orders.channel (string).")
    files = drift_advice.affected_files(CODE, {}, view, "channel")
    assert files == [] and "không cần sửa" in drift_advice._headline(view, files, False)  # noqa: SLF001


def test_ai_explanation_is_optional_and_falls_back(monkeypatch: pytest.MonkeyPatch):
    from src.services import drift_advice, llm

    view = _view("column_removed", "Cột shopee_orders.order_date đã bị xóa")
    files = drift_advice.affected_files(CODE, {}, view, "order_date")
    actions = drift_advice.build_actions(view, "order_date", files)
    text, source = drift_advice.ai_explain(view, "order_date", files, actions)
    assert source == "mock" and text  # LLM_PROVIDER=mock trong test
    monkeypatch.setattr(llm, "call_llm", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("không có khóa")))
    assert drift_advice.ai_explain(view, "order_date", files, actions) == ("", "unavailable")


async def test_diff_and_suggest_endpoints(world, drift_on):
    engineer = await client_for("engineer", world["dept"].id)
    schema_drift.check_source(world["source"])
    rename_header(world["dir"] / "shopee_orders.csv", "order_date", "ordered_at")
    created, _ = schema_drift.check_source(world["source"])
    diff = (await engineer.get(f"{API}/schema-changes/{created[0].id}/diff")).json()
    statuses = {r["name"]: r["status"] for r in diff["rows"]}
    assert statuses["order_date"] == "renamed_from" and statuses["ordered_at"] == "renamed_to"
    advice = await engineer.post(f"{API}/schema-changes/{created[0].id}/suggest", json={"use_ai": True})
    assert advice.status_code == 200 and advice.json()["files"] == []  # chưa có pipeline nào dùng
    reviewer = await client_for("reviewer", world["dept"].id)
    assert (await reviewer.post(f"{API}/schema-changes/{created[0].id}/suggest", json={})).status_code == 403
    assert (await engineer.get(f"{API}/schema-changes/999999999/diff")).status_code == 404
    await engineer.aclose()
    await reviewer.aclose()

"""Đo "bản vá nhanh" khi nguồn đổi cấu trúc: bao nhiêu thay đổi tự vá được bằng code, tốn bao nhiêu token, kết quả có giống lần chạy gốc không.

So sánh với cách cũ (tạo run mới, lập kế hoạch lại từ đầu): một run đầy đủ ở chế độ `mock` tốn `full_run_tokens` token (số ước lượng của mock).
Mỗi kịch bản: áp thay đổi lên bảng raw của sandbox → bộ phát hiện (`schema_drift.diff`) → kế hoạch vá (`patch_plan.build_plan`) → chạy các node
của run vá (profiler → patch_apply → testgen → V1 → V2 → patch_verify) → so bảng đích với lần chạy gốc. Không LLM, không mạng.
Kịch bản cần người chọn được trả lời như một người dùng sẽ chọn (ghi rõ trong bảng); kịch bản cần AI KHÔNG chạy ở đây (mock không phản ánh chất lượng).

    python eval/run_patch.py        # → eval/results/patch.md (+ patch.json)
"""

import json
import os
import shutil
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "eval_work" / "patch"
WITH_LLM = "--with-llm" in sys.argv  # gọi LLM thật cho kịch bản cần AI (tốn token, cần khóa API trong .env)
os.environ.update(
    {
        "DATABASE_URL": "",  # không đụng cơ sở dữ liệu thật
        "LLM_PROVIDER": "mock",  # pipeline gốc luôn dựng bằng mock (tất định); --with-llm chỉ đổi sang LLM thật SAU khi đã dựng xong
        "LLM_FALLBACK": "none",
        "LANGCHAIN_TRACING_V2": "false",
        "STORE_PATH": str(WORK / "app.db"),
        "CHECKPOINT_PATH": str(WORK / "checkpoints.db"),
        "SOURCES_DIR": str(WORK / "sources"),
        "WORKSPACES_DIR": str(WORK / "workspaces"),
        "MOCK_LARGE_ROWS": "20000",
    }
)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import duckdb  # noqa: E402
import simulate_drift as sim  # noqa: E402

from src.agents.nodes.codegen import codegen_node  # noqa: E402
from src.agents.nodes.common import sandbox_db  # noqa: E402
from src.agents.nodes.patch import patch_apply_node, patch_verify_node  # noqa: E402
from src.agents.nodes.profiler import profiler_node  # noqa: E402
from src.agents.nodes.safety import safety_node  # noqa: E402
from src.agents.nodes.sandbox_run import sandbox_run_node  # noqa: E402
from src.agents.nodes.testgen import testgen_node  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.models.drift import SchemaChangeView  # noqa: E402
from src.services import patch_plan  # noqa: E402

RESULTS = ROOT / "eval" / "results"
CASES = [
    # (kịch bản, câu trả lời của người dùng cho câu hỏi "cột nào thay cột cũ?", mô tả lựa chọn)
    (next(s for s in sim.SCENARIOS if s.key == "rename_column"), {"1": "use:ordered_at"}, "chọn cột nghi đổi tên"),
    (
        sim.Scenario(
            "rename_and_retype",
            "Đổi tên cột VÀ đổi kiểu (website_orders.amount_vnd → amount, số → chuỗi)",
            (
                "ALTER TABLE raw.website_orders RENAME COLUMN amount_vnd TO amount",
                "ALTER TABLE raw.website_orders ALTER amount TYPE VARCHAR",
            ),
            "blocked",
        ),
        {"1": "use:amount"},
        "chọn cột amount thay amount_vnd",
    ),
    (next(s for s in sim.SCENARIOS if s.key == "money_to_number"), {}, ""),
    (
        sim.Scenario(
            "float_to_string",
            "Kiểu số thực đổi thành chuỗi (tiki_orders.grand_total)",
            ("ALTER TABLE raw.tiki_orders ALTER grand_total TYPE VARCHAR",),
            "blocked",
        ),
        {},
        "",
    ),
    (next(s for s in sim.SCENARIOS if s.key == "add_column"), {}, ""),
    (next(s for s in sim.SCENARIOS if s.key == "drop_used_column"), {"1": "drop"}, "chọn bỏ cột khỏi pipeline"),
]
PARENT = WORK / "parent"
MAX_FIX = 3  # như MAX_FIX_ATTEMPTS của luồng thật


def cost_of(usage: list[dict]) -> dict:
    return {
        "tokens": sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in usage),
        "cost_usd": round(sum(u.get("cost_usd", 0.0) for u in usage), 5),
        "llm_calls": len(usage),
    }


def views_of(drafts: list) -> list[SchemaChangeView]:
    now = datetime.now(UTC)
    return [
        SchemaChangeView(
            id=index, source_id=1, source_name="eval", table=d.table, from_version=1, to_version=2, change_type=d.change_type,
            severity=d.severity, detail=d.detail, hint=d.hint, detected_at=now, status="open",
        )
        for index, d in enumerate(drafts, 1)
    ]  # fmt: skip


def run_case(base: dict, scenario: sim.Scenario, answers: dict, choice: str) -> dict:
    db = sandbox_db(base)
    shutil.copy(base["_snapshot"], db)
    with duckdb.connect(str(db)) as con:
        for statement in scenario.sql:
            con.execute(statement)
    started = time.perf_counter()
    structure, _stats, _ = sim.detect(base, db)
    views = views_of(structure)
    new_tables = sim.tables_of(db)
    plan = patch_plan.build_plan(
        base["run_id"], base, views, answers, lambda v: (base["_tables"].get(v.table, {}), new_tables.get(v.table, {}))
    )
    row = {
        "key": scenario.key,
        "title": scenario.title,
        "changes": [f"{d.severity}: {d.change_type}" for d in structure],
        "actions": [i.action for i in plan.items],
        "choice": choice,
        "code_fixes": plan.code_fixes,
        "llm_items": plan.llm_items,
        "questions": plan.questions,
        "estimate": plan.estimate,
        "tokens": 0,
        "outcome": "",
        "detail": "",
        "files": [],
    }
    if not plan.ready:
        return {**row, "outcome": "needs_person", "detail": "Cần người chọn hoặc không vá được tự động."}
    if plan.llm_items and not WITH_LLM:
        return {
            **row,
            "outcome": "needs_ai",
            "detail": "Phần còn lại cần AI sửa file (chạy với --with-llm để gọi LLM thật; mock không phản ánh chất lượng).",
        }
    seed = patch_plan.seed_state(base["run_id"], base, plan, "eval")
    seed["patch"]["parent_workspace"] = str(PARENT)
    state = {**base, **seed}
    usage: list[dict] = []

    def step(node) -> None:  # noqa: ANN001
        out = node(state)
        usage.extend(out.get("llm_usage", []))
        state.update(out)

    step(profiler_node)
    step(patch_apply_node)
    row["files"] = sorted({a["file"] for a in state["patch"]["applied"]})
    row["already_ok"] = state["patch"]["already_ok"]
    needs_ai = bool(state["patch"]["llm_items"])
    if needs_ai and not WITH_LLM:
        return {**row, "outcome": "needs_ai", "detail": "Có file không sửa được an toàn bằng code, cần AI."}
    if needs_ai:
        step(codegen_node)  # Codegen chỉ nhận các file cần sửa (patch.llm_files) và lời nhắc chỉ có tên cột/kiểu
    step(testgen_node)
    for attempt in range(
        MAX_FIX + 1 if needs_ai else 1
    ):  # vòng sửa V1/V2 ↔ Codegen như luồng thật (chỉ khi đã dùng AI)
        step(safety_node)
        if state["safety"]["passed"]:
            step(sandbox_run_node)
            if state["sandbox"]["passed"]:
                break
        if attempt < MAX_FIX and needs_ai:
            step(codegen_node)
            step(testgen_node)
    if not state["safety"]["passed"]:
        return {**row, "outcome": "failed_v1", "detail": state["safety"]["issues"][0][:160], **cost_of(usage)}
    if not state["sandbox"]["passed"]:
        return {**row, "outcome": "failed_v2", "detail": state["sandbox"]["error"][:160], **cost_of(usage)}
    verify = patch_verify_node(state)["patch"]["regression"]
    seconds = round(time.perf_counter() - started, 1)
    outcome = "passed_same" if verify.get("same") else "passed_different"
    detail = (
        ""
        if verify.get("same")
        else f"{verify.get('differing_rows')} dòng khác ({verify.get('rows_before')} → {verify.get('rows_after')})"
    )
    return {
        **row,
        "outcome": outcome,
        "detail": detail,
        "seconds": seconds,
        "llm_files": state["patch"]["llm_files"],
        **cost_of(usage),
    }


LABEL = {
    "passed_same": "Vá xong, bảng đích GIỐNG lần chạy gốc",
    "passed_different": "Vá xong, bảng đích KHÁC lần chạy gốc (hiện cho người duyệt)",
    "failed_v1": "V1 chặn bản vá",
    "failed_v2": "V2 (dbt build/test) thất bại",
    "needs_ai": "Cần AI sửa file",
    "needs_person": "Cần người chọn / không vá được",
}


def write_report(rows: list[dict], golden: tuple[int, float] | None) -> dict:
    changed = [r for r in rows if any(a != "none" for a in r["actions"])]
    auto = [r for r in changed if r["outcome"].startswith("passed")]
    summary = {
        "date": date.today().isoformat(),
        "cases": len(rows),
        "need_change": len(changed),
        "fixed_by_code": len(auto),
        "same_as_original": sum(r["outcome"] == "passed_same" for r in rows),
        "needs_ai_or_person": sum(r["outcome"] in ("needs_ai", "needs_person") for r in rows),
        "failed": sum(r["outcome"].startswith("failed") for r in rows),
        "patch_tokens": sum(r["tokens"] for r in rows),
        "old_way_tokens": golden[0] if golden else None,
        "old_way_usd": golden[1] if golden else None,
    }
    lines = [
        "# Bản vá nhanh khi nguồn đổi cấu trúc",
        "",
        f"- Ngày chạy: {summary['date']} • nguồn thử DuckDB (seed 42, 3 nguồn × 120 dòng) • `python eval/run_patch.py` • "
        + (
            "Codegen/Testgen của bản vá gọi LLM THẬT (pipeline gốc dựng bằng mock)"
            if WITH_LLM
            else "LLM `mock` (không phản ánh chất lượng mô hình thật)"
        ),
        "- Mỗi kịch bản: áp thay đổi lên bảng raw → kế hoạch vá (`patch_plan.build_plan`) → profiler → `patch_apply` → testgen → V1 → V2 → `patch_verify` (so bảng đích với lần chạy gốc).",
        "- Cách cũ để so: tạo run mới và lập kế hoạch lại từ đầu, tốn một run đầy đủ. Mock không đếm token nên số của cách cũ lấy từ phép đo LLM thật ở bộ golden.",
        "",
        f"**Cần sửa code: {summary['need_change']}/{summary['cases']} kịch bản • xử lý xong không cần AI, qua V1+V2: {summary['fixed_by_code']}/{summary['need_change']} "
        f"• bảng đích giống lần chạy gốc: {summary['same_as_original']}/{summary['cases']} • cần AI hoặc người: {summary['needs_ai_or_person']} • V1/V2 chặn: {summary['failed']}**",
        f"Token của các bản vá chạy ở đây: **{summary['patch_tokens']}**. Cách cũ (tạo run mới, lập kế hoạch lại) tốn một run đầy đủ: "
        + (
            f"trung bình **{golden[0]} token ≈ {golden[1]} USD** mỗi run (LLM thật, đo ở bộ golden, `eval/results/golden_agent.md`), chưa kể các câu hỏi lại và lần duyệt kế hoạch."
            if golden
            else "chưa có số đo LLM thật để so."
        ),
        "",
        "| # | Kịch bản | Thay đổi phát hiện | Xử lý | Lựa chọn của người dùng | File sửa | Token (USD) | Kết quả |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for index, r in enumerate(rows, 1):
        detail = LABEL[r["outcome"]] + (f" — {r['detail']}" if r["detail"] else "")
        lines.append(
            f"| {index} | {r['title']} | {'<br>'.join(r['changes']) or '—'} | {', '.join(r['actions']) or '—'} | {r['choice'] or '—'} | "
            f"{'<br>'.join(r['files']) or '—'}{('<br>đã đúng sẵn: ' + ', '.join(r['already_ok'])) if r.get('already_ok') else ''} | {r['tokens']} ({r.get('cost_usd', 0)}) | {detail.replace('|', '/')} |"
        )
    lines += [
        "",
        "Ghi chú:",
        "- Xử lý: `none` = không cần sửa code, `code` = sửa tất định bằng sqlglot, `llm` = cần AI, `ask` = cần người chọn, `blocked` = không vá được.",
        '- "đã đúng sẵn": pipeline sinh ra đã ép kiểu cột đó ở staging (luật phòng thủ của giai đoạn 5) nên đổi kiểu ở nguồn không làm hỏng gì; bản vá không đổi file đó.',
        "- Nếu bảng đích khác lần chạy gốc (nguồn mất giá trị khi đổi kiểu, hoặc dữ liệu đã đổi), `patch_verify` đưa sự khác biệt lên màn duyệt J2 thay vì im lặng.",
        "- Kịch bản cần AI (bỏ cột đang dùng) không chạy ở đây: với LLM thật, ngữ cảnh chỉ gồm tên cột/kiểu và đúng các file cần sửa.",
        "- Đây là mô phỏng trên sandbox, không phải trên nguồn production.",
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    name = "patch_llm" if WITH_LLM else "patch"
    (RESULTS / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / f"{name}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return summary


def golden_cost() -> tuple[int, float] | None:
    """Chi phí TRUNG BÌNH một run đầy đủ với LLM thật (đo ở bộ golden, eval/results/golden_agent.json): mock không đếm token nên lấy số đo thật này."""
    path = RESULTS / "golden_agent.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("rows") or []
    tokens = [c.get("tokens") for c in cases if isinstance(c.get("tokens"), int | float)]
    costs = [c.get("cost_usd") for c in cases if isinstance(c.get("cost_usd"), int | float)]
    return (round(sum(tokens) / len(tokens)), round(sum(costs) / len(costs), 4)) if tokens and costs else None


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    base = sim.build_baseline(WORK)
    if WITH_LLM:  # từ đây Codegen/Testgen của bản vá gọi model thật theo config/models.yaml (khóa trong .env)
        os.environ.pop("LLM_PROVIDER", None)
        os.environ.pop("LLM_FALLBACK", None)
        get_settings.cache_clear()
    PARENT.mkdir(parents=True, exist_ok=True)
    shutil.copy(base["_snapshot"], PARENT / "sandbox.duckdb")  # bảng đích của lần chạy gốc
    golden = golden_cost()
    rows = []
    for scenario, answers, choice in CASES:
        row = run_case(base, scenario, answers, choice)
        rows.append(row)
        print(f"{row['key']:<20} {row['outcome']:<17} {row['detail'][:90]}")
    summary = write_report(rows, golden)
    print(
        f"Đã ghi {RESULTS / ('patch_llm.md' if WITH_LLM else 'patch.md')}: {summary['fixed_by_code']}/{summary['need_change']} vá bằng code, token vá {summary['patch_tokens']}."
    )


if __name__ == "__main__":
    main()

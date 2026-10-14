"""Mô phỏng 6 kịch bản "backend đổi nguồn mà không báo" lên một nguồn thử (DuckDB, dữ liệu giả lập seed 42) — CLAUDE.md bản 2, 5.7.

Với mỗi kịch bản: (1) áp thay đổi lên bảng raw của sandbox, (2) chạy bộ phát hiện (`schema_drift.diff` + `compare_profiles`),
(3) chạy lại CHÍNH pipeline đã sinh (preflight `check_source_schema` + `dbt build` + test), (4) so bảng đích với bản gốc.
Không cần LLM, không cần mạng, không đụng cơ sở dữ liệu ứng dụng. Kết quả: eval/results/drift.md (+ drift.json).

    python scripts/simulate_drift.py
"""

import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "eval_work" / "drift"
if __name__ == "__main__":
    os.environ.update(
        {
            "DATABASE_URL": "",  # không đụng cơ sở dữ liệu thật
            "LLM_PROVIDER": "mock",
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

import duckdb  # noqa: E402

from src.agents.nodes.codegen import codegen_node  # noqa: E402
from src.agents.nodes.common import all_files, sandbox_db  # noqa: E402
from src.agents.nodes.ingest import ingest_node  # noqa: E402
from src.agents.nodes.mock_data import mock_data_node  # noqa: E402
from src.agents.nodes.planner import planner_node  # noqa: E402
from src.agents.nodes.profiler import profiler_node  # noqa: E402
from src.agents.nodes.safety import safety_node  # noqa: E402
from src.agents.nodes.sandbox_run import sandbox_run_node  # noqa: E402
from src.agents.nodes.testgen import testgen_node  # noqa: E402
from src.agents.tools.dbt_tools import PREFLIGHT_FAILED, run_dbt_build  # noqa: E402
from src.agents.tools.duckdb_tools import RAW_SCHEMA, connect_read, read_catalog  # noqa: E402
from src.services import schema_drift  # noqa: E402
from src.services.connectors.base import normalize_type  # noqa: E402
from src.services.llm_mock import DUPLICATE_OPTIONS, Q_DUPLICATES, Q_STATUS, STATUS_OPTIONS  # noqa: E402
from src.services.profiling import table_profile  # noqa: E402
from src.services.seed import SeedConfig, generate_sources  # noqa: E402

RESULTS = ROOT / "eval" / "results"
MART_ORDER = "order_date"


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    sql: tuple[str, ...]  # lệnh áp lên schema raw của sandbox
    expect: str  # blocked | harmless | warned — kết quả mong đợi (xem mục 5.7)


SCENARIOS = [
    Scenario(
        "money_to_number",
        "Cột tiền từ chuỗi sang số (shopee_orders.total_amount)",
        (
            "ALTER TABLE raw.shopee_orders ALTER total_amount TYPE BIGINT "
            "USING try_cast(replace(total_amount, '.', '') AS BIGINT)",
        ),
        "blocked",
    ),
    Scenario(
        "rename_column",
        "Đổi tên cột order_date → ordered_at (shopee_orders)",
        ("ALTER TABLE raw.shopee_orders RENAME COLUMN order_date TO ordered_at",),
        "blocked",
    ),
    Scenario(
        "drop_used_column",
        "Xóa cột đang dùng (tiki_orders.grand_total)",
        ("ALTER TABLE raw.tiki_orders DROP COLUMN grand_total",),
        "blocked",
    ),
    Scenario(
        "add_column",
        "Thêm cột mới (website_orders.channel)",
        ("ALTER TABLE raw.website_orders ADD COLUMN channel VARCHAR",),
        "harmless",
    ),
    Scenario(
        "null_heavy",
        "Cột ngày bỗng rỗng nhiều (shopee_orders.order_date rỗng ~60%)",
        ("UPDATE raw.shopee_orders SET order_date = NULL WHERE rowid % 10 < 6",),
        "blocked",
    ),
    Scenario(
        "money_x1000",
        "Cột tiền đổi đơn vị ×1000 (shopee_orders.total_amount: 1.075.000 → 1.075.000.000)",
        ("UPDATE raw.shopee_orders SET total_amount = cast(total_amount AS VARCHAR) || '.000'",),
        "warned",
    ),
]


def build_baseline(work: Path = WORK) -> dict:
    """Pipeline đúng (mock, seed cố định) đã qua V1 + V2; trả về state kèm bản chụp sandbox và bảng đích gốc."""
    shutil.rmtree(work, ignore_errors=True)
    generate_sources(SeedConfig(out_dir=work / "sources", seed=42, dirty=0.05, rows_per_source=120))
    state: dict = {
        "run_id": "drift-base",
        "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày",
        "requester": "eval",
        "answers": {Q_STATUS: STATUS_OPTIONS[0], Q_DUPLICATES: DUPLICATE_OPTIONS[0]},
    }
    for node in (planner_node, ingest_node, profiler_node, mock_data_node, codegen_node, testgen_node):
        state.update(node(state))
    if issues := safety_node(state)["safety"]["issues"]:
        raise RuntimeError(f"Pipeline gốc không qua V1: {issues[0]}")
    sandbox = sandbox_run_node(state)["sandbox"]
    if not sandbox["passed"]:
        raise RuntimeError(f"Pipeline gốc không qua V2: {sandbox['error'][:200]}")
    db = sandbox_db(state)
    snapshot = db.with_name("baseline.duckdb")
    shutil.copy(db, snapshot)
    state["_snapshot"] = str(snapshot)
    state["_mart"] = read_mart(db, state["spec"]["target"])
    state["_tables"] = tables_of(db)
    state["_profiles"] = profiles_of(db)
    return state


def tables_of(db: Path) -> dict:
    """Cấu trúc các bảng raw ở dạng của `schema_drift` (kiểu chuẩn hóa, vị trí)."""
    raw = read_catalog(db).get(RAW_SCHEMA, {})
    return {
        table: {
            column: {"type": normalize_type(dtype), "nullable": True, "position": index}
            for index, (column, dtype) in enumerate(columns.items())
        }
        for table, columns in raw.items()
    }


def profiles_of(db: Path) -> dict[str, dict]:
    """Hồ sơ thống kê an toàn (số dòng, % rỗng, dạng giá trị, min/max) của từng bảng raw — không có giá trị thật."""
    raw = read_catalog(db).get(RAW_SCHEMA, {})
    out = {}
    with duckdb.connect(str(db), read_only=True) as con:
        for table, columns in raw.items():
            con.execute(f'CREATE OR REPLACE TEMP VIEW src AS SELECT * FROM {RAW_SCHEMA}."{table}"')
            item = {"name": table, "kind": "duckdb", "table": table, "columns": columns}
            full = table_profile(item, "low", [], query=lambda sql: con.execute(sql).fetchall())
            out[table] = schema_drift._slim_profile(full)  # noqa: SLF001 — cùng định dạng với bản cơ sở lưu trong hệ thống
    return out


def read_mart(db: Path, target: str) -> list[tuple]:
    with connect_read(db) as con:
        return con.execute(f'SELECT * FROM main."{target}" ORDER BY {MART_ORDER}').fetchall()


def detect(base: dict, db: Path) -> tuple[list, list, float]:
    """Bộ phát hiện của hệ thống: thay đổi cấu trúc (mức độ) + cảnh báo thống kê; kèm số giây."""
    started = time.perf_counter()
    depended = {(t, c) for _, _, t, c in schema_drift.extract_dependencies(all_files(base), _catalog_items(base))}
    structure = schema_drift.diff(base["_tables"], tables_of(db), depended)
    stats = []
    new_profiles = profiles_of(db)
    for table, profile in new_profiles.items():
        if table in base["_profiles"]:
            stats.extend(schema_drift.compare_profiles(table, base["_profiles"][table], profile))
    return structure, stats, time.perf_counter() - started


def _catalog_items(base: dict) -> list[dict]:
    return [{"name": t, "columns": {c: m["type"] for c, m in cols.items()}} for t, cols in base["_tables"].items()]


def classify_pipeline(base: dict, result, db: Path) -> tuple[str, str]:
    """Chạy lại pipeline đã sinh cho ra: fail sớm (preflight) / fail ở test / chạy xong giống gốc / chạy xong nhưng khác gốc."""
    if not result.ok:
        message = result.log_tail.strip().splitlines()
        if PREFLIGHT_FAILED in result.log_tail:
            return "fail_early", "; ".join(line.lstrip("- ") for line in message[1:3] if line)
        failed = [r for r in result.results if r.status not in ("success", "pass", "warn")]
        return "fail_test", ", ".join(r.unique_id.split(".")[2] for r in failed[:2]) or "dbt build thất bại"
    same = read_mart(db, base["spec"]["target"]) == base["_mart"]
    return ("passed_same" if same else "passed_different"), ""


def run_scenario(base: dict, scenario: Scenario) -> dict:
    """Áp một kịch bản lên bản chụp sandbox rồi đo: phát hiện, chạy lại pipeline, so kết quả."""
    db = sandbox_db(base)
    shutil.copy(base["_snapshot"], db)
    with duckdb.connect(str(db)) as con:
        for statement in scenario.sql:
            con.execute(statement)
    structure, stats, detect_seconds = detect(base, db)
    started = time.perf_counter()
    result = run_dbt_build(Path(base["workspace"]))
    rerun_seconds = time.perf_counter() - started
    outcome, detail = classify_pipeline(base, result, db)
    breaking = [d for d in structure if d.severity == "breaking"]
    warnings = [d for d in structure if d.severity == "warning"] + stats
    silent_wrong = outcome == "passed_different" and not breaking and not warnings
    return {
        "key": scenario.key,
        "title": scenario.title,
        "expect": scenario.expect,
        "structure": [f"{d.severity}: {d.change_type}" for d in structure],
        "stats": [d.change_type for d in stats],
        "hints": [d.hint for d in structure if d.hint],
        "gate_blocks": bool(breaking),
        "pipeline": outcome,
        "pipeline_detail": detail,
        "silent_wrong": silent_wrong,
        "detect_seconds": round(detect_seconds, 2),
        "rerun_seconds": round(rerun_seconds, 2),
    }


def control(base: dict) -> dict:
    """Đối chứng: không đổi gì → không được có thay đổi nào (báo nhầm) và pipeline phải chạy lại đúng như cũ."""
    db = sandbox_db(base)
    shutil.copy(base["_snapshot"], db)
    structure, stats, _ = detect(base, db)
    result = run_dbt_build(Path(base["workspace"]))
    outcome, _ = classify_pipeline(base, result, db)
    return {"false_alarms": len(structure) + len(stats), "pipeline": outcome}


def summarize(rows: list[dict], ctl: dict) -> dict:
    handled = [r for r in rows if r["gate_blocks"] or r["pipeline"] in ("fail_early", "fail_test")]
    return {
        "date": date.today().isoformat(),
        "total": len(rows),
        "blocked_or_failed_early": len(handled),
        "harmless_unchanged": sum(r["pipeline"] == "passed_same" and not r["gate_blocks"] for r in rows),
        "warned_only": sum(r["pipeline"] == "passed_different" and bool(r["stats"]) for r in rows),
        "silent_wrong": sum(r["silent_wrong"] for r in rows),
        "false_alarms": ctl["false_alarms"] + sum(r["gate_blocks"] for r in rows if r["expect"] == "harmless"),
        "mean_detect_seconds": round(sum(r["detect_seconds"] for r in rows) / len(rows), 2),
    }


PIPELINE_LABEL = {
    "fail_early": "fail sớm ở preflight",
    "fail_test": "fail ở test dbt",
    "passed_same": "chạy xong, kết quả như gốc",
    "passed_different": "chạy xong, KẾT QUẢ KHÁC GỐC",
}


def write_report(summary: dict, rows: list[dict], ctl: dict) -> None:
    lines = [
        '# Schema drift — 6 kịch bản "backend đổi nguồn không báo"',
        "",
        f"- Ngày chạy: {summary['date']} • nguồn thử DuckDB (seed 42, 3 nguồn × 120 dòng) • pipeline sinh bằng mock • `python scripts/simulate_drift.py`",
        "- Mỗi kịch bản: áp thay đổi lên bảng raw → bộ phát hiện (`schema_drift`) → chạy lại pipeline đã sinh (preflight + dbt build + test) → so bảng đích với bản gốc.",
        "- Phạm vi: đây là mô phỏng trên sandbox, không phải trên cơ sở dữ liệu production; không có LLM, không có mạng.",
        "",
        f"**Chặn hoặc fail sớm: {summary['blocked_or_failed_early']}/{summary['total']}** (cộng kịch bản vô hại vẫn đúng: "
        f"{summary['blocked_or_failed_early'] + summary['harmless_unchanged']}/{summary['total']}) • vô hại, vẫn đúng: {summary['harmless_unchanged']} • "
        f"chỉ cảnh báo thống kê: {summary['warned_only']} • **sai nhưng báo thành công mà không có tín hiệu nào: {summary['silent_wrong']}**.",
        f"Báo nhầm (không đổi gì mà vẫn có thay đổi, hoặc kịch bản vô hại bị chặn): {summary['false_alarms']} • "
        f"thời gian phát hiện trung bình: {summary['mean_detect_seconds']} giây (đo sau khi áp thay đổi, trên dữ liệu thử nhỏ).",
        f"Đối chứng (không đổi gì): {ctl['false_alarms']} thay đổi, pipeline {PIPELINE_LABEL[ctl['pipeline']]}.",
        "",
        "| # | Kịch bản | Cấu trúc (mức: loại) | Thống kê | Chặn trước run | Pipeline chạy lại | Phát hiện (s) |",
        "|---|---|---|---|---|---|---|",
    ]
    for index, r in enumerate(rows, 1):
        pipeline = PIPELINE_LABEL[r["pipeline"]] + (f" — {r['pipeline_detail']}" if r["pipeline_detail"] else "")
        lines.append(
            f"| {index} | {r['title']} | {'<br>'.join(r['structure']) or '—'} | {', '.join(r['stats']) or '—'} | "
            f"{'có' if r['gate_blocks'] else 'không'} | {pipeline.replace('|', '/')} | {r['detect_seconds']} |"
        )
    lines += [
        "",
        "Ghi chú:",
        "- Kịch bản 6 (đổi đơn vị) không đổi cấu trúc: pipeline vẫn chạy xong với số khác. Hệ thống chỉ cảnh báo thống kê (`stat_new_shape`); đây là giới hạn đã nêu trong spec, cần người phán đoán.",
        '- "Chặn trước run" = có thay đổi `breaking` → `drift_gate` dừng run trước Planner. "Pipeline chạy lại" = lớp phòng thủ thứ hai nằm trong pipeline đã sinh (preflight `check_source_schema`, test nguồn, test ép kiểu).',
        "- Hệ thống phát hiện thay đổi, không ngăn được backend đổi; cần hợp đồng dữ liệu giữa các đội.",
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "drift.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / "drift.json").write_text(
        json.dumps({"summary": summary, "control": ctl, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    base = build_baseline()
    print("Pipeline gốc đạt V1 + V2.", flush=True)
    ctl = control(base)
    rows = []
    for scenario in SCENARIOS:
        row = run_scenario(base, scenario)
        rows.append(row)
        print(
            f"- {scenario.key}: chặn={row['gate_blocks']} pipeline={row['pipeline']} sai-im-lặng={row['silent_wrong']}",
            flush=True,
        )
    summary = summarize(rows, ctl)
    write_report(summary, rows, ctl)
    print(f"Đã ghi {RESULTS / 'drift.md'}: {summary}")


if __name__ == "__main__":
    main()

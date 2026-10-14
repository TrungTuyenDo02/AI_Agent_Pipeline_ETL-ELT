"""V2 Sandbox (code thuần): ghi file đã qua V1 vào workspace, chạy `dbt build` trên DuckDB local, đo kết quả."""

import logging
import re
from pathlib import Path

import duckdb

from src.agents.nodes.common import all_files, mart_path, register_failure, sandbox_db, spec_of
from src.agents.state import PipelineState
from src.agents.tools.dbt_tools import DbtResult, run_dbt_build, write_generated_files
from src.agents.tools.duckdb_tools import RAW_SCHEMA, connect_read
from src.agents.tools.pii import mask_rows
from src.agents.tools.sql_tools import SOURCE_RE, SqlCheckError, render_dbt_sql
from src.models.contracts import SandboxResult, hand_off
from src.services.connectors.base import normalize_type

logger = logging.getLogger(__name__)
SAMPLE_ROWS = 10


def failure_message(result: DbtResult) -> str:
    """Tóm tắt lỗi dbt: tối đa 3 model/test lỗi, hoặc cuối log nếu dbt dừng trước khi chạy."""
    if result.timed_out:
        return result.log_tail
    failed = [r for r in result.results if r.status not in ("success", "pass")]
    if failed:
        return "\n".join(f"{r.unique_id} [{r.status}]: {r.message}" for r in failed[:3])
    return result.log_tail or "dbt build thất bại không rõ lý do."


def mart_sample(db: Path, target: str) -> tuple[int, list[dict]]:
    """Số dòng và vài dòng đầu của bảng đích (đã che PII) — để người không rành SQL xem kết quả mẫu."""
    with connect_read(db) as con:
        rows = con.execute(f'SELECT count(*) FROM main."{target}"').fetchone()[0]
        rel = con.sql(f'SELECT * FROM main."{target}" LIMIT {SAMPLE_ROWS}')
        sample = [dict(zip(rel.columns, [str(v) for v in row], strict=True)) for row in rel.fetchall()]
    return rows, mask_rows(sample)


def reconcile_staging(db: Path, files: dict[str, str]) -> list[dict]:
    """Mục 9: số dòng VÀO (bảng raw) so với số dòng RA (model staging đọc đúng một nguồn), đo bằng code.

    Khác nhau = staging đã loại/nhân dòng; Reviewer phải thấy lý do (khử trùng, lọc theo đặc tả), không im lặng.
    """
    out = []
    with connect_read(db) as con:
        for path, sql in sorted(files.items()):
            sources = {m.group(2) for m in SOURCE_RE.finditer(sql)}
            if not path.startswith("models/staging/") or len(sources) != 1:
                continue
            source = sources.pop()
            try:
                rows_in = con.execute(f'SELECT count(*) FROM {RAW_SCHEMA}."{source}"').fetchone()[0]
                rows_out = con.execute(f"SELECT count(*) FROM ({render_dbt_sql(sql)})").fetchone()[0]
            except (duckdb.Error, SqlCheckError) as exc:
                logger.warning("reconcile failed", extra={"model": path, "error": str(exc)[:200]})
                continue
            model = re.sub(r"^.*/|\.sql$", "", path)
            out.append({"model": model, "source": source, "rows_in": rows_in, "rows_out": rows_out})
    return out


def type_mismatches(db: Path, spec) -> list[str]:  # noqa: ANN001 — PipelineSpec
    """Kiểu cột của bảng đích phải cùng nhóm kiểu với đặc tả (integer/decimal/float/string/boolean/date/timestamp). Thay cho hợp
    đồng mô hình dbt (`contract: enforced`): dbt-duckdb chưa ổn định với kiểu thập phân/thời gian, xem docs/adr/0010."""
    with connect_read(db) as con:
        rows = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'main' AND table_name = ?",
            [spec.target],
        ).fetchall()
    actual = {name.lower(): data_type for name, data_type in rows}
    issues = []
    for column in spec.output_columns:
        want, got = normalize_type(column.type), normalize_type(actual.get(column.name.lower(), ""))
        if want != "other" and got != "other" and want != got:
            issues.append(
                f"Cột {column.name} của bảng đích có kiểu {actual[column.name.lower()]} nhưng đặc tả yêu cầu {column.type}."
            )
    return issues


def _summary(result: DbtResult) -> dict:
    tests = [r for r in result.results if r.unique_id.startswith("test.")]
    models = [r for r in result.results if r.unique_id.startswith("model.")]
    return {
        "models_ok": sum(r.status == "success" for r in models),
        "models_total": len(models),
        "tests_ok": sum(r.status in ("pass", "warn") for r in tests),
        "tests_total": len(tests),
    }


def sandbox_run_node(state: PipelineState) -> dict:
    """Chạy dbt build; lỗi được ghi sổ lỗi và quay lại Codegen (tối đa N lần)."""
    workspace = Path(state["workspace"])
    write_generated_files(workspace, all_files(state))
    result = run_dbt_build(workspace)
    spec = spec_of(state)
    if not result.ok:
        message = failure_message(result)
        sandbox = hand_off(SandboxResult, {"passed": False, "error": message, **_summary(result)})
        return {"sandbox": sandbox, **register_failure(state, message, state["code_files"].get(mart_path(spec), ""))}
    if mismatched := type_mismatches(sandbox_db(state), spec):
        message = "\n".join(mismatched)
        sandbox = hand_off(SandboxResult, {"passed": False, "error": message, **_summary(result)})
        return {"sandbox": sandbox, **register_failure(state, message, state["code_files"].get(mart_path(spec), ""))}
    rows, sample = mart_sample(sandbox_db(state), spec.target)
    return {
        "sandbox": hand_off(
            SandboxResult, {"passed": True, "error": "", "target_rows": rows, "sample": sample, **_summary(result)}
        ),
        "reconciliation": reconcile_staging(sandbox_db(state), state.get("code_files", {})),
    }

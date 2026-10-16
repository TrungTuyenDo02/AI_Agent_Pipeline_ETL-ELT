"""Bản tối ưu đã áp dụng phải giống hệt bản gốc trên dữ liệu sandbox (V2 kiểm lại); lỗi/lệch → khôi phục bản gốc, không gọi Codegen."""

from pathlib import Path

import duckdb
import pytest

from src.agents import routing
from src.agents.graph import EDGES
from src.agents.nodes import compare
from src.agents.nodes.common import mart_path, spec_of
from src.agents.nodes.compare import compare_node, fingerprint_difference, mart_fingerprint
from src.agents.nodes.opt_revert import opt_revert_node
from src.agents.nodes.safety import safety_node
from src.agents.nodes.sandbox_run import optimized_output_issue, sandbox_run_node
from src.agents.tools.sql_tools import render_dbt_sql
from src.models.evidence import OptimizationReport, QueryMetrics


def _table(path: Path, rows: str) -> Path:
    with duckdb.connect(str(path)) as con:
        con.execute(f"CREATE TABLE main.fct AS SELECT * FROM (VALUES {rows}) v(k, amount, n)")
    return path


def test_fingerprint_ignores_row_order_and_float_noise_but_counts_duplicates(tmp_path: Path):
    base = mart_fingerprint(
        _table(tmp_path / "a.duckdb", "('x', 1.0::DOUBLE, 1), ('x', 1.0, 1), ('y', 0.0, NULL)"), "fct"
    )
    shuffled = mart_fingerprint(
        _table(tmp_path / "b.duckdb", "('y', -0.0000001::DOUBLE, NULL), ('x', 1.0000000001, 1), ('x', 1.0, 1)"), "fct"
    )
    deduped = mart_fingerprint(_table(tmp_path / "c.duckdb", "('x', 1.0::DOUBLE, 1), ('y', 0.0, NULL)"), "fct")
    changed = mart_fingerprint(
        _table(tmp_path / "d.duckdb", "('x', 1.0::DOUBLE, 1), ('x', 2.0, 1), ('y', 0.0, NULL)"), "fct"
    )
    assert base is not None and base["rows"] == 3
    assert fingerprint_difference(base, shuffled) == ""
    assert "số dòng" in fingerprint_difference(base, deduped)
    assert "khác nội dung" in fingerprint_difference(base, changed)
    assert "không đọc được" in fingerprint_difference(base, None)


def test_fingerprint_missing_table_or_file_is_none(tmp_path: Path):
    assert mart_fingerprint(tmp_path / "missing.duckdb", "fct") is None
    assert mart_fingerprint(_table(tmp_path / "a.duckdb", "('x', 1.0, 1)"), "other") is None


@pytest.mark.parametrize(
    ("fn", "state", "expected"),
    [
        (routing.after_safety, {"safety": {"passed": False}, "opt_baseline": {"code_files": {}}}, "opt_revert"),
        (routing.after_sandbox, {"sandbox": {"passed": False}, "opt_baseline": {"code_files": {}}}, "opt_revert"),
        (
            routing.after_sandbox,
            {"sandbox": {"passed": False}, "fix_attempts": 1, "error_signatures": ["a"]},
            "codegen",
        ),
    ],
)
def test_failed_optimization_reverts_instead_of_codegen(fn, state: dict, expected: str):
    assert fn(state) == expected


def test_revert_goes_back_through_v1_v2():
    assert ("opt_revert", "safety") in EDGES


def test_revert_restores_original_and_marks_skipped():
    state = {
        "code_files": {"models/marts/x.sql": "-- tối ưu"},
        "opt_baseline": {"code_files": {"models/marts/x.sql": "-- gốc"}, "fingerprint": {}},
        "optimization": {"decision": "applied", "reason": "Nhanh hơn 40%", "equivalence": [{"dataset": "small"}]},
        "sandbox": {"passed": False, "error": "Bản tối ưu (E4) cho kết quả khác bản gốc: khác số dòng: 3 ≠ 1."},
    }
    update = opt_revert_node(state)
    assert update["code_files"] == {"models/marts/x.sql": "-- gốc"} and update["opt_baseline"] == {}
    report = update["optimization"]
    assert report["decision"] == "skipped" and "khôi phục bản gốc" in report["reason"]
    assert report["equivalence"][-1]["dataset"] == "sandbox" and not report["equivalence"][-1]["equal"]
    assert "fix_attempts" not in update  # không tính vào lượt sửa của Codegen


def test_v2_reports_sandbox_difference_only_while_optimization_on_trial(tmp_path: Path):
    _table(tmp_path / "sandbox.duckdb", "('x', 1.0::DOUBLE, 1), ('y', 2.0, 2)")
    expected = mart_fingerprint(tmp_path / "sandbox.duckdb", "fct")
    state = {"workspace": str(tmp_path), "opt_baseline": {"fingerprint": expected}}
    assert optimized_output_issue(state, "fct") == ""
    assert optimized_output_issue({"workspace": str(tmp_path)}, "fct") == ""  # không thử tối ưu → không so
    lie = {**expected, "rows": 5}
    issue = optimized_output_issue({**state, "opt_baseline": {"fingerprint": lie}}, "fct")
    assert "khác bản gốc trên dữ liệu sandbox" in issue and "5 ≠ 2" in issue


def _applied(proposed_sql: str):
    """Thay V3 bằng quyết định `applied` cố định (không phụ thuộc thời gian đo)."""

    def evaluate(candidate: dict, datasets: dict[str, str]) -> OptimizationReport:
        metrics = QueryMetrics(median_ms=1.0, runs=1)
        return OptimizationReport(
            original_sql=proposed_sql, proposed_sql=proposed_sql, decision="applied", before=metrics, after=metrics
        )

    return evaluate


def test_compare_does_not_apply_without_sandbox_baseline(pipeline_state: dict, monkeypatch, tmp_path: Path):
    """Không chụp được bảng đích gốc trên sandbox → không kiểm lại được → không áp dụng."""
    monkeypatch.setattr(compare, "evaluate_candidate", _applied("select 1"))
    monkeypatch.setattr(compare, "sandbox_db", lambda state: tmp_path / "missing.duckdb")
    original = dict(pipeline_state["code_files"])
    update = compare_node({**pipeline_state, "opt_candidate": {"source": "rules"}})
    assert update["optimization"]["decision"] == "skipped" and "sandbox" in update["optimization"]["reason"]
    assert "code_files" not in update and "opt_baseline" not in update
    assert pipeline_state["code_files"] == original


def _through_v1_v2(state: dict) -> str:
    """Chạy V1 rồi V2 (nếu V1 đạt) như graph; trả bước kế tiếp."""
    state.update(safety_node(state))
    if (step := routing.after_safety(state)) != "sandbox_run":
        return step
    state.update(sandbox_run_node(state))
    return routing.after_sandbox(state)


def _sandboxed(pipeline_state: dict) -> tuple[dict, str]:
    assert _through_v1_v2(pipeline_state) == "optimizer"
    mart = mart_path(spec_of(pipeline_state))
    return pipeline_state, render_dbt_sql(pipeline_state["code_files"][mart])


def test_equivalent_optimization_is_confirmed_on_sandbox(pipeline_state: dict, monkeypatch):
    state, sql = _sandboxed(pipeline_state)
    monkeypatch.setattr(compare, "evaluate_candidate", _applied(sql))
    state.update(compare_node({**state, "opt_candidate": {"source": "rules"}}))
    assert state["opt_baseline"]["fingerprint"]["rows"] == state["sandbox"]["target_rows"]
    attempts = state.get("fix_attempts", 0)
    assert _through_v1_v2(state) == "package"
    assert state["opt_baseline"] == {} and state["optimization"]["decision"] == "applied"
    assert state["optimization"]["equivalence"][-1]["dataset"] == "sandbox"
    assert state.get("fix_attempts", 0) == attempts


def test_optimization_that_changes_sandbox_output_is_reverted(pipeline_state: dict, monkeypatch):
    state, sql = _sandboxed(pipeline_state)
    original = dict(state["code_files"])
    attempts, signatures = state.get("fix_attempts", 0), list(state.get("error_signatures", []))
    monkeypatch.setattr(compare, "evaluate_candidate", _applied(f"{sql}\nlimit 1"))
    state.update(compare_node({**state, "opt_candidate": {"source": "rules"}}))
    assert state["code_files"] != original
    assert _through_v1_v2(state) == "opt_revert"  # V1 hoặc V2 phát hiện; không quay về Codegen
    assert state.get("fix_attempts", 0) == attempts and state.get("error_signatures", []) == signatures
    state.update(opt_revert_node(state))
    assert state["code_files"] == original and state["optimization"]["decision"] == "skipped"
    assert _through_v1_v2(state) == "package"  # bản gốc chạy lại đạt, sandbox khớp code gốc
    assert state["sandbox"]["passed"] and state["opt_baseline"] == {}

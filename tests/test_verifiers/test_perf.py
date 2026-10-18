"""Đo hiệu năng (code thuần, 0 token): số đo từng model từ artifact dbt."""

import json
from pathlib import Path

import duckdb

from src.agents.nodes.package import package_node
from src.agents.review_gate import gate_problems, review_gate
from src.agents.tools.bottleneck import analyze_bottlenecks
from src.agents.tools.dbt_tools import read_archived_run, read_run_results
from src.agents.tools.duckdb_tools import explain_outline


def _write_artifacts(workspace: Path, invocation: str, results: list[dict]) -> None:
    target = workspace / "target"
    target.mkdir(parents=True, exist_ok=True)
    run = {"metadata": {"invocation_id": invocation, "dbt_version": "1.9.0"}, "elapsed_time": 1.5, "results": results}
    (target / "run_results.json").write_text(json.dumps(run), encoding="utf-8")
    nodes = {"model.p.fct": {"config": {"materialized": "table"}}}
    (target / "manifest.json").write_text(json.dumps({"metadata": {"adapter_type": "duckdb"}, "nodes": nodes}), "utf-8")


def _timing(phase: str, start: str, end: str) -> dict:
    return {"name": phase, "started_at": f"2026-10-18T00:00:{start}Z", "completed_at": f"2026-10-18T00:00:{end}Z"}


def test_run_results_partial_failure_keeps_measured_models(tmp_path: Path):
    ok = {
        "unique_id": "model.p.fct",
        "status": "success",
        "timing": [_timing("compile", "00.000", "00.100"), _timing("execute", "00.100", "00.350")],
        "adapter_response": {"rows_affected": 42},
        "compiled_code": "select 1",
    }
    failed = {"unique_id": "model.p.other", "status": "error", "message": "boom", "timing": []}
    _write_artifacts(tmp_path, "inv-1", [ok, failed])
    run = read_run_results(tmp_path)
    fct, other = run.results
    assert (fct.compile_ms, fct.execute_ms, fct.rows, fct.materialized) == (100.0, 250.0, 42, "table")
    assert (other.status, other.execute_ms, other.rows) == ("error", None, None)  # lỗi: không bịa số đo
    assert run.invocation_id == "inv-1" and run.elapsed_ms == 1500.0
    # Lần dbt sau không ghi đè số đo lần trước
    _write_artifacts(tmp_path, "inv-2", [{**ok, "timing": []}])
    read_run_results(tmp_path)
    assert read_archived_run(tmp_path, "inv-1")["results"][0]["execute_ms"] == 250.0
    assert read_archived_run(tmp_path, "inv-1")["results"][0]["sql"] == "select 1"
    assert read_archived_run(tmp_path, "inv-2")["results"][0]["execute_ms"] is None
    assert read_archived_run(tmp_path, "missing") == {}


def test_run_results_missing_returns_empty(tmp_path: Path):
    run = read_run_results(tmp_path)
    assert run.results == [] and run.invocation_id == "" and run.elapsed_ms is None


def _bench(tmp_path: Path) -> tuple[Path, dict]:
    """Sandbox giả: 3 model, `slow_range` nối theo khoảng (điểm nghẽn đã biết), số đo dbt khớp thứ tự đó."""
    db = tmp_path / "sandbox.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("create table t as select range as i, range % 7 as g from range(3000)")
    sql = {
        "slow_range": "select a.g, count(*) as n from t a join t b on a.i < b.i and a.g = 3 group by a.g",
        "agg": "select g, sum(i) as s from t where i > 100 group by g",
        "tiny": "select 1 as x",
    }
    results = [{"unique_id": f"model.p.{m}", "status": "success", "sql": q} for m, q in sql.items()]
    (tmp_path / "target" / "runs").mkdir(parents=True)
    (tmp_path / "target" / "runs" / "inv.json").write_text(json.dumps({"results": results}), encoding="utf-8")
    timings = [{"model": "tiny", "execute_ms": 1.0}, {"model": "slow_range", "execute_ms": 90.0}]
    timings.append({"model": "agg", "execute_ms": 9.0})
    return db, {"dbt_invocation": "inv", "model_timings": timings, "wall_ms": 70.0}


def test_bottleneck_report_finds_known_model_and_operator(tmp_path: Path):
    db, sandbox = _bench(tmp_path)
    report = analyze_bottlenecks(tmp_path, db, sandbox, top_n=2, budget_sec=30)
    assert report.measured and report.top_n == 2 and len(report.findings) == 2
    first = report.findings[0]
    assert (first.rank, first.model, first.analyzed) == (1, "slow_range", True)
    assert "JOIN" in first.operator and first.hypothesis and first.next_step and first.unknown
    assert (
        report.model_total_ms == 100.0 and report.dbt_wall_ms == 70.0 and report.dag_wall_ms is None
    )  # hai con số tách biệt, không cộng dồn
    assert report.analysis_ms > 0
    text = json.dumps(report.model_dump(), ensure_ascii=False)
    assert "'3'" not in text and "a.g = 3" not in text and "i > 100" not in text  # không mang hằng số/SQL vào báo cáo


def test_bottleneck_report_degrades_without_failing(tmp_path: Path):
    db, sandbox = _bench(tmp_path)
    assert analyze_bottlenecks(tmp_path, db, {}, top_n=3, budget_sec=5).measured is False  # "chưa đo"
    timed_out = analyze_bottlenecks(tmp_path, db, sandbox, top_n=3, budget_sec=0)
    assert [f.analyzed for f in timed_out.findings] == [False, False, False]
    assert "hết thời gian" in timed_out.findings[0].unknown
    broken = tmp_path / "target" / "runs" / "inv.json"
    broken.write_text(
        json.dumps({"results": [{"unique_id": "model.p.slow_range", "sql": "select nope from t"}]}), "utf-8"
    )
    report = analyze_bottlenecks(tmp_path, db, sandbox, top_n=2, budget_sec=5)
    assert report.findings[0].analyzed is False and "Chưa phân tích được" in report.findings[0].unknown
    assert "không còn SQL" in report.findings[1].unknown


def test_explain_outline_masks_literals_before_llm(tmp_path: Path):
    db, _ = _bench(tmp_path)
    text = explain_outline(db, "select g from t where i > 1234 and g = 5")
    assert "1234" not in text and "?" in text and "rows=" in text


def _passed_state(tmp_path: Path) -> dict:
    db, sandbox = _bench(tmp_path)
    sandbox.update({"passed": True, "models_ok": 3, "models_total": 3, "tests_ok": 4, "tests_total": 4})
    return {
        "workspace": str(tmp_path),
        "sandbox": sandbox,
        "safety": {"passed": True, "issues": []},
        "code_files": {"dags/x.py": "", "models/marts/m.sql": ""},
        "test_files": {"tests/assert_m.sql": ""},
        "optimization": {"original_sql": "select 1", "decision": "skipped", "reason": "giữ nguyên"},
    }


def test_review_gate_three_states(tmp_path: Path):
    state = _passed_state(tmp_path)
    gate = review_gate(state)
    assert gate.passed and gate_problems(state) == [] and len(gate.checks) == 4
    assert {c.id: c.status for c in gate.extra} == {"airflow_run": "unverified", "optimization": "passed"}
    empty = review_gate({})  # checkpoint cũ/thiếu bằng chứng: chưa kiểm chứng, không tự coi là đạt
    assert not empty.passed and {c.status for c in empty.checks} == {"unverified"}
    failing = {**state, "sandbox": {**state["sandbox"], "tests_ok": 3}}
    assert [c.id for c in review_gate(failing).checks if c.status == "failed"] == ["dbt_tests"]
    assert "3/4 test đạt" in gate_problems(failing)[0]
    no_dag = {**state, "code_files": {"models/marts/m.sql": ""}}
    assert {c.id: c.status for c in review_gate(no_dag).checks}["dag"] == "failed"
    no_tests = {**state, "test_files": {}}
    assert {c.id: c.status for c in review_gate(no_tests).checks}["expected"] == "failed"
    no_safety = {k: v for k, v in state.items() if k != "safety"}
    assert {c.id: c.status for c in review_gate(no_safety).checks}["dag"] == "unverified"
    applied = {**state, "optimization": {**state["optimization"], "decision": "applied", "equivalence": []}}
    assert {c.id: c.status for c in review_gate(applied).extra}["optimization"] == "unverified"
    assert review_gate(applied).passed  # bổ sung không chặn duyệt


def test_package_attaches_bottlenecks_and_separates_measured_from_unverified(tmp_path: Path):
    update = package_node({**_passed_state(tmp_path), "spec": {}, "request_text": "x"})
    perf = update["optimization"]["bottlenecks"]
    assert perf["measured"] and perf["findings"][0]["model"] == "slow_range"
    assert update["optimization"]["decision"] == "skipped"  # không có bản sửa vẫn có báo cáo
    measured = {(m["node"], m["check"]): m for m in update["evidence"]["measured"]}
    assert measured[("Đo hiệu năng", "Tổng thời gian các model")]["result"] == "100.0 ms"
    assert measured[("Đo hiệu năng", "Thời gian lệnh dbt build")]["result"] == "70.0 ms"
    assert measured[("Đo hiệu năng", "Thời gian toàn DAG (Airflow)")]["result"] == "chưa đo"
    assert all(m["passed"] for (node, _), m in measured.items() if node == "Kiểm tra bắt buộc")
    assert [m["passed"] for m in update["evidence"]["measured"] if m["node"] == "Kiểm tra bắt buộc"] == [True] * 4
    airflow = measured[("Bổ sung", "Airflow chạy thật trên sandbox, chạy lại không nhân đôi dữ liệu")]
    assert airflow["result"].startswith("Chưa kiểm chứng") and airflow["passed"] is None
    assert not any(perf["findings"][0]["hypothesis"] in m["result"] for m in update["evidence"]["measured"])


def test_package_without_timings_says_not_measured(tmp_path: Path):
    state = {**_passed_state(tmp_path), "spec": {}, "request_text": "x"}
    state["sandbox"] = {k: v for k, v in state["sandbox"].items() if k not in ("model_timings", "dbt_invocation")}
    update = package_node(state)
    assert update["optimization"]["bottlenecks"]["measured"] is False
    assert any(m["result"] == "chưa đo" for m in update["evidence"]["measured"])

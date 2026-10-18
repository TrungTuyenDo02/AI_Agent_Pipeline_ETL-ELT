"""Test E4 Optimizer + V3 Đối chiếu: tối ưu thành công, bị loại vì lệch kết quả, `skipped` do lợi ích nhỏ."""

from pathlib import Path

import duckdb
import pytest

from src.agents.nodes.compare import compare_node, compare_results, decide, evaluate_candidate
from src.agents.nodes.optimizer import OptimizeJob, optimize_standalone, optimizer_node, prepare_datasets
from src.agents.tools.duckdb_tools import QueryResult
from src.models.evidence import QueryMetrics

ORIGINAL = "with u as (select * from raw.a union select * from raw.b) select k, sum(v) as total from u group by k"


def _result(rows: list[tuple], types: list[str] | None = None) -> QueryResult:
    return QueryResult(columns=["k", "v"], types=types or ["VARCHAR", "DOUBLE"], rows=rows)


@pytest.fixture
def datasets(tmp_path: Path) -> dict[str, str]:
    """Các bộ dữ liệu nhỏ có hai bảng a, b không trùng dòng giữa nhau."""
    paths = {}
    for name, n in {"small": 50, "dirty": 30, "empty": 0, "few": 3, "dupkeys": 40, "large": 50000}.items():
        paths[name] = str(tmp_path / f"{name}.duckdb")
        with duckdb.connect(paths[name]) as con:
            con.execute("CREATE SCHEMA raw")
            con.execute(f"CREATE TABLE raw.a AS SELECT 'a' || (i % 97) AS k, i * 1.5 AS v FROM range({n}) t(i)")
            con.execute(f"CREATE TABLE raw.b AS SELECT 'b' || (i % 89) AS k, i * 2.0 AS v FROM range({n}) t(i)")
    return paths


def test_compare_results_ignores_row_order_and_small_float_noise():
    equal, _ = compare_results(_result([("x", 1.0), ("y", 2.0)]), _result([("y", 2.0000000001), ("x", 1.0)]), 1e-6)
    assert equal


@pytest.mark.parametrize(
    ("other", "message"),
    [
        (_result([("x", 1.0), ("z", 2.0)]), "chỉ có ở bản gốc"),
        (_result([("x", 1.0)]), "số dòng"),
        (_result([("x", 1.0), ("y", 2.0)], ["VARCHAR", "BIGINT"]), "kiểu cột"),
        (QueryResult(columns=["k", "w"], types=["VARCHAR", "DOUBLE"], rows=[("x", 1.0), ("y", 2.0)]), "cột"),
    ],
)
def test_compare_results_detects_differences(other: QueryResult, message: str):
    equal, detail = compare_results(_result([("x", 1.0), ("y", 2.0)]), other, 1e-6)
    assert not equal and message in detail.lower()


@pytest.mark.parametrize(
    ("before", "after", "cost", "spread", "decision"),
    [
        (100.0, 50.0, 0.0, 2.0, "applied"),
        (100.0, 95.0, 0.0, 2.0, "skipped"),
        (100.0, 50.0, 1000.0, 2.0, "skipped"),
        (100.0, 50.0, 0.0, None, "skipped"),  # thiếu IQR: không đủ bằng chứng kết luận nhanh hơn
        (100.0, 50.0, 0.0, 60.0, "skipped"),  # chênh lệch nằm trong độ phân tán đo được
    ],
)
def test_decide_gate(before: float, after: float, cost: float, spread: float | None, decision: str):
    metrics = [QueryMetrics(median_ms=ms, runs=3, spread_ms=spread) for ms in (before, after)]
    result, reason, gain = decide(*metrics, cost)
    assert result == decision and reason
    assert gain == pytest.approx(100 * (before - after) / before, abs=0.1)


def _candidate(sql: str, before_ms: float) -> dict:
    before = {"median_ms": before_ms, "runs": 3, "spread_ms": 0.0}
    return {"original_sql": ORIGINAL, "sql": sql, "before": before, "attempt": 1}


def test_benchmark_reports_peak_memory(datasets: dict[str, str]):
    from src.agents.tools.duckdb_tools import benchmark_query

    metrics = benchmark_query(Path(datasets["large"]), ORIGINAL, runs=2)
    assert metrics.median_ms > 0 and metrics.runs == 2
    assert metrics.peak_memory_mb is not None and metrics.peak_memory_mb > 0
    assert metrics.spread_ms is not None and metrics.spread_ms >= 0  # IQR = Q3 − Q1
    assert benchmark_query(Path(datasets["small"]), ORIGINAL, runs=1).spread_ms is None  # 1 lần đo: chưa đo được IQR


def _paired(monkeypatch: pytest.MonkeyPatch, before_ms: float, after_ms: float) -> list[tuple]:
    """Cố định kết quả đo xen kẽ (logic quyết định, không phụ thuộc tốc độ máy); ghi lại câu nào được đo."""
    calls: list[tuple] = []

    def fake(db: Path, first: str, second: str, runs: int):
        calls.append((first, second))
        return (QueryMetrics(median_ms=before_ms, runs=runs, spread_ms=1.0),
                QueryMetrics(median_ms=after_ms, runs=runs, spread_ms=1.0))  # fmt: skip

    monkeypatch.setattr("src.agents.nodes.compare.benchmark_pair", fake)
    return calls


def test_equivalent_rewrite_is_measured_and_decided(datasets: dict[str, str], monkeypatch: pytest.MonkeyPatch):
    rewrite = ORIGINAL.replace(" union ", " union all ")
    calls = _paired(monkeypatch, 100.0, 10.0)
    report = evaluate_candidate(_candidate(rewrite, before_ms=999.0), datasets)
    assert all(c.equal for c in report.equivalence) and len(report.equivalence) == 5
    assert report.decision == "applied" and report.after is not None
    assert calls == [(ORIGINAL, rewrite)]  # bản gốc và bản sửa đo cùng phiên
    assert report.before.median_ms == 100.0  # dùng số đo cùng phiên, không dùng số đo bản gốc của lượt đầu (999)


def test_benchmark_pair_measures_both_in_same_session(datasets: dict[str, str]):
    from src.agents.tools.duckdb_tools import benchmark_pair

    before, after = benchmark_pair(
        Path(datasets["large"]), ORIGINAL, ORIGINAL.replace(" union ", " union all "), runs=4
    )
    assert before.runs == after.runs == 4 and before.median_ms > 0 and after.median_ms > 0
    assert before.spread_ms is not None and after.spread_ms is not None


def test_rewrite_with_different_result_is_rejected(datasets: dict[str, str]):
    wrong = ORIGINAL.replace("sum(v)", "avg(v)")
    report = evaluate_candidate(_candidate(wrong, before_ms=1e6), datasets)
    assert report.decision == "skipped" and "lệch" in report.reason
    assert report.after is None  # không đo tốc độ khi kết quả đã lệch


FILTERED = "select k, sum(v) as total from raw.a where v > 3 group by k"
TWICE = "select k, count(*) as n from (select k from raw.a union all select k from raw.a) t group by k"


@pytest.mark.parametrize(
    ("original", "wrong"),
    [
        (FILTERED, FILTERED.replace("v > 3", "v >= 3")),  # đổi toán tử so sánh
        (FILTERED, FILTERED.replace(" where v > 3", "")),  # bỏ điều kiện lọc
        (TWICE, TWICE.replace("from (select k", "from (select distinct k from (select k").replace(") t", ")) t")),
    ],
    ids=["comparison_operator", "dropped_filter", "added_distinct"],
)
def test_deliberately_wrong_rewrite_is_rejected_and_original_kept(datasets: dict[str, str], original: str, wrong: str):
    report = evaluate_candidate({**_candidate(wrong, before_ms=1e6), "original_sql": original}, datasets)
    assert report.decision == "skipped" and "lệch" in report.reason and report.original_sql == original
    assert any(not c.equal for c in report.equivalence)


def test_small_gain_is_skipped(datasets: dict[str, str], monkeypatch: pytest.MonkeyPatch):
    _paired(monkeypatch, 100.0, 95.0)
    report = evaluate_candidate(_candidate(ORIGINAL.replace(" union ", " union all "), before_ms=1e6), datasets)
    assert report.decision == "skipped" and "ngưỡng" in report.reason


def test_applied_rule_ships_assumptions_as_dbt_tests():
    from src.agents.nodes.compare import assumption_tests

    candidate = {
        "assumptions": [
            {
                "text": "raw.a không\ntrùng dòng",
                "check_sql": "SELECT count(*) FROM raw.a WHERE k IN (SELECT k FROM main.stg_b)",
            },
            {"text": "không có câu kiểm", "check_sql": ""},
        ]
    }
    tests = assumption_tests(candidate, ["stg_b"])
    assert list(tests) == ["tests/assert_opt_assumption_1.sql"]  # giả định không có câu kiểm thì không sinh test rỗng
    sql = tests["tests/assert_opt_assumption_1.sql"]
    assert "{{ source('raw', 'a') }}" in sql and "{{ ref('stg_b') }}" in sql and "raw.a" not in sql.split("\n", 1)[1]
    assert "where violations <> 0" in sql and "không trùng dòng" in sql  # dbt test: có dòng = vi phạm = lỗi
    from src.agents.nodes.safety import check_sql

    catalog = {"raw": {"a": {"k": "VARCHAR"}}, "main": {"stg_b": {"k": "VARCHAR"}}}
    assert check_sql(sql, catalog)[0] == []  # test sinh ra qua được V1 (như mọi file tests/)


def test_identical_proposal_is_skipped_without_benchmark(datasets: dict[str, str]):
    reformatted = "\n  ".join(ORIGINAL.split(" "))  # chỉ khác xuống dòng/thụt lề
    report = evaluate_candidate(_candidate(reformatted, before_ms=1e6), datasets)
    assert report.decision == "skipped" and "không đề xuất" in report.reason and report.after is None


def test_invalid_candidate_is_skipped(datasets: dict[str, str]):
    report = evaluate_candidate({**_candidate("drop table raw.a", 1.0), "invalid": "Lệnh DROP bị chặn"}, datasets)
    assert report.decision == "skipped" and not report.equivalence[0].equal


def test_optimize_standalone_tries_deterministic_sources_before_llm(datasets: dict[str, str]):
    report, usages = optimize_standalone(OptimizeJob(sql=ORIGINAL, datasets=datasets))
    assert {f.rule for f in report.findings} >= {"select_star", "union_distinct"}
    assert report.attempts >= 1 and report.proposed_sql
    if report.decision == "applied":
        assert all(c.equal for c in report.equivalence)
    if usages:  # chỉ gọi LLM khi luật/sqlglot không cho ứng viên đạt
        assert usages[0].simulated and report.attempts >= 2


def test_rule_candidate_wins_without_llm(datasets: dict[str, str]):
    sql = "select count(*) as n from (select * from raw.a union select * from raw.a) as x"
    report, usages = optimize_standalone(OptimizeJob(sql=sql, datasets=datasets))
    assert report.explanation.startswith("[rules]") or usages  # luật luôn được thử trước
    if report.explanation.startswith("[rules]"):
        assert any(c.dataset.startswith("giả định") and c.equal for c in report.equivalence)


def test_false_assumption_rejects_rule_candidate(datasets: dict[str, str]):
    from src.agents.nodes.compare import evaluate_candidate as evaluate

    with duckdb.connect(datasets["dirty"]) as con:
        con.execute("INSERT INTO raw.a SELECT * FROM raw.a LIMIT 2")  # bộ dirty có dòng trùng
    candidate = {
        **_candidate("select count(*) from raw.a", before_ms=1e6),
        "original_sql": "select count(*) from (select distinct * from raw.a) as x",
        "assumptions": [
            {
                "text": "raw.a không trùng dòng",
                "check_sql": "select (select count(*) from raw.a) - (select count(*) from (select distinct * from raw.a))",
            }
        ],
    }
    report = evaluate(candidate, datasets)
    assert report.decision == "skipped"  # hoặc lệch kết quả, hoặc giả định sai — không bao giờ được áp dụng
    assert any(not c.equal for c in report.equivalence)


def test_optimize_standalone_skips_clean_query(datasets: dict[str, str]):
    report, usages = optimize_standalone(OptimizeJob(sql="select k from raw.a group by k", datasets=datasets))
    assert report.decision == "skipped" and usages == []


def test_optimizer_and_compare_nodes_loop_until_decision(pipeline_state: dict):
    sources = []
    for _ in range(3):
        update = optimizer_node(pipeline_state)
        candidate = update["opt_candidate"]
        assert candidate["before"]["median_ms"] > 0
        sources.append(candidate["source"])
        pipeline_state.update(update)
        result = compare_node(pipeline_state)
        pipeline_state.update(result)
        if "optimization" in result:
            break
    report = pipeline_state["optimization"]
    assert report["decision"] in ("applied", "skipped")
    assert sources[-1] == "llm" or sources[0] in ("rules", "sqlglot")
    if report["decision"] == "applied":
        assert all(c["equal"] for c in report["equivalence"])
        assert "{{ ref('stg_shopee_orders') }}" in pipeline_state["code_files"]["models/marts/fct_daily_revenue.sql"]


def test_compare_node_sends_rejection_back_to_optimizer(pipeline_state: dict, mock_llm, monkeypatch):
    from src.agents.nodes import optimizer

    monkeypatch.setattr(optimizer, "DETERMINISTIC_SOURCES", {})
    mock_llm("optimizer", {"sql": "select order_date, 0 as order_count, 0 as revenue_vnd from main.stg_tiki_orders"})
    prepare_datasets(pipeline_state)
    pipeline_state.update(optimizer_node(pipeline_state))
    result = compare_node(pipeline_state)
    assert "optimization" not in result
    assert "lệch" in result["opt_candidate"]["feedback"] and result["opt_candidate"]["history"]


def test_optimizer_provider_outage_keeps_original_instead_of_failing_run(datasets: dict[str, str], monkeypatch):
    """Nhà cung cấp optimizer quá hạn/lỗi/đang ngắt mạch: bỏ qua tối ưu, giữ bản gốc, lần chạy không FAILED."""
    from src.agents.nodes import optimizer
    from src.services.llm import LLMCallError

    def outage(task: str, variables: dict[str, str]):
        raise LLMCallError("Nhà cung cấp anthropic/claude-haiku-5-5 đang tạm ngắt vì nhiều lần lỗi liên tiếp.")

    monkeypatch.setattr(optimizer, "call_llm", outage)
    job = optimizer.ProposalInput(sql=ORIGINAL, findings=[], bench_db=datasets["small"])
    candidate, usage = optimizer.llm_rewrite(job)
    assert usage is None and "tạm ngắt" in candidate["invalid"]
    report = evaluate_candidate({**candidate, "original_sql": ORIGINAL, "attempt": 1}, datasets)
    assert report.decision == "skipped"


def test_missing_optimizer_key_keeps_original_instead_of_failing_run(datasets: dict[str, str], monkeypatch):
    """Optimizer dùng Anthropic mà chưa có ANTHROPIC_API_KEY: ứng viên bị loại kèm lý do, lần chạy không dừng."""
    from src.agents.nodes import optimizer
    from src.services.llm import LLMConfigError

    def missing_key(task: str, variables: dict[str, str]):
        raise LLMConfigError("Bước 'optimizer' dùng Anthropic nhưng chưa có ANTHROPIC_API_KEY.")

    monkeypatch.setattr(optimizer, "call_llm", missing_key)
    job = optimizer.ProposalInput(sql=ORIGINAL, findings=[], bench_db=datasets["small"])
    candidate, usage = optimizer.llm_rewrite(job)
    assert usage is None and "ANTHROPIC_API_KEY" in candidate["invalid"]
    report = evaluate_candidate({**candidate, "original_sql": ORIGINAL, "attempt": 1}, datasets)
    assert report.decision == "skipped"


# ---- Tín hiệu điểm nghẽn (bằng chứng thực thi) khi sqlglot không thấy mẫu ----
RANGE_JOIN = "select b.band, count(*) as n from raw.orders o join raw.bands b on o.amount >= b.lo and o.amount < b.hi group by b.band"
FANOUT_JOIN = (
    "select c.city, sum(o.amount) / count(distinct c.version) as revenue "
    "from raw.orders o join raw.customers c on o.customer_id = c.customer_id group by c.city"
)
CLEAN = "select status, sum(amount) as revenue from raw.orders group by status"


def _exec_db(path: Path, rows: int) -> str:
    """Dữ liệu giống eval/benchmarks/perf: đơn hàng, dải giá (nối theo khoảng), khách nhiều phiên bản (nối nhân dòng)."""
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE SCHEMA raw")
        con.execute(
            "CREATE TABLE raw.orders AS SELECT range AS order_id, range % 5000 AS customer_id, "
            f"round((range * 7919) % 100000 / 100.0, 2) AS amount, ['paid', 'pending'][range % 2 + 1] AS status FROM range({rows})"
        )
        con.execute(
            "CREATE TABLE raw.bands AS SELECT range * 10.0 AS lo, (range + 1) * 10.0 AS hi, 'B' || range AS band FROM range(100)"
        )
        con.execute(
            "CREATE TABLE raw.customers AS SELECT range % 5000 AS customer_id, 'C' || (range % 40) AS city, "
            "range // 5000 AS version FROM range(100000)"
        )
    return str(path)


@pytest.fixture(scope="module")
def exec_dbs(tmp_path_factory) -> dict[str, str]:
    root = tmp_path_factory.mktemp("exec")
    return {"small": _exec_db(root / "small.duckdb", 3000), "large": _exec_db(root / "large.duckdb", 300_000)}


def test_execution_findings_catch_missed_patterns_but_not_clean_query(exec_dbs: dict[str, str]):
    from src.agents.tools.bottleneck import execution_findings
    from src.agents.tools.slow_patterns import detect_slow_patterns

    large = Path(exec_dbs["large"])
    assert detect_slow_patterns(RANGE_JOIN) == [] and detect_slow_patterns(FANOUT_JOIN) == []  # hai ca sqlglot bỏ sót
    assert [f.rule for f in execution_findings(large, RANGE_JOIN, 10, 30)] == ["exec_non_equi_join"]
    fanout = {f.rule: f.message for f in execution_findings(large, FANOUT_JOIN, 10, 30)}
    assert "exec_join_fanout" in fanout and "không thêm DISTINCT" in fanout["exec_join_fanout"]
    assert "không mặc định sai nghiệp vụ" in fanout["exec_join_fanout"]
    assert execution_findings(large, CLEAN, 10, 30) == []  # đối chứng: không có mẫu cụ thể
    assert execution_findings(large, RANGE_JOIN, 1e9, 30) == []  # chạy nhanh hơn ngưỡng: không tối ưu hàng loạt
    assert execution_findings(Path(exec_dbs["small"]), RANGE_JOIN, 100, 30) == []  # dữ liệu nhỏ, dưới ngưỡng mặc định
    assert execution_findings(large, "select nope from raw.orders", 0, 30) == []  # lỗi: giữ luồng cũ


def test_matching_timing_requires_same_model_sql_version_and_top_n(tmp_path: Path):
    import json

    from src.agents.tools.bottleneck import matching_timing
    from src.agents.tools.dbt_tools import source_sha

    runs = tmp_path / "target" / "runs"
    runs.mkdir(parents=True)
    results = [{"unique_id": "model.p.m", "source_sha": source_sha("select 1\n")}, {"unique_id": "model.p.d"}]
    (runs / "inv.json").write_text(json.dumps({"results": results}), encoding="utf-8")
    sandbox = {
        "dbt_invocation": "inv",
        "model_timings": [{"model": "m", "execute_ms": 90.0}, {"model": "d", "execute_ms": 5.0}],
    }
    assert matching_timing(tmp_path, sandbox, "m", "select 1\r\n", 3) == 90.0  # cùng SQL (khác xuống dòng)
    assert matching_timing(tmp_path, sandbox, "m", "select 2", 3) is None  # lệch phiên bản SQL
    assert matching_timing(tmp_path, sandbox, "d", "select 1", 3) is None  # không có dấu phiên bản
    slower = {**sandbox, "model_timings": [*sandbox["model_timings"], {"model": "x", "execute_ms": 500.0}]}
    assert matching_timing(tmp_path, slower, "m", "select 1", 1) is None  # không trong top N
    assert matching_timing(tmp_path, {**sandbox, "dbt_invocation": "khac"}, "m", "select 1", 3) is None  # thiếu báo cáo
    assert matching_timing(tmp_path, {}, "m", "select 1", 3) is None


def test_signal_lets_optimizer_investigate_and_keeps_all_checks(exec_dbs: dict[str, str]):
    from src.agents.tools.bottleneck import execution_findings

    skipped, _ = optimize_standalone(OptimizeJob(sql=RANGE_JOIN, datasets=exec_dbs))
    assert skipped.decision == "skipped" and "Không phát hiện" in skipped.reason  # luồng cũ: bỏ sót
    signals = execution_findings(Path(exec_dbs["large"]), RANGE_JOIN, 10, 30)
    report, _ = optimize_standalone(OptimizeJob(sql=RANGE_JOIN, datasets=exec_dbs, signals=signals))
    assert "Không phát hiện" not in report.reason and [f.rule for f in report.findings] == ["exec_non_equi_join"]
    if report.decision == "applied":  # áp dụng thì vẫn qua đủ đối chiếu kết quả trên mọi bộ
        assert report.equivalence and all(c.equal for c in report.equivalence)
    clean, usages = optimize_standalone(OptimizeJob(sql=CLEAN, datasets=exec_dbs, signals=[]))
    assert clean.decision == "skipped" and usages == []


def test_optimizer_node_keeps_old_flow_without_matching_report(pipeline_state: dict):
    from src.agents.nodes.optimizer import execution_signal

    sql = "select 1 as x"
    assert execution_signal({**pipeline_state, "sandbox": {}}, sql) == []  # checkpoint cũ / chưa có số đo
    stale = {"dbt_invocation": "khong-co", "model_timings": [{"model": "fct_daily_revenue", "execute_ms": 1e6}]}
    assert execution_signal({**pipeline_state, "sandbox": stale}, sql) == []  # không có báo cáo khớp phiên bản

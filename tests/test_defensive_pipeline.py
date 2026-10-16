"""Pipeline sinh ra phải tự phòng thủ trước thay đổi cấu trúc nguồn (CLAUDE.md bản 2, 5.5 và 5.7).

Sáu kịch bản "backend đổi không báo" (scripts/simulate_drift.py) chạy lại CHÍNH pipeline đã sinh trong sandbox: hoặc fail sớm có
thông báo rõ, hoặc vẫn đúng (thay đổi vô hại); không bao giờ cho kết quả sai mà báo thành công mà không có tín hiệu nào.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest
import yaml

from src.agents.nodes.safety import safety_node
from src.agents.nodes.sandbox_run import type_mismatches
from src.agents.tools.sql_tools import select_star_issues

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import simulate_drift as sim  # noqa: E402

MART = "models/marts/fct_daily_revenue.sql"


# ---------- Luật tĩnh của V1 ----------


@pytest.mark.parametrize(
    ("sql", "flagged"),
    [
        ("select * from {{ ref('stg_a') }}", True),
        ("select t.* from {{ ref('stg_a') }} t", True),
        ("with x as (select * from {{ ref('stg_a') }}) select a from x", True),  # SELECT * trong CTE cũng bị chặn
        ("select a, b from {{ ref('stg_a') }}", False),
        ("select count(*) as n from {{ ref('stg_a') }}", False),
        ("select a from {{ ref('stg_a') }} where exists (select 1 from {{ ref('stg_b') }})", False),
    ],
)
def test_select_star_rule(sql: str, flagged: bool):
    assert bool(select_star_issues(sql)) is flagged


def test_v1_rejects_select_star_in_mart_and_staging(pipeline_state: dict):
    pipeline_state["code_files"][MART] = pipeline_state["code_files"][MART].replace(
        "select source, order_id, order_date, status, amount_vnd\n    from all_orders", "select *\n    from all_orders"
    )
    issues = safety_node(pipeline_state)["safety"]["issues"]
    assert any("SELECT *" in i for i in issues), issues


def test_v1_rejects_dag_without_preflight_first(pipeline_state: dict):
    dag = next(path for path in pipeline_state["code_files"] if path.startswith("dags/"))
    pipeline_state["code_files"][dag] = pipeline_state["code_files"][dag].replace(
        "preflight >> build_models >> run_tests", "build_models >> run_tests"
    )
    issues = safety_node(pipeline_state)["safety"]["issues"]
    assert any("check_source_schema" in i for i in issues), issues


def test_v1_requires_cast_failure_tests(pipeline_state: dict):
    cast_tests = [p for p in pipeline_state["test_files"] if p.endswith("_castable.sql")]
    assert cast_tests, "mỗi cột ngày/tiền đọc bằng biểu thức ép kiểu phải có test đếm dòng không ép được"
    for path in cast_tests:
        pipeline_state["test_files"].pop(path)
    issues = safety_node(pipeline_state)["safety"]["issues"]
    assert any("Thiếu test ép kiểu" in i for i in issues), issues


def test_clean_pipeline_passes_v1(pipeline_state: dict):
    assert safety_node(pipeline_state)["safety"] == {"passed": True, "issues": []}


# ---------- Khai báo nguồn dbt (sources.yml) ----------


def test_sources_yml_declares_columns_types_and_tests(built_state: dict):
    doc = yaml.safe_load((Path(built_state["workspace"]) / "models" / "sources.yml").read_text(encoding="utf-8"))
    tables = {t["name"]: t for t in doc["sources"][0]["tables"]}
    shopee = {c["name"]: c for c in tables["shopee_orders"]["columns"]}
    assert shopee["total_amount"]["data_type"] and shopee["order_id"]["data_tests"]
    assert "unique" in shopee["order_id"]["data_tests"] or "not_null" in shopee["order_id"]["data_tests"]
    assert set(tables) == {"shopee_orders", "tiki_orders", "website_orders"}


def test_preflight_macro_ships_with_template():
    macro = Path(__file__).resolve().parents[1] / "pipelines" / "template" / "macros" / "check_source_schema.sql"
    text = macro.read_text(encoding="ascii")  # dbt đọc theo bảng mã của hệ điều hành: giữ ASCII
    assert "macro check_source_schema" in text and "P113_SOURCE_SCHEMA_CHANGED" in text


# ---------- V2: kiểu cột bảng đích ----------


def _spec(columns: list[tuple[str, str]]) -> SimpleNamespace:
    return SimpleNamespace(target="fct", output_columns=[SimpleNamespace(name=n, type=t) for n, t in columns])


def test_target_column_types_must_match_spec(tmp_path: Path):
    db = tmp_path / "t.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("create table main.fct as select date '2026-01-01' as d, 5 as n, 'x' as s")
    assert type_mismatches(db, _spec([("d", "DATE"), ("n", "BIGINT"), ("s", "VARCHAR")])) == []
    issues = type_mismatches(db, _spec([("d", "VARCHAR"), ("n", "DECIMAL(18,2)")]))
    assert len(issues) == 2 and "d" in issues[0] and "n" in issues[1]


# ---------- 6 kịch bản backend đổi không báo ----------


@pytest.fixture(scope="module")
def drift_world(seeded_sources: Path, tmp_path_factory: pytest.TempPathFactory) -> dict:
    base = sim.build_baseline(tmp_path_factory.mktemp("drift"))
    return {"control": sim.control(base), "rows": {s.key: sim.run_scenario(base, s) for s in sim.SCENARIOS}}


@pytest.mark.slow
def test_no_change_means_no_alarm_and_same_result(drift_world: dict):
    assert drift_world["control"] == {"false_alarms": 0, "pipeline": "passed_same"}


@pytest.mark.slow
@pytest.mark.parametrize("key", [s.key for s in sim.SCENARIOS])
def test_never_wrong_but_successful_without_any_signal(drift_world: dict, key: str):
    row = drift_world["rows"][key]
    assert not row["silent_wrong"], row
    if row["pipeline"] == "passed_different":  # chạy xong mà khác gốc thì buộc phải có cảnh báo đi kèm
        assert row["stats"] or row["structure"], row


@pytest.mark.slow
@pytest.mark.parametrize("key", ["money_to_number", "rename_column", "drop_used_column"])
def test_structural_changes_block_and_fail_early_with_clear_message(drift_world: dict, key: str):
    row = drift_world["rows"][key]
    assert row["gate_blocks"] and row["pipeline"] == "fail_early"
    assert row["pipeline_detail"], "preflight phải nói rõ cột nào lệch"


@pytest.mark.slow
def test_rename_is_suggested(drift_world: dict):
    assert any("possible_rename" in hint for hint in drift_world["rows"]["rename_column"]["hints"])


@pytest.mark.slow
def test_added_column_is_harmless(drift_world: dict):
    row = drift_world["rows"]["add_column"]
    assert not row["gate_blocks"] and row["pipeline"] == "passed_same"
    assert row["structure"] == ["info: column_added"]


@pytest.mark.slow
def test_null_heavy_column_fails_a_dbt_test_and_warns(drift_world: dict):
    row = drift_world["rows"]["null_heavy"]
    assert row["pipeline"] == "fail_test" and "stat_null_increase" in row["stats"]


@pytest.mark.slow
def test_unit_change_only_warns(drift_world: dict):
    """Đổi đơn vị ×1000 không đổi cấu trúc: code không bắt chắc được, chỉ cảnh báo thống kê cho người phán đoán."""
    row = drift_world["rows"]["money_x1000"]
    assert not row["gate_blocks"] and "stat_new_shape" in row["stats"]


@pytest.mark.slow
def test_at_least_five_of_six_are_stopped_or_harmless(drift_world: dict):
    rows = drift_world["rows"].values()
    ok = [r for r in rows if r["gate_blocks"] or r["pipeline"] in ("fail_early", "fail_test", "passed_same")]
    assert len(ok) >= 5

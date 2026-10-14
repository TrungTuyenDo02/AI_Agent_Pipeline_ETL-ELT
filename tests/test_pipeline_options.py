"""Lựa chọn pipeline do agent đề xuất (CLAUDE.md bản 2, mục 4.4): nạp toàn bộ/phần mới, lịch chạy, kết nối — dữ liệu có cấu trúc."""

from pathlib import Path

import pytest

from src.agents.nodes.plan_review import parse_plan_reply, plan_payload
from src.agents.nodes.safety import check_dag
from src.agents.nodes.spec_check import check_spec
from src.models.spec import (
    INCREMENTAL_MIN_ROWS,
    PipelineOptions,
    PipelineSpec,
    apply_overrides,
    decide_options,
    pick_time_column,
)
from src.services.llm_mock import mock_codegen
from src.services.prompt_context import spec_for_build

BIG = INCREMENTAL_MIN_ROWS + 5
ORDERS = {
    "name": "orders",
    "kind": "csv",
    "source_kind": "file",
    "columns": {"id": "BIGINT", "updated_at": "TIMESTAMP", "created_at": "TIMESTAMP"},
}
EVENTS = {
    "name": "events",
    "kind": "postgres",
    "source_kind": "postgres",
    "columns": {"id": "BIGINT", "note": "VARCHAR"},
}


def options(request: str = "Tính doanh thu ngày", sources=(ORDERS,), rows=None, overrides=None) -> PipelineOptions:
    return decide_options(
        request, list(sources), rows if rows is not None else {s["name"]: 1000 for s in sources}, overrides
    )


# ---------- Cách nạp ----------


def test_small_data_is_loaded_in_full_with_a_plain_reason():
    result = options()
    assert result.load_mode == "full" and result.incremental_column == ""
    assert "nhỏ" in result.load_reason and "toàn bộ" in result.load_reason


def test_large_table_with_time_column_suggests_incremental_using_updated_at_first():
    result = options(rows={"orders": BIG})
    assert result.load_mode == "incremental" and result.incremental_column == "updated_at"
    assert f"{BIG:,}" in result.load_reason and "updated_at" in result.load_reason


def test_large_table_without_time_column_stays_full_and_says_why():
    result = options(sources=(EVENTS,), rows={"events": BIG})
    assert result.load_mode == "full" and "không có cột thời gian" in result.load_reason


def test_unknown_row_count_loads_everything_to_be_safe():
    result = options(rows={"orders": None})
    assert result.load_mode == "full" and "Chưa đo được" in result.load_reason


@pytest.mark.parametrize(
    ("columns", "expected"),
    [(["a", "created_at", "updated_at"], "updated_at"), (["id", "modified_at"], "modified_at"), (["id", "event_time"], "event_time"),
     (["id", "order_ts"], "order_ts"), (["id", "name"], ""), ([], "")],
)  # fmt: skip
def test_pick_time_column(columns: list[str], expected: str):
    assert pick_time_column(columns) == expected


# ---------- Lịch chạy ----------


@pytest.mark.parametrize(
    ("request_text", "schedule"),
    [
        ("Cập nhật doanh thu mỗi giờ", "hourly"),
        ("tính tồn kho hằng giờ cho từng cửa hàng", "hourly"),
        ("Chạy khi có sự kiện đơn mới", "event"),
        ("Tính doanh thu theo ngày", "daily"),
    ],
)
def test_schedule_follows_the_request_with_daily_default(request_text: str, schedule: str):
    result = options(request_text)
    assert result.schedule == schedule and result.schedule_reason


# ---------- Kết nối lấy từ sổ nguồn ----------


def test_connections_describe_how_each_source_is_read():
    result = options(sources=(ORDERS, EVENTS))
    assert [(c.source, c.kind) for c in result.connections] == [("orders", "file"), ("events", "postgres")]
    assert "tệp" in result.connections[0].via and "chỉ đọc" in result.connections[1].via


# ---------- Lựa chọn của DE ----------


def test_engineer_choices_override_defaults_and_ignore_invalid_values():
    base = options()
    chosen = apply_overrides(
        base,
        {"load_mode": "incremental", "incremental_column": "updated_at", "schedule": "hourly"},
        [list(ORDERS["columns"])],
    )
    assert (chosen.load_mode, chosen.incremental_column, chosen.schedule) == ("incremental", "updated_at", "hourly")
    assert "Bạn chọn" in chosen.load_reason and "Bạn chọn" in chosen.schedule_reason
    ignored = apply_overrides(
        base,
        {"load_mode": "xóa hết", "schedule": "mỗi giây", "incremental_column": "khong_co"},
        [list(ORDERS["columns"])],
    )
    assert (ignored.load_mode, ignored.schedule, ignored.incremental_column) == ("full", "daily", "")
    back_to_full = apply_overrides(chosen, {"load_mode": "full"}, [])
    assert (
        back_to_full.load_mode == "full" and back_to_full.incremental_column == ""
    )  # nạp toàn bộ thì bỏ cột thời gian


def test_overrides_survive_a_replan():
    result = options(overrides={"schedule": "hourly"})
    assert result.schedule == "hourly"


# ---------- J1b: đọc và áp quyết định ----------


def test_plan_reply_keeps_only_valid_options():
    reply = parse_plan_reply(
        {
            "decision": "approve",
            "options": {
                "load_mode": "incremental",
                "schedule": "xxx",
                "incremental_column": " updated_at ",
                "hack": "1",
            },
        }
    )
    assert reply == {
        "decision": "approve",
        "note": "",
        "options": {"load_mode": "incremental", "incremental_column": "updated_at"},
    }
    assert parse_plan_reply({"decision": "approve", "options": "rác"}) == {"decision": "approve", "note": ""}
    assert parse_plan_reply({"decision": "revise", "note": "sửa", "options": {"schedule": "hourly"}})["options"] == {
        "schedule": "hourly"
    }


def test_plan_payload_offers_choices_and_candidate_columns():
    spec = {"target": "x", "sources": [{"name": "orders"}], "options": options().model_dump(mode="json")}
    payload = plan_payload(spec, [ORDERS, EVENTS])
    assert [c["value"] for c in payload["option_choices"]["schedule"]] == ["hourly", "daily", "event"]
    assert payload["time_columns"] == [
        "created_at",
        "id",
        "updated_at",
    ]  # cột của nguồn được chọn, không lẫn nguồn khác
    assert payload["spec"]["options"]["connections"][0]["source"] == "orders"


# ---------- V0 ----------


def _spec(**option_fields) -> dict:
    return PipelineSpec(
        request_text="x", target="fct_x", grain=["d"], sources=[{"name": "orders", "kind": "csv"}],
        output_columns=[{"name": "d", "type": "DATE"}], options=PipelineOptions(**option_fields),
    ).model_dump(mode="json")  # fmt: skip


def test_v0_checks_incremental_needs_a_real_time_column():
    catalog = [ORDERS]
    assert not [e for e in check_spec(_spec(), catalog) if "thời gian" in e]
    assert any("chưa chọn cột nào" in e for e in check_spec(_spec(load_mode="incremental"), catalog))
    assert any(
        "không có ở nguồn nào" in e
        for e in check_spec(_spec(load_mode="incremental", incremental_column="ghost"), catalog)
    )
    assert not [
        e
        for e in check_spec(_spec(load_mode="incremental", incremental_column="updated_at"), catalog)
        if "thời gian" in e
    ]


# ---------- Codegen nhận lựa chọn, không nhận lý do ----------


def test_build_spec_for_llm_has_choices_but_not_reasons_or_row_counts():
    spec = {"target": "t", "sources": [], "options": options(rows={"orders": BIG}).model_dump(mode="json")}
    built = spec_for_build(spec)
    assert built["options"] == {"load_mode": "incremental", "incremental_column": "updated_at", "schedule": "daily"}
    assert str(BIG) not in str(built) and "reason" not in str(built)


@pytest.mark.parametrize(("schedule", "literal"), [("daily", '"@daily"'), ("hourly", '"@hourly"'), ("event", "None")])
def test_mock_dag_uses_the_chosen_schedule_and_still_passes_v1(schedule: str, literal: str):
    from src.services.llm import to_json

    spec = {"target": "fct_daily_revenue", "sources": ["shopee_orders"], "options": {"schedule": schedule}}
    files = {f["path"]: f["content"] for f in mock_codegen({"spec": to_json(spec)})["files"]}
    dag = files["dags/fct_daily_revenue_dag.py"]
    assert f"schedule={literal}" in dag and check_dag(dag) == []


# ---------- Trọn luồng ----------


@pytest.mark.slow
def test_planner_fills_options_and_engineer_choice_reaches_the_dag(seeded_sources: Path):
    from src.agents import runner
    from src.agents.runner import ResumeRequest

    outcome = runner.start_run("Gộp đơn hàng 3 nguồn, tính doanh thu ngày", "an-chon-lich")
    answers = {q["id"]: q["options"][0] for q in outcome.pending["questions"]}
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="clarify", value={"answers": answers}))
    spec = outcome.pending["spec"]
    assert spec["options"]["load_mode"] == "full" and spec["options"]["schedule"] == "daily"
    assert {c["source"] for c in spec["options"]["connections"]} == {"shopee_orders", "tiki_orders", "website_orders"}
    assert outcome.pending["option_choices"]["load_mode"] and "order_date" in outcome.pending["time_columns"]
    reply = {"decision": "approve", "options": {"schedule": "hourly"}}
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="plan", value=reply))
    assert outcome.status == "waiting_review", outcome.error
    values = runner.get_values(outcome.run_id)
    assert values["spec"]["options"]["schedule"] == "hourly" and values["plan_options"] == {"schedule": "hourly"}
    assert 'schedule="@hourly"' in values["code_files"]["dags/fct_daily_revenue_dag.py"]

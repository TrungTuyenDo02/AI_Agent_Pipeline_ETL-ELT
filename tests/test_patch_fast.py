"""Bản vá nhanh khi nguồn đổi cấu trúc: sửa SQL tất định, kế hoạch vá, node vá, rẽ nhánh graph (không cần cơ sở dữ liệu)."""

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from src.agents import routing
from src.agents.nodes.package import _patch_items
from src.agents.nodes.patch import compare_marts, patch_apply_node
from src.agents.tools import drift_fix
from src.models.drift import FixStep, PatchPlan, SchemaChangeView
from src.services import patch_plan

STAGING = """{{ config(materialized='ephemeral') }}
with src as (
    select order_id, order_date, "total_amount", status from {{ source('raw', 'shopee_orders') }}
),
cleaned as (select order_id, try_strptime(order_date, '%d/%m/%Y') as order_day, total_amount from src)
select order_id, order_day, total_amount from cleaned
"""
MART = "select order_id, order_day from {{ ref('stg_shopee_orders') }}"
ORACLE = "with expected as (select order_date as d from {{ source('raw', 'shopee_orders') }}) select d from expected"
FILES = {"models/staging/stg_shopee_orders.sql": STAGING, "models/marts/fct.sql": MART}
TESTS = {"tests/assert_fct_reconciles.sql": ORACLE, "tests/assert_shopee_orders_order_date_castable.sql": ORACLE}


def col(type_: str, position: int) -> dict:
    return {"type": type_, "nullable": True, "position": position}


BEFORE = {"order_id": col("string", 0), "order_date": col("string", 1), "total_amount": col("string", 2)}


def change(kind: str, detail: str, hint: str = "", table: str = "shopee_orders", cid: int = 1) -> SchemaChangeView:
    return SchemaChangeView(
        id=cid, source_id=1, table=table, from_version=1, to_version=2, change_type=kind,
        severity="breaking", detail=detail, hint=hint, detected_at=datetime.now(UTC), status="open",
    )  # fmt: skip


def plan_for(view: SchemaChangeView, after: dict, answers: dict | None = None) -> PatchPlan:
    values = {"code_files": FILES, "test_files": TESTS}
    return patch_plan.build_plan("run-1", values, [view], answers or {}, lambda _v: (BEFORE, after))


RENAME = change("possible_rename", "Cột shopee_orders.order_date biến mất", "possible_rename: order_date → ordered_at")
RENAMED = {"order_id": col("string", 0), "ordered_at": col("string", 1), "total_amount": col("string", 2)}


# ---------- Sửa SQL tất định ----------


def test_rename_keeps_output_column_name_and_jinja():
    out, changed = drift_fix.rewrite(
        STAGING, "shopee_orders", [FixStep(kind="rename", old="order_date", new="ordered_at")]
    )
    assert changed
    assert "ordered_at AS order_date" in out  # cột đầu ra giữ tên cũ: model phía sau không phải đổi
    assert "TRY_STRPTIME(order_date," in out  # câu SELECT thứ hai đọc từ CTE `src`, không đọc bảng nguồn: không đổi
    assert "{{ source('raw', 'shopee_orders') }}" in out and out.startswith("{{ config(materialized='ephemeral') }}")


def test_rename_inside_expression_changes_only_the_reference():
    sql = "select try_strptime(order_date, '%d/%m/%Y') as order_day from {{ source('raw', 'shopee_orders') }}"
    out, changed = drift_fix.rewrite(sql, "shopee_orders", [FixStep(kind="rename", old="order_date", new="ordered_at")])
    assert changed and "TRY_STRPTIME(ordered_at," in out and "AS order_day" in out


def test_cast_wraps_column_and_is_idempotent():
    step = FixStep(kind="cast", column="total_amount", sql_type="VARCHAR")
    out, changed = drift_fix.rewrite(STAGING, "shopee_orders", [step])
    assert changed and 'TRY_CAST("total_amount" AS TEXT) AS "total_amount"' in out
    already = "select cast(total_amount as varchar) as total_amount from {{ source('raw', 'shopee_orders') }}"
    assert drift_fix.rewrite(already, "shopee_orders", [step]) == (already, False)


def test_rename_then_cast_chain_for_renamed_and_retyped_column():
    steps = [
        FixStep(kind="rename", old="order_date", new="ordered_at"),
        FixStep(kind="cast", column="ordered_at", sql_type="VARCHAR"),
    ]
    out, changed = drift_fix.rewrite(STAGING, "shopee_orders", steps)
    assert changed and "TRY_CAST(ordered_at AS TEXT) AS order_date" in out


def test_unsafe_or_unparsable_sql_is_not_rewritten():
    steps = [FixStep(kind="rename", old="a", new="b")]
    assert drift_fix.rewrite("select {{ var('x') }} from {{ source('raw', 't') }}", "t", steps) is None
    assert drift_fix.rewrite("select from from", "t", steps) is None
    assert drift_fix.rewrite("drop table x", "t", steps) is None


def test_unqualified_column_with_two_tables_is_left_alone():
    sql = "select a.id, order_date from {{ source('raw', 'shopee_orders') }} a join {{ source('raw', 'other') }} b on a.id = b.id"
    assert drift_fix.rewrite(sql, "shopee_orders", [FixStep(kind="rename", old="order_date", new="ordered_at")]) == (
        sql,
        False,
    )


def test_files_to_fix_skips_marts_and_generated_cast_tests():
    files = {**FILES, **TESTS}
    assert drift_fix.files_to_fix(files, "shopee_orders", "order_date") == [
        "models/staging/stg_shopee_orders.sql",
        "tests/assert_fct_reconciles.sql",
    ]
    assert drift_fix.files_to_fix(files, "shopee_orders", "khong_co") == []


# ---------- Kế hoạch vá ----------


def test_rename_needs_an_answer_then_becomes_a_code_fix():
    plan = plan_for(RENAME, RENAMED)
    item = plan.items[0]
    assert item.action == "ask" and not plan.ready and plan.questions == 1
    assert item.question.options[0].value == "use:ordered_at" and "đã đổi tên" in item.question.options[0].label
    assert item.question.options[-1].value == "drop"
    answered = plan_for(RENAME, RENAMED, {"1": "use:ordered_at"})
    assert answered.ready and answered.code_fixes == 1 and "0 token" in answered.estimate
    assert answered.items[0].steps == [FixStep(kind="rename", old="order_date", new="ordered_at")]


def test_answer_must_name_a_new_column():
    assert not plan_for(RENAME, RENAMED, {"1": "use:order_id"}).ready  # cột đã có từ trước không phải cột thay thế
    assert not plan_for(RENAME, RENAMED, {"1": "use:khong_co"}).ready
    assert not plan_for(RENAME, RENAMED, {"1": "bat_ky"}).ready


def test_rename_to_a_different_type_adds_a_cast_back_to_the_old_type():
    after = {"order_id": col("string", 0), "ordered_at": col("date", 1), "total_amount": col("string", 2)}
    plan = plan_for(RENAME, after, {"1": "use:ordered_at"})
    assert [s.kind for s in plan.items[0].steps] == ["rename", "cast"] and plan.items[0].steps[1].sql_type == "VARCHAR"


def test_dropping_a_column_needs_ai():
    view = change("column_removed", "Cột shopee_orders.order_date đã bị xóa và pipeline đang dùng cột này.")
    plan = plan_for(view, {"order_id": col("string", 0), "total_amount": col("string", 2)}, {"1": "drop"})
    assert plan.ready and plan.llm_items == 1 and "AI" in plan.estimate


def test_incompatible_type_is_cast_back_in_staging():
    view = change("type_incompatible", "Cột shopee_orders.total_amount đổi kiểu string → integer (không tương thích).")
    plan = plan_for(view, {**BEFORE, "total_amount": col("integer", 2)})
    assert plan.items[0].action == "code" and plan.items[0].steps[0].sql_type == "VARCHAR"
    assert plan.items[0].files == ["models/staging/stg_shopee_orders.sql"]


def test_unknown_old_type_goes_to_ai():
    view = change("type_incompatible", "Cột shopee_orders.total_amount đổi kiểu other → integer.")
    plan = plan_for(view, BEFORE | {"total_amount": col("integer", 2)})
    assert plan.items[0].action == "code"  # BEFORE nói cột này là string
    odd = patch_plan.build_plan(
        "r",
        {"code_files": FILES, "test_files": TESTS},
        [view],
        {},
        lambda _v: ({"total_amount": col("other", 2)}, {"total_amount": col("integer", 2)}),
    )
    assert odd.items[0].action == "llm"


@pytest.mark.parametrize(
    ("kind", "detail"),
    [
        ("column_added", "Cột mới shopee_orders.channel (string)."),
        ("type_widened", "Cột shopee_orders.total_amount đổi kiểu integer → decimal (mở rộng an toàn)."),
        ("nullable_tightened", "Cột shopee_orders.order_id từ cho phép rỗng thành NOT NULL."),
        ("stat_null_increase", "Cột shopee_orders.order_date rỗng nhiều hơn."),
    ],
)
def test_harmless_changes_need_no_code(kind: str, detail: str):
    plan = plan_for(change(kind, detail), BEFORE)
    assert plan.items[0].action == "none" and plan.ready and plan.code_fixes == 0 and "0 token" in plan.estimate


def test_removed_table_cannot_be_patched():
    plan = plan_for(change("table_removed", "Bảng shopee_orders không còn ở nguồn."), {})
    assert plan.items[0].action == "blocked" and not plan.ready and plan.blocked == 1


def test_change_to_a_column_the_pipeline_does_not_read_needs_no_code():
    view = change("type_incompatible", "Cột shopee_orders.ghi_chu đổi kiểu string → integer (không tương thích).")
    plan = patch_plan.build_plan(
        "r",
        {"code_files": FILES},
        [view],
        {},
        lambda _v: ({"ghi_chu": col("string", 0)}, {"ghi_chu": col("integer", 0)}),
    )
    assert plan.items[0].action == "none" and "không đọc cột này" in plan.items[0].summary


# ---------- Áp bản vá và node ----------


def test_apply_plan_rewrites_staging_and_oracle_but_not_the_mart():
    plan = plan_for(RENAME, RENAMED, {"1": "use:ordered_at"})
    code, tests, applied, leftover, already_ok = patch_plan.apply_plan(FILES, TESTS, plan)
    assert "ordered_at AS order_date" in code["models/staging/stg_shopee_orders.sql"]
    assert code["models/marts/fct.sql"] == MART  # mart đọc qua ref(): giữ nguyên
    assert "ordered_at" in tests["tests/assert_fct_reconciles.sql"]
    assert {a["file"] for a in applied} == {"models/staging/stg_shopee_orders.sql", "tests/assert_fct_reconciles.sql"}
    assert leftover == [] and already_ok == []


def test_apply_plan_escalates_files_it_cannot_rewrite_safely():
    files = {
        "models/staging/stg_shopee_orders.sql": "select {{ var('x') }}, order_date from {{ source('raw', 'shopee_orders') }}"
    }
    plan = patch_plan.build_plan(
        "r", {"code_files": files}, [RENAME], {"1": "use:ordered_at"}, lambda _v: (BEFORE, RENAMED)
    )
    _, _, applied, leftover, _ = patch_plan.apply_plan(files, {}, plan)
    assert (
        applied == [] and leftover[0].action == "llm" and leftover[0].files == ["models/staging/stg_shopee_orders.sql"]
    )
    assert "var(" not in patch_plan.llm_hint(leftover)  # lời nhắc cho AI chỉ có tên cột và đường dẫn file


def test_patch_apply_node_drops_generated_cast_tests_and_sets_llm_hint_only_when_needed():
    plan = plan_for(RENAME, RENAMED, {"1": "use:ordered_at"})
    state = {
        "code_files": FILES,
        "test_files": TESTS,
        "profile": {},
        "source_catalog": [],
        "patch": {"parent": "run-1", "plan": plan.model_dump()},
    }
    out = patch_apply_node(state)
    assert (
        "tests/assert_shopee_orders_order_date_castable.sql" not in out["test_files"]
    )  # Testgen dựng lại theo hồ sơ mới
    assert out["rescue_hint"] == "" and out["patch"]["llm_items"] == [] and len(out["patch"]["applied"]) == 2
    drop = change("column_removed", "Cột shopee_orders.order_date đã bị xóa và pipeline đang dùng cột này.")
    dropped = plan_for(drop, {"order_id": col("string", 0)}, {"1": "drop"})
    out = patch_apply_node({**state, "patch": {"parent": "run-1", "plan": dropped.model_dump()}})
    assert out["patch"]["llm_files"] and out["rescue_hint"].startswith("BẢN VÁ")


def test_seed_state_carries_the_approved_plan_so_nothing_is_asked_again():
    parent = {
        "spec": {"target": "fct"},
        "answers": {"q": "a"},
        "answered": [{"id": "q"}],
        "plan_options": {"schedule": "daily"},
        "code_files": FILES,
        "test_files": TESTS,
        "workspace": "/w/run-1",
    }
    seed = patch_plan.seed_state("run-1", parent, plan_for(RENAME, RENAMED, {"1": "use:ordered_at"}), "an")
    assert seed["patch_of"] == "run-1" and seed["spec"] == {"target": "fct"} and seed["answers"] == {"q": "a"}
    assert seed["plan_review"]["decision"] == "approve" and seed["previous_files"] == {**FILES, **TESTS}
    assert seed["patch"]["parent_workspace"] == "/w/run-1" and seed["patch"]["changes"] == [{"id": 1, "source_id": 1}]


def test_compare_marts_reports_same_different_and_missing(tmp_path: Path):
    def make(name: str, rows: list[tuple]) -> Path:
        path = tmp_path / name
        with duckdb.connect(str(path)) as con:
            con.execute("create table fct (d varchar, n integer)")
            con.executemany("insert into fct values (?, ?)", rows)
        return path

    old, same, other = (
        make("old.duckdb", [("a", 1), ("b", 2)]),
        make("same.duckdb", [("b", 2), ("a", 1)]),
        make("other.duckdb", [("a", 1), ("c", 9)]),
    )
    assert compare_marts(old, same, "fct") == {
        "compared": True,
        "same": True,
        "schema_same": True,
        "rows_before": 2,
        "rows_after": 2,
        "differing_rows": 0,
    }
    different = compare_marts(old, other, "fct")
    assert different["same"] is False and different["differing_rows"] == 2
    assert compare_marts(tmp_path / "khong-co.duckdb", same, "fct")["compared"] is False


@pytest.mark.parametrize(
    ("before_sql", "after_sql"),
    [
        ("select 1::integer as amount", "select 1::integer as total"),
        ("select 1::integer as amount", "select 1::bigint as amount"),
        ("select 1 as a, 1 as b", "select 1 as b, 1 as a"),
        ("select 1 as amount where false", "select 1::bigint as amount where false"),
    ],
)
def test_compare_marts_detects_schema_changes(tmp_path: Path, before_sql: str, after_sql: str):
    paths = [tmp_path / name for name in ("old.duckdb", "new.duckdb")]
    for path, sql in zip(paths, (before_sql, after_sql), strict=True):
        with duckdb.connect(str(path)) as con:
            con.execute(f"create table fct as {sql}")
    result = compare_marts(*paths, "fct")
    assert result["compared"] is True and result["same"] is False
    assert result["schema_same"] is False
    assert result["note"]


@pytest.mark.parametrize(
    ("before_rows", "after_rows", "expected"),
    [
        ([(1,), (1,), (2,)], [(1,), (2,), (2,)], 2),
        ([(1,), (1,)], [(1,)], 1),
        ([(1,), (1,), (2,)], [(2,), (1,), (1,)], 0),
    ],
)
def test_compare_marts_counts_duplicate_rows(tmp_path: Path, before_rows: list, after_rows: list, expected: int):
    paths = [tmp_path / name for name in ("old.duckdb", "new.duckdb")]
    for path, rows in zip(paths, (before_rows, after_rows), strict=True):
        with duckdb.connect(str(path)) as con:
            con.execute("create table fct (n integer)")
            con.executemany("insert into fct values (?)", rows)
    result = compare_marts(*paths, "fct")
    assert result["same"] is (expected == 0)
    assert result["differing_rows"] == expected


def test_compare_marts_handles_nested_values_and_nan(tmp_path: Path):
    paths = [tmp_path / name for name in ("old.duckdb", "new.duckdb")]
    for path in paths:
        with duckdb.connect(str(path)) as con:
            con.execute("create table fct as select [1, NULL] as a, {'k': [2]} as b, 'NaN'::double as n")
    result = compare_marts(*paths, "fct")
    assert result["same"] is True and result["differing_rows"] == 0


def test_patch_schema_change_is_shown_in_review_and_progress():
    from src.agents.progress import _detail_patch_verify

    regression = {
        "compared": True,
        "same": False,
        "schema_same": False,
        "rows_before": 1,
        "rows_after": 1,
        "differing_rows": 0,
        "note": "Tên, thứ tự hoặc kiểu cột của bảng đích đã thay đổi.",
    }
    state = {"patch": {"regression": regression}}
    evidence = _patch_items(state)[1]
    assert evidence.passed is None and regression["note"] in evidence.result
    assert regression["note"] in _detail_patch_verify(state)


def test_patch_evidence_is_measured_by_code():
    plan = plan_for(RENAME, RENAMED, {"1": "use:ordered_at"})
    state = {
        "patch": {
            "plan": plan.model_dump(),
            "applied": [{"file": "a"}],
            "llm_files": [],
            "regression": {"compared": True, "same": True, "rows_after": 7},
        },
        "llm_usage": [],
    }
    items = _patch_items(state)
    assert items[0].passed and "0 token" in items[0].result
    assert items[1].passed and "giống hệt" in items[1].result
    different = {
        **state["patch"],
        "regression": {"compared": True, "same": False, "rows_before": 7, "rows_after": 5, "differing_rows": 4},
    }
    assert _patch_items({**state, "patch": different})[1].passed is None  # khác lần chạy gốc: cần Reviewer giải thích
    assert _patch_items({}) == []


# ---------- Rẽ nhánh graph ----------


@pytest.mark.parametrize(
    ("fn", "state", "expected"),
    [
        (routing.start_route, {}, "input_gate"),
        (routing.start_route, {"patch_of": "run-1"}, "patch_start"),
        (routing.after_patch_start, {}, "ingest"),
        (routing.after_patch_start, {"error": "x"}, "fail"),
        (routing.after_profiler, {}, "schema_guard"),
        (routing.after_profiler, {"patch_of": "run-1"}, "patch_apply"),
        (routing.after_patch_apply, {"patch": {"llm_items": []}}, "testgen"),
        (routing.after_patch_apply, {"patch": {"llm_items": [{"change_id": 1}]}}, "codegen"),
        (routing.after_sandbox, {"sandbox": {"passed": True}, "patch_of": "run-1"}, "patch_verify"),
        (routing.after_sandbox, {"sandbox": {"passed": True}}, "optimizer"),
        (routing.after_sandbox, {"sandbox": {"passed": True}, "optimization": {"decision": "skipped"}}, "package"),
    ],
)
def test_patch_routing(fn, state: dict, expected: str):
    assert fn(state) == expected


def test_codegen_for_a_patch_only_sees_the_files_that_need_ai():
    from src.agents.nodes.codegen import previous_code

    state = {
        "code_files": FILES,
        "rescue_hint": "BẢN VÁ ...",
        "patch": {"llm_files": ["models/staging/stg_shopee_orders.sql"]},
    }
    sent = previous_code(state)
    assert (
        "stg_shopee_orders.sql" in sent and "fct.sql" in sent
    )  # model đích đọc qua ref() cũng được gửi để AI thấy tên cột đầu ra

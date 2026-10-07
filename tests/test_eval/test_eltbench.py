"""Test bộ chấm ELT-Bench: so với bảng kết quả đúng, dựng yêu cầu, đọc cấu hình nguồn, chạy model chuẩn."""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pytest

ELTBENCH = Path(__file__).resolve().parents[2] / "eval" / "benchmarks" / "eltbench"
sys.path.insert(0, str(ELTBENCH))

import run_eltbench  # noqa: E402
from backfill_runs import parse_report  # noqa: E402
from gt_compare import compare_to_ground_truth, load_ground_truth, normalize  # noqa: E402
from import_eltbench import source_tables  # noqa: E402
from run_eltbench import request_text  # noqa: E402

GT = "COURSE_ID,NAME,PER_UG,PASSED\n1.0,Machine Learning,14.285714,true\n2.0,Database,,false\n"


@pytest.fixture
def gt_csv(tmp_path: Path) -> Path:
    path = tmp_path / "courses.csv"
    path.write_text(GT, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("1.0", 1.0),
        (3, 3.0),
        ("TRUE", 1.0),
        ("abc ", "abc"),
        ("2016-01-01 00:00:00.000", "2016-01-01 00:00:00"),
    ],
)
def test_normalize(value: object, expected: object):
    assert normalize(value) == expected


def test_matches_ignoring_column_case_order_row_order_and_rounding(gt_csv: Path):
    columns = ["passed", "per_ug", "name", "course_id"]
    rows = [(False, None, "Database", 2), (True, 14.2857142857, "Machine Learning", 1)]
    assert compare_to_ground_truth(columns, rows, gt_csv) == (True, "Khớp 2 dòng")


@pytest.mark.parametrize(
    ("columns", "rows", "message"),
    [
        (["course_id", "name", "per_ug"], [(1, "Machine Learning", 14.29), (2, "Database", None)], "thiếu"),
        (["course_id", "name", "per_ug", "passed"], [(1, "Machine Learning", 14.285714, True)], "số dòng"),
        (
            ["course_id", "name", "per_ug", "passed"],
            [(1, "Machine Learning", 15.0, True), (2, "Database", None, False)],
            "1/2 dòng khác",
        ),
    ],
)
def test_detects_differences(gt_csv: Path, columns: list[str], rows: list[tuple], message: str):
    ok, detail = compare_to_ground_truth(columns, rows, gt_csv)
    assert not ok and message in detail


def test_request_text_keeps_exact_model_and_column_names():
    text = request_text(
        {
            "name": "trucks",
            "description": "Each record is a truck.",
            "columns": [{"name": "truck_id", "description": "Id"}, {"name": "per_Weight", "description": "%"}],
        }
    )
    assert "`trucks`" in text and "- truck_id: Id" in text and "- per_Weight: %" in text


def test_source_tables_follow_benchmark_file_layout():
    cfg = {
        "postgres": {"config": {"tables": ["registration"]}},
        "mongodb": {"config": {"tables": ["prof"]}},
        "aws_s3": {"data": [{"path": "s3://bucket/RA.csv", "table": "RA"}]},
        "custom_api": {"config": {"tables": ["course"]}},
        "flat_files": [{"table": "student", "format": "jsonl", "path": "https://drive"}],
    }
    tables = {t.name: t for t in source_tables(cfg, "cs_semester")}
    assert tables["registration"].member == "db/cs_semester/registration.csv"
    assert tables["RA"].kind == "aws_s3" and tables["RA"].fmt == "csv"
    assert tables["course"].archive == "data_api.zip"
    assert tables["student"].member == "db/cs_semester/student.jsonl"


def test_dataset_in_repo_has_every_selected_task():
    for task in run_eltbench.task_names():
        folder = run_eltbench.DATA_DIR / task
        assert (folder / "data_model.yaml").exists() and any((folder / "ground_truth").glob("*.csv")), task


def test_reference_models_match_ground_truth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Model dbt chuẩn của cs_semester qua E0 + V1 phải khớp bảng kết quả đúng (kiểm chứng bộ chấm)."""
    monkeypatch.setattr(run_eltbench, "WORK_DIR", tmp_path)
    db = run_eltbench.load_task_db("cs_semester")
    results = [
        run_eltbench.check_reference("cs_semester", path, db)
        for path in sorted((run_eltbench.REFERENCE_DIR / "cs_semester").glob("*.sql"))
    ]
    assert len(results) == 3
    assert all(r["ok"] for r in results), results


# --- B1: thời gian lẻ giây, tự kiểm 34/34, lỗi benchmark đã biết, báo lệch rõ ràng ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2021, 4, 1, 19, 42, 58, 123000), "2021-04-01 19:42:58.123"),
        ("2021-04-01 19:42:58.123", "2021-04-01 19:42:58.123"),
        ("2021-04-01 19:42:58.123000", "2021-04-01 19:42:58.123"),
        ("2020-02-25 17:30:43.610", "2020-02-25 17:30:43.61"),
        (datetime(2020, 2, 25, 17, 30, 43, 610000), "2020-02-25 17:30:43.61"),
        ("2019-09-11 0:00:00", "2019-09-11 00:00:00"),
        (datetime(2019, 9, 11), "2019-09-11 00:00:00"),
        ("2023-05-25 09:00:00.000 +0000", "2023-05-25 09:00:00"),
        ("2023-05-25 16:00:00+07:00", "2023-05-25 09:00:00"),
        (datetime(2023, 5, 25, 16, 0, tzinfo=timezone(timedelta(hours=7))), "2023-05-25 09:00:00"),
        (datetime(2021, 4, 1, 19, 42, 58, 123456), "2021-04-01 19:42:58.123"),  # cùng độ chính xác: mili giây
        (date(2021, 4, 1), "2021-04-01"),
        ("2019-09-18 23:48:31.176+07", "2019-09-18 16:48:31.176"),
        ("2019-09-18 10:18:31-05:30", "2019-09-18 15:48:31"),
    ],
)
def test_normalize_timestamps_to_one_precision(value: object, expected: str):
    assert normalize(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [('"regular"', "regular"), ('"5"', 5.0), ("null", None), ('"a', '"a'), ('"say "hi""', '"say "hi""')],
)
def test_normalize_variant_json_export(value: str, expected: object):
    assert normalize(value) == expected


def test_millisecond_timestamp_matches_and_one_millisecond_off_does_not(tmp_path: Path):
    path = tmp_path / "sessions.csv"
    path.write_text("SESSION_ID,STARTED_AT\n1.0,2021-04-01 19:42:58.123\n", encoding="utf-8")
    assert compare_to_ground_truth(["session_id", "started_at"], [(1, datetime(2021, 4, 1, 19, 42, 58, 123000))], path)[
        0
    ]
    ok, detail = compare_to_ground_truth(
        ["session_id", "started_at"], [(1, datetime(2021, 4, 1, 19, 42, 58, 124000))], path
    )
    assert not ok and "started_at" in detail


def test_mismatch_names_columns_and_prints_samples(gt_csv: Path):
    rows = [(1, "Machine Learning", 15.0, True), (2, "Database", None, False)]
    ok, detail = compare_to_ground_truth(["course_id", "name", "per_ug", "passed"], rows, gt_csv)
    assert not ok and "cột lệch ['per_ug']" in detail and "đúng=(14.285714) / agent=(15.0)" in detail


def test_ignore_columns_only_drops_listed_extra_columns(gt_csv: Path):
    columns = ["course_id", "name", "per_ug", "passed", "spec_only"]
    rows = [(1, "Machine Learning", 14.285714, True, 9), (2, "Database", None, False, 9)]
    assert not compare_to_ground_truth(columns, rows, gt_csv)[0]
    assert compare_to_ground_truth(columns, rows, gt_csv, frozenset({"spec_only"}))[0]
    assert not compare_to_ground_truth(columns, rows, gt_csv, frozenset({"other"}))[0]


def test_selfcheck_every_ground_truth_grades_itself_as_match():
    """Mỗi bảng đúng nạp có kiểu (như bảng agent sinh ra) phải được chấm khớp chính nó: 34/34."""
    results = run_eltbench.run_selfcheck()
    assert len(results) == 34
    assert [r for r in results if not r["ok"]] == []


def test_known_issues_list_exactly_the_spec_columns_missing_from_ground_truth():
    """Đề yêu cầu cột mà bảng đúng không có ⇔ đã ghi trong known_issues.yaml (không sót, không thừa)."""
    found = {}
    for task in run_eltbench.task_names():
        for model in run_eltbench.models_of(task):
            path = run_eltbench.ground_truth_path(task, model["name"])
            spec = {c["name"].lower() for c in model.get("columns", [])}
            truth = set(load_ground_truth(path)[0])
            assert truth <= spec, (task, model["name"], truth - spec)
            if spec - truth:
                found[(task, model["name"])] = frozenset(spec - truth)
    assert found == run_eltbench.known_issues()


def test_summary_reports_with_and_without_known_issues():
    rows = [
        {"ok": True, "known_issue": False, "ok_if_issue_ignored": True, "gt_rows": 3},
        {"ok": False, "known_issue": True, "ok_if_issue_ignored": True, "gt_rows": 40},
        {"ok": False, "known_issue": False, "ok_if_issue_ignored": False, "gt_rows": 9},
    ]
    text = "\n".join(run_eltbench.summary_lines(rows))
    assert "1/3 model" in text and "**Không gồm**" in text and ": 1/2" in text
    assert "thay vì bỏ model: 2/3" in text and "1/3 bảng đúng có ≤ 5 dòng" in text and "options[0]" in text


def _changed(value: object) -> object:
    """Đổi một ô thành giá trị khác thật (để kiểm bộ chấm không quá dễ dãi)."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int | float):
        return value + 1
    if isinstance(value, datetime):
        return value + timedelta(seconds=1)
    if isinstance(value, date):
        return value + timedelta(days=1)
    return f"{value}x"


def test_selfcheck_detects_one_changed_cell_in_every_ground_truth():
    """Ngược với tự kiểm: đổi 1 ô (dòng đầu, cột đầu khác NULL) ở mỗi bảng đúng → phải bị chấm lệch: 34/34."""
    missed = []
    for task in run_eltbench.task_names():
        for model in run_eltbench.models_of(task):
            path = run_eltbench.ground_truth_path(task, model["name"])
            with duckdb.connect() as con:
                rel = con.sql(f"SELECT * FROM read_csv('{path.as_posix()}', header = true, sample_size = -1)")
                columns, rows = rel.columns, [list(r) for r in rel.fetchall()]
            col = next(i for i, v in enumerate(rows[0]) if v is not None)
            rows[0][col] = _changed(rows[0][col])
            if compare_to_ground_truth(columns, [tuple(r) for r in rows], path)[0]:
                missed.append((task, model["name"], columns[col]))
    assert missed == []


# --- B2: lưu đầu ra mỗi lần chạy, chấm lại 0 token ---


def _fake_workspace(root: Path, task: str, model: str) -> Path:
    """Workspace giả: bảng đích = bảng đúng (có kiểu) trong sandbox.duckdb + một file SQL dbt."""
    workspace = root / "ws"
    (workspace / "models" / "marts").mkdir(parents=True)
    (workspace / "models" / "marts" / f"{model}.sql").write_text("select 1", encoding="utf-8")
    (workspace / "models" / "marts" / "notes.txt").write_text("bỏ qua", encoding="utf-8")
    path = run_eltbench.ground_truth_path(task, model).as_posix()
    with duckdb.connect(str(workspace / "sandbox.duckdb")) as con:
        con.execute(f"CREATE TABLE main.\"{model}\" AS SELECT * FROM read_csv('{path}', header = true)")
    return workspace


META = {"run_id": "r1", "auto_answers": 1, "fix_attempts": 0, "rescue": 0, "tokens": 10, "cost_usd": 0.1, "seconds": 2}


def test_saved_output_regrades_without_running_agent(tmp_path: Path):
    workspace = _fake_workspace(tmp_path, "human_resources", "positions")
    batch = tmp_path / "batch"
    run_eltbench.save_output(
        batch, "human_resources", "positions", META | {"status": "approved"}, workspace, "positions"
    )
    folder = batch / "human_resources__positions"
    assert (folder / "output.parquet").exists() and (folder / "models" / "marts" / "positions.sql").exists()
    assert not (folder / "models" / "marts" / "notes.txt").exists()
    row = run_eltbench.grade_saved(folder)
    assert row["ok"] and row["run_id"] == "r1" and row["gt_rows"] == 4 and row["detail"] == "Khớp 4 dòng"
    assert [r["model"] for r in run_eltbench.regrade(batch)] == ["positions"]


def test_failed_run_is_saved_without_output_and_graded_false(tmp_path: Path):
    workspace = _fake_workspace(tmp_path, "human_resources", "positions")
    meta = META | {"status": "failed", "error": "Đã dừng ở bước cứu hộ"}
    run_eltbench.save_output(tmp_path / "b", "human_resources", "positions", meta, workspace, "positions")
    row = run_eltbench.grade_saved(tmp_path / "b" / "human_resources__positions")
    assert not (tmp_path / "b" / "human_resources__positions" / "output.parquet").exists()
    assert not row["ok"] and row["detail"] == "Đã dừng ở bước cứu hộ"


def test_missing_target_table_is_reported(tmp_path: Path):
    workspace = _fake_workspace(tmp_path, "human_resources", "positions")
    run_eltbench.save_output(
        tmp_path / "b", "human_resources", "positions", META | {"status": "approved"}, workspace, "x"
    )
    row = run_eltbench.grade_saved(tmp_path / "b" / "human_resources__positions")
    assert not row["ok"] and "Không đọc được bảng đích" in row["detail"]


def test_backfill_parses_old_report_table():
    text = (
        "- Ngày chạy: 2026-10-02 • provider/model: openai/x\n\n**Khớp bảng kết quả đúng: 1/1 model**\n\n"
        "| Task | Model | status | tokens | detail |\n|---|---|---|---|---|\n"
        "| human_resources | positions | approved | 17057 | Khớp 4 dòng |\n"
    )
    when, who, rows = parse_report(text)
    assert (when, who) == ("2026-10-02", "openai/x")
    assert rows[("human_resources", "positions")]["tokens"] == "17057"

"""Mốc DE làm tay (U4): đọc human_baseline.csv, so với agent, công Reviewer, bộ chấm cho DE. Ô trống → `—`."""

import sqlite3
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "baseline"))

import check_de  # noqa: E402
from baseline_compare import (  # noqa: E402
    BASELINE_CSV,
    COLUMNS,
    changed_lines,
    collect_reviews,
    compare_lines,
    load_baseline,
    per_case,
    reviewer_effort,
    reviewer_lines,
    summary_ratio,
)

HEADER = ",".join(COLUMNS)
AGENT = {
    "provider": "openai",
    "model": "m",
    "rows": [{"case": "g01", "seconds": 60.0, "ok": True}, {"case": "g02", "seconds": 120.0, "ok": False}],
}


def _csv(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "human_baseline.csv"
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
    return path


def test_shipped_template_is_empty_with_right_header():
    assert BASELINE_CSV.read_text(encoding="utf-8").strip() == HEADER
    assert load_baseline(BASELINE_CSV) == []


def test_blank_or_invalid_minutes_are_not_measured(tmp_path: Path):
    rows = load_baseline(_csv(tmp_path, "g01,de_a,3,30,khớp,2026-10-12", "g02,de_a,3,,,", "g03,de_a,3,abc,,"))
    assert [r["case_id"] for r in rows] == ["g01"] and rows[0]["phút"] == 30


def test_wrong_header_fails_loudly(tmp_path: Path):
    path = tmp_path / "human_baseline.csv"
    path.write_text("case,minutes\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tiêu đề"):
        load_baseline(path)


def test_per_case_uses_median_and_experience_span(tmp_path: Path):
    rows = load_baseline(_csv(tmp_path, "g01,a,2,20,,", "g01,b,5,40,,", "g01,c,3,90,,"))
    assert per_case(rows)["g01"] == {"minutes": 40, "people": 3, "experience": "2–5"}


def test_compare_without_human_data_shows_dash():
    lines = compare_lines({}, AGENT)
    assert "| g01 | 1,0 | — | — | — | — |" in lines
    assert "| g02 | 2,0 (sai) | — | — | — | — |" in lines
    assert summary_ratio({}, AGENT).startswith("—")


def test_compare_with_human_data_gives_ratio():
    human = {"g01": {"minutes": 4.0, "people": 1, "experience": "3"}}
    assert "| g01 | 1,0 | 4,0 | 1 | 3 | 0,25 |" in compare_lines(human, AGENT)
    assert summary_ratio(human, AGENT) == "0,25 (1 ca)"


def test_changed_lines_counts_added_and_removed():
    before = {"a.sql": "select 1\nfrom x\n", "old.sql": "x\ny\n"}
    after = {"a.sql": "select 2\nfrom x\n", "new.sql": "z\n"}
    assert changed_lines(before, after) == 2 + 2 + 1


def test_reviewer_effort_without_human_reviews_is_dash():
    assert reviewer_lines(reviewer_effort([]))[0].endswith("— (chưa có quyết định của người duyệt thật) |")


def test_reviewer_effort_rates():
    runs = [
        {"decisions": ["approve"], "changed_lines": None},
        {"decisions": ["reject", "approve"], "changed_lines": 12},
    ]
    effort = reviewer_effort(runs)
    assert effort["approved_first"] == 0.5 and effort["avg_changed_lines"] == 12
    assert "50% (2 lần chạy" in reviewer_lines(effort)[0]


def test_collect_reviews_skips_auto_reviewers(tmp_path: Path):
    db = tmp_path / "app.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE reviews (id INTEGER PRIMARY KEY, run_id TEXT, reviewer TEXT, decision TEXT, decided_at TEXT)"
        )
        conn.executemany(
            "INSERT INTO reviews (run_id, reviewer, decision, decided_at) VALUES (?, ?, ?, ?)",
            [
                ("r1", "eval-auto-reviewer", "approve", "1"),
                ("r2", "binh", "reject", "2"),
                ("r2", "binh", "approve", "3"),
            ],
        )
    values = {"previous_files": {"a.sql": "x\n"}, "code_files": {"a.sql": "y\n"}, "test_files": {}}
    runs = collect_reviews(db, lambda _run_id: values)
    assert runs == [
        {"run_id": "r2", "decisions": ["reject", "approve"], "changed_lines": 2, "reviewer": "binh", "day": "3"}
    ]
    assert "binh 3" in reviewer_lines(reviewer_effort(runs))[0]


def test_check_de_uses_golden_comparer(tmp_path: Path):
    db = tmp_path / "dev.duckdb"
    expected = (ROOT / "eval" / "datasets" / "golden" / "g01_three_sources" / "expected.csv").as_posix()
    with duckdb.connect(str(db)) as con:
        con.execute(f"CREATE TABLE fct AS SELECT * FROM read_csv_auto('{expected}')")
    assert check_de.check("g01_three_sources", db, "fct")[0]
    assert not check_de.check("g02_duplicate_rows", db, "fct")[0]
    ok, detail = check_de.check("g01_three_sources", db, "fct; drop table fct")
    assert not ok and "không hợp lệ" in detail

"""Bảng WORKLOG.md phải đúng 5 ô mỗi dòng, không dòng trống chen giữa (chạy trong CI)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_worklog", ROOT / "scripts" / "check_worklog.py")
check_worklog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_worklog)

HEADER = "| Member | Task | Status | Output | Time |\n|---|---|---|---|---|\n"


def test_repo_worklog_is_valid():
    assert check_worklog.check((ROOT / "WORKLOG.md").read_text(encoding="utf-8")) == []


def test_checker_catches_bad_rows():
    bad_cells = HEADER + "| a | b | ✅ Done | c | d | e |\n"
    assert any("ô" in e for e in check_worklog.check(bad_cells))
    assert any("Status" in e for e in check_worklog.check(HEADER + "| a | b | WIP | c | — |\n"))
    blank_inside = HEADER + "| a | b | ✅ Done | c | — |\n\n| a | b | ✅ Done | c | — |\n"
    assert any("trống chen" in e for e in check_worklog.check(blank_inside))
    assert check_worklog.check(HEADER + "| a | b | ✅ Done | c | ~2h |\n") == []

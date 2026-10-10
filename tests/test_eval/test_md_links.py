"""Không có liên kết tương đối chết trong các file .md của repo (chạy trong CI)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_md_links", ROOT / "scripts" / "check_md_links.py")
check_md_links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_md_links)


def test_no_broken_relative_links():
    errors = [e for path in check_md_links.markdown_files() for e in check_md_links.broken_links(path)]
    assert errors == []


def test_checker_detects_a_broken_link(tmp_path):
    page = tmp_path / "a.md"
    page.write_text("[x](khong-co.md) và `[code](bo-qua.md)`\n", encoding="utf-8")
    check_md_links.ROOT = tmp_path
    try:
        assert len(check_md_links.broken_links(page)) == 1
    finally:
        check_md_links.ROOT = ROOT

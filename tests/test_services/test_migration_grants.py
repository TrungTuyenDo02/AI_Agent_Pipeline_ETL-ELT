"""Mọi bảng migration tạo trên PostgreSQL phải được GRANT cho tài khoản ứng dụng (p113_app chỉ có quyền DML được cấp).

Test chạy trên SQLite nên không bắt được thiếu quyền; quét mã migration (V, 0 token) thay vào đó.
Lỗi từng gặp: 0007 tạo `glossary_terms` mà không GRANT → "permission denied" trên Neon (sửa ở 0009).
"""

import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
CREATED = re.compile(r"create_table\(\s*\"(\w+)\"")
GRANTED = re.compile(r"GRANT\s+[A-Z, ]+\s+ON\s+(?!SEQUENCE)([\w, ]+?)\s+TO", re.IGNORECASE)


def _scan() -> tuple[set[str], set[str]]:
    created, granted = set(), set()
    for path in VERSIONS.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        created |= set(CREATED.findall(source))
        for names in GRANTED.findall(source):
            granted |= {name.strip() for name in names.split(",")}
    return created, granted


def test_every_created_table_is_granted_to_app_role():
    created, granted = _scan()
    assert {"glossary_terms", "llm_calls", "budget_counters"} <= created  # bộ quét còn nhận ra bảng
    assert created - granted == set()

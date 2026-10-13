"""Sổ lỗi (SQLite hoặc PostgreSQL): ghi lỗi V-node, tìm mục giống đã được Reviewer duyệt để gợi ý cho Codegen.

Mục mới mặc định `approved=False`; chỉ mục đã duyệt mới được đưa vào prompt (tối đa 3), và chỉ là gợi ý.
`warnings` cho người duyệt thấy mục có chữ giống lệnh cài cắm / bí mật (chỉ cảnh báo, không chặn).
"""

import hashlib
import re
from pathlib import Path

from sqlalchemy import Engine, text

from src.agents.tools.injection_scan import scan_text
from src.config import get_settings
from src.models.evidence import ErrorEntry
from src.services.state_db import is_postgres, state_engine

MAX_HINTS = 3
# Chỉ dùng cho SQLite; trên PostgreSQL bảng do Alembic tạo (migration 0003_state_tables).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS error_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    signature TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    cause TEXT NOT NULL DEFAULT '',
    fix TEXT NOT NULL DEFAULT '',
    sql_before TEXT NOT NULL DEFAULT '',
    sql_after TEXT NOT NULL DEFAULT '',
    occurrences INTEGER NOT NULL DEFAULT 1,
    approved INTEGER NOT NULL DEFAULT 0
);
"""
_CODES = (
    ("SAFETY_BLOCKED", re.compile(r"bị chặn|không có trong danh mục|không hợp lệ", re.I)),
    ("BINDER_ERROR", re.compile(r"binder error|could not be resolved|not found", re.I)),
    ("PARSER_ERROR", re.compile(r"parser error|syntax|cú pháp", re.I)),
    ("CONVERSION_ERROR", re.compile(r"conversion error|could not convert", re.I)),
    ("TEST_FAILURE", re.compile(r"\bfail\b|got \d+ results", re.I)),
    ("TIMEOUT", re.compile(r"timeout|thời gian", re.I)),
)


def classify_error(message: str) -> str:
    """Mã lỗi ngắn theo nội dung thông báo."""
    return next((code for code, pattern in _CODES if pattern.search(message)), "UNKNOWN")


def error_signature(message: str) -> str:
    """Chữ ký lỗi: bỏ số, đường dẫn, chuỗi trong nháy rồi băm — cùng loại lỗi cho cùng chữ ký."""
    text_ = message.lower()
    text_ = re.sub(r"[a-z]:[\\/][^\s'\"]+|/[^\s'\"]+", "<path>", text_)
    text_ = re.sub(r"'[^']*'|\"[^\"]*\"", "<str>", text_)
    text_ = re.sub(r"\d+", "<n>", text_)
    text_ = re.sub(r"\s+", " ", text_).strip()
    return hashlib.sha1(text_.encode("utf-8")).hexdigest()[:12]


class ErrorMemory:
    """Truy cập bảng `error_entries`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.engine: Engine = state_engine(path)
        if not is_postgres(self.engine):
            with self.engine.begin() as conn:
                for statement in _SCHEMA.split(";"):
                    if statement.strip():
                        conn.execute(text(statement))

    def record(self, entry: ErrorEntry) -> ErrorEntry:
        """Thêm lỗi mới hoặc tăng số lần gặp nếu chữ ký đã có."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO error_entries (code, signature, description, sql_before) "
                    "VALUES (:code, :signature, :description, :sql_before) "
                    "ON CONFLICT(signature) DO UPDATE SET occurrences = error_entries.occurrences + 1"
                ),
                {
                    "code": entry.code,
                    "signature": entry.signature,
                    "description": entry.description[:2000],
                    "sql_before": entry.sql_before[:4000],
                },
            )
            row = (
                conn.execute(text("SELECT * FROM error_entries WHERE signature=:s"), {"s": entry.signature})
                .mappings()
                .one()
            )
        return _to_entry(row)

    def approved_hints(self, signature: str, code: str) -> list[ErrorEntry]:
        """Tối đa 3 mục ĐÃ DUYỆT: cùng chữ ký trước, rồi cùng mã lỗi."""
        with self.engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT * FROM error_entries WHERE approved=1 AND (signature=:s OR code=:c) "
                        "ORDER BY CASE WHEN signature=:s THEN 0 ELSE 1 END, occurrences DESC LIMIT :n"
                    ),
                    {"s": signature, "c": code, "n": MAX_HINTS},
                )
                .mappings()
                .all()
            )
        return [_to_entry(r) for r in rows]

    def pending(self) -> list[ErrorEntry]:
        """Các mục chờ Reviewer duyệt."""
        with self.engine.connect() as conn:
            rows = (
                conn.execute(text("SELECT * FROM error_entries WHERE approved=0 ORDER BY occurrences DESC"))
                .mappings()
                .all()
            )
        return [_to_entry(r) for r in rows]

    def approve(self, entry_id: int, fix: str) -> bool:
        """Reviewer duyệt một mục (kèm cách sửa). Trả False nếu không có mục đó."""
        with self.engine.begin() as conn:
            cur = conn.execute(
                text("UPDATE error_entries SET approved=1, fix=:fix WHERE id=:id"), {"fix": fix, "id": entry_id}
            )
        return cur.rowcount > 0

    def discard(self, entry_id: int) -> bool:
        """Bỏ một mục không hữu ích."""
        with self.engine.begin() as conn:
            cur = conn.execute(text("DELETE FROM error_entries WHERE id=:id"), {"id": entry_id})
        return cur.rowcount > 0


def _to_entry(row) -> ErrorEntry:  # noqa: ANN001 — RowMapping của SQLAlchemy
    data = dict(row)
    data["approved"] = bool(data["approved"])
    # Mục đã duyệt được đưa vào prompt Codegen → cảnh báo người duyệt nếu nội dung giống lệnh cài cắm hoặc lộ bí mật
    data["warnings"] = scan_text(data["description"], data["cause"], data["fix"], data["sql_before"])
    return ErrorEntry(**data)


def get_error_memory() -> ErrorMemory:
    """Sổ lỗi dùng chung file SQLite với store (hoặc cùng PostgreSQL khi STATE_BACKEND=postgres)."""
    return ErrorMemory(get_settings().store_path)

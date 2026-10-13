"""Bộ nhớ dài hạn của agent (CLAUDE.md mục 8 và 13): bảng `memory_items`.

Quy tắc:
- Mục do agent tự ghi luôn ở trạng thái `pending`; chỉ mục `approved` mới được đưa vào prompt (tối đa `MAX_ITEMS`).
- Mỗi mục thuộc một tài khoản; mọi truy vấn đều lọc theo tài khoản, agent không đọc được bộ nhớ của người khác.
- Trước khi dùng lại, nội dung được quét mẫu lệnh độc hại/bí mật (`warnings`, chỉ cảnh báo người duyệt, không chặn).
- Tìm theo loại + từ khóa (chưa dùng vector). Cột `embedding` để trống, sau này thêm pgvector không phải làm lại bảng.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Engine, text

from src.agents.tools.injection_scan import scan_text
from src.config import get_settings
from src.services.state_db import is_postgres, state_engine

MAX_ITEMS = 3
MAX_CONTENT = 2000
KINDS = ("error_fix", "pipeline_pattern", "preference", "chat_summary")

# Chỉ dùng cho SQLite; trên PostgreSQL bảng do Alembic tạo (migration 0003_state_tables).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved')),
    content_hash TEXT NOT NULL,
    source_run_id TEXT NOT NULL DEFAULT '',
    warnings TEXT NOT NULL DEFAULT '[]',
    embedding TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (account, content_hash)
);
"""


class MemoryItem(BaseModel):
    id: int
    account: str
    kind: str
    content: str
    status: str
    source_run_id: str = ""
    warnings: list[str] = []
    created_at: str = ""


def _hash(content: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", content.strip().lower()).encode("utf-8")).hexdigest()


class AgentMemory:
    """Truy cập bảng `memory_items`, luôn theo tài khoản."""

    def __init__(self, path: Path) -> None:
        self.engine: Engine = state_engine(path)
        self._pg = is_postgres(self.engine)
        if not self._pg:
            with self.engine.begin() as conn:
                conn.execute(text(_SCHEMA))

    def add(self, account: str, kind: str, content: str, source_run_id: str = "") -> MemoryItem | None:
        """Agent đề xuất một mục (luôn `pending`). Trùng nội dung của cùng tài khoản thì trả mục cũ."""
        content = content.strip()[:MAX_CONTENT]
        if not account or not content or kind not in KINDS:
            return None
        warnings = scan_text(content)
        now = datetime.now(UTC)
        params = {
            "account": account,
            "kind": kind,
            "content": content,
            "hash": _hash(content),
            "run": source_run_id,
            "warnings": json.dumps(warnings, ensure_ascii=False),
            "now": now if self._pg else now.isoformat(timespec="seconds"),
        }
        cast = "CAST(:warnings AS JSONB)" if self._pg else ":warnings"
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO memory_items (account, kind, content, content_hash, source_run_id, warnings, created_at) "
                    f"VALUES (:account, :kind, :content, :hash, :run, {cast}, :now) "
                    "ON CONFLICT (account, content_hash) DO NOTHING"
                ),
                params,
            )
            row = (
                conn.execute(
                    text("SELECT * FROM memory_items WHERE account=:account AND content_hash=:hash"),
                    {"account": account, "hash": params["hash"]},
                )
                .mappings()
                .one()
            )
        return _to_item(row)

    def pending(self, account: str) -> list[MemoryItem]:
        """Các mục của tài khoản đang chờ duyệt (mới nhất trước)."""
        return self._select("account=:account AND status='pending'", {"account": account}, "id DESC", 100)

    def approved(self, account: str, kind: str | None = None, query: str = "") -> list[MemoryItem]:
        """Tối đa `MAX_ITEMS` mục ĐÃ DUYỆT của tài khoản, ưu tiên mục chứa nhiều từ khóa trong `query`."""
        where = "account=:account AND status='approved'"
        params: dict[str, object] = {"account": account}
        if kind:
            where += " AND kind=:kind"
            params["kind"] = kind
        items = self._select(where, params, "id DESC", 50)
        words = {w for w in re.findall(r"\w{3,}", query.lower())}
        if words:
            items.sort(key=lambda item: -sum(1 for w in words if w in item.content.lower()))
        return items[:MAX_ITEMS]

    def approve(self, account: str, item_id: int) -> bool:
        """Người duyệt đồng ý cho dùng lại. Chỉ tác động tới mục của chính tài khoản đó."""
        with self.engine.begin() as conn:
            cur = conn.execute(
                text("UPDATE memory_items SET status='approved' WHERE id=:id AND account=:account"),
                {"id": item_id, "account": account},
            )
        return cur.rowcount > 0

    def discard(self, account: str, item_id: int) -> bool:
        with self.engine.begin() as conn:
            cur = conn.execute(
                text("DELETE FROM memory_items WHERE id=:id AND account=:account"), {"id": item_id, "account": account}
            )
        return cur.rowcount > 0

    def _select(self, where: str, params: dict[str, object], order: str, limit: int) -> list[MemoryItem]:
        with self.engine.connect() as conn:
            rows = (
                conn.execute(text(f"SELECT * FROM memory_items WHERE {where} ORDER BY {order} LIMIT {limit}"), params)
                .mappings()
                .all()
            )
        return [_to_item(r) for r in rows]


def _to_item(row) -> MemoryItem:  # noqa: ANN001 — RowMapping của SQLAlchemy
    data = dict(row)
    warnings = data.get("warnings")
    if isinstance(warnings, str):
        warnings = json.loads(warnings or "[]")
    created = data.get("created_at")
    return MemoryItem(
        id=data["id"],
        account=data["account"],
        kind=data["kind"],
        content=data["content"],
        status=data["status"],
        source_run_id=data.get("source_run_id", ""),
        warnings=[str(w) for w in (warnings or [])],
        created_at=created.isoformat(timespec="seconds") if hasattr(created, "isoformat") else str(created or ""),
    )


def get_agent_memory() -> AgentMemory:
    return AgentMemory(get_settings().store_path)

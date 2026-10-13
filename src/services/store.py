"""Kho lưu trữ SQLite cho các lần chạy và quyết định duyệt (dùng chung CLI và API)."""

import json
import logging
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from src.config import get_settings
from src.models.evidence import ReviewDecision
from src.models.schemas import RunRecord, RunStatus

logger = logging.getLogger(__name__)
VN_TZ = timezone(timedelta(hours=7))  # "hôm nay" của trần chi phí tính theo giờ Việt Nam
INTERRUPTED = "Server khởi động lại khi lần chạy đang chạy nên lần chạy bị dừng. Hãy tạo lại yêu cầu."

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    request_text TEXT NOT NULL,
    requester TEXT NOT NULL,
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    decided_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    """Truy cập bảng `runs` và `reviews`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_run(self, request_text: str, requester: str) -> RunRecord:
        """Tạo lần chạy mới với provider/model hiện tại."""
        settings = get_settings()
        model = settings.models_summary
        now = _now()
        record = RunRecord(
            id=uuid.uuid4().hex[:10],
            request_text=request_text,
            requester=requester,
            status=RunStatus.RUNNING,
            provider=settings.llm_provider,
            model=model,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record.id, request_text, requester, record.status, record.provider, model, now, now, "{}"),
            )
        return record

    def update_run(self, run_id: str, status: RunStatus, summary: dict | None = None) -> None:
        """Cập nhật trạng thái (và tóm tắt nếu có) của một lần chạy."""
        with self._connect() as conn:
            if summary is None:
                conn.execute("UPDATE runs SET status=?, updated_at=? WHERE id=?", (status, _now(), run_id))
            else:
                conn.execute(
                    "UPDATE runs SET status=?, updated_at=?, summary=? WHERE id=?",
                    (status, _now(), json.dumps(summary, ensure_ascii=False, default=str), run_id),
                )

    def fail_interrupted_runs(self) -> int:
        """Lúc khởi động: lần chạy còn `running` không còn tiến trình nào chạy → đánh dấu lỗi kèm lý do."""
        with self._connect() as conn:
            rows = conn.execute("SELECT id, summary FROM runs WHERE status=?", (RunStatus.RUNNING,)).fetchall()
            for row in rows:
                summary = {**json.loads(row["summary"] or "{}"), "error": INTERRUPTED}
                conn.execute(
                    "UPDATE runs SET status=?, updated_at=?, summary=? WHERE id=?",
                    (RunStatus.FAILED, _now(), json.dumps(summary, ensure_ascii=False), row["id"]),
                )
        return len(rows)

    def spent_today(self, requester: str) -> float:
        """Chi phí LLM thật (USD) của các lần chạy người này tạo hôm nay (giờ VN); bỏ lần chạy mô phỏng."""
        start = datetime.now(VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT summary FROM runs WHERE requester=? AND created_at>=?",
                (requester, start.isoformat(timespec="seconds")),
            ).fetchall()
        total = 0.0
        for row in rows:
            summary = json.loads(row["summary"] or "{}")
            if not summary.get("simulated"):
                total += float(summary.get("cost_usd") or 0.0)
        return round(total, 6)

    def get_run(self, run_id: str) -> RunRecord | None:
        """Lấy một lần chạy theo id; không có thì trả None."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return _to_record(row) if row else None

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        """Danh sách lần chạy mới nhất trước."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)).fetchall()
        return [_to_record(r) for r in rows]

    def add_review(self, decision: ReviewDecision) -> None:
        """Ghi lại quyết định approve/reject."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO reviews (run_id, reviewer, decision, note, decided_at) VALUES (?, ?, ?, ?, ?)",
                (decision.run_id, decision.reviewer, decision.decision, decision.note, decision.decided_at),
            )

    def list_reviews(self, run_id: str) -> list[ReviewDecision]:
        """Các quyết định duyệt của một lần chạy, cũ trước."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM reviews WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        return [
            ReviewDecision(**{k: r[k] for k in ("run_id", "reviewer", "decision", "note", "decided_at")}) for r in rows
        ]

    def ping(self) -> bool:
        """Kiểm tra kết nối (dùng cho `/health`)."""
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1")
            return True
        except sqlite3.Error as exc:
            logger.error("store ping failed", extra={"error": str(exc)})
            return False


def _to_record(row: sqlite3.Row) -> RunRecord:
    data = dict(row)
    data["summary"] = json.loads(data["summary"] or "{}")
    return RunRecord(**data)


def get_store() -> Store:
    """Tạo Store theo đường dẫn trong cấu hình."""
    return Store(get_settings().store_path)

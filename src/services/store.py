"""Kho lưu trữ cho các lần chạy và quyết định duyệt (dùng chung CLI và API).

SQLite (demo, test) hoặc PostgreSQL/Neon (triển khai thật) tùy `STATE_BACKEND`, xem `state_db`.
"""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import Engine, text

from src.config import get_settings
from src.models.evidence import ReviewDecision
from src.models.schemas import RunRecord, RunStatus
from src.services.state_db import is_postgres, state_engine

logger = logging.getLogger(__name__)
VN_TZ = timezone(timedelta(hours=7))  # "hôm nay" của trần chi phí tính theo giờ Việt Nam
INTERRUPTED = "Server khởi động lại khi lần chạy đang chạy nên lần chạy bị dừng. Hãy tạo lại yêu cầu."

# Chỉ dùng cho SQLite; trên PostgreSQL bảng do Alembic tạo (migration 0003_state_tables).
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


def _value(item: object) -> str:
    """Giá trị chuỗi của enum (hoặc chuỗi thường)."""
    return str(getattr(item, "value", item))


class Store:
    """Truy cập bảng `runs` và `reviews`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.engine: Engine = state_engine(path)
        self._pg = is_postgres(self.engine)
        if not self._pg:
            with self.engine.begin() as conn:
                for statement in _SCHEMA.split(";"):
                    if statement.strip():
                        conn.execute(text(statement))

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
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO runs (id, request_text, requester, status, provider, model, created_at, updated_at, summary) "
                    "VALUES (:id, :request_text, :requester, :status, :provider, :model, :now, :now, '{}')"
                ),
                {
                    "id": record.id,
                    "request_text": request_text,
                    "requester": requester,
                    "status": _value(record.status),
                    "provider": record.provider,
                    "model": model,
                    "now": now,
                },
            )
        return record

    def update_run(self, run_id: str, status: RunStatus, summary: dict | None = None) -> None:
        """Cập nhật trạng thái (và tóm tắt nếu có) của một lần chạy."""
        with self.engine.begin() as conn:
            if summary is None:
                conn.execute(
                    text("UPDATE runs SET status=:status, updated_at=:now WHERE id=:id"),
                    {"status": _value(status), "now": _now(), "id": run_id},
                )
            else:
                conn.execute(
                    text("UPDATE runs SET status=:status, updated_at=:now, summary=:summary WHERE id=:id"),
                    {
                        "status": _value(status),
                        "now": _now(),
                        "summary": json.dumps(summary, ensure_ascii=False, default=str),
                        "id": run_id,
                    },
                )

    def fail_interrupted_runs(self) -> int:
        """Lúc khởi động: lần chạy còn `running` không còn tiến trình nào chạy → đánh dấu lỗi kèm lý do."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id, summary FROM runs WHERE status=:s"), {"s": _value(RunStatus.RUNNING)}
            ).all()
            for row in rows:
                summary = {**json.loads(row.summary or "{}"), "error": INTERRUPTED}
                conn.execute(
                    text("UPDATE runs SET status=:status, updated_at=:now, summary=:summary WHERE id=:id"),
                    {
                        "status": _value(RunStatus.FAILED),
                        "now": _now(),
                        "summary": json.dumps(summary, ensure_ascii=False),
                        "id": row.id,
                    },
                )
        return len(rows)

    def spent_today(self, requester: str) -> float:
        """Chi phí LLM thật (USD) của các lần chạy người này tạo hôm nay (giờ VN); bỏ lần chạy mô phỏng."""
        start = datetime.now(VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT summary FROM runs WHERE requester=:r AND created_at>=:t"),
                {"r": requester, "t": start.isoformat(timespec="seconds")},
            ).all()
        total = 0.0
        for row in rows:
            summary = json.loads(row.summary or "{}")
            if not summary.get("simulated"):
                total += float(summary.get("cost_usd") or 0.0)
        return round(total, 6)

    def runs_today(self, requester: str) -> int:
        """Số lần chạy người này tạo hôm nay (giờ VN); lần bị chặn ở cửa kiểm tra đầu vào KHÔNG tính vào hạn mức."""
        start = datetime.now(VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        with self.engine.connect() as conn:
            return conn.execute(
                text("SELECT count(*) FROM runs WHERE requester=:r AND created_at>=:t AND status!=:s"),
                {"r": requester, "t": start.isoformat(timespec="seconds"), "s": _value(RunStatus.REJECTED_INPUT)},
            ).scalar_one()

    def get_run(self, run_id: str) -> RunRecord | None:
        """Lấy một lần chạy theo id; không có thì trả None."""
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM runs WHERE id=:id"), {"id": run_id}).mappings().first()
        return _to_record(row) if row else None

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        """Danh sách lần chạy mới nhất trước."""
        order = "seq" if self._pg else "rowid"  # cùng giây thì lần tạo sau xếp trước
        with self.engine.connect() as conn:
            rows = (
                conn.execute(text(f"SELECT * FROM runs ORDER BY created_at DESC, {order} DESC LIMIT :n"), {"n": limit})
                .mappings()
                .all()
            )
        return [_to_record(r) for r in rows]

    def add_review(self, decision: ReviewDecision) -> None:
        """Ghi lại quyết định approve/reject."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO reviews (run_id, reviewer, decision, note, decided_at) "
                    "VALUES (:run_id, :reviewer, :decision, :note, :decided_at)"
                ),
                {
                    "run_id": decision.run_id,
                    "reviewer": decision.reviewer,
                    "decision": _value(decision.decision),
                    "note": decision.note,
                    "decided_at": decision.decided_at,
                },
            )

    def list_reviews(self, run_id: str) -> list[ReviewDecision]:
        """Các quyết định duyệt của một lần chạy, cũ trước."""
        with self.engine.connect() as conn:
            rows = (
                conn.execute(text("SELECT * FROM reviews WHERE run_id=:id ORDER BY id"), {"id": run_id})
                .mappings()
                .all()
            )
        return [
            ReviewDecision(**{k: r[k] for k in ("run_id", "reviewer", "decision", "note", "decided_at")}) for r in rows
        ]

    def ping(self) -> bool:
        """Kiểm tra kết nối (dùng cho `/health`)."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:  # noqa: BLE001 — health chỉ báo ok/error, không làm sập endpoint
            logger.error("store ping failed", extra={"error": type(exc).__name__})
            return False


def _to_record(row) -> RunRecord:  # noqa: ANN001 — RowMapping của SQLAlchemy
    data = dict(row)
    data.pop("seq", None)
    data["summary"] = json.loads(data["summary"] or "{}")
    return RunRecord(**data)


def get_store() -> Store:
    """Tạo Store theo đường dẫn trong cấu hình."""
    return Store(get_settings().store_path)

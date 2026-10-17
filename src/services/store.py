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
INTERRUPTED_PAUSING = (
    "Server khởi động lại khi lần chạy đang chờ tạm dừng. Lần chạy đã tạm dừng ở bước cuối cùng đã lưu; "
    "bấm Tiếp tục để làm lại bước đang dở."
)
# Cột `pause_requested` chỉ đúng khi lần chạy còn đang chạy: dòng yêu cầu sót lại (tranh chấp hiếm) không đổi nghĩa trạng thái
_SELECT_RUNS = (
    "SELECT runs.*, CASE WHEN c.run_id IS NOT NULL AND runs.status = 'running' THEN 1 ELSE 0 END AS pause_requested "
    "FROM runs LEFT JOIN run_controls c ON c.run_id = runs.id"
)

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
CREATE TABLE IF NOT EXISTS run_controls (
    run_id TEXT PRIMARY KEY,
    pause_requested_by TEXT NOT NULL,
    pause_requested_at TEXT NOT NULL
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
        """Cập nhật trạng thái (và tóm tắt nếu có) của một lần chạy.

        Sang trạng thái khác `running` (chờ người, xong, lỗi, đã tạm dừng) thì bỏ yêu cầu tạm dừng còn treo trong CÙNG giao
        dịch: kết quả cuối không bao giờ bị ghi đè thành "đang chờ tạm dừng".
        """
        with self.engine.begin() as conn:
            if _value(status) != _value(RunStatus.RUNNING):
                conn.execute(text("DELETE FROM run_controls WHERE run_id=:id"), {"id": run_id})
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

    def request_pause(self, run_id: str, by: str) -> bool:
        """Ghi yêu cầu tạm dừng (bền vững, tải lại trang không mất) nếu lần chạy CÒN đang chạy; bấm lặp không tạo thêm dòng.

        Trả True khi lần chạy đang có yêu cầu tạm dừng sau lệnh này (mới ghi hoặc đã có từ trước).
        """
        params = {"id": run_id, "by": by, "now": _now(), "running": _value(RunStatus.RUNNING)}
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO run_controls (run_id, pause_requested_by, pause_requested_at) "
                    "SELECT :id, :by, :now WHERE EXISTS (SELECT 1 FROM runs WHERE id=:id AND status=:running) "
                    "ON CONFLICT (run_id) DO NOTHING"
                ),
                params,
            )
            return (
                conn.execute(
                    text(
                        "SELECT 1 FROM run_controls c JOIN runs r ON r.id = c.run_id "
                        "WHERE c.run_id=:id AND r.status=:running"
                    ),
                    params,
                ).first()
                is not None
            )

    def take_pause(self, run_id: str) -> bool:
        """Runner gọi ở ranh giới giữa hai node: có yêu cầu tạm dừng thì nhận (xóa dòng) và trả True."""
        with self.engine.begin() as conn:
            return conn.execute(text("DELETE FROM run_controls WHERE run_id=:id"), {"id": run_id}).rowcount == 1

    def clear_pause(self, run_id: str) -> None:
        """Bỏ yêu cầu tạm dừng cũ (lúc đưa một lượt chạy mới vào hàng đợi)."""
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM run_controls WHERE run_id=:id"), {"id": run_id})

    def fail_interrupted_runs(self) -> int:
        """Lúc khởi động: lần chạy còn `running` không còn tiến trình nào chạy → đánh dấu lỗi kèm lý do.

        Lần chạy đang chờ tạm dừng thì thành "đã tạm dừng" (người dùng đã muốn dừng; checkpoint cuối vẫn dùng được để tiếp tục).
        """
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT runs.id, runs.summary, c.run_id AS pausing FROM runs "
                    "LEFT JOIN run_controls c ON c.run_id = runs.id WHERE runs.status=:s"
                ),
                {"s": _value(RunStatus.RUNNING)},
            ).all()
            for row in rows:
                pausing = row.pausing is not None
                note = {"notice": INTERRUPTED_PAUSING} if pausing else {"error": INTERRUPTED}
                summary = {**json.loads(row.summary or "{}"), **note}
                conn.execute(
                    text("UPDATE runs SET status=:status, updated_at=:now, summary=:summary WHERE id=:id"),
                    {
                        "status": _value(RunStatus.PAUSED if pausing else RunStatus.FAILED),
                        "now": _now(),
                        "summary": json.dumps(summary, ensure_ascii=False),
                        "id": row.id,
                    },
                )
                conn.execute(text("DELETE FROM run_controls WHERE run_id=:id"), {"id": row.id})
        return len(rows)

    def spent_today(self, requester: str) -> float:
        """Chi phí LLM thật (USD) của các lần chạy người này tạo hôm nay (giờ VN); bỏ lần chạy mô phỏng.

        Chỉ để thống kê theo lần chạy. Hạn mức tiền dùng sổ chi phí (`cost_ledger.spent_today`): tính theo ngày gọi, đủ cả
        lượt thất bại và "Hỏi AI".
        """
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
            row = conn.execute(text(f"{_SELECT_RUNS} WHERE runs.id=:id"), {"id": run_id}).mappings().first()
        return _to_record(row) if row else None

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        """Danh sách lần chạy mới nhất trước."""
        order = "runs.seq" if self._pg else "runs.rowid"  # cùng giây thì lần tạo sau xếp trước
        with self.engine.connect() as conn:
            rows = (
                conn.execute(text(f"{_SELECT_RUNS} ORDER BY runs.created_at DESC, {order} DESC LIMIT :n"), {"n": limit})
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
    data["pause_requested"] = bool(data.get("pause_requested"))
    return RunRecord(**data)


def get_store() -> Store:
    """Tạo Store theo đường dẫn trong cấu hình."""
    return Store(get_settings().store_path)

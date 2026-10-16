"""Sổ chi phí LLM và giữ trước ngân sách (ADR 0014). Bước V: code thuần, 0 token.

Mỗi lượt gọi LLM thật một dòng `llm_calls` (chỉ metadata: người, run, task, model, token, tiền; KHÔNG lưu prompt hay phản hồi).
Trước khi gọi: giữ trước khoản dự toán trên bảng đếm `budget_counters` (run → người/ngày → toàn hệ thống/ngày) bằng một câu
UPDATE có điều kiện, nên hai job không cùng dùng một phần ngân sách còn lại (SQLite lẫn PostgreSQL).
Sau khi gọi: quyết toán đúng một lần → `settled` (có usage), `released` (chắc chắn không tính tiền) hoặc `unknown`
(đã gửi mà không có usage: khoản dự toán vẫn tính vào ngân sách cho tới khi đối soát tay).
Tiền lưu bằng micro-USD (số nguyên) để cộng trừ không lệch. Ngày tính theo giờ Việt Nam, lúc giữ trước.
"""

import math
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import Connection, Engine, text

from src.config import Settings, get_settings
from src.services.state_db import is_postgres, state_engine

VN_TZ = timezone(timedelta(hours=7))
SYSTEM_OWNER = "system"  # lượt gọi không gắn người dùng (eval, CLI không qua run): chỉ áp trần toàn hệ thống
RESERVED, SETTLED, RELEASED, UNKNOWN = "reserved", "settled", "released", "unknown"

# Chỉ dùng cho SQLite; trên PostgreSQL bảng do Alembic tạo (migration 0008_llm_cost_ledger).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_calls (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    run_id TEXT NOT NULL DEFAULT '',
    task TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    day TEXT NOT NULL,
    status TEXT NOT NULL,
    reserved_micros INTEGER NOT NULL,
    cost_micros INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_llm_calls_status ON llm_calls (status, expires_at);
CREATE TABLE IF NOT EXISTS budget_counters (
    scope TEXT NOT NULL,
    subject TEXT NOT NULL,
    day TEXT NOT NULL,
    reserved_micros INTEGER NOT NULL DEFAULT 0,
    spent_micros INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scope, subject, day)
);
"""

_LIMIT_TEXT = {
    "run": ("lần chạy này", "USD/lần chạy (RUN_COST_BUDGET_USD)"),
    "user": ("hôm nay bạn", "USD/người/ngày (LLM_DAILY_BUDGET_USD)"),
    "global": ("toàn hệ thống hôm nay", "USD/ngày cho cả hệ thống (LLM_GLOBAL_DAILY_BUDGET_USD)"),
}


class BudgetDeniedError(RuntimeError):
    """Không đủ ngân sách để giữ trước lượt gọi; thông báo tiếng Việt."""


def to_micros(usd: float, round_up: bool = False) -> int:
    value = usd * 1_000_000
    return math.ceil(value - 1e-9) if round_up else round(value)


def to_usd(micros: int) -> float:
    return round(micros / 1_000_000, 6)


_CALLER: ContextVar[tuple[str, str]] = ContextVar("llm_caller", default=(SYSTEM_OWNER, ""))


@contextmanager
def llm_caller(owner: str, run_id: str = "") -> Iterator[None]:
    """Gắn người dùng (+ run) cho mọi lượt gọi LLM trong khối này: runner bọc mỗi lượt chạy graph, API bọc "Hỏi AI"."""
    token = _CALLER.set((owner or SYSTEM_OWNER, run_id))
    try:
        yield
    finally:
        _CALLER.reset(token)


def current_caller() -> tuple[str, str]:
    """(người dùng, run_id) của lượt gọi hiện tại; ngoài khối `llm_caller` là (`system`, "")."""
    return _CALLER.get()


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def _scopes(owner: str, run_id: str, day: str, settings: Settings) -> list[tuple[str, str, str, int]]:
    """(phạm vi, chủ thể, ngày, trần micro-USD; 0 = không chặn), luôn cùng thứ tự để hai giao dịch không khóa chéo nhau."""
    scopes = [("run", run_id, "", to_micros(settings.run_cost_budget_usd))] if run_id else []
    user_limit = 0 if owner == SYSTEM_OWNER else to_micros(settings.llm_daily_budget_usd)
    scopes.append(("user", owner, day, user_limit))
    scopes.append(("global", "*", day, to_micros(settings.llm_global_daily_budget_usd)))
    return scopes


def _weights(status: str, reserved: int, cost: int) -> tuple[int, int]:
    """Phần (đang giữ, đã tính) mà một lượt gọi chiếm trên bảng đếm ở mỗi trạng thái."""
    return {
        RESERVED: (reserved, 0),
        UNKNOWN: (0, reserved),  # không rõ đã tốn bao nhiêu: tính bằng khoản dự toán, không tự hoàn
        SETTLED: (0, cost),
        RELEASED: (0, 0),
    }[status]


class CostLedger:
    """Truy cập bảng `llm_calls` và `budget_counters` (cùng nơi lưu với bảng `runs`)."""

    def __init__(self, path: Path) -> None:
        self.engine: Engine = state_engine(path)
        if not is_postgres(self.engine):
            with self.engine.begin() as conn:
                for statement in _SCHEMA.split(";"):
                    if statement.strip():
                        conn.execute(text(statement))

    def reserve(
        self,
        *,
        owner: str,
        run_id: str,
        task: str,
        provider: str,
        model: str,
        estimate_usd: float,
        ttl_sec: float,
        now: datetime | None = None,
    ) -> str:
        """Giữ trước `estimate_usd` trên mọi hạn mức áp dụng (cùng một giao dịch); thiếu ở bất kỳ hạn mức nào thì không giữ gì."""
        now = now or _now()
        self.expire_stale(now)
        day = now.astimezone(VN_TZ).date().isoformat()
        amount = to_micros(estimate_usd, round_up=True)
        call_id = uuid.uuid4().hex
        with self.engine.begin() as conn:
            for scope, subject, scope_day, limit in _scopes(owner, run_id, day, get_settings()):
                key = {"s": scope, "k": subject, "d": scope_day, "x": amount, "limit": limit}
                conn.execute(
                    text(
                        "INSERT INTO budget_counters (scope, subject, day, reserved_micros, spent_micros) "
                        "VALUES (:s, :k, :d, 0, 0) ON CONFLICT (scope, subject, day) DO NOTHING"
                    ),
                    key,
                )
                guard = " AND spent_micros + reserved_micros + :x <= :limit" if limit else ""
                result = conn.execute(
                    text(
                        "UPDATE budget_counters SET reserved_micros = reserved_micros + :x "
                        f"WHERE scope=:s AND subject=:k AND day=:d{guard}"
                    ),
                    key,
                )
                if result.rowcount != 1:
                    raise BudgetDeniedError(_denied_message(conn, scope, subject, scope_day, amount, limit))
            conn.execute(
                text(
                    "INSERT INTO llm_calls (id, owner, run_id, task, provider, model, day, status, reserved_micros, "
                    "created_at, updated_at, expires_at) VALUES (:id, :owner, :run_id, :task, :provider, :model, :day, "
                    ":status, :reserved, :now, :now, :expires)"
                ),
                {
                    "id": call_id, "owner": owner, "run_id": run_id, "task": task, "provider": provider, "model": model,
                    "day": day, "status": RESERVED, "reserved": amount, "now": _iso(now),
                    "expires": _iso(now + timedelta(seconds=ttl_sec)),
                },
            )  # fmt: skip
        return call_id

    def settle(
        self, call_id: str, cost_usd: float, input_tokens: int = 0, output_tokens: int = 0, note: str = ""
    ) -> bool:
        """Quyết toán theo usage thật (kể cả phản hồi về muộn sau khi đã chuyển `unknown`). False = đã quyết toán rồi."""
        return self._transition(
            call_id, (RESERVED, UNKNOWN), SETTLED, to_micros(cost_usd), input_tokens, output_tokens, note
        )

    def release(self, call_id: str, note: str = "") -> bool:
        """Hoàn khoản giữ trước: chỉ khi chắc chắn nhà cung cấp không tính tiền lượt này."""
        return self._transition(call_id, (RESERVED,), RELEASED, 0, note=note)

    def mark_unknown(self, call_id: str, note: str = "") -> bool:
        """Đã gửi mà không có usage (timeout, mất kết nối, treo quá hạn): khoản dự toán chuyển thành chi phí tạm."""
        return self._transition(call_id, (RESERVED,), UNKNOWN, None, note=note)

    def reconcile(self, call_id: str, cost_usd: float, note: str = "đối soát tay") -> bool:
        """Đối soát tay một lượt `unknown` (hoặc còn treo) bằng số tiền thật lấy từ trang usage/hóa đơn của nhà cung cấp."""
        return self._transition(call_id, (UNKNOWN, RESERVED), SETTLED, to_micros(cost_usd), note=note)

    def expire_stale(self, now: datetime | None = None) -> int:
        """Lượt giữ trước quá hạn (tiến trình chết, treo) → `unknown`. Không hoàn tiền."""
        with self.engine.connect() as conn:
            ids = conn.execute(
                text("SELECT id FROM llm_calls WHERE status=:s AND expires_at < :now"),
                {"s": RESERVED, "now": _iso(now or _now())},
            ).scalars()
            stale = list(ids)
        return sum(self.mark_unknown(call_id, note="quá hạn chờ phản hồi") for call_id in stale)

    def get_call(self, call_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM llm_calls WHERE id=:id"), {"id": call_id}).mappings().first()
        return dict(row) if row else None

    def list_calls(self, status: str = UNKNOWN, limit: int = 50) -> list[dict]:
        """Các lượt gọi theo trạng thái, mới nhất trước (CLI đối soát)."""
        self.expire_stale()
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM llm_calls WHERE status=:s ORDER BY created_at DESC LIMIT :n"),
                {"s": status, "n": limit},
            ).mappings()
            return [dict(r) for r in rows]

    def used_usd(self, scope: str, subject: str, day: str = "") -> float:
        """Đã tính + đang giữ (USD) của một hạn mức."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT spent_micros + reserved_micros FROM budget_counters WHERE scope=:s AND subject=:k AND day=:d"
                ),
                {"s": scope, "k": subject, "d": day},
            ).first()
        return to_usd(row[0]) if row else 0.0

    def spent_today(self, owner: str) -> float:
        """Chi phí LLM thật hôm nay (giờ VN) của một người, tính theo ngày gọi; gồm cả khoản đang giữ và `unknown`."""
        return self.used_usd("user", owner, _now().astimezone(VN_TZ).date().isoformat())

    def _transition(
        self,
        call_id: str,
        sources: tuple[str, ...],
        target: str,
        cost: int | None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        note: str = "",
    ) -> bool:
        """Đổi trạng thái đúng một lần (WHERE status=cũ) và dời phần chiếm trên bảng đếm tương ứng."""
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM llm_calls WHERE id=:id"), {"id": call_id}).mappings().first()
            if not row or row["status"] not in sources:
                return False
            reserved = row["reserved_micros"]
            new_cost = reserved if target == UNKNOWN else (cost or 0)
            changed = conn.execute(
                text(
                    "UPDATE llm_calls SET status=:to, cost_micros=:cost, input_tokens=:inp, output_tokens=:out, "
                    "note=:note, updated_at=:now WHERE id=:id AND status=:prev"
                ),
                {
                    "to": target, "cost": new_cost, "inp": input_tokens or row["input_tokens"],
                    "out": output_tokens or row["output_tokens"], "note": note or row["note"], "now": _iso(_now()),
                    "id": call_id, "prev": row["status"],
                },
            )  # fmt: skip
            if changed.rowcount != 1:
                return False  # bên khác vừa quyết toán lượt này
            old = _weights(row["status"], reserved, row["cost_micros"])
            new = _weights(target, reserved, new_cost)
            for scope, subject, day, _ in _scopes(row["owner"], row["run_id"], row["day"], get_settings()):
                conn.execute(
                    text(
                        "UPDATE budget_counters SET reserved_micros = reserved_micros + :r, "
                        "spent_micros = spent_micros + :sp WHERE scope=:s AND subject=:k AND day=:d"
                    ),
                    {"r": new[0] - old[0], "sp": new[1] - old[1], "s": scope, "k": subject, "d": day},
                )
        return True


def _denied_message(conn: Connection, scope: str, subject: str, day: str, need: int, limit: int) -> str:
    row = conn.execute(
        text("SELECT spent_micros, reserved_micros FROM budget_counters WHERE scope=:s AND subject=:k AND day=:d"),
        {"s": scope, "k": subject, "d": day},
    ).first()
    spent, held = (row[0], row[1]) if row else (0, 0)
    who, unit = _LIMIT_TEXT[scope]
    return (
        f"Không đủ ngân sách để giữ trước lượt gọi này: {who} đã dùng {to_usd(spent):.4f} USD, đang giữ "
        f"{to_usd(held):.4f} USD, lượt này cần giữ tối đa {to_usd(need):.4f} USD, trần {to_usd(limit):.2f} {unit}. "
        "Liên hệ quản trị viên nếu cần thêm."
    )


def get_ledger() -> CostLedger:
    """Sổ chi phí theo đường dẫn trong cấu hình (cùng nơi lưu với `runs`)."""
    return CostLedger(get_settings().store_path)

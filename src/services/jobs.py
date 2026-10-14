"""Hàng đợi chạy nền cho API: graph chạy lâu (tới vài phút) nên API trả về ngay, web hỏi tiến trình định kỳ.

Các lần chạy được xếp hàng: với SQLite **lần lượt trên một luồng** (checkpointer dùng chung một kết nối nên không chạy
song song, đủ cho bản demo); với PostgreSQL chạy tối đa `RUN_WORKERS` lần cùng lúc. Tiến trình từng bước giữ trong bộ nhớ (mất khi khởi động lại; trạng thái và
kết quả vẫn nằm trong store/checkpointer).

Bước sinh code (codegen) và chạy sandbox (sandbox_run) được ghi `audit_log` kèm người khởi động thao tác.

Ngoài các bước đã xong, hàng đợi giữ **node đang chạy** (lúc bắt đầu + mô tả việc đang làm) và **thời gian đo thật**
của mỗi node qua các lần chạy (file JSON cạnh store) để web ước lượng "thường mất khoảng bao lâu". Chưa đủ mẫu thì
không ước lượng.
"""

import json
import logging
import statistics
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from src.agents.progress import NodeStart, StepEvent
from src.agents.runner import PermissionDeniedError, RunOutcome, RunStateError
from src.config import get_settings
from src.models.schemas import RunStatus
from src.services import auth
from src.services.store import get_store

logger = logging.getLogger(__name__)
EventSink = Callable[[StepEvent | NodeStart], None]
Job = Callable[[EventSink], RunOutcome]
TIMING_KEEP = 20  # số lần đo gần nhất giữ cho mỗi node
TIMING_MIN_SAMPLES = 3  # ít hơn thì không ước lượng (trả None)
AUDITED_NODES = {"codegen": "code.generate", "sandbox_run": "sandbox.run"}  # CLAUDE.md mục 7


class JobLimitError(Exception):
    """Vượt giới hạn theo người (số lần chạy cùng lúc hoặc trần chi phí LLM trong ngày); thông báo tiếng Việt."""


def check_limits(owner: str, active: int, new_run: bool = False) -> None:
    """CLAUDE.md mục 14.2-14.3: chặn TRƯỚC khi tạo/chạy tiếp lần chạy của `owner` (người tạo yêu cầu).

    `new_run`: đang tạo lần chạy mới (chạy tiếp/chạy lại một lần chạy đã có không tính vào số lần chạy trong ngày).
    """
    settings = get_settings()
    daily = settings.user_daily_run_limit
    if new_run and daily:
        done = get_store().runs_today(owner)
        if done >= daily:
            raise JobLimitError(
                f"Hôm nay bạn đã tạo {done} lần chạy, chạm giới hạn {daily} lần/người/ngày. Mai gửi tiếp "
                "hoặc liên hệ quản trị viên."
            )
    if active >= settings.max_active_runs_per_user:
        raise JobLimitError(
            f"Bạn đang có {active} lần chạy đang chờ hoặc đang chạy (tối đa {settings.max_active_runs_per_user}). "
            "Đợi một lần chạy xong rồi gửi tiếp."
        )
    budget = settings.llm_daily_budget_usd
    if budget and settings.llm_provider != "mock":
        spent = get_store().spent_today(owner)
        if spent >= budget:
            raise JobLimitError(
                f"Đã dùng {spent:.2f} USD chi phí AI hôm nay, chạm trần {budget:.2f} USD/người/ngày. "
                "Liên hệ quản trị viên nếu cần thêm."
            )


class NodeTimings:
    """Thời gian chạy đo thật của từng node (giây), lưu ra file để còn sau khi khởi động lại."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._samples: dict[str, list[float]] = {}
        if path and path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                self._samples = {k: [float(x) for x in v][-TIMING_KEEP:] for k, v in loaded.items()}
            except (ValueError, TypeError, AttributeError):
                logger.warning("node timings unreadable, starting empty", extra={"path": str(path)})

    def add(self, node: str, seconds: float) -> None:
        """Thêm một lần đo và ghi file (lỗi ghi file không làm hỏng lần chạy)."""
        self._samples[node] = [*self._samples.get(node, []), round(seconds, 2)][-TIMING_KEEP:]
        if self._path:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._path.write_text(json.dumps(self._samples), encoding="utf-8")
            except OSError:
                logger.warning("cannot save node timings", extra={"path": str(self._path)})

    def typical(self, node: str) -> tuple[float | None, int]:
        """(trung vị giây, số mẫu); trung vị là None khi chưa đủ mẫu."""
        samples = self._samples.get(node, [])
        return (round(statistics.median(samples), 1) if len(samples) >= TIMING_MIN_SAMPLES else None), len(samples)


class JobQueue:
    """Một luồng nền chạy graph; lưu sự kiện từng bước theo run_id."""

    def __init__(self, timings_path: Path | None = None) -> None:
        settings = get_settings()
        # SQLite dùng chung một kết nối checkpoint nên chỉ an toàn với 1 luồng; PostgreSQL (pool kết nối) chạy song song được
        self._workers = settings.run_workers if settings.state_backend == "postgres" else 1
        self._executor = ThreadPoolExecutor(max_workers=self._workers, thread_name_prefix="p113-run")
        self._lock = threading.Lock()
        self._events: dict[str, list[dict]] = {}
        self._futures: dict[str, Future] = {}
        self._current: dict[str, NodeStart] = {}
        self._owners: dict[str, str] = {}  # run_id → người tạo yêu cầu (giới hạn theo người)
        self._order: list[str] = []  # thứ tự đưa vào hàng đợi (tính vị trí chờ)
        self._timings = NodeTimings(timings_path)

    def _record(self, run_id: str, actor: str = "") -> EventSink:
        def sink(event: StepEvent | NodeStart) -> None:
            with self._lock:
                if isinstance(event, NodeStart):
                    self._current[run_id] = event
                    return
                started = self._current.pop(run_id, None)
                if started and started.node == event.node:  # đo đúng từ lúc node bắt đầu tới lúc xong
                    self._timings.add(event.node, time.time() - started.started_at)
                self._events.setdefault(run_id, []).append({**event.model_dump(), "finished_at": time.time()})
            if actor and event.node in AUDITED_NODES:  # ngoài khóa: ghi DB không chặn web hỏi tiến trình
                outcome = "ok" if event.ok else "fail"
                auth.audit(AUDITED_NODES[event.node], actor, target=run_id, outcome=outcome)

        return sink

    def _run(self, run_id: str, job: Job, actor: str) -> None:
        try:
            job(self._record(run_id, actor))
        except (RunStateError, PermissionDeniedError) as exc:  # thao tác lặp (bấm 2 lần) hoặc trạng thái đã đổi
            logger.warning("job rejected", extra={"run_id": run_id, "error": str(exc)})
        except Exception:  # ranh giới luồng nền: không để luồng chết, đánh dấu lần chạy lỗi
            logger.exception("job crashed", extra={"run_id": run_id})
            record = get_store().get_run(run_id)
            summary = {**(record.summary if record else {}), "error": "Có lỗi nội bộ khi chạy nền. Xem log."}
            get_store().update_run(run_id, RunStatus.FAILED, summary)
        finally:
            with self._lock:
                self._current.pop(run_id, None)  # dừng ở J1/J2 hoặc lỗi: không còn node nào đang chạy

    def _active(self, owner: str, exclude: str = "") -> int:
        return sum(
            1
            for run_id, future in self._futures.items()
            if run_id != exclude and not future.done() and self._owners.get(run_id) == owner
        )

    def check(self, owner: str, run_id: str = "") -> None:
        """Ném JobLimitError nếu `owner` đã đủ số lần chạy cùng lúc hoặc chạm trần chi phí hôm nay."""
        with self._lock:
            active = self._active(owner, exclude=run_id)
        check_limits(owner, active, new_run=not run_id)

    def submit(self, run_id: str, job: Job, actor: str = "", owner: str = "") -> None:
        """Đánh dấu đang chạy rồi đưa vào hàng đợi (`actor` = người khởi động, để ghi nhật ký kiểm toán;
        `owner` = người tạo yêu cầu, để giới hạn theo người)."""
        get_store().update_run(run_id, RunStatus.RUNNING)
        with self._lock:
            self._owners[run_id] = owner or actor
            self._order = [r for r in self._order if r != run_id and not self._futures[r].done()] + [run_id]
            self._futures[run_id] = self._executor.submit(self._run, run_id, job, actor)

    def position(self, run_id: str) -> int | None:
        """Số lần chạy đứng TRƯỚC trong hàng (0 = đang chạy hoặc sắp chạy); None nếu không ở trong hàng."""
        with self._lock:
            future = self._futures.get(run_id)
            if not future or future.done() or run_id not in self._order:
                return None
            ahead = self._order[: self._order.index(run_id)]
            waiting = sum(1 for r in ahead if not self._futures[r].done())
            return max(0, waiting - (self._workers - 1))  # các luồng còn trống chạy ngay, không phải chờ

    def events(self, run_id: str) -> list[dict]:
        """Các bước đã chạy của lần chạy (theo thứ tự)."""
        with self._lock:
            return list(self._events.get(run_id, []))

    def current(self, run_id: str) -> dict | None:
        """Node đang chạy: tên, lúc bắt đầu, đã chạy bao lâu, thường mất bao lâu (đo thật), việc đang làm."""
        with self._lock:
            started = self._current.get(run_id)
            if started is None:
                return None
            typical, samples = self._timings.typical(started.node)
        return {
            **started.model_dump(),
            "elapsed_s": round(time.time() - started.started_at, 1),
            "typical_s": typical,
            "samples": samples,
        }

    def busy(self, run_id: str) -> bool:
        """Lần chạy đang chạy hoặc đang xếp hàng."""
        with self._lock:
            future = self._futures.get(run_id)
        return bool(future and not future.done())

    def wait(self, run_id: str, timeout: float = 600) -> None:
        """Chờ lần chạy xong (dùng cho test/CLI)."""
        with self._lock:
            future = self._futures.get(run_id)
        if future:
            future.result(timeout=timeout)


@lru_cache
def get_jobs() -> JobQueue:
    """Hàng đợi dùng chung của tiến trình API (thời gian từng node lưu cạnh store)."""
    return JobQueue(get_settings().store_path.parent / "node_timings.json")

"""Circuit breaker cho lời gọi LLM: mỗi cặp nhà cung cấp × model một bộ ngắt riêng (isolation).

Ba trạng thái:
- CLOSED (bình thường): lời gọi đi qua, đếm kết quả trong cửa sổ gần nhất. Khi đủ `min_calls` lượt và tỉ lệ lỗi
  ≥ `failure_rate` thì chuyển OPEN.
- OPEN (ngắt mạch): không gọi nhà cung cấp nữa (fail fast) → bên gọi chuyển sang dự phòng hoặc báo lỗi ngay, không chờ
  timeout. Hết `reset_sec` thì chuyển HALF_OPEN.
- HALF_OPEN (thử lại): chỉ cho tối đa `probes` lượt thăm dò. Đủ `probes` lượt thành công → CLOSED (xóa bộ đếm);
  một lượt thất bại → OPEN lại.

Chỉ lỗi hạ tầng (mạng, hạn mức, model lỗi: `LLMCallError`) mới tính là lỗi; đầu ra sai định dạng thì không.
Trạng thái nằm trong bộ nhớ của tiến trình (mất khi khởi động lại, đúng ý: khởi động lại thì thử lại từ đầu).
"""

import threading
import time
from collections import deque
from collections.abc import Callable
from enum import StrEnum

from src.config import Settings, get_settings

WINDOW = 10  # số lượt gần nhất dùng để tính tỉ lệ lỗi


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        key: str,
        *,
        min_calls: int,
        failure_rate: float,
        reset_sec: float,
        probes: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.key = key
        self.min_calls, self.failure_rate, self.reset_sec, self.probes = min_calls, failure_rate, reset_sec, probes
        self._clock = clock
        self._lock = threading.Lock()
        self._state = BreakerState.CLOSED
        self._results: deque[bool] = deque(maxlen=WINDOW)  # True = thành công
        self._opened_at = 0.0
        self._probes_started = 0
        self._probes_ok = 0

    @property
    def state(self) -> BreakerState:
        with self._lock:
            self._maybe_half_open()
            return self._state

    def _maybe_half_open(self) -> None:
        if self._state is BreakerState.OPEN and self._clock() - self._opened_at >= self.reset_sec:
            self._state = BreakerState.HALF_OPEN
            self._probes_started = self._probes_ok = 0

    def allow(self) -> bool:
        """Có được gọi nhà cung cấp lúc này không (HALF_OPEN: chỉ trong giới hạn lượt thăm dò)."""
        with self._lock:
            self._maybe_half_open()
            if self._state is BreakerState.CLOSED:
                return True
            if self._state is BreakerState.HALF_OPEN and self._probes_started < self.probes:
                self._probes_started += 1
                return True
            return False

    def retry_in(self) -> int:
        """Số giây còn lại tới lúc được thử lại (0 nếu không ở OPEN)."""
        with self._lock:
            if self._state is not BreakerState.OPEN:
                return 0
            return max(0, round(self.reset_sec - (self._clock() - self._opened_at)))

    def record_success(self) -> None:
        with self._lock:
            if self._state is BreakerState.HALF_OPEN:
                self._probes_ok += 1
                if self._probes_ok >= self.probes:
                    self._state = BreakerState.CLOSED
                    self._results.clear()  # đủ probe thành công: reset bộ đếm
            elif self._state is BreakerState.CLOSED:
                self._results.append(True)

    def record_failure(self) -> None:
        with self._lock:
            if self._state is BreakerState.HALF_OPEN:
                self._open()
            elif self._state is BreakerState.CLOSED:
                self._results.append(False)
                failures = sum(1 for ok in self._results if not ok)
                if len(self._results) >= self.min_calls and failures / len(self._results) >= self.failure_rate:
                    self._open()

    def _open(self) -> None:
        self._state = BreakerState.OPEN
        self._opened_at = self._clock()

    def snapshot(self) -> dict:
        with self._lock:
            self._maybe_half_open()
            failures = sum(1 for ok in self._results if not ok)
            return {
                "key": self.key,
                "state": str(self._state),
                "recent_calls": len(self._results),
                "recent_failures": failures,
            }


_BREAKERS: dict[str, CircuitBreaker] = {}
_LOCK = threading.Lock()


def get_breaker(key: str, settings: Settings | None = None) -> CircuitBreaker:
    """Bộ ngắt của một cặp `nhà cung cấp/model` (tạo khi cần, dùng chung cả tiến trình)."""
    settings = settings or get_settings()
    with _LOCK:
        if key not in _BREAKERS:
            _BREAKERS[key] = CircuitBreaker(
                key,
                min_calls=settings.breaker_min_calls,
                failure_rate=settings.breaker_failure_rate,
                reset_sec=settings.breaker_reset_sec,
                probes=settings.breaker_probes,
            )
        return _BREAKERS[key]


def breaker_snapshots() -> list[dict]:
    """Trạng thái mọi bộ ngắt đã dùng (cho /status và giao diện)."""
    with _LOCK:
        breakers = list(_BREAKERS.values())
    return [b.snapshot() for b in breakers]


def reset_breakers() -> None:
    """Xóa mọi bộ ngắt (dùng trong test)."""
    with _LOCK:
        _BREAKERS.clear()

"""Circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED, cách ly theo nhà cung cấp × model, và nối vào lời gọi LLM."""

import pytest

from src.config import Settings
from src.services.circuit_breaker import BreakerState, CircuitBreaker, breaker_snapshots, get_breaker
from src.services.llm import FallbackProvider, LLMCallError, LLMRequest, LLMResponse
from tests.test_services.test_llm import KEYS


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make(clock: Clock) -> CircuitBreaker:
    return CircuitBreaker("openai/m", min_calls=4, failure_rate=0.5, reset_sec=30, probes=2, clock=clock)


def test_stays_closed_until_enough_calls_and_failure_rate():
    breaker = make(Clock())
    for _ in range(3):  # 3 lỗi nhưng chưa đủ số lượt tối thiểu
        breaker.record_failure()
    assert breaker.state is BreakerState.CLOSED and breaker.allow()
    breaker.record_failure()  # lượt thứ 4: tỉ lệ lỗi 100% ≥ 50%
    assert breaker.state is BreakerState.OPEN and not breaker.allow()


def test_a_few_failures_among_many_successes_do_not_open():
    breaker = make(Clock())
    for _ in range(8):
        breaker.record_success()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state is BreakerState.CLOSED  # 2/10 = 20% < 50%


def test_open_then_half_open_after_reset_timeout_and_limited_probes():
    clock = Clock()
    breaker = make(clock)
    for _ in range(4):
        breaker.record_failure()
    assert breaker.retry_in() == 30
    clock.now = 29
    assert not breaker.allow()
    clock.now = 31
    assert breaker.state is BreakerState.HALF_OPEN
    assert breaker.allow() and breaker.allow() and not breaker.allow()  # chỉ 2 lượt thăm dò


def test_enough_successful_probes_close_and_reset_counter():
    clock = Clock()
    breaker = make(clock)
    for _ in range(4):
        breaker.record_failure()
    clock.now = 31
    assert breaker.allow() and breaker.allow()
    breaker.record_success()
    assert breaker.state is BreakerState.HALF_OPEN  # mới 1/2 probe
    breaker.record_success()
    assert breaker.state is BreakerState.CLOSED
    assert breaker.snapshot()["recent_calls"] == 0  # bộ đếm đã reset


def test_failed_probe_reopens():
    clock = Clock()
    breaker = make(clock)
    for _ in range(4):
        breaker.record_failure()
    clock.now = 31
    assert breaker.allow()
    breaker.record_failure()
    assert breaker.state is BreakerState.OPEN and breaker.retry_in() == 30


def test_breakers_are_isolated_per_provider_and_model():
    settings = Settings(llm_provider="openai", **KEYS)
    a, b = get_breaker("openai/gpt-6-luna", settings), get_breaker("anthropic/claude-haiku-5-5", settings)
    for _ in range(settings.breaker_min_calls):
        a.record_failure()
    assert a.state is BreakerState.OPEN and b.state is BreakerState.CLOSED  # nhà A hỏng không kéo nhà B
    states = {s["key"]: s["state"] for s in breaker_snapshots()}
    assert states == {"openai/gpt-6-luna": "open", "anthropic/claude-haiku-5-5": "closed"}


class Failing:
    model = "m"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        self.calls += 1
        raise LLMCallError("Gọi OpenAI thất bại (APITimeoutError).")


def test_open_breaker_fails_fast_without_calling_provider():
    settings = Settings(llm_provider="openai", **KEYS)
    primary = Failing()
    provider = FallbackProvider(primary, settings, key="openai/m", use_fallback=False)
    request = LLMRequest(task="optimizer", variables={})
    for _ in range(settings.breaker_min_calls):
        with pytest.raises(LLMCallError, match="APITimeoutError"):
            provider.complete(request, ("", ""))
    assert primary.calls == settings.breaker_min_calls
    with pytest.raises(LLMCallError, match="tạm ngắt"):
        provider.complete(request, ("", ""))
    assert primary.calls == settings.breaker_min_calls  # đang ngắt mạch: không gọi nhà cung cấp, không chờ timeout


def test_open_breaker_sends_calls_to_fallback(monkeypatch: pytest.MonkeyPatch):
    from src.services import llm
    from src.services.llm_mock import MockProvider

    class FakeGoogle:
        def __init__(self, settings: Settings, model: str = "", task: str = "") -> None:
            self.model = "gemini-x"

        def complete(self, request: LLMRequest, prompt: tuple[str, str]):
            return MockProvider().complete(request, prompt).model_copy(update={"text": '{"from": "gemini"}'})

    monkeypatch.setattr(llm, "GoogleProvider", FakeGoogle)
    settings = Settings(llm_provider="openai", **KEYS)
    primary = Failing()
    provider = FallbackProvider(primary, settings, key="openai/m", use_fallback=True)
    request = LLMRequest(task="planner", variables={})
    for _ in range(settings.breaker_min_calls + 2):
        assert provider.complete(request, ("", "")).text == '{"from": "gemini"}'
    assert primary.calls == settings.breaker_min_calls  # sau khi ngắt, các lượt sau sang Gemini ngay


def test_timeouts_per_task():
    settings = Settings(llm_provider="openai", **KEYS)
    assert settings.timeout_for("optimizer") == 60 < settings.timeout_for("codegen")

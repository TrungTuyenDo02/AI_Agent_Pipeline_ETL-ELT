"""Sổ chi phí LLM + giữ trước ngân sách (ADR 0014): giữ trước nguyên tử, quyết toán đúng một lần, `unknown` không tự hoàn,
model thiếu giá bị chặn, lượt thất bại vẫn ghi tiền, dự phòng giữ riêng, ngày tính theo lúc gọi."""

import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import openai
import pytest

from src.config import Settings
from src.models.schemas import LLMUsage
from src.services import cost_ledger, llm
from src.services.cost_ledger import SYSTEM_OWNER, BudgetDeniedError, CostLedger, llm_caller
from src.services.llm import (
    CostMeter,
    FallbackProvider,
    LLMBudgetError,
    LLMCallError,
    LLMConfigError,
    LLMRequest,
    LLMResponse,
    run_budget,
)

KEYS = {"openai_api_key": "sk-test-123", "anthropic_api_key": "sk-ant-test-123", "google_api_key": "g-test-123"}
REQUEST = LLMRequest(task="codegen", variables={})
PROMPT = ("hệ thống", "người dùng")


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CostLedger:
    settings = Settings(llm_daily_budget_usd=1.0, run_cost_budget_usd=0.5, llm_global_daily_budget_usd=2.0)
    monkeypatch.setattr(cost_ledger, "get_settings", lambda: settings)
    book = CostLedger(tmp_path / "ledger.db")
    monkeypatch.setattr(llm, "get_ledger", lambda: book)
    return book


def _reserve(book: CostLedger, usd: float, owner: str = "an", run_id: str = "", **kw) -> str:
    return book.reserve(
        owner=owner, run_id=run_id, task="codegen", provider="openai", model="gpt-6-luna", estimate_usd=usd,
        ttl_sec=kw.pop("ttl_sec", 60), **kw,
    )  # fmt: skip


def _today() -> str:
    return datetime.now(UTC).astimezone(cost_ledger.VN_TZ).date().isoformat()


def test_reserve_then_settle_moves_estimate_to_actual(ledger: CostLedger):
    call_id = _reserve(ledger, 0.2, run_id="r1")
    assert ledger.used_usd("user", "an", _today()) == pytest.approx(0.2)  # đang giữ cũng tính là đã dùng
    assert ledger.settle(call_id, 0.05, input_tokens=100, output_tokens=20)
    assert ledger.used_usd("user", "an", _today()) == pytest.approx(0.05)
    assert ledger.used_usd("run", "r1") == pytest.approx(0.05)
    assert ledger.used_usd("global", "*", _today()) == pytest.approx(0.05)
    row = ledger.get_call(call_id)
    assert (row["status"], row["input_tokens"], row["output_tokens"]) == ("settled", 100, 20)
    assert not ledger.settle(call_id, 9.0)  # quyết toán đúng một lần
    assert ledger.used_usd("user", "an", _today()) == pytest.approx(0.05)


def test_denied_reservation_changes_nothing(ledger: CostLedger):
    _reserve(ledger, 0.3, run_id="r1")
    with pytest.raises(BudgetDeniedError, match="Không đủ ngân sách để giữ trước.*RUN_COST_BUDGET_USD"):
        _reserve(ledger, 0.3, run_id="r1")  # trần run 0,5
    # cả giao dịch hủy: người và toàn hệ thống không bị giữ thêm
    assert ledger.used_usd("user", "an", _today()) == pytest.approx(0.3)
    assert ledger.used_usd("global", "*", _today()) == pytest.approx(0.3)
    with pytest.raises(BudgetDeniedError, match="LLM_DAILY_BUDGET_USD"):
        _reserve(ledger, 0.8)  # trần người 1,0
    _reserve(ledger, 0.4, owner="binh")  # người khác vẫn được


def test_system_owner_skips_user_cap_but_not_global(ledger: CostLedger):
    _reserve(ledger, 1.5, owner=SYSTEM_OWNER)  # quá trần người 1,0 nhưng `system` không áp trần người
    with pytest.raises(BudgetDeniedError, match="LLM_GLOBAL_DAILY_BUDGET_USD"):
        _reserve(ledger, 0.6, owner=SYSTEM_OWNER)  # toàn hệ thống 2,0


def test_concurrent_reservations_never_exceed_limit(ledger: CostLedger):
    ok, denied = [], []

    def worker() -> None:
        try:
            ok.append(_reserve(ledger, 0.1))
        except BudgetDeniedError:
            denied.append(1)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ok) == 10 and len(denied) == 10  # trần người 1,0 / 0,1 mỗi lượt
    assert ledger.used_usd("user", "an", _today()) == pytest.approx(1.0)


def test_unknown_keeps_estimate_and_late_response_settles(ledger: CostLedger):
    call_id = _reserve(ledger, 0.2)
    assert ledger.mark_unknown(call_id, note="timeout")
    assert ledger.used_usd("user", "an", _today()) == pytest.approx(0.2)  # không tự hoàn
    assert not ledger.release(call_id)  # đã gửi thì không hoàn được nữa
    assert ledger.settle(call_id, 0.03)  # phản hồi về muộn
    assert ledger.used_usd("user", "an", _today()) == pytest.approx(0.03)


def test_release_returns_reservation(ledger: CostLedger):
    call_id = _reserve(ledger, 0.2)
    assert ledger.release(call_id)
    assert ledger.used_usd("user", "an", _today()) == 0.0
    assert ledger.get_call(call_id)["status"] == "released"


def test_stale_reservation_expires_to_unknown(ledger: CostLedger):
    call_id = _reserve(ledger, 0.2, ttl_sec=1, now=datetime.now(UTC) - timedelta(minutes=5))
    assert ledger.expire_stale() == 1
    assert ledger.get_call(call_id)["status"] == "unknown"
    assert ledger.used_usd("user", "an", ledger.get_call(call_id)["day"]) == pytest.approx(0.2)
    assert ledger.reconcile(call_id, 0.01)
    assert [c["id"] for c in ledger.list_calls("settled")] == [call_id]


def test_daily_cap_counts_by_call_day_not_run_creation(ledger: CostLedger):
    yesterday = datetime.now(UTC) - timedelta(days=1)
    ledger.settle(_reserve(ledger, 0.2, run_id="old", now=yesterday), 0.2)
    assert ledger.spent_today("an") == 0.0  # hôm qua không tính vào hôm nay
    ledger.settle(_reserve(ledger, 0.25, run_id="old"), 0.25)  # run cũ chạy tiếp hôm nay: tính vào hôm nay
    assert ledger.spent_today("an") == pytest.approx(0.25)
    assert ledger.used_usd("run", "old") == pytest.approx(0.45)  # trần run cộng dồn qua các ngày


# --- CostMeter: giữ trước quanh lượt gọi thật -----------------------------------------------------------------------


class _Provider:
    """Nhà cung cấp giả: trả lời hoặc ném lỗi định sẵn."""

    def __init__(self, model: str = "gpt-6-luna", error: BaseException | None = None, answered_by: str = "") -> None:
        self.model, self.error, self.calls, self.answered_by = model, error, 0, answered_by or model

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        self.calls += 1
        if self.error:
            raise self.error
        usage = LLMUsage(
            task=request.task, provider="fake", model=self.answered_by, input_tokens=10, output_tokens=5, cost_usd=0.004
        )
        return LLMResponse(text="{}", usage=usage)


def _meter() -> CostMeter:
    return CostMeter(Settings(llm_provider="openai", **KEYS))


def _only_call(book: CostLedger, status: str) -> dict:
    calls = book.list_calls(status)
    assert len(calls) == 1, calls
    return calls[0]


def test_meter_settles_success_under_caller(ledger: CostLedger):
    with llm_caller("an", "r9"):
        _meter().call(_Provider(), REQUEST, PROMPT)
    row = _only_call(ledger, "settled")
    assert (row["owner"], row["run_id"], row["task"], row["cost_micros"]) == ("an", "r9", "codegen", 4000)
    assert ledger.used_usd("run", "r9") == pytest.approx(0.004)


def test_meter_keeps_estimate_when_answering_model_has_no_price(ledger: CostLedger):
    """Dự phòng phía máy chủ trả lời bằng model chưa có giá: không quyết toán 0 USD mà giữ khoản dự toán (`unknown`)."""
    _meter().call(_Provider(answered_by="claude-moi-chua-co-gia"), REQUEST, PROMPT)
    row = _only_call(ledger, "unknown")
    assert row["cost_micros"] == row["reserved_micros"] > 0 and "chưa có giá" in row["note"]


def test_meter_blocks_model_without_price(ledger: CostLedger):
    provider = _Provider(model="model-chua-co-gia")
    with pytest.raises(LLMConfigError, match="chưa có giá"):
        _meter().call(provider, REQUEST, PROMPT)
    assert provider.calls == 0 and ledger.list_calls("reserved") == []


def test_meter_records_cost_of_anthropic_cut_off(ledger: CostLedger):
    """Bị cắt ở max_tokens vẫn tính tiền: ghi đủ vào sổ và trần token của lần chạy (trước đây bị mất)."""
    from src.services.llm import AnthropicProvider

    usage = SimpleNamespace(
        input_tokens=100, output_tokens=50, cache_read_input_tokens=0, cache_creation_input_tokens=0
    )
    message = SimpleNamespace(model="claude-haiku-5-5", stop_reason="max_tokens", usage=usage, content=[])
    provider = AnthropicProvider(Settings(llm_provider="openai", **KEYS), task="optimizer")
    provider.client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=lambda **_: message)))
    with run_budget(100_000) as budget, pytest.raises(LLMCallError, match="max_tokens"):
        _meter().call(provider, LLMRequest(task="optimizer", variables={}), PROMPT)
    assert budget.used == 150
    assert _only_call(ledger, "settled")["cost_micros"] == round(100 * 0.10 + 50 * 0.50)  # micro-USD


class _LengthError(openai.OpenAIError):
    """Giống LengthFinishReasonError: mang bản trả lời đã tính tiền."""

    def __init__(self) -> None:
        super().__init__("length")
        usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=12000, prompt_tokens_details=None)
        self.completion = SimpleNamespace(usage=usage)


class _StatusError(openai.OpenAIError):
    def __init__(self, status: int) -> None:
        super().__init__(f"status {status}")
        self.status_code = status


def _openai_raising(error: BaseException):
    provider = llm.OpenAIProvider(Settings(llm_provider="openai", **KEYS), "gpt-6-luna", "codegen")

    class Boom:
        def invoke(self, messages):
            raise error

    provider.client = Boom()
    return provider


def test_meter_records_openai_length_error_usage(ledger: CostLedger):
    with pytest.raises(LLMCallError):
        _meter().call(_openai_raising(_LengthError()), REQUEST, PROMPT)
    assert _only_call(ledger, "settled")["output_tokens"] == 12000


def test_meter_releases_rejected_request_and_marks_timeout_unknown(ledger: CostLedger):
    with pytest.raises(LLMCallError):
        _meter().call(_openai_raising(_StatusError(400)), REQUEST, PROMPT)
    assert _only_call(ledger, "released")
    with pytest.raises(LLMCallError):
        _meter().call(_openai_raising(openai.OpenAIError("timeout")), REQUEST, PROMPT)
    unknown = _only_call(ledger, "unknown")
    assert unknown["cost_micros"] == unknown["reserved_micros"] > 0  # chưa rõ: tính bằng dự toán


def test_estimate_covers_max_output_and_sdk_retries():
    settings = Settings(llm_provider="openai", **KEYS)
    one = llm.estimate_cost_usd("gpt-6-luna", 0, settings.max_tokens_for("codegen"))
    assert llm.estimate_call_usd(settings, "gpt-6-luna", "codegen", ("", "")) >= one * (1 + llm.SDK_MAX_RETRIES)


def test_budget_denial_stops_before_breaker_and_fallback(ledger: CostLedger, monkeypatch: pytest.MonkeyPatch):
    backup = _Provider(model="gemini-3.1-flash-lite")
    monkeypatch.setattr(llm, "GoogleProvider", lambda settings, task="": backup)
    primary = _Provider()
    _reserve(ledger, 0.99)  # còn 0,01 USD: không đủ giữ trước một lượt codegen
    provider = FallbackProvider(primary, Settings(llm_provider="openai", **KEYS), key="t/deny", meter=_meter())
    with llm_caller("an"), pytest.raises(LLMBudgetError, match="giữ trước"):
        provider.complete(REQUEST, PROMPT)
    assert primary.calls == 0 and backup.calls == 0


def test_fallback_reserves_separately_and_records_both(ledger: CostLedger, monkeypatch: pytest.MonkeyPatch):
    backup = _Provider(model="gemini-3.1-flash-lite")
    monkeypatch.setattr(llm, "GoogleProvider", lambda settings, task="": backup)
    primary = _Provider(error=LLMCallError("Gọi OpenAI thất bại (APITimeoutError)."))
    provider = FallbackProvider(primary, Settings(llm_provider="openai", **KEYS), key="t/fallback", meter=_meter())
    with llm_caller("an"):
        response = provider.complete(REQUEST, PROMPT)
    assert response.usage.model == "gemini-3.1-flash-lite"
    assert _only_call(ledger, "unknown")["model"] == "gpt-6-luna"  # lượt chính đã gửi, không có usage
    assert _only_call(ledger, "settled")["model"] == "gemini-3.1-flash-lite"


def test_fallback_blocks_backup_without_price(ledger: CostLedger, monkeypatch: pytest.MonkeyPatch):
    backup = _Provider(model="gemini-moi-chua-co-gia")
    monkeypatch.setattr(llm, "GoogleProvider", lambda settings, task="": backup)
    primary = _Provider(error=LLMCallError("Gọi OpenAI thất bại (RateLimitError)."))
    provider = FallbackProvider(primary, Settings(llm_provider="openai", **KEYS), key="t/noprice", meter=_meter())
    with pytest.raises(LLMConfigError, match="chưa có giá"):
        provider.complete(REQUEST, PROMPT)
    assert backup.calls == 0


def test_get_provider_meters_every_real_path():
    settings = Settings(llm_provider="openai", llm_fallback="google", **KEYS)
    assert isinstance(llm.get_provider(settings, task="codegen").meter, CostMeter)
    google = llm.get_provider(Settings(llm_provider="google", **KEYS), task="codegen")
    assert isinstance(google, llm.MeteredProvider)


def test_cli_cost_lists_and_reviewer_reconciles():
    from src.cli import main
    from src.services.cost_ledger import get_ledger

    book = get_ledger()
    call_id = book.reserve(
        owner="cli", run_id="", task="codegen", provider="openai", model="gpt-6-luna", estimate_usd=0.01, ttl_sec=60
    )
    book.mark_unknown(call_id)
    assert main(["cost"]) == 0
    assert main(["cost", "--settle", call_id, "--usd", "0.002"]) == 2  # engineer không được đối soát
    assert book.get_call(call_id)["status"] == "unknown"
    assert main(["cost", "--settle", call_id, "--usd", "0.002", "--as", "reviewer"]) == 0
    assert book.get_call(call_id)["cost_micros"] == 2000

"""Test cổng LLM: dựng prompt, parse JSON, chọn nhà cung cấp, báo lỗi thiếu khóa bằng tiếng Việt."""

import pytest

from src.config import Settings
from src.services.cost import compute_cost_usd, estimate_cost_usd
from src.services.llm import (
    LLMConfigError,
    LLMOutputError,
    LLMRequest,
    OpenAIProvider,
    call_llm,
    get_provider,
    parse_json_output,
    render_prompt,
)
from src.services.llm_mock import MockProvider


def test_render_prompt_splits_system_and_user_and_fills_variables():
    system, user = render_prompt(LLMRequest(task="planner", variables={"request_text": "doanh thu ngày"}))
    assert "pipeline spec" in system
    assert "version:" not in system  # đầu file (version, nhật ký thay đổi) không gửi LLM
    assert "doanh thu ngày" in user
    assert user.rstrip().endswith("Produce the pipeline spec for the request.")  # yêu cầu của lần gọi ở cuối
    assert '<data name="request">' in user


def test_render_prompt_unknown_task_raises():
    with pytest.raises(LLMConfigError):
        render_prompt(LLMRequest(task="khong-co", variables={}))


@pytest.mark.parametrize(
    "text",
    ['{"a": 1}', 'Kết quả:\n```json\n{"a": 1}\n```', 'trước {"a": 1} sau'],
)
def test_parse_json_output_accepts_common_formats(text):
    assert parse_json_output(text) == {"a": 1}


@pytest.mark.parametrize("text", ["không có json", "[1, 2]", "{sai"])
def test_parse_json_output_rejects_invalid(text):
    with pytest.raises(LLMOutputError):
        parse_json_output(text)


def test_default_provider_is_mock_and_marks_simulated():
    assert isinstance(get_provider(), MockProvider)
    response = call_llm("planner", {"request_text": "x", "source_catalog": "[]", "answers": "(chưa có)"})
    assert response.usage.simulated is True
    assert response.usage.cost_usd == 0


@pytest.mark.parametrize("key", ["", "sk-your-key-here"])
def test_openai_without_real_key_gives_vietnamese_instruction(key):
    settings = Settings(llm_provider="openai", openai_api_key=key)
    with pytest.raises(LLMConfigError, match="OPENAI_API_KEY"):
        OpenAIProvider(settings)


def test_unknown_mock_task_returns_empty_object():
    response = MockProvider().complete(LLMRequest(task="khac", variables={}), ("", ""))
    assert response.text == "{}"


def test_cost_estimates():
    assert estimate_cost_usd("gpt-4o-mini", 1_000_000, 1_000_000) == pytest.approx(0.75)
    assert estimate_cost_usd("model-la", 1000, 1000) == 0.0
    assert compute_cost_usd(3600, 0.5) == pytest.approx(0.5)


# ---- Hướng C: model theo từng bước + dự phòng Gemini (không gọi mạng) ----

KEYS = {"openai_api_key": "sk-test-123", "anthropic_api_key": "sk-ant-test-123", "google_api_key": "AIza-test-123"}


def test_model_table_from_yaml():
    """Tên model chỉ nằm trong config/models.yaml: planner/codegen = gpt-6-luna, optimizer = Opus 5.5."""
    settings = Settings(llm_provider="openai", **KEYS)
    assert settings.model_for("planner") == settings.model_for("codegen") == "gpt-6-luna"
    assert settings.choice_for("planner").temperature is False  # gpt-6-luna từ chối temperature=0
    assert settings.choice_for("optimizer").provider == "anthropic"
    assert settings.model_for("optimizer") == "claude-opus-5-5"
    assert settings.model_for("codegen", "google") == settings.google_model_name == "gemini-3.1-flash-lite"
    assert "optimizer=claude-opus-5-5" in settings.models_summary
    assert settings.providers_in_use == {"openai", "anthropic"}


def test_model_table_from_another_file(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text(
        "models:\n"
        "  planner: {provider: openai, name: m-a}\n  codegen: {provider: openai, name: m-a}\n"
        "  testgen: {provider: openai, name: m-b}\n  optimizer: {provider: openai, name: m-a}\n"
        "fallback: {provider: google, name: g-1}\n",
        encoding="utf-8",
    )
    settings = Settings(llm_provider="openai", models_file=path, **KEYS)
    assert settings.model_for("testgen") == "m-b" and settings.model_for("planner") == "m-a"
    assert Settings(llm_provider="google", models_file=path, **KEYS).model_for("planner") == "g-1"


def test_model_table_missing_task_fails(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text("models:\n  planner: {provider: openai, name: m}\nfallback: {provider: google, name: g}\n")
    with pytest.raises(ValueError, match="codegen"):
        Settings(models_file=path).model_table


def test_get_provider_wraps_fallback_and_uses_task_model():
    from src.services.llm import AnthropicProvider, FallbackProvider

    provider = get_provider(Settings(llm_provider="openai", llm_fallback="google", **KEYS), task="optimizer")
    assert isinstance(provider, FallbackProvider) and isinstance(provider.primary, AnthropicProvider)
    assert provider.primary.model == "claude-opus-5-5"
    assert provider.primary.output_config["effort"] == "medium"
    assert provider.primary.output_config["format"]["type"] == "json_schema"
    plain = get_provider(Settings(llm_provider="openai", llm_fallback="none", **KEYS), task="codegen")
    assert isinstance(plain, OpenAIProvider) and plain.model == "gpt-6-luna"
    assert plain.client.bound.temperature is None  # `temperature: false` trong models.yaml → không gửi tham số


def test_anthropic_provider_without_key_gives_vietnamese_instruction():
    from src.services.llm import AnthropicProvider

    with pytest.raises(LLMConfigError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider(Settings(llm_provider="openai", anthropic_api_key=""), task="optimizer")


class _FakeMessages:
    def __init__(self, message=None, error: Exception | None = None) -> None:
        self.message, self.error, self.kwargs = message, error, {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.message


def _anthropic_with(fake: _FakeMessages):
    from types import SimpleNamespace

    from src.services.llm import AnthropicProvider

    provider = AnthropicProvider(Settings(llm_provider="openai", **KEYS), task="optimizer")
    provider.client = SimpleNamespace(beta=SimpleNamespace(messages=fake))
    return provider


def _claude_message(stop_reason: str = "end_turn"):
    from types import SimpleNamespace

    usage = SimpleNamespace(
        input_tokens=100, output_tokens=50, cache_read_input_tokens=20, cache_creation_input_tokens=0
    )
    content = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text='{"sql": "SELECT 1"}')]
    return SimpleNamespace(model="claude-opus-5-5", stop_reason=stop_reason, usage=usage, content=content)


def test_anthropic_provider_reads_text_usage_and_sends_no_temperature():
    fake = _FakeMessages(_claude_message())
    response = _anthropic_with(fake).complete(LLMRequest(task="optimizer", variables={}), ("sys", "user"))
    assert response.text == '{"sql": "SELECT 1"}'  # bỏ khối thinking, chỉ lấy văn bản
    assert response.usage.provider == "anthropic" and response.usage.model == "claude-opus-5-5"
    assert (response.usage.input_tokens, response.usage.cached_tokens) == (120, 20)
    assert response.usage.cost_usd == pytest.approx((120 * 4 + 50 * 20) / 1_000_000)
    assert "temperature" not in fake.kwargs and "thinking" not in fake.kwargs  # Opus 5.5 trả 400 nếu gửi
    assert fake.kwargs["system"] == "sys" and fake.kwargs["messages"] == [{"role": "user", "content": "user"}]
    assert fake.kwargs["fallbacks"] == "default"


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_anthropic_cut_off_or_refusal_becomes_call_error(stop_reason):
    from src.services.llm import LLMCallError

    with pytest.raises(LLMCallError, match=stop_reason):
        _anthropic_with(_FakeMessages(_claude_message(stop_reason))).complete(
            LLMRequest(task="optimizer", variables={}), ("", "")
        )


def test_anthropic_api_error_becomes_call_error():
    import anthropic

    from src.services.llm import LLMCallError

    fake = _FakeMessages(error=anthropic.APIConnectionError(request=None))  # type: ignore[arg-type]
    with pytest.raises(LLMCallError, match="Anthropic"):
        _anthropic_with(fake).complete(LLMRequest(task="optimizer", variables={}), ("", ""))


class _Failing:
    def complete(self, request: LLMRequest, prompt: tuple[str, str]):
        from src.services.llm import LLMCallError

        raise LLMCallError("Gọi OpenAI thất bại (RateLimitError).")


def test_fallback_switches_to_gemini_only_on_call_error(monkeypatch):
    from src.services import llm

    class FakeGoogle:
        def __init__(self, settings: Settings, model: str = "", task: str = "") -> None:
            self.model = model or settings.google_model_name

        def complete(self, request: LLMRequest, prompt: tuple[str, str]):
            return MockProvider().complete(request, prompt).model_copy(update={"text": '{"from": "gemini"}'})

    monkeypatch.setattr(llm, "GoogleProvider", FakeGoogle)
    provider = llm.FallbackProvider(_Failing(), Settings(llm_provider="openai", **KEYS))
    response = provider.complete(LLMRequest(task="planner", variables={}), ("", ""))
    assert response.text == '{"from": "gemini"}'


def test_fallback_without_google_key_reports_both_errors():
    from src.services.llm import FallbackProvider, LLMCallError

    provider = FallbackProvider(_Failing(), Settings(llm_provider="openai", openai_api_key="sk-test-123"))
    with pytest.raises(LLMCallError, match="RateLimitError.*GOOGLE_API_KEY"):
        provider.complete(LLMRequest(task="planner", variables={}), ("", ""))


def test_google_provider_without_key_gives_vietnamese_instruction():
    from src.services.llm import GoogleProvider

    with pytest.raises(LLMConfigError, match="GOOGLE_API_KEY"):
        GoogleProvider(Settings(llm_provider="google", google_api_key=""))


def test_new_model_prices():
    assert estimate_cost_usd("gpt-6-luna", 1_000_000, 1_000_000) == pytest.approx(0.60)
    assert estimate_cost_usd("gemini-3.8-flash", 1_000_000, 1_000_000) == pytest.approx(4.50)
    assert estimate_cost_usd("gpt-5.6-luna", 1_000_000, 1_000_000) == pytest.approx(1.40)
    assert estimate_cost_usd("gpt-5.6-terra", 1_000_000, 1_000_000) == pytest.approx(14.00)
    assert estimate_cost_usd("gemini-3.1-flash-lite", 1_000_000, 1_000_000) == pytest.approx(1.75)
    assert estimate_cost_usd("claude-opus-5-5", 1_000_000, 1_000_000) == pytest.approx(24.00)


def test_openai_length_error_becomes_call_error_for_fallback(monkeypatch):
    """gpt-5.6-luna có thể dùng hết token cho suy luận ẩn → LengthFinishReasonError phải thành LLMCallError (dự phòng)."""
    import openai

    from src.services.llm import LLMCallError

    provider = OpenAIProvider(Settings(llm_provider="openai", **KEYS), "gpt-5.6-luna")

    class Boom:
        def invoke(self, messages):
            raise openai.OpenAIError("length limit reached")

    provider.client = Boom()
    with pytest.raises(LLMCallError):
        provider.complete(LLMRequest(task="planner", variables={}), ("", ""))


def test_openai_sends_temperature_when_model_accepts_it():
    """Model khác tên trong bảng (gọi thẳng theo tên) vẫn gửi nhiệt độ như trước.

    (langchain-openai tự bỏ temperature với họ gpt-5 nên gpt-5.6-luna từng chạy được; họ gpt-6 thì không.)
    """
    provider = OpenAIProvider(Settings(llm_provider="openai", **KEYS), "gpt-4o-mini", task="planner")
    assert provider.client.bound.temperature == 0.0

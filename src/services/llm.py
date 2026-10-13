"""Cổng gọi LLM duy nhất của hệ thống: `openai`, `google` hoặc `mock` (LLM_PROVIDER); dự phòng Gemini (LLM_FALLBACK).

Mọi node gọi `call_llm(task, variables)`; prompt nằm ở `src/prompts/<task>.md`. Nhà cung cấp + model của từng bước
(OpenAI, Anthropic hoặc Google) đọc từ `config/models.yaml`.
"""

import json
import logging
import re
import time
from pathlib import Path
from string import Template
from typing import Protocol

from pydantic import BaseModel

from src.config import Settings, get_settings
from src.models.llm_outputs import output_schema
from src.models.schemas import LLMUsage
from src.services.cost import estimate_cost_usd

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
USER_MARKER = "<!-- USER -->"
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)  # đầu file prompt (version, nhật ký thay đổi): không gửi LLM
DATA_TAG_RE = re.compile(r"<(\s*/?\s*data\b)", re.IGNORECASE)


class LLMConfigError(RuntimeError):
    """Cấu hình LLM chưa đủ (ví dụ thiếu khóa). Thông báo bằng tiếng Việt."""


class LLMCallError(RuntimeError):
    """Gọi LLM thất bại (mạng, hết hạn mức, ...)."""


class LLMOutputError(ValueError):
    """LLM trả về nội dung không đúng định dạng JSON yêu cầu."""


class LLMRequest(BaseModel):
    """Yêu cầu gọi LLM: tên tác vụ + biến điền vào prompt."""

    task: str
    variables: dict[str, str]


class LLMResponse(BaseModel):
    """Kết quả: văn bản trả về + thống kê token/chi phí."""

    text: str
    usage: LLMUsage


class LLMProvider(Protocol):
    """Giao diện chung cho mọi nhà cung cấp."""

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        """Gọi mô hình với (system, user) đã dựng sẵn."""
        ...


def neutralize_data_tags(value: str) -> str:
    """`</data>` trong dữ liệu (yêu cầu, ô CSV nguồn, thông báo lỗi) sẽ đóng khối sớm và biến phần sau thành chỉ dẫn
    (prompt injection) → đổi `<` của mọi thẻ data thành `&lt;`. Dữ liệu bình thường không đổi một ký tự."""
    return DATA_TAG_RE.sub(r"&lt;\1", value)


def render_prompt(request: LLMRequest) -> tuple[str, str]:
    """Đọc `src/prompts/<task>.md`, điền biến `$ten_bien`, tách phần system và user."""
    path = PROMPTS_DIR / f"{request.task}.md"
    if not path.exists():
        raise LLMConfigError(f"Không tìm thấy prompt cho tác vụ '{request.task}' ({path}).")
    system, _, user = path.read_text(encoding="utf-8").partition(USER_MARKER)
    system = COMMENT_RE.sub("", system)  # bỏ chú thích TRƯỚC khi điền biến: dữ liệu không bị đụng tới
    variables = {key: neutralize_data_tags(str(value)) for key, value in request.variables.items()}
    fill = Template(system).safe_substitute(variables), Template(user).safe_substitute(variables)
    return fill[0].strip(), fill[1].strip()


class UsageInfo(BaseModel):
    """Số liệu một lần gọi để dựng LLMUsage."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    started: float
    cached_tokens: int = 0


def _usage(request: LLMRequest, info: UsageInfo) -> LLMUsage:
    return LLMUsage(
        task=request.task,
        provider=info.provider,
        model=info.model,
        input_tokens=info.input_tokens,
        output_tokens=info.output_tokens,
        cached_tokens=info.cached_tokens,
        cost_usd=estimate_cost_usd(info.model, info.input_tokens, info.output_tokens),
        latency_ms=round((time.perf_counter() - info.started) * 1000, 1),
    )


def _response(request: LLMRequest, message: object, info: UsageInfo) -> LLMResponse:
    """Dựng kết quả từ tin nhắn LangChain (`.text` gộp mọi khối văn bản, đúng cho cả OpenAI lẫn Gemini)."""
    meta = getattr(message, "usage_metadata", None) or {}
    cached = (meta.get("input_token_details") or {}).get("cache_read") or 0
    info = info.model_copy(
        update={
            "input_tokens": meta.get("input_tokens", 0),
            "output_tokens": meta.get("output_tokens", 0),
            "cached_tokens": cached,
        }
    )
    return LLMResponse(text=str(getattr(message, "text", "")), usage=_usage(request, info))


def openai_response_format(settings: Settings, task: str) -> dict:
    """JSON Schema strict của tác vụ (structured output); tắt công tắc hoặc không có schema → json_object."""
    schema = output_schema(task) if settings.llm_structured_output else None
    if schema is None:
        return {"type": "json_object"}
    return {"type": "json_schema", "json_schema": {"name": f"{task}_output", "strict": True, "schema": schema}}


class OpenAIProvider:
    """Gọi OpenAI qua langchain-openai, ép đầu ra theo schema. Mỗi bước có model, trần token, nhiệt độ riêng."""

    def __init__(self, settings: Settings, model: str = "", task: str = "") -> None:
        if not settings.has_openai_key:
            raise LLMConfigError(
                "Bạn đang chọn LLM_PROVIDER=openai nhưng chưa có OPENAI_API_KEY. "
                "Mở file .env, điền OPENAI_API_KEY=<khóa của bạn>, hoặc đổi LLM_PROVIDER=mock để chạy mô phỏng."
            )
        from langchain_openai import ChatOpenAI

        self.model = model or settings.model_for(task)
        choice = settings.choice_for(task)  # models.yaml: `temperature: false` = model chỉ nhận nhiệt độ mặc định
        accepts_temperature = choice.temperature or self.model != choice.name
        client = ChatOpenAI(
            model=self.model,
            api_key=settings.openai_api_key,
            temperature=settings.temperature_for(task) if accepts_temperature else None,
            max_tokens=settings.max_tokens_for(task),
            timeout=120,
            max_retries=2,
        )
        self.client = client.bind(response_format=openai_response_format(settings, task))

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        """Gọi OpenAI và ghi lại token/chi phí ước tính."""
        import openai

        info = UsageInfo(
            provider="openai", model=self.model, input_tokens=0, output_tokens=0, started=time.perf_counter()
        )
        try:
            message = self.client.invoke([("system", prompt[0]), ("human", prompt[1])])
        except openai.OpenAIError as exc:  # gồm cả LengthFinishReasonError (model suy luận dùng hết token)
            raise LLMCallError(f"Gọi OpenAI thất bại ({type(exc).__name__}). Kiểm tra khóa, mạng và hạn mức.") from exc
        return _response(request, message, info)


def anthropic_output_config(settings: Settings, task: str, effort: str) -> dict:
    """`output_config` của Anthropic: mức effort + JSON Schema đầu ra (cùng schema strict với OpenAI)."""
    config: dict = {"effort": effort}
    schema = output_schema(task) if settings.llm_structured_output else None
    if schema is not None:
        config["format"] = {"type": "json_schema", "schema": schema}
    return config


class AnthropicProvider:
    """Gọi Claude qua SDK chính thức `anthropic`, ép đầu ra theo schema.

    Opus 5.5 luôn suy luận và không nhận `temperature`: độ sâu suy luận chỉnh bằng `effort` trong models.yaml (mặc
    định medium). Bật dự phòng phía máy chủ (`fallbacks="default"`): nếu model từ chối vì bộ lọc an toàn, Anthropic tự
    chạy lại bằng model khác trong cùng lời gọi; `usage.model` ghi đúng model đã trả lời.
    """

    def __init__(self, settings: Settings, model: str = "", task: str = "") -> None:
        if not settings.has_anthropic_key:
            raise LLMConfigError(
                f"Bước '{task}' dùng Anthropic (config/models.yaml) nhưng chưa có ANTHROPIC_API_KEY. "
                "Mở file .env, điền ANTHROPIC_API_KEY=<khóa của bạn>, hoặc đổi provider của bước này trong models.yaml."
            )
        import anthropic

        choice = settings.choice_for(task)
        self.model = model or choice.name
        self.max_tokens = settings.max_tokens_for(task)
        self.output_config = anthropic_output_config(settings, task, choice.effort or "medium")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=300, max_retries=2)

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        """Gọi Claude và ghi lại token/chi phí ước tính; bị cắt ngang hoặc từ chối = gọi thất bại (sang dự phòng)."""
        import anthropic

        started = time.perf_counter()
        try:
            message = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=prompt[0],
                messages=[{"role": "user", "content": prompt[1]}],
                output_config=self.output_config,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AnthropicError as exc:
            raise LLMCallError(
                f"Gọi Anthropic thất bại ({type(exc).__name__}). Kiểm tra khóa, mạng và hạn mức."
            ) from exc
        if message.stop_reason in ("max_tokens", "refusal"):
            raise LLMCallError(f"Anthropic dừng giữa chừng (stop_reason={message.stop_reason}), không có JSON đầy đủ.")
        usage = message.usage
        cached = usage.cache_read_input_tokens or 0
        info = UsageInfo(
            provider="anthropic",
            model=message.model or self.model,
            # Anthropic tách token trúng/ghi cache khỏi input_tokens; cộng lại cho giống cách đếm của OpenAI
            input_tokens=usage.input_tokens + cached + (usage.cache_creation_input_tokens or 0),
            output_tokens=usage.output_tokens,
            cached_tokens=cached,
            started=started,
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        return LLMResponse(text=text, usage=_usage(request, info))


class GoogleProvider:
    """Gọi Google Gemini qua langchain-google-genai, ép đầu ra theo schema (response_json_schema)."""

    def __init__(self, settings: Settings, model: str = "", task: str = "") -> None:
        if not settings.has_google_key:
            raise LLMConfigError(
                "Cần GOOGLE_API_KEY để dùng Gemini (LLM_PROVIDER=google hoặc dự phòng LLM_FALLBACK=google). "
                "Tạo khóa ở Google AI Studio rồi tự điền GOOGLE_API_KEY=<khóa> vào .env, hoặc đặt LLM_FALLBACK=none."
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        self.model = model or settings.google_model_name
        schema = output_schema(task) if settings.llm_structured_output else None
        self.client = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=settings.google_api_key,
            temperature=settings.temperature_for(task),
            max_tokens=settings.max_tokens_for(task),
            timeout=120,
            max_retries=2,
            response_mime_type="application/json",
            response_schema=schema,
        )

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        """Gọi Gemini và ghi lại token/chi phí ước tính."""
        from google.genai.errors import APIError
        from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

        info = UsageInfo(
            provider="google", model=self.model, input_tokens=0, output_tokens=0, started=time.perf_counter()
        )
        try:
            message = self.client.invoke([("system", prompt[0]), ("human", prompt[1])])
        except (ChatGoogleGenerativeAIError, APIError) as exc:
            raise LLMCallError(f"Gọi Gemini thất bại ({type(exc).__name__}). Kiểm tra khóa, mạng và hạn mức.") from exc
        return _response(request, message, info)


class FallbackProvider:
    """Gọi nhà cung cấp chính; chỉ khi GỌI THẤT BẠI (mạng, hạn mức, model lỗi) mới chuyển sang dự phòng.

    Câu trả lời sai định dạng KHÔNG chuyển dự phòng (các node đã tự xử lý). Dự phòng chỉ dựng khi cần.
    """

    def __init__(self, primary: LLMProvider, settings: Settings) -> None:
        self.primary, self.settings = primary, settings

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        """Gọi chính, lỗi thì gọi Gemini; `usage.provider/model` ghi đúng bên đã trả lời."""
        try:
            return self.primary.complete(request, prompt)
        except LLMCallError as exc:
            logger.warning("llm primary failed, using fallback", extra={"task": request.task, "error": str(exc)})
            try:
                backup = GoogleProvider(self.settings, task=request.task)
            except LLMConfigError as config_exc:
                raise LLMCallError(f"{exc} Không dùng được dự phòng Gemini: {config_exc}") from exc
            return backup.complete(request, prompt)


PROVIDERS: dict[str, type] = {"openai": OpenAIProvider, "anthropic": AnthropicProvider, "google": GoogleProvider}


def get_provider(settings: Settings | None = None, task: str = "") -> LLMProvider:
    """Chọn nhà cung cấp + model của từng bước theo config/models.yaml; bọc dự phòng nếu LLM_FALLBACK=google."""
    settings = settings or get_settings()
    if settings.llm_provider == "google":
        return GoogleProvider(settings, settings.model_for(task, "google"), task)
    if settings.llm_provider == "openai":
        choice = settings.choice_for(task)
        primary = PROVIDERS[choice.provider](settings, choice.name, task)
        wrap = settings.llm_fallback == "google" and choice.provider != "google"
        return FallbackProvider(primary, settings) if wrap else primary
    from src.services.llm_mock import MockProvider

    return MockProvider()


def call_llm(task: str, variables: dict[str, str]) -> LLMResponse:
    """Dựng prompt cho `task` và gọi nhà cung cấp hiện tại."""
    request = LLMRequest(task=task, variables=variables)
    response = get_provider(task=task).complete(request, render_prompt(request))
    logger.info("llm call", extra=response.usage.model_dump())
    return response


def parse_json_output(text: str) -> dict:
    """Lấy object JSON từ câu trả lời (chấp nhận khối ```json ... ```)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{") : text.rfind("}") + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMOutputError(f"LLM không trả về JSON hợp lệ: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise LLMOutputError("LLM phải trả về một object JSON.")
    return data


def to_json(value: object) -> str:
    """Chuyển dữ liệu thành JSON gọn (không thụt lề, không khoảng trắng thừa) để chèn vào prompt."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)

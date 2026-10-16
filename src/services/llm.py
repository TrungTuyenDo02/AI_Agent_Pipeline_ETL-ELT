"""Cổng gọi LLM duy nhất của hệ thống: `openai`, `google` hoặc `mock` (LLM_PROVIDER); dự phòng Gemini (LLM_FALLBACK).

Mọi node gọi `call_llm(task, variables)`; prompt nằm ở `src/prompts/<task>.md`. Nhà cung cấp + model của từng bước
(OpenAI, Anthropic hoặc Google) đọc từ `config/models.yaml`.
"""

import json
import logging
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from src.config import Settings, get_settings
from src.models.llm_outputs import output_schema
from src.models.schemas import LLMUsage
from src.services.circuit_breaker import get_breaker
from src.services.cost import PRICES_PER_MILLION, estimate_cost_usd
from src.services.cost_ledger import BudgetDeniedError, current_caller, get_ledger

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
USER_MARKER = "<!-- USER -->"
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)  # đầu file prompt (version, nhật ký thay đổi): không gửi LLM
DATA_TAG_RE = re.compile(r"<(\s*/?\s*data\b)", re.IGNORECASE)
SDK_MAX_RETRIES = 2  # SDK tự gọi lại (mạng, 429, 5xx); dự toán giữ trước tính đủ số lần này
# Mã lỗi máy chủ từ chối ngay, SDK không gọi lại và nhà cung cấp không tính tiền → hoàn khoản giữ trước
NOT_BILLED_STATUS = frozenset({400, 401, 403, 404, 422})


class LLMConfigError(RuntimeError):
    """Cấu hình LLM chưa đủ (ví dụ thiếu khóa). Thông báo bằng tiếng Việt."""


class LLMCallError(RuntimeError):
    """Gọi LLM thất bại (mạng, hết hạn mức, ...).

    `usage`: nhà cung cấp vẫn trả số token (bị cắt ở max_tokens, từ chối) → vẫn tính tiền.
    `not_billed`: chắc chắn không tính tiền (máy chủ từ chối ngay bằng mã 4xx không được thử lại) → hoàn khoản giữ trước.
    """

    def __init__(self, message: str, usage: LLMUsage | None = None, not_billed: bool = False) -> None:
        super().__init__(message)
        self.usage, self.not_billed = usage, not_billed


class LLMBudgetError(LLMCallError):
    """Hết trần token (RUN_TOKEN_BUDGET) hoặc không đủ ngân sách tiền để giữ trước: dừng và báo rõ, không gọi dự phòng."""


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


def _not_billed(exc: BaseException) -> bool:
    """Máy chủ đã trả lời bằng mã lỗi 4xx không được thử lại (OpenAI/Anthropic: `status_code`, Gemini: `code`)."""
    return (getattr(exc, "status_code", None) or getattr(exc, "code", None)) in NOT_BILLED_STATUS


def _openai_error_usage(request: LLMRequest, exc: BaseException, info: UsageInfo) -> LLMUsage | None:
    """`LengthFinishReasonError` mang theo bản trả lời đã tính tiền (model dùng hết max_tokens): lấy usage của nó."""
    usage = getattr(getattr(exc, "completion", None), "usage", None)
    if usage is None:
        return None
    cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    update = {
        "input_tokens": usage.prompt_tokens or 0,
        "output_tokens": usage.completion_tokens or 0,
        "cached_tokens": cached,
    }
    return _usage(request, info.model_copy(update=update))


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
            timeout=settings.timeout_for(task),
            max_retries=SDK_MAX_RETRIES,
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
            raise LLMCallError(
                f"Gọi OpenAI thất bại ({type(exc).__name__}). Kiểm tra khóa, mạng và hạn mức.",
                usage=_openai_error_usage(request, exc, info),
                not_billed=_not_billed(exc),
            ) from exc
        return _response(request, message, info)


def anthropic_output_config(settings: Settings, task: str, effort: str | None) -> dict:
    """`output_config` của Anthropic: mức effort (chỉ khi models.yaml khai báo; Haiku không nhận) + JSON Schema đầu ra."""
    config: dict = {"effort": effort} if effort else {}
    schema = output_schema(task) if settings.llm_structured_output else None
    if schema is not None:
        config["format"] = {"type": "json_schema", "schema": schema}
    return config


class AnthropicProvider:
    """Gọi Claude qua SDK chính thức `anthropic`, ép đầu ra theo schema.

    Không gửi `temperature`. `effort` chỉ gửi khi models.yaml khai báo (Opus/Sonnet nhận; Haiku 4.5 không nhận nên để trống).
    Bật dự phòng phía máy chủ (`fallbacks="default"`): nếu model từ chối vì bộ lọc an toàn, Anthropic tự
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
        self.output_config = anthropic_output_config(settings, task, choice.effort)
        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, timeout=settings.timeout_for(task), max_retries=SDK_MAX_RETRIES
        )

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
                f"Gọi Anthropic thất bại ({type(exc).__name__}). Kiểm tra khóa, mạng và hạn mức.",
                not_billed=_not_billed(exc),
            ) from exc
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
        if message.stop_reason in ("max_tokens", "refusal"):  # vẫn tính tiền: mang usage theo lỗi để sổ chi phí ghi đủ
            raise LLMCallError(
                f"Anthropic dừng giữa chừng (stop_reason={message.stop_reason}), không có JSON đầy đủ.",
                usage=_usage(request, info),
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
            timeout=settings.timeout_for(task),
            max_retries=SDK_MAX_RETRIES,
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
            raise LLMCallError(
                f"Gọi Gemini thất bại ({type(exc).__name__}). Kiểm tra khóa, mạng và hạn mức.",
                not_billed=_not_billed(exc),
            ) from exc
        return _response(request, message, info)


def estimate_call_usd(settings: Settings, model: str, task: str, prompt: tuple[str, str]) -> float:
    """Dự toán xấu nhất của một lượt gọi: đầu ra tối đa `max_tokens_for(task)`, nhân đủ số lần SDK tự gọi lại.

    Token đầu vào ước bằng số ký tự / 2: luôn ≥ số thật với tiếng Việt, JSON, SQL (khoảng 3–4 ký tự/token), không cần tiktoken.
    """
    schema = output_schema(task) if settings.llm_structured_output else None
    chars = len(prompt[0]) + len(prompt[1]) + (len(json.dumps(schema, ensure_ascii=False)) if schema else 0)
    one = estimate_cost_usd(model, chars // 2 + 1, settings.max_tokens_for(task))
    return one * (1 + SDK_MAX_RETRIES)


def _provider_name(provider: object) -> str:
    return next((name for name, cls in PROVIDERS.items() if isinstance(provider, cls)), type(provider).__name__)


class CostMeter:
    """Giữ trước ngân sách trước mỗi lượt gọi THẬT và quyết toán sau đó (sổ chi phí, ADR 0014). Bước V, 0 token.

    Model chưa có giá → dừng (LLMConfigError), không tính 0 USD. Không đủ ngân sách → LLMBudgetError, không gọi dự phòng.
    Quyết toán: có usage (kể cả lỗi bị cắt/từ chối) → tiền thật; lỗi chắc chắn không tính tiền → hoàn; còn lại → `unknown`.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def begin(self, provider: object, request: LLMRequest, prompt: tuple[str, str]) -> str:
        """Kiểm giá + giữ trước; trả mã lượt gọi trong sổ."""
        model = str(getattr(provider, "model", ""))
        if model not in PRICES_PER_MILLION:
            raise LLMConfigError(
                f"Model '{model}' (bước '{request.task}') chưa có giá trong src/services/cost.py nên không gọi thật: "
                "không tính được chi phí thì hạn mức tiền mất tác dụng. Thêm giá (USD/1 triệu token) rồi chạy lại."
            )
        owner, run_id = current_caller()
        ttl = self.settings.timeout_for(request.task) * (1 + SDK_MAX_RETRIES) + 60
        try:
            return get_ledger().reserve(
                owner=owner, run_id=run_id, task=request.task, provider=_provider_name(provider), model=model,
                estimate_usd=estimate_call_usd(self.settings, model, request.task, prompt), ttl_sec=ttl,
            )  # fmt: skip
        except BudgetDeniedError as exc:
            raise LLMBudgetError(str(exc)) from exc
        except SQLAlchemyError as exc:  # không ghi được sổ thì không kiểm được hạn mức: dừng, không gọi
            raise LLMBudgetError(
                f"Không mở được sổ chi phí ({type(exc).__name__}) nên không gọi LLM thật. Kiểm tra cơ sở dữ liệu."
            ) from exc

    def finish(self, call_id: str, response: LLMResponse | None = None, error: BaseException | None = None) -> None:
        """Quyết toán một lần; lỗi ghi sổ chỉ ghi log (lượt gọi tự chuyển `unknown` khi quá hạn), không làm mất kết quả."""
        usage = response.usage if response else getattr(error, "usage", None)
        if usage is not None and error is not None:  # lượt thất bại vẫn tốn token: cộng vào trần token của lần chạy
            _count_tokens(usage)
        try:
            ledger = get_ledger()
            if usage is not None and usage.model not in PRICES_PER_MILLION:
                # dự phòng phía máy chủ (Anthropic) trả lời bằng model chưa có giá: không tính 0, giữ khoản dự toán
                ledger.mark_unknown(call_id, note=f"model trả lời chưa có giá: {usage.model}")
            elif usage is not None:
                ledger.settle(call_id, usage.cost_usd, usage.input_tokens, usage.output_tokens)
            elif isinstance(error, LLMCallError) and error.not_billed:
                ledger.release(call_id, note=f"không tính tiền: {type(error.__cause__ or error).__name__}")
            else:
                ledger.mark_unknown(call_id, note=f"không có usage: {type(error.__cause__ or error).__name__}")
        except SQLAlchemyError as exc:
            logger.error("cost ledger settle failed", extra={"call_id": call_id, "error": type(exc).__name__})

    def release(self, call_id: str, note: str) -> None:
        """Hoàn khoản giữ trước của lượt chắc chắn chưa gửi (ví dụ đang ngắt mạch)."""
        try:
            get_ledger().release(call_id, note=note)
        except SQLAlchemyError as exc:
            logger.error("cost ledger release failed", extra={"call_id": call_id, "error": type(exc).__name__})

    def call(self, provider: LLMProvider, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        """Giữ trước → gọi → quyết toán."""
        call_id = self.begin(provider, request, prompt)
        try:
            response = provider.complete(request, prompt)
        except BaseException as exc:
            self.finish(call_id, error=exc)
            raise
        self.finish(call_id, response=response)
        return response


class MeteredProvider:
    """Bọc một nhà cung cấp thật bằng sổ chi phí (đường không có dự phòng, ví dụ LLM_PROVIDER=google)."""

    def __init__(self, inner: LLMProvider, meter: CostMeter) -> None:
        self.inner, self.meter = inner, meter
        self.model = getattr(inner, "model", "")

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        return self.meter.call(self.inner, request, prompt)


class FallbackProvider:
    """Gọi nhà cung cấp chính qua circuit breaker; lỗi hoặc đang ngắt mạch thì sang dự phòng Gemini (nếu bật).

    Chỉ khi GỌI THẤT BẠI (mạng, hạn mức, model lỗi) mới tính là lỗi: câu trả lời sai định dạng KHÔNG chuyển dự phòng và
    không làm bộ ngắt đếm lỗi (các node đã tự xử lý). Bộ ngắt riêng cho từng cặp `nhà cung cấp/model` nên một nhà
    cung cấp hỏng không kéo nhà khác hỏng theo. Đang ngắt mạch → không chờ timeout, bên gọi nhận lỗi/dự phòng ngay.
    Dự phòng chỉ dựng khi cần; `use_fallback=False` thì chỉ có ngắt mạch, không có dự phòng.
    `meter` (sổ chi phí): giữ trước TRƯỚC khi xin bộ ngắt (bị từ chối ngân sách thì không chiếm lượt thăm dò), giữ riêng
    cho dự phòng lúc chuyển sang; thiếu ngân sách hay thiếu giá thì dừng, không chuyển dự phòng.
    """

    def __init__(
        self,
        primary: LLMProvider,
        settings: Settings,
        key: str = "",
        use_fallback: bool = True,
        meter: CostMeter | None = None,
    ) -> None:
        self.primary, self.settings, self.use_fallback, self.meter = primary, settings, use_fallback, meter
        self.key = key or f"{type(primary).__name__}/{getattr(primary, 'model', '?')}"

    def complete(self, request: LLMRequest, prompt: tuple[str, str]) -> LLMResponse:
        """Gọi chính, lỗi hoặc ngắt mạch thì gọi Gemini; `usage.provider/model` ghi đúng bên đã trả lời."""
        breaker = get_breaker(self.key, self.settings)
        call_id = self.meter.begin(self.primary, request, prompt) if self.meter else ""
        if breaker.allow():
            try:
                response = self.primary.complete(request, prompt)
            except LLMCallError as exc:
                self._finish(call_id, error=exc)
                breaker.record_failure()
                failure = exc
            except BaseException as exc:
                self._finish(call_id, error=exc)
                raise
            else:
                self._finish(call_id, response=response)
                breaker.record_success()
                return response
        else:
            if self.meter and call_id:
                self.meter.release(call_id, note="đang ngắt mạch, không gửi")
            failure = LLMCallError(
                f"Nhà cung cấp {self.key} đang tạm ngắt vì nhiều lần lỗi liên tiếp; thử lại sau khoảng "
                f"{breaker.retry_in()} giây."
            )
        if not self.use_fallback:
            raise failure
        logger.warning("llm primary unavailable, using fallback", extra={"task": request.task, "error": str(failure)})
        try:
            backup = GoogleProvider(self.settings, task=request.task)
        except LLMConfigError as config_exc:
            raise LLMCallError(f"{failure} Không dùng được dự phòng Gemini: {config_exc}") from failure
        return self.meter.call(backup, request, prompt) if self.meter else backup.complete(request, prompt)

    def _finish(self, call_id: str, response: LLMResponse | None = None, error: BaseException | None = None) -> None:
        if self.meter and call_id:
            self.meter.finish(call_id, response=response, error=error)


PROVIDERS: dict[str, type] = {"openai": OpenAIProvider, "anthropic": AnthropicProvider, "google": GoogleProvider}


def get_provider(settings: Settings | None = None, task: str = "") -> LLMProvider:
    """Chọn nhà cung cấp + model của từng bước theo config/models.yaml; bọc dự phòng nếu LLM_FALLBACK=google.

    Mọi đường gọi thật đều qua sổ chi phí (CostMeter); mock không tốn tiền nên không qua.
    """
    settings = settings or get_settings()
    if settings.llm_provider == "google":
        return MeteredProvider(GoogleProvider(settings, settings.model_for(task, "google"), task), CostMeter(settings))
    if settings.llm_provider == "openai":
        choice = settings.choice_for(task)
        primary = PROVIDERS[choice.provider](settings, choice.name, task)
        use_fallback = settings.llm_fallback == "google" and choice.provider != "google"
        return FallbackProvider(
            primary,
            settings,
            key=f"{choice.provider}/{choice.name}",
            use_fallback=use_fallback,
            meter=CostMeter(settings),
        )
    from src.services.llm_mock import MockProvider

    return MockProvider()


@dataclass
class RunBudget:
    """Trần token của một lần chạy: `used` cộng dồn token vào + ra của mọi lượt gọi LLM trong lần chạy."""

    limit: int
    used: int = 0


_BUDGET: ContextVar[RunBudget | None] = ContextVar("run_token_budget", default=None)


@contextmanager
def run_budget(limit: int, used: int = 0) -> Iterator[RunBudget]:
    """Đặt trần token cho các lượt gọi LLM trong khối này (runner bọc mỗi lượt chạy graph). `limit` = 0: không chặn."""
    budget = RunBudget(limit=limit, used=used)
    token = _BUDGET.set(budget)
    try:
        yield budget
    finally:
        _BUDGET.reset(token)


def _count_tokens(usage: LLMUsage) -> None:
    """Cộng token của một lượt gọi vào trần token của lần chạy hiện tại (nếu có)."""
    budget = _BUDGET.get()
    if budget:
        budget.used += usage.input_tokens + usage.output_tokens


def call_llm(task: str, variables: dict[str, str]) -> LLMResponse:
    """Dựng prompt cho `task` và gọi nhà cung cấp hiện tại; vượt trần token của lần chạy thì từ chối gọi."""
    budget = _BUDGET.get()
    if budget and budget.limit and budget.used >= budget.limit:
        raise LLMBudgetError(
            f"Lần chạy đã dùng {budget.used:,} token, chạm trần {budget.limit:,} token mỗi lần chạy "
            "(RUN_TOKEN_BUDGET) nên dừng lại. Hãy tách yêu cầu nhỏ hơn hoặc nhờ quản trị viên tăng trần."
        )
    request = LLMRequest(task=task, variables=variables)
    response = get_provider(task=task).complete(request, render_prompt(request))
    _count_tokens(response.usage)
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

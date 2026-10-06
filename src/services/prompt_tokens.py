"""Đếm token prompt offline (không cần khóa): dùng cho ngân sách token và báo cáo eval/results/prompt_tokens.md."""

import json
from functools import lru_cache

import tiktoken

from src.config import get_settings
from src.models.llm_outputs import output_schema
from src.services.llm import LLMRequest, render_prompt

ENCODING_NAME = "o200k_base"  # bộ mã của họ GPT-4o/GPT-5; số gần đúng với model khác


@lru_cache
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING_NAME)


def count_tokens(text: str) -> int:
    """Số token của một đoạn văn bản."""
    return len(_encoding().encode(text))


def schema_tokens(task: str) -> int:
    """Token ước tính của JSON Schema đầu ra gửi kèm lời gọi (0 khi tắt structured output hoặc không có schema)."""
    schema = output_schema(task) if get_settings().llm_structured_output else None
    return count_tokens(json.dumps(schema, ensure_ascii=False, separators=(",", ":"))) if schema else 0


def static_tokens(task: str) -> dict[str, int]:
    """Phần tĩnh (giống hệt mọi lần gọi): system prompt + schema đầu ra."""
    system, _ = render_prompt(LLMRequest(task=task, variables={}))
    parts = {"system": count_tokens(system), "schema": schema_tokens(task)}
    return {**parts, "total": parts["system"] + parts["schema"]}

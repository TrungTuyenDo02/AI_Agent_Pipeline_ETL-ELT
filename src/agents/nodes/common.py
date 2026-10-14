"""Hàm dùng chung cho các node."""

from pathlib import Path

import logging

from src.agents.state import PipelineState
from src.agents.tools.pii import mask_literals
from src.models.evidence import ErrorEntry
from src.models.spec import PipelineSpec
from src.services.agent_memory import get_agent_memory
from src.services.error_memory import classify_error, error_signature, get_error_memory
from src.services.llm import LLMResponse

logger = logging.getLogger(__name__)
SANDBOX_DB = "sandbox.duckdb"


def spec_of(state: PipelineState) -> PipelineSpec:
    """Đặc tả hiện tại dưới dạng Pydantic."""
    return PipelineSpec.model_validate(state.get("spec") or {"request_text": state.get("request_text", "")})


def mart_path(spec: PipelineSpec) -> str:
    """Đường dẫn model đích trong dự án dbt."""
    return f"models/marts/{spec.target}.sql"


def sandbox_db(state: PipelineState) -> Path:
    """File DuckDB sandbox của lần chạy."""
    return Path(state["workspace"]) / SANDBOX_DB


def usage_of(response: LLMResponse) -> list[dict]:
    """Mục thống kê LLM để cộng dồn vào `llm_usage`."""
    return [response.usage.model_dump()]


def register_failure(state: PipelineState, message: str, sql_before: str = "") -> dict:
    """Ghi lỗi V-node vào sổ lỗi và tăng bộ đếm sửa; trả về phần cập nhật state."""
    signature = error_signature(message)
    entry = ErrorEntry(code=classify_error(message), signature=signature, description=message, sql_before=sql_before)
    get_error_memory().record(entry)
    return {
        "fix_attempts": state.get("fix_attempts", 0) + 1,
        "error_signatures": [*state.get("error_signatures", []), signature],
        "error_notes": [*state.get("error_notes", []), f"{entry.code}: {mask_literals(message)[:200]}"],
    }


def all_files(state: PipelineState) -> dict[str, str]:
    """Toàn bộ file sinh ra (code + test)."""
    return {**state.get("code_files", {}), **state.get("test_files", {})}


def memory_notes(state: PipelineState) -> list[str]:
    """Tối đa 3 mục bộ nhớ ĐÃ DUYỆT của chính người tạo yêu cầu (lỗi từng gặp và đã sửa). Chỉ là gợi ý cho LLM."""
    account = state.get("requester", "")
    if not account:
        return []
    try:
        items = get_agent_memory().approved(account, "error_fix", state.get("request_text", ""))
    except Exception:  # bộ nhớ lỗi không được làm hỏng lần chạy
        logger.exception("agent memory unavailable")
        return []
    return [item.content[:300] for item in items]


def remember_fixes(run_id: str, values: dict) -> int:
    """Lần chạy đã tự sửa lỗi và tới bước duyệt: đề xuất các lỗi đã gặp vào bộ nhớ (luôn `pending`, chờ Reviewer duyệt)."""
    account, notes = values.get("requester", ""), list(dict.fromkeys(values.get("error_notes", [])))[:3]
    attempts = values.get("fix_attempts", 0)
    if not account or not notes or not attempts:
        return 0
    memory, saved = get_agent_memory(), 0
    for note in notes:
        item = memory.add(account, "error_fix", f"Lỗi từng gặp ({note}); agent đã tự sửa được sau {attempts} lần.", run_id)
        saved += 1 if item else 0
    return saved

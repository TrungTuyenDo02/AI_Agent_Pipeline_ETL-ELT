"""G0 Cửa kiểm tra đầu vào: chặn yêu cầu vô nghĩa/lạc đề TRƯỚC Planner (tầng 0–1 bằng code, tầng 2 bằng model nhỏ).

Cùng luật với kiểm tra ở API/CLI (`src/services/input_gate.py`); đứng đầu graph để mọi đường vào (API, CLI, eval, chạy lại)
đều qua cửa. Kết luận:
- `ok` → Planner;
- `rejected` → lần chạy dừng với trạng thái `rejected_input`, không tính vào hạn mức;
- `needs_info` → `input_info` hỏi người dùng bằng mẫu câu cố định (thiếu ô nào) hoặc xin viết lại, tối đa MAX_CLARIFY_ROUNDS vòng.
"""

from langgraph.types import interrupt

from src.agents.state import PipelineState
from src.config import get_settings
from src.models.schemas import RunStatus
from src.services.input_gate import evaluate

MAX_REPLY_CHARS = 2000
HANDOFF = (
    "Đã hỏi bổ sung {rounds} vòng nhưng yêu cầu vẫn chưa đủ rõ. Hãy nhờ kỹ sư dữ liệu hỗ trợ trực tiếp, hoặc gửi lại yêu cầu "
    "mới nêu rõ bảng/nguồn và việc cần làm."
)


def input_gate_node(state: PipelineState) -> dict:
    """Kiểm tra `request_text`; token của tầng 2 (nếu có) vào `llm_usage` với task `input_gate`."""
    result, usage = evaluate(state.get("request_text", ""), state.get("source_catalog"))
    update: dict = {"input_gate": result.model_dump(), "llm_usage": usage}
    if result.status == "rejected":
        update.update(status=RunStatus.REJECTED_INPUT.value, error=result.message)
    return update


def input_info_node(state: PipelineState) -> dict:
    """Tạm dừng hỏi người dùng. Thiếu ô (`missing`) → câu trả lời được nối vào yêu cầu; xin viết lại (`rewrite`) → thay yêu cầu."""
    gate, rounds = state.get("input_gate") or {}, state.get("clarify_rounds", 0)
    if rounds >= get_settings().max_clarify_rounds:
        return {"status": RunStatus.FAILED.value, "error": HANDOFF.format(rounds=rounds)}
    reply = interrupt(
        {
            "kind": "input",
            "code": gate.get("code", ""),
            "message": gate.get("message", ""),
            "missing": gate.get("missing", []),
            "examples": gate.get("examples", []),
        }
    )
    reply = reply if isinstance(reply, dict) else {}
    text = str(reply.get("text", "")).strip()[:MAX_REPLY_CHARS]
    if reply.get("action") == "abort" or not text:
        return {
            "status": RunStatus.FAILED.value,
            "error": "Đã dừng theo yêu cầu của người dùng ở bước bổ sung thông tin.",
        }
    request = text if gate.get("code") == "rewrite" else f"{state.get('request_text', '')}\n{text}"
    return {"request_text": request[: MAX_REPLY_CHARS * 2], "clarify_rounds": rounds + 1}

"""G0 Cửa kiểm tra đầu vào (code, 0 token ở tầng 0–1): chặn yêu cầu vô nghĩa/lạc đề TRƯỚC Planner.

Cùng luật với kiểm tra ở API/CLI (`src/services/input_gate.py`); đứng đầu graph để mọi đường vào (API, CLI, eval,
chạy lại) đều qua cửa. Bị chặn: lần chạy dừng với trạng thái `rejected_input`, không gọi LLM, không tính vào hạn mức.
"""

from src.agents.state import PipelineState
from src.models.schemas import RunStatus
from src.services.input_gate import precheck


def input_gate_node(state: PipelineState) -> dict:
    """Kiểm tra `request_text`; `ok` → Planner, còn lại → dừng kèm thông điệp tiếng Việt."""
    result = precheck(state.get("request_text", ""), state.get("source_catalog"))
    gate = result.model_dump()
    if result.status == "ok":
        return {"input_gate": gate}
    return {"input_gate": gate, "status": RunStatus.REJECTED_INPUT.value, "error": result.message}

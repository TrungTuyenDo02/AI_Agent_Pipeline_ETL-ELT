"""J2 Duyệt: graph tạm dừng chờ approve/reject.

Quyền (chỉ vai trò Reviewer) được kiểm trước khi tới đây: API (`require_role`) và runner (`review_permission_error`).
"""

import logging

from langgraph.types import interrupt
from pydantic import ValidationError

from src.agents.nodes.common import all_files
from src.agents.nodes.schema_guard import promote_snapshot
from src.agents.state import PipelineState
from src.config import get_settings
from src.models.evidence import ReviewDecision
from src.models.schemas import RunStatus

logger = logging.getLogger(__name__)


def validate_decision(reply: object, run_id: str) -> ReviewDecision | None:
    """Quyết định hợp lệ hay không (sai định dạng → None)."""
    try:
        return ReviewDecision.model_validate({**(reply if isinstance(reply, dict) else {}), "run_id": run_id})
    except ValidationError:
        return None


def review_node(state: PipelineState) -> dict:
    """Chờ quyết định; reject kèm ghi chú → quay lại Codegen với bộ file hiện tại làm gốc so sánh."""
    reply = interrupt({"kind": "review", "run_id": state["run_id"], "requester": state.get("requester", "")})
    decision = validate_decision(reply, state["run_id"])
    if decision is None:
        return {"review": {"invalid": True}}
    if decision.decision == "approve":
        return {"review": decision.model_dump()}
    return {
        "review": decision.model_dump(),
        "review_notes": [*state.get("review_notes", []), decision.note or "(không có ghi chú)"],
        "review_rounds": state.get("review_rounds", 0) + 1,
        "previous_files": all_files(state),
        "fix_attempts": 0,
        "error_signatures": [],
        "status": RunStatus.RUNNING.value,
    }


def finalize_node(state: PipelineState) -> dict:
    """Đã duyệt: code trong workspace sẵn sàng để Engineer mở PR → CI/CD (không tự push).

    Cấu trúc nguồn của lần chạy này thành bản chuẩn mới (mục 8) — chỉ khi Reviewer duyệt.
    """
    if get_settings().database_url:
        try:
            promote_snapshot(state, (state.get("review") or {}).get("reviewer", ""))
        except Exception as exc:  # noqa: BLE001 — lỗi CSDL không được làm mất quyết định duyệt; log để xử lý
            logger.error(
                "schema baseline save failed", extra={"run_id": state.get("run_id"), "error": type(exc).__name__}
            )
    return {"status": RunStatus.APPROVED.value}


def fail_node(state: PipelineState) -> dict:
    """Dừng hẳn với lý do rõ ràng."""
    reason = state.get("error") or "Vượt quá số vòng cho phép (lập kế hoạch / sửa lỗi / duyệt)."
    return {"status": RunStatus.FAILED.value, "error": reason}

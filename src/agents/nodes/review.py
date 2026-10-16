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
from src.services import schema_drift

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
            reviewer = (state.get("review") or {}).get("reviewer", "")
            promote_snapshot(state, reviewer)
            close_patched_changes(state, reviewer)
        except Exception as exc:  # noqa: BLE001 — lỗi CSDL không được làm mất quyết định duyệt; log để xử lý
            logger.error(
                "schema baseline save failed", extra={"run_id": state.get("run_id"), "error": type(exc).__name__}
            )
    return {"status": RunStatus.APPROVED.value}


def close_patched_changes(state: PipelineState, reviewer: str) -> int:
    """Reviewer duyệt bản vá → các thay đổi cấu trúc mà bản vá đã xử lý thành `acknowledged` và cấu trúc mới thành bản chuẩn (số đỏ giảm)."""
    done = 0
    for change in {(c["source_id"], c["id"]) for c in (state.get("patch") or {}).get("changes", [])}:
        done += schema_drift.acknowledge(change[0], reviewer or "reviewer", change_id=change[1])
    return done


def _round_limit_reason(state: PipelineState) -> str:
    """Lý do dừng khi không có lỗi cụ thể: quá số vòng hỏi làm rõ thì chuyển cho người xử lý."""
    limit = get_settings().max_clarify_rounds
    if state.get("clarify_rounds", 0) >= limit and (state.get("spec") or {}).get("questions"):
        return (
            f"Đã hỏi làm rõ {limit} vòng nhưng yêu cầu vẫn chưa đủ rõ. Hãy viết lại yêu cầu cụ thể hơn "
            "(nguồn, bảng đích, cột, điều kiện lọc) hoặc nhờ kỹ sư dữ liệu hỗ trợ trực tiếp."
        )
    return "Vượt quá số vòng cho phép (lập kế hoạch / sửa lỗi / duyệt)."


def fail_node(state: PipelineState) -> dict:
    """Dừng hẳn với lý do rõ ràng."""
    reason = state.get("error") or _round_limit_reason(state)
    return {"status": RunStatus.FAILED.value, "error": reason}

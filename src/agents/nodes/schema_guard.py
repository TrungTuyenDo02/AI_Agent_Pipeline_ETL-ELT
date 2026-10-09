"""Vs Soát cấu trúc nguồn (code, 0 token): so ảnh chụp cấu trúc MỚI NHẤT với bản Reviewer đã duyệt (mục 8).

- Thêm cột / đổi kiểu / giá trị mới ở cột phân loại → cảnh báo kèm đề xuất sửa, chạy tiếp; Reviewer xem ở J2.
- Cột bị xóa hoặc nghi đổi tên → tạm dừng: Engineer xác nhận từng cặp đổi tên (không tự đoán) hoặc dừng hẳn.
- Ảnh chụp chỉ thành bản chuẩn khi Reviewer duyệt lần chạy (`finalize`).
"""

from langgraph.types import interrupt

from src.agents.state import PipelineState
from src.models.schemas import RunStatus
from src.services.schema_watch import check_against_baselines, save_baselines, snapshot_from_profile


def confirmed_renames(report: dict, reply: dict) -> dict[str, str]:
    """Chỉ nhận cặp đổi tên nằm trong danh sách nghi vấn do code đưa ra (người không gõ tên tùy ý)."""
    allowed = {(old, new) for change in report.get("changes", []) for old, new in change.get("rename_candidates", [])}
    wanted = reply.get("renames") if isinstance(reply.get("renames"), dict) else {}
    return {str(old): str(new) for old, new in wanted.items() if (old, new) in allowed}


def schema_guard_node(state: PipelineState) -> dict:
    """So sánh rồi chạy tiếp, hoặc chờ Engineer xác nhận khi có cột bị xóa / nghi đổi tên."""
    snapshot = snapshot_from_profile(state.get("profile", {}), state.get("source_catalog", []))
    report = check_against_baselines(snapshot).model_dump()
    out = {"schema_snapshot": snapshot, "schema_report": report}
    if not report["blocking"]:
        return out
    reply = interrupt({"kind": "schema", "report": report})
    reply = reply if isinstance(reply, dict) else {}
    if reply.get("action") != "continue":
        return {
            **out,
            "status": RunStatus.FAILED.value,
            "error": "Đã dừng: nguồn có cột bị xóa hoặc đổi tên, người dùng chọn không chạy tiếp.",
        }
    decision = {"by": str(reply.get("by", ""))[:64], "renames": confirmed_renames(report, reply)}
    return {**out, "schema_decision": decision}


def promote_snapshot(state: PipelineState, approved_by: str) -> int:
    """Gọi khi Reviewer duyệt: ảnh chụp của lần chạy thành bản chuẩn mới."""
    snapshot = state.get("schema_snapshot") or {}
    return save_baselines(snapshot, state.get("run_id", ""), approved_by) if snapshot else 0

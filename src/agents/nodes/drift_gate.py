"""G1 Kiểm tra cấu trúc nguồn (code, 0 token): trước Planner, so cấu trúc hiện tại của các nguồn bạn được dùng với bản chuẩn.

- Có thay đổi `breaking` đang `open` → CHẶN run: nêu rõ bằng tiếng Việt thay đổi gì, ở bảng/cột nào; Engineer chọn "Tôi đã biết, dùng
  cấu trúc mới" (đặt bản chuẩn mới, ghi AuditLog) hoặc dừng. Không tự động chạy tiếp, không tự sửa.
- `warning`/`info` cho chạy tiếp; được ghi vào state để hiện ở màn Duyệt kế hoạch (J1b).
- Cấu trúc nguồn lúc bắt đầu cũng được ghi vào state: ngay trước J2 hệ thống kiểm lại (`schema_drift.recheck_run`).
- Không có cơ sở dữ liệu ứng dụng (CLI demo): không có nơi lưu bản chuẩn nên bỏ qua kiểm tra, ghi rõ `checked: false`.
"""

from langgraph.types import interrupt

from src.agents.state import PipelineState
from src.config import get_settings
from src.models.drift import SchemaChangeView
from src.models.schemas import RunStatus
from src.services import schema_drift
from src.services import source_registry as registry

CACHE_SEC = (
    30  # nguồn vừa kiểm trong 30 giây thì dùng lại kết quả (nhiều lần chạy liên tiếp không hỏi lại cơ sở dữ liệu nguồn)
)
MAX_SHOWN = 12
STOPPED = "Đã dừng: nguồn dữ liệu đổi cấu trúc (thay đổi chặn) và người dùng chọn không chạy tiếp."


def change_payload(change: SchemaChangeView) -> dict:
    return {
        "id": change.id, "source_id": change.source_id, "source_name": change.source_name, "table": change.table,
        "severity": change.severity, "change_type": change.change_type, "detail": change.detail, "hint": change.hint,
    }  # fmt: skip


def blocking_message(changes: list[SchemaChangeView]) -> str:
    """Thông điệp tiếng Việt nêu thay đổi gì, ở bảng/cột nào, và hai lựa chọn."""
    lines = [f"- {c.source_name}: {c.detail}" + (f" ({c.hint})" if c.hint else "") for c in changes[:MAX_SHOWN]]
    more = f"\n… và {len(changes) - MAX_SHOWN} thay đổi khác." if len(changes) > MAX_SHOWN else ""
    return (
        "Cấu trúc nguồn dữ liệu đã đổi so với bản chuẩn, có thay đổi chặn:\n"
        + "\n".join(lines)
        + more
        + '\nNếu bạn biết thay đổi này và muốn dùng cấu trúc mới, chọn "Tôi đã biết, dùng cấu trúc mới"; nếu không hãy dừng và hỏi đội phụ trách nguồn.'
    )


def drift_gate_node(state: PipelineState) -> dict:
    """Kiểm cấu trúc các nguồn người tạo yêu cầu được dùng; chặn khi có `breaking` đang mở, cho qua và ghi cảnh báo khi còn lại."""
    settings = get_settings()
    if not settings.database_url or not settings.drift_gate_enabled:
        return {"drift": {"checked": False}}
    requester = state.get("requester", "")
    user = registry.user_context(requester)
    sources = [s for s in registry.get_visible_sources(user) if s.enabled]
    report = schema_drift.check_sources(
        sources, with_profile=lambda s: s.kind == "file", cache_sec=CACHE_SEC
    )  # hồ sơ thống kê: chỉ nguồn tệp (đã nhớ sẵn), nguồn CSDL ngoài đo khi kiểm định kỳ
    if report.open_breaking:
        reply = interrupt(
            {
                "kind": "drift",
                "message": blocking_message(report.open_breaking),
                "changes": [change_payload(c) for c in report.open_breaking[:50]],
            }
        )
        reply = reply if isinstance(reply, dict) else {}
        if reply.get("action") != "continue":
            return {"status": RunStatus.FAILED.value, "error": STOPPED, "drift": {"checked": True}}
        by = str(reply.get("by") or requester)[:64]
        for source_id in sorted({c.source_id for c in report.open_breaking}):
            schema_drift.acknowledge(source_id, by)
        schema_drift.forget_recent()
        report = schema_drift.check_sources(sources, cache_sec=0)
    return {
        "drift": {
            "checked": True,
            "unreachable": report.unreachable,
            "warnings": [change_payload(c) for c in report.warnings[:50]],
            "tables": report.tables,
        }
    }

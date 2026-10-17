"""Thay đổi cấu trúc nguồn (giai đoạn 5): danh sách, xác nhận "Tôi đã biết, dùng cấu trúc mới", kiểm tra lại, kiểm tra định kỳ.

Chỉ phát hiện và báo; KHÔNG tự tạo run, tự chạy hay tự merge bản vá. Bản vá chỉ do người bấm "Đề xuất bản vá" (`POST /runs/{id}/patch`)
và đi qua luồng chuẩn (sandbox → test → duyệt J2). Kiểm tra định kỳ (`POST /sources/check-drift`) dùng khóa nội bộ `DRIFT_CHECK_TOKEN`.
"""

import hmac
import logging
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

from src.api.deps import CurrentUser, LoggedIn, client_ip
from src.api.sources import user_context
from src.config import get_settings
from src.models.drift import Advice, ChangeDiff, DriftReport, SchemaChangeView
from src.models.sources import DataSource
from src.services import auth, drift_advice, schema_drift
from src.services import source_registry as registry
from src.services.cost_ledger import llm_caller

logger = logging.getLogger(__name__)
router = APIRouter(tags=["drift"])
cron_router = APIRouter(tags=["drift"])
NO_SOURCE = "Không tìm thấy nguồn dữ liệu này."
NO_CHANGE = "Không tìm thấy thay đổi này."
CAN_ACT = ("admin", "engineer")


def _need_database() -> None:
    if not get_settings().database_url:
        raise HTTPException(status_code=503, detail="Cần cấu hình DATABASE_URL để theo dõi thay đổi cấu trúc nguồn.")


def _visible(user: CurrentUser) -> dict[int, DataSource]:
    return {s.id: s for s in registry.get_visible_sources(user_context(user))}


def _may_act(user: CurrentUser) -> None:
    if user.role not in CAN_ACT:
        raise HTTPException(
            status_code=403, detail="Chỉ Admin hoặc Engineer của phòng ban được thao tác với cấu trúc nguồn."
        )


@router.get("/schema-changes", response_model=list[SchemaChangeView])
def list_schema_changes(
    user: LoggedIn,
    status: Literal["open", "acknowledged", "resolved"] | None = None,
    severity: Literal["info", "warning", "breaking"] | None = None,
    source_id: int | None = Query(default=None, ge=1),
) -> list[SchemaChangeView]:
    """Thay đổi cấu trúc của các nguồn bạn được thấy, kèm pipeline bị ảnh hưởng (lần chạy dùng đúng bảng/cột đó)."""
    _need_database()
    visible = _visible(user)
    ids = [source_id] if source_id in visible else [] if source_id else list(visible)
    return schema_drift.list_changes(ids, status=status, severity=severity)


@router.post("/schema-changes/{change_id}/acknowledge", response_model=dict)
def acknowledge_change(change_id: int, user: LoggedIn, request: Request) -> dict:
    """ "Tôi đã biết, dùng cấu trúc mới": đặt cấu trúc hiện tại của bảng đó làm bản chuẩn mới (ghi AuditLog)."""
    _need_database()
    _may_act(user)
    change = schema_drift.get_change(change_id)
    if change is None or change.source_id not in _visible(user):
        raise HTTPException(status_code=404, detail=NO_CHANGE)  # không thấy nguồn thì cũng như không có thay đổi
    done = schema_drift.acknowledge(change.source_id, user.name, table=change.table)
    schema_drift.forget_recent()
    auth.audit(
        "schema.acknowledge", user.name, target=f"change:{change_id}", ip=client_ip(request), detail={"changes": done}
    )
    return {"acknowledged": done}


class SuggestBody(BaseModel):
    """`run_id`: pipeline cần đề xuất (mặc định lần chạy đầu tiên dùng bảng đó); `use_ai`: nhờ Gemini diễn giải thêm (tốn một lượt nhỏ)."""

    run_id: str = ""
    use_ai: bool = False


def _visible_change(change_id: int, user: CurrentUser) -> SchemaChangeView:
    change = schema_drift.get_change(change_id)
    if change is None or change.source_id not in _visible(user):
        raise HTTPException(status_code=404, detail=NO_CHANGE)
    return change


@router.get("/schema-changes/{change_id}/diff", response_model=ChangeDiff)
def change_diff(change_id: int, user: LoggedIn) -> ChangeDiff:
    """Hình trước/sau của thay đổi: bảng nào, cột nào, đổi gì (chỉ cấu trúc)."""
    _need_database()
    _visible_change(change_id, user)
    diff = drift_advice.change_diff(change_id)
    if diff is None:
        raise HTTPException(status_code=404, detail=NO_CHANGE)
    return diff


@router.post("/schema-changes/{change_id}/suggest", response_model=Advice)
def suggest_fix(change_id: int, body: SuggestBody, user: LoggedIn) -> Advice:
    """Đề xuất sửa pipeline: file nào cần sửa và sửa gì (code dựng, 0 token). `use_ai=true` thêm lời diễn giải của Gemini.
    Chỉ đề xuất; không tạo run (tạo bản vá là nút "Đề xuất bản vá")."""
    _need_database()
    _may_act(user)
    change = _visible_change(change_id, user)
    with llm_caller(user.name):  # "Hỏi AI" tính vào hạn mức tiền của người bấm (sổ chi phí)
        return drift_advice.suggest(change, body.run_id, body.use_ai)


@router.post("/sources/{source_id}/check-drift", response_model=DriftReport)
def check_source_drift(source_id: int, user: LoggedIn, request: Request) -> DriftReport:
    """Nút "Kiểm tra lại cấu trúc" ở trang Nguồn dữ liệu (Admin hoặc Engineer có quyền với nguồn)."""
    _need_database()
    _may_act(user)
    source = _visible(user).get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=NO_SOURCE)
    report = schema_drift.check_sources([source], with_profile=True, cache_sec=0)
    auth.audit(
        "schema.check",
        user.name,
        target=f"source:{source_id}",
        ip=client_ip(request),
        detail={"new": len(report.new_changes)},
    )
    return report


@cron_router.post("/sources/check-drift", response_model=dict)
def check_all_drift(request: Request, x_drift_token: str = Header(default="")) -> dict:
    """Kiểm tra định kỳ mọi nguồn đang bật (lịch GitHub Actions hoặc bộ lập lịch khác). Bảo vệ bằng khóa nội bộ `DRIFT_CHECK_TOKEN`
    (không đặt trong repo); chưa cấu hình thì endpoint tắt. Mỗi lần chạy ghi `SchemaChange` nếu có thay đổi."""
    token = get_settings().drift_check_token
    if not token:
        raise HTTPException(status_code=503, detail="Chưa cấu hình DRIFT_CHECK_TOKEN nên kiểm tra định kỳ đang tắt.")
    if not hmac.compare_digest(x_drift_token.encode(), token.encode()):
        auth.audit("schema.check", "cron", outcome="denied", ip=client_ip(request))
        raise HTTPException(status_code=403, detail="Khóa kiểm tra định kỳ không đúng.")
    _need_database()
    report = schema_drift.check_sources(registry.list_sources(include_disabled=False), with_profile=True, cache_sec=0)
    auth.audit(
        "schema.check", "cron", ip=client_ip(request),
        detail={"checked": report.checked_sources, "new": len(report.new_changes), "breaking": len(report.open_breaking)},
    )  # fmt: skip
    return {
        "checked": report.checked_sources,
        "new_changes": len(report.new_changes),
        "open_breaking": len(report.open_breaking),
        "open_warnings": len(report.warnings),
        "unreachable": report.unreachable,
    }

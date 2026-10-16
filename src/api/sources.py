"""Sổ nguồn dữ liệu: đăng ký nguồn, phòng ban, quyền xem thêm (CLAUDE.md bản 2, giai đoạn 3).

Quản trị (tạo/sửa nguồn, phòng ban, cấp quyền): chỉ Admin. Người thường: `GET /sources` chỉ trả nguồn mình được phép
(phòng ban mình + được cấp thêm). Phản hồi KHÔNG BAO GIỜ chứa giá trị bí mật; tên tham chiếu (`secret_ref`) chỉ Admin thấy.
"""

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from src.api.deps import Admin, CurrentUser, LoggedIn, client_ip
from src.models.sources import (
    CreateSourceBody,
    Department,
    DepartmentBody,
    SourceGrant,
    SourceView,
    UpdateSourceBody,
    UserContext,
)
from src.services import source_registry as registry

router = APIRouter(tags=["sources"])
NO_SOURCE = "Không tìm thấy nguồn dữ liệu này."


class GrantBody(BaseModel):
    """Cấp thêm quyền xem một nguồn cho đúng MỘT người hoặc MỘT phòng ban."""

    user_id: int | None = None
    department_id: int | None = None


def user_context(user: CurrentUser) -> UserContext:
    """Người dùng đang đăng nhập (từ phiên) kèm phòng ban, để lọc nguồn."""
    return UserContext(name=user.name, role=user.role, user_id=user.id, department_id=user.department_id)


def _views(sources: list, show_secret_ref: bool) -> list[SourceView]:
    names = {d.id: d.name for d in registry.list_departments()}
    return [registry.view(s, names, show_secret_ref) for s in sources]


@router.get("/sources", response_model=list[SourceView])
def list_sources(user: LoggedIn, request: Request) -> list[SourceView]:
    """Nguồn dữ liệu mà bạn được phép dùng (Admin: tất cả, kể cả nguồn đang tắt)."""
    visible = registry.get_visible_sources(user_context(user))
    registry.audit_access(user.name, "source.list", visible, ip_hint=client_ip(request))
    return _views(visible, show_secret_ref=user.role == "admin")


@router.post("/sources", status_code=status.HTTP_201_CREATED, response_model=SourceView)
def create_source(body: CreateSourceBody, admin: Admin) -> SourceView:
    """Admin đăng ký nguồn mới. Mức truy cập LLM vượt trần theo độ nhạy cảm → 422."""
    try:
        source = registry.create_source(body, admin.name)
    except registry.RegistryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _views([source], show_secret_ref=True)[0]


@router.patch("/sources/{source_id}", response_model=SourceView)
def update_source(source_id: int, body: UpdateSourceBody, admin: Admin) -> SourceView:
    """Admin sửa nguồn (độ nhạy cảm, mức LLM, bảng được phép, cột hạn chế, bật/tắt)."""
    try:
        source = registry.update_source(source_id, body, admin.name)
    except registry.RegistryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if source is None:
        raise HTTPException(status_code=404, detail=NO_SOURCE)
    return _views([source], show_secret_ref=True)[0]


@router.get("/sources/{source_id}/grants", response_model=list[SourceGrant])
def list_grants(source_id: int, admin: Admin) -> list[SourceGrant]:
    """Các quyền xem thêm của một nguồn."""
    return registry.list_grants(source_id)


@router.post("/sources/{source_id}/grants", status_code=status.HTTP_201_CREATED, response_model=SourceGrant)
def add_grant(source_id: int, body: GrantBody, admin: Admin) -> SourceGrant:
    """Cấp thêm quyền xem nguồn cho một người hoặc một phòng ban."""
    try:
        return registry.add_grant(source_id, admin.name, body.user_id, body.department_id)
    except registry.RegistryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/sources/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_grant(grant_id: int, admin: Admin) -> None:
    """Thu hồi một quyền xem thêm."""
    try:
        removed = registry.remove_grant(grant_id, admin.name)
    except registry.RegistryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Không tìm thấy quyền này.")


@router.get("/departments", response_model=list[Department])
def list_departments(admin: Admin) -> list[Department]:
    """Mọi phòng ban (Admin)."""
    return registry.list_departments()


@router.post("/departments", status_code=status.HTTP_201_CREATED, response_model=Department)
def create_department(body: DepartmentBody, admin: Admin) -> Department:
    """Admin tạo phòng ban."""
    try:
        return registry.create_department(body.name)
    except registry.RegistryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

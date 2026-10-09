"""Phụ thuộc dùng chung của API: người dùng đã đăng nhập, kiểm tra vai trò, lần chạy theo id.

Phân quyền kiểm ở BACKEND cho từng API (ẩn nút trên web không phải là phân quyền):
- chưa đăng nhập / phiên hết hạn / đã đăng xuất → 401;
- sai vai trò → 403 thông báo chung, ghi `audit_log` + log cảnh báo (không lộ chi tiết luật).
Thao tác ghi (POST/PATCH/...) phải kèm header `X-Requested-With`: trang lạ không gửi được header này nếu CORS
không cho phép, nên cookie phiên không bị lợi dụng (CSRF).
"""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from src.config import get_settings
from src.models.schemas import RunRecord
from src.services import auth
from src.services.store import get_store

logger = logging.getLogger(__name__)

SESSION_COOKIE = "p113_session"
CSRF_HEADER = "X-Requested-With"
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
FORBIDDEN = "Bạn không có quyền thực hiện thao tác này."


class CurrentUser(BaseModel):
    """Người đang thao tác (lấy từ phiên đăng nhập, không bao giờ từ header do trình duyệt tự khai)."""

    id: int
    name: str  # tên đăng nhập: ghi vào requester/reviewer của lần chạy
    display_name: str
    role: auth.Role


def client_ip(request: Request) -> str:
    """IP người gọi (chỉ để ghi nhật ký)."""
    return request.client.host if request.client else ""


def require_auth_config() -> None:
    """Thiếu cấu hình đăng nhập → 503 kèm TÊN biến còn thiếu (không kèm giá trị)."""
    missing = get_settings().missing_auth_settings
    if missing:
        raise HTTPException(status_code=503, detail=f"Máy chủ chưa cấu hình đăng nhập: thiếu {', '.join(missing)}.")


def check_csrf(request: Request) -> None:
    """Thao tác ghi phải có header `X-Requested-With` (web và test luôn gửi)."""
    if request.method not in SAFE_METHODS and not request.headers.get(CSRF_HEADER):
        raise HTTPException(status_code=403, detail="Yêu cầu bị chặn: thiếu header X-Requested-With.")


def current_user(request: Request) -> CurrentUser:
    """Người dùng của phiên trong cookie; không có/hết hạn/đã thu hồi → 401."""
    require_auth_config()
    token = request.cookies.get(SESSION_COOKIE, "")
    user = auth.user_for_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập.", headers={"WWW-Authenticate": "Cookie"})
    check_csrf(request)
    return CurrentUser(id=user.id, name=user.username, display_name=user.display_name, role=user.role)


def require_role(*roles: str) -> Callable[..., CurrentUser]:
    """Phụ thuộc: chỉ cho các vai trò `roles`; sai vai trò → 403 + ghi nhật ký."""

    def dependency(request: Request, user: Annotated[CurrentUser, Depends(current_user)]) -> CurrentUser:
        if user.role not in roles:
            path = request.url.path
            logger.warning("permission denied", extra={"user": user.name, "role": user.role, "path": path})
            target = f"{request.method} {path}"
            auth.audit("permission.denied", user.name, target, "denied", client_ip(request), {"role": user.role})
            raise HTTPException(status_code=403, detail=FORBIDDEN)
        return user

    return dependency


LoggedIn = Annotated[CurrentUser, Depends(current_user)]
Engineer = Annotated[CurrentUser, Depends(require_role("engineer"))]
Reviewer = Annotated[CurrentUser, Depends(require_role("reviewer"))]
Admin = Annotated[CurrentUser, Depends(require_role("admin"))]
# Xem dữ liệu (hồ sơ cột + dòng xem trước đã che PII): người làm và người duyệt pipeline, không phải Admin
DataViewer = Annotated[CurrentUser, Depends(require_role("engineer", "reviewer"))]


def run_or_404(run_id: str) -> RunRecord:
    """Lần chạy theo id, 404 (tiếng Việt) nếu không có."""
    record = get_store().get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lần chạy này.")
    return record

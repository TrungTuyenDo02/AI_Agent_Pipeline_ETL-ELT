"""Sổ lỗi: xem mục chờ duyệt; chỉ Reviewer duyệt (kèm cách sửa) hoặc bỏ. Chỉ mục đã duyệt mới được gợi ý cho Codegen."""

from fastapi import APIRouter, HTTPException, Request

from src.api.deps import Reviewer, client_ip
from src.api.requests import ErrorFixBody
from src.models.evidence import ErrorEntry
from src.services import auth
from src.services.error_memory import get_error_memory

router = APIRouter(prefix="/errors", tags=["errors"])


@router.get("", response_model=list[ErrorEntry])
def pending_errors() -> list[ErrorEntry]:
    """Các mục sổ lỗi chờ duyệt (gặp nhiều nhất trước)."""
    return get_error_memory().pending()


@router.post("/{entry_id}/approve")
def approve_error(entry_id: int, body: ErrorFixBody, user: Reviewer, request: Request) -> dict:
    """Duyệt một mục để Codegen dùng làm gợi ý lần sau."""
    if not get_error_memory().approve(entry_id, body.fix.strip()):
        raise HTTPException(status_code=404, detail="Không tìm thấy mục sổ lỗi này.")
    auth.audit("error_book.approve", user.name, target=str(entry_id), ip=client_ip(request))
    return {"id": entry_id, "approved": True}


@router.post("/{entry_id}/discard")
def discard_error(entry_id: int, user: Reviewer, request: Request) -> dict:
    """Bỏ một mục không hữu ích."""
    if not get_error_memory().discard(entry_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy mục sổ lỗi này.")
    auth.audit("error_book.discard", user.name, target=str(entry_id), ip=client_ip(request))
    return {"id": entry_id, "discarded": True}

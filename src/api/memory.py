"""Bộ nhớ agent: Reviewer xem các mục agent đề xuất (chờ duyệt) và duyệt hoặc bỏ. Chỉ mục đã duyệt mới vào prompt."""

from fastapi import APIRouter, HTTPException, Request

from src.api.deps import Reviewer, client_ip
from src.services import auth
from src.services.agent_memory import MemoryItem, get_agent_memory

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=list[MemoryItem])
def pending_memory(user: Reviewer) -> list[MemoryItem]:
    """Các mục bộ nhớ agent đề xuất, chờ duyệt (mới nhất trước)."""
    return get_agent_memory().pending_all()


@router.post("/{item_id}/approve")
def approve_memory(item_id: int, user: Reviewer, request: Request) -> dict:
    """Duyệt để agent dùng lại cho đúng tài khoản đã sinh ra mục này."""
    memory = get_agent_memory()
    item = memory.get(item_id)
    if not item or not memory.approve(item.account, item_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy mục bộ nhớ này.")
    auth.audit("memory.approve", user.name, target=str(item_id), ip=client_ip(request))
    return {"id": item_id, "approved": True}


@router.post("/{item_id}/discard")
def discard_memory(item_id: int, user: Reviewer, request: Request) -> dict:
    memory = get_agent_memory()
    item = memory.get(item_id)
    if not item or not memory.discard(item.account, item_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy mục bộ nhớ này.")
    auth.audit("memory.discard", user.name, target=str(item_id), ip=client_ip(request))
    return {"id": item_id, "discarded": True}

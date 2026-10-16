"""Từ điển nghiệp vụ (CLAUDE.md bản 2, giai đoạn 6): ai đăng nhập cũng đọc được phần của mình; chỉ Admin thêm/sửa. Agent chỉ đọc."""

from fastapi import APIRouter, HTTPException, Request, status

from src.api.deps import Admin, LoggedIn, client_ip
from src.api.sources import user_context
from src.models.glossary import GlossaryBody, GlossaryTerm, UpdateGlossaryBody
from src.services import auth, glossary

router = APIRouter(tags=["glossary"])
NO_TERM = "Không tìm thấy thuật ngữ này."


@router.get("/glossary", response_model=list[GlossaryTerm])
def list_glossary(user: LoggedIn) -> list[GlossaryTerm]:
    """Thuật ngữ bạn được dùng: dùng chung + của phòng ban mình (Admin: tất cả)."""
    return glossary.list_terms(user_context(user))


@router.post("/glossary", status_code=status.HTTP_201_CREATED, response_model=GlossaryTerm)
def create_glossary_term(body: GlossaryBody, admin: Admin, request: Request) -> GlossaryTerm:
    try:
        term = glossary.create_term(body, admin.name)
    except glossary.GlossaryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    auth.audit("glossary.create", admin.name, target=f"term:{term.id}", ip=client_ip(request))
    return term


@router.patch("/glossary/{term_id}", response_model=GlossaryTerm)
def update_glossary_term(term_id: int, body: UpdateGlossaryBody, admin: Admin, request: Request) -> GlossaryTerm:
    try:
        term = glossary.update_term(term_id, body, admin.name)
    except glossary.GlossaryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if term is None:
        raise HTTPException(status_code=404, detail=NO_TERM)
    auth.audit("glossary.update", admin.name, target=f"term:{term_id}", ip=client_ip(request))
    return term

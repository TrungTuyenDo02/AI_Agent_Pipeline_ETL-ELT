"""Từ điển nghiệp vụ (CLAUDE.md bản 2, giai đoạn 6): giúp Planner đoán đúng bảng/cột và giúp tầng 1 của cửa kiểm tra nhận ra yêu cầu hợp lệ.

- Lưu cùng cơ sở dữ liệu ứng dụng (bảng `glossary_terms`, migration 0007, seed từ `config/glossary_seed.yaml`). Không có DATABASE_URL (CLI demo,
  eval offline): dùng chính file seed, chỉ đọc.
- Chỉ Admin thêm/sửa (kiểm ở API). Agent CHỈ ĐỌC, không bao giờ tự ghi.
- Thuật ngữ vào prompt chỉ qua `LLMContext.glossary_for()` (cửa `build_llm_context`), tối đa `GLOSSARY_MAX_TERMS` mục chọn bằng khớp từ khóa.
"""

import logging
import re
from datetime import UTC, datetime
from functools import lru_cache

import yaml
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.agents.tools.input_checks import normalize
from src.config import GLOSSARY_SEED_FILE, get_settings
from src.models.glossary import GlossaryBody, GlossaryTerm, UpdateGlossaryBody
from src.models.sources import UserContext
from src.services import source_registry
from src.services.auth import ID, Base, get_engine

logger = logging.getLogger(__name__)
LIST = JSON().with_variant(JSONB, "postgresql")
NEEDS_DATABASE = "Cần cấu hình DATABASE_URL (cơ sở dữ liệu ứng dụng) để sửa từ điển nghiệp vụ."
DUPLICATE = "Đã có thuật ngữ này trong từ điển."
MAX_DEFINITION_CHARS = 200  # định nghĩa đưa vào prompt cắt gọn để không phình


class GlossaryError(ValueError):
    """Thao tác từ điển không hợp lệ. Thông báo tiếng Việt."""


class GlossaryRow(Base):
    __tablename__ = "glossary_terms"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    synonyms: Mapped[list] = mapped_column(LIST, nullable=False, default=list)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    maps_to: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _has_db() -> bool:
    return bool(get_settings().database_url)


def _term(row: GlossaryRow) -> GlossaryTerm:
    return GlossaryTerm(
        id=row.id, term=row.term, synonyms=list(row.synonyms or []), definition=row.definition,
        maps_to=row.maps_to or "", department_id=row.department_id,
    )  # fmt: skip


@lru_cache(maxsize=1)
def seed_terms() -> tuple[GlossaryTerm, ...]:
    """Thuật ngữ mẫu từ `config/glossary_seed.yaml` (dùng cho migration và khi không có cơ sở dữ liệu)."""
    data = yaml.safe_load(GLOSSARY_SEED_FILE.read_text(encoding="utf-8")) or {}
    return tuple(
        GlossaryTerm(
            id=index,
            term=item["term"],
            synonyms=list(item.get("synonyms") or []),
            definition=item["definition"],
            maps_to=item.get("maps_to", ""),
        )  # fmt: skip
        for index, item in enumerate(data.get("terms", []), start=1)
    )


def list_terms(user: UserContext | None = None) -> list[GlossaryTerm]:
    """Thuật ngữ `user` được dùng: dùng chung + của phòng ban mình; Admin (hoặc `user=None`) thấy tất cả. Sắp theo tên."""
    if not _has_db():
        return sorted(seed_terms(), key=lambda t: normalize(t.term))
    with Session(get_engine()) as db:
        query = select(GlossaryRow).order_by(GlossaryRow.term)
        if user is not None and user.role != "admin":
            query = query.where(
                or_(GlossaryRow.department_id.is_(None), GlossaryRow.department_id == user.department_id)
            )
        return [_term(r) for r in db.scalars(query)]


def keyword_terms(username: str) -> list[str]:
    """Thuật ngữ + từ đồng nghĩa người này được dùng, làm từ khóa nhận diện cho tầng 1 của cửa kiểm tra. Lỗi cơ sở dữ liệu → rỗng."""
    try:
        terms = list_terms(source_registry.user_context(username) if username else None)
    except Exception:  # noqa: BLE001 — từ điển chỉ giúp nhận diện; hỏng thì cửa vẫn chạy bằng danh mục
        logger.warning("glossary unavailable for gate", exc_info=True)
        return []
    return [phrase for t in terms for phrase in (t.term, *t.synonyms)]


SPEC_MARKERS = (
    " bang dich ",
    " cac cot ",
)  # phần mô tả bảng đích/cột đầu ra: từ vựng chung chung, không nói lên ý nghiệp vụ
MIN_CORE_CHARS = 15


def _core(normalized: str) -> str:
    """Phần nêu ý nghiệp vụ của yêu cầu: cắt đoạn mô tả bảng đích/cột đầu ra (nhắc "số đơn", "ngày đặt đơn" ở mọi yêu cầu) nếu phần trước đủ dài."""
    padded = f" {normalized} "
    cuts = [i for i in (padded.find(m) for m in SPEC_MARKERS) if i >= MIN_CORE_CHARS]
    return padded[: min(cuts)].strip() if cuts else normalized


def relevant_terms(request_text: str, terms: list[GlossaryTerm], limit: int) -> list[GlossaryTerm]:
    """Thuật ngữ xuất hiện trong yêu cầu (khớp nguyên cụm, bỏ dấu, không phân biệt hoa/thường), nhiều chữ nhất trước, tối đa `limit`."""
    padded = f" {_core(normalize(request_text))} "
    scored: list[tuple[int, int, GlossaryTerm]] = []
    for order, term in enumerate(terms):
        hits = [p for p in (normalize(x) for x in (term.term, *term.synonyms)) if p and f" {p} " in padded]
        if hits:
            scored.append((-max(len(h) for h in hits), order, term))
    return [t for _, _, t in sorted(scored)[: max(limit, 0)]]


def create_term(body: GlossaryBody, by: str) -> GlossaryTerm:
    if not _has_db():
        raise GlossaryError(NEEDS_DATABASE)
    with Session(get_engine()) as db:
        _check_department(db, body.department_id)
        row = GlossaryRow(
            term=body.term, synonyms=body.synonyms, definition=body.definition, maps_to=body.maps_to,
            department_id=body.department_id, updated_by=by[:64], updated_at=datetime.now(UTC),
        )  # fmt: skip
        db.add(row)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise GlossaryError(DUPLICATE) from exc
        db.refresh(row)
        return _term(row)


def update_term(term_id: int, body: UpdateGlossaryBody, by: str) -> GlossaryTerm | None:
    if not _has_db():
        raise GlossaryError(NEEDS_DATABASE)
    changes = body.model_dump(exclude_unset=True)
    with Session(get_engine()) as db:
        row = db.get(GlossaryRow, term_id)
        if row is None:
            return None
        if "department_id" in changes:
            changes["department_id"] = changes["department_id"] or None  # 0 = dùng chung
            _check_department(db, changes["department_id"])
        for key, value in changes.items():
            if value is not None or key == "department_id":
                setattr(row, key, value)
        row.updated_by, row.updated_at = by[:64], datetime.now(UTC)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise GlossaryError(DUPLICATE) from exc
        db.refresh(row)
        return _term(row)


def delete_term(term_id: int) -> bool:
    if not _has_db():
        raise GlossaryError(NEEDS_DATABASE)
    with Session(get_engine()) as db:
        row = db.get(GlossaryRow, term_id)
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True


def _check_department(db: Session, department_id: int | None) -> None:
    if department_id is not None and db.get(source_registry.Department_, department_id) is None:
        raise GlossaryError("Phòng ban không tồn tại.")


def _named_tables(maps_to: str) -> set[str]:
    """Bảng mà `maps_to` nhắc tới: `bảng.cột`, hoặc một mục trần trong danh sách phân tách bằng `,`/`;` (vd "shopee_orders, tiki_orders")."""
    named = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\.[A-Za-z_]", maps_to))
    named |= {p for p in (x.strip() for x in re.split(r"[;,]", maps_to)) if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p)}
    return named


def _visible_tables_only(maps_to: str, visible: set[str]) -> str:
    """Bỏ ánh xạ nếu nó nhắc một bảng người dùng không được thấy (không lộ bảng ngoài quyền); định nghĩa chữ vẫn giữ."""
    return maps_to if _named_tables(maps_to) <= visible else ""


def entries_for_prompt(terms: list[GlossaryTerm], visible_tables: set[str]) -> list[dict]:
    """Dạng gọn đưa vào prompt Planner: thuật ngữ, định nghĩa (cắt gọn), ánh xạ (chỉ bảng được thấy)."""
    out = []
    for t in terms:
        entry = {"term": t.term, "definition": t.definition[:MAX_DEFINITION_CHARS]}
        if maps_to := _visible_tables_only(t.maps_to, visible_tables):
            entry["maps_to"] = maps_to
        out.append(entry)
    return out

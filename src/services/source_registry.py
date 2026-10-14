"""Sổ đăng ký nguồn dữ liệu + phân quyền theo phòng ban (CLAUDE.md bản 2, giai đoạn 3).

CỬA DUY NHẤT vào danh sách nguồn: mọi nơi cần biết "người này được thấy nguồn/bảng nào" (catalog, nạp dữ liệu, Planner, API, cửa
kiểm tra đầu vào) phải gọi `get_visible_sources(user)` hoặc `visible_catalog(user)`. `tests/test_source_registry.py` quét mã nguồn để
bảo đảm không ai đọc thư mục nguồn bằng đường vòng.

- Mặc định người dùng chỉ thấy nguồn của phòng ban mình (và nguồn được cấp thêm qua `SourceGrant`); Admin thấy tất cả.
- Nguồn tắt (`enabled=false`) không ai dùng được để chạy; Admin vẫn thấy để quản lý.
- Lưu cùng cơ sở dữ liệu với tài khoản (bảng do Alembic quản lý, migration 0005). Không có DATABASE_URL (CLI demo không cần
  PostgreSQL): dùng nguồn mặc định "P113 Retail" trong bộ nhớ, chỉ đọc.
- `secret_ref` chỉ là tên tham chiếu; giá trị thật giải ở lớp kết nối (`secrets.resolve`).
"""

import logging
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, delete, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.agents.tools.duckdb_tools import discover_sources
from src.config import get_settings
from src.models.sources import (
    ACCESS_TEXT,
    ALL_TABLES,
    CreateSourceBody,
    DataSource,
    Department,
    SourceGrant,
    SourceView,
    UpdateSourceBody,
    UserContext,
    access_problem,
    cap_access,
)
from src.services import auth, secrets
from src.services.auth import ID, Base, get_engine
from src.services.company import read_manifest

logger = logging.getLogger(__name__)
Department_ = auth.Department  # lớp ORM, tách khỏi mô hình Pydantic `Department`
LIST = JSON().with_variant(JSONB, "postgresql")
DEFAULT_DEPARTMENT_NAME = "Mặc định"
DEFAULT_SOURCE_NAME = "P113 Retail"
NEEDS_DATABASE = "Cần cấu hình DATABASE_URL (cơ sở dữ liệu ứng dụng) để quản lý nguồn dữ liệu."


class RegistryError(ValueError):
    """Cấu hình nguồn/phòng ban không hợp lệ. Thông báo tiếng Việt, không chứa bí mật."""


class SourceRow(Base):
    """Nguồn dữ liệu đã đăng ký (bảng `data_sources`)."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    secret_ref: Mapped[str] = mapped_column(String(64), default="")
    allowed_tables: Mapped[list] = mapped_column(LIST)
    sensitivity: Mapped[str] = mapped_column(String(8), default="medium")
    llm_access: Mapped[str] = mapped_column(String(16), default="profile")
    restricted_columns: Mapped[list] = mapped_column(LIST)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GrantRow(Base):
    """Cấp thêm quyền xem một nguồn cho một người hoặc một phòng ban (bảng `source_grants`)."""

    __tablename__ = "source_grants"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _now() -> datetime:
    return datetime.now(UTC)


def _model(row: SourceRow) -> DataSource:
    return DataSource(
        id=row.id,
        name=row.name,
        department_id=row.department_id,
        kind=row.kind,  # type: ignore[arg-type]
        secret_ref=row.secret_ref or "",
        allowed_tables=list(row.allowed_tables or []),
        sensitivity=row.sensitivity,  # type: ignore[arg-type]
        llm_access=row.llm_access,  # type: ignore[arg-type]
        restricted_columns=list(row.restricted_columns or []),
        enabled=bool(row.enabled),
    )


def _memory_default() -> DataSource:
    """Nguồn mặc định khi không có cơ sở dữ liệu (CLI demo): thư mục nguồn của cấu hình, mọi bảng, mức profile."""
    return DataSource(
        id=1,
        name=DEFAULT_SOURCE_NAME,
        department_id=1,
        kind="file",
        allowed_tables=[ALL_TABLES],
        sensitivity="medium",
        llm_access=cap_access("medium", get_settings().llm_access_default),
    )


def _has_db() -> bool:
    return bool(get_settings().database_url)


# ---------- Người dùng ----------


def user_context(username: str, role: str | None = None) -> UserContext:
    """Người dùng kèm phòng ban.

    Có tài khoản trong cơ sở dữ liệu → lấy vai trò, phòng ban thật. Không có (tên do CLI tin cậy trên máy chủ, hoặc không có
    cơ sở dữ liệu) → phòng mặc định với vai trò `role` (mặc định `engineer`); API không bao giờ đi nhánh này vì luôn có phiên
    đăng nhập thật.
    """
    if _has_db():
        user = auth.find_user(username)
        if user is not None:
            return UserContext(name=user.username, role=user.role, user_id=user.id, department_id=user.department_id)
    return UserContext(
        name=username, role=role or "engineer", department_id=1 if not _has_db() else _default_department()
    )


def _default_department() -> int | None:
    with Session(get_engine()) as db:
        return db.scalar(select(Department_.id).order_by(Department_.id).limit(1))


# ---------- Phòng ban ----------


def list_departments() -> list[Department]:
    """Mọi phòng ban, theo tên."""
    if not _has_db():
        return [Department(id=1, name=DEFAULT_DEPARTMENT_NAME)]
    with Session(get_engine()) as db:
        return [Department(id=d.id, name=d.name) for d in db.scalars(select(Department_).order_by(Department_.name))]


def create_department(name: str) -> Department:
    """Tạo phòng ban (tên không trùng)."""
    if not _has_db():
        raise RegistryError(NEEDS_DATABASE)
    clean = name.strip()
    with Session(get_engine()) as db:
        row = Department_(name=clean, created_at=_now())
        db.add(row)
        try:
            db.commit()
        except IntegrityError as exc:
            raise RegistryError("Tên phòng ban đã tồn tại.") from exc
        return Department(id=row.id, name=row.name)


# ---------- Nguồn ----------


def list_sources(include_disabled: bool = True) -> list[DataSource]:
    """Mọi nguồn (dành cho Admin quản lý)."""
    if not _has_db():
        return [_memory_default()]
    with Session(get_engine()) as db:
        query = select(SourceRow).order_by(SourceRow.name)
        if not include_disabled:
            query = query.where(SourceRow.enabled.is_(True))
        return [_model(r) for r in db.scalars(query)]


def get_source(source_id: int) -> DataSource | None:
    """Một nguồn theo id (None nếu không có)."""
    return next((s for s in list_sources() if s.id == source_id), None)


def _check_fields(merged: dict) -> None:
    """Luật liên trường, kiểm cả ở API lẫn ở đây (phòng thủ lần hai)."""
    if not merged["allowed_tables"]:
        raise RegistryError(f"Hãy liệt kê bảng được phép (hoặc '{ALL_TABLES}' cho mọi bảng).")
    if merged["kind"] in ("duckdb", "postgres") and not merged["secret_ref"]:
        raise RegistryError("Nguồn DuckDB/PostgreSQL cần secret_ref (tên tham chiếu tới chuỗi kết nối).")
    if problem := access_problem(merged["sensitivity"], merged["llm_access"]):
        raise RegistryError(problem)


def create_source(body: CreateSourceBody, actor: str) -> DataSource:
    """Đăng ký nguồn mới. Mức truy cập LLM để trống → mặc định LLM_ACCESS_DEFAULT hạ về trần theo độ nhạy cảm; đặt quá trần → từ chối."""
    if not _has_db():
        raise RegistryError(NEEDS_DATABASE)
    sensitivity = body.sensitivity or "medium"
    merged = {
        "kind": body.kind,
        "secret_ref": body.secret_ref or "",
        "allowed_tables": body.allowed_tables or [],
        "sensitivity": sensitivity,
        "llm_access": body.llm_access or cap_access(sensitivity, get_settings().llm_access_default),
    }
    _check_fields(merged)
    now = _now()
    with Session(get_engine()) as db:
        if db.get(Department_, body.department_id) is None:
            raise RegistryError("Không có phòng ban này.")
        row = SourceRow(
            name=body.name.strip(),
            department_id=body.department_id,
            restricted_columns=body.restricted_columns or [],
            enabled=True if body.enabled is None else body.enabled,
            created_at=now,
            updated_at=now,
            **merged,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError as exc:
            raise RegistryError("Tên nguồn đã tồn tại.") from exc
        source = _model(row)
    auth.audit(
        "source.create", actor, target=f"source:{source.id}", detail={"kind": source.kind, "sensitivity": sensitivity}
    )
    return source


def update_source(source_id: int, body: UpdateSourceBody, actor: str) -> DataSource | None:
    """Sửa nguồn. Nâng độ nhạy cảm mà không nói rõ mức LLM → mức LLM tự hạ về trần (ghi nhật ký); nói rõ mà quá trần → từ chối."""
    if not _has_db():
        raise RegistryError(NEEDS_DATABASE)
    with Session(get_engine()) as db:
        row = db.get(SourceRow, source_id)
        if row is None:
            return None
        merged = {
            "kind": body.kind or row.kind,
            "secret_ref": row.secret_ref if body.secret_ref is None else body.secret_ref,
            "allowed_tables": row.allowed_tables if body.allowed_tables is None else body.allowed_tables,
            "sensitivity": body.sensitivity or row.sensitivity,
            "llm_access": body.llm_access or row.llm_access,
        }
        downgraded = (
            body.llm_access is None and cap_access(merged["sensitivity"], merged["llm_access"]) != merged["llm_access"]
        )
        if downgraded:
            merged["llm_access"] = cap_access(merged["sensitivity"], merged["llm_access"])
        _check_fields(merged)
        if body.department_id is not None:
            if db.get(Department_, body.department_id) is None:
                raise RegistryError("Không có phòng ban này.")
            row.department_id = body.department_id
        for key, value in merged.items():
            setattr(row, key, value)
        if body.name:
            row.name = body.name.strip()
        if body.restricted_columns is not None:
            row.restricted_columns = body.restricted_columns
        if body.enabled is not None:
            row.enabled = body.enabled
        row.updated_at = _now()
        try:
            db.commit()
        except IntegrityError as exc:
            raise RegistryError("Tên nguồn đã tồn tại.") from exc
        source = _model(row)
    detail = {k: v for k, v in body.model_dump(exclude_none=True).items() if k != "secret_ref"}
    auth.audit(
        "source.update", actor, target=f"source:{source_id}", detail={**detail, "llm_access_downgraded": downgraded}
    )
    return source


# ---------- Quyền xem thêm ----------


def add_grant(source_id: int, actor: str, user_id: int | None = None, department_id: int | None = None) -> SourceGrant:
    """Cấp thêm quyền xem nguồn cho đúng MỘT người hoặc MỘT phòng ban."""
    if not _has_db():
        raise RegistryError(NEEDS_DATABASE)
    if (user_id is None) == (department_id is None):
        raise RegistryError("Hãy chọn đúng một người hoặc một phòng ban để cấp quyền.")
    with Session(get_engine()) as db:
        if db.get(SourceRow, source_id) is None:
            raise RegistryError("Không có nguồn này.")
        row = GrantRow(
            source_id=source_id, user_id=user_id, department_id=department_id, created_by=actor[:64], created_at=_now()
        )
        db.add(row)
        db.commit()
        grant = SourceGrant(id=row.id, source_id=source_id, user_id=user_id, department_id=department_id)
    auth.audit(
        "source.grant", actor, target=f"source:{source_id}", detail={"user_id": user_id, "department_id": department_id}
    )
    return grant


def list_grants(source_id: int | None = None) -> list[SourceGrant]:
    """Các quyền xem thêm (của một nguồn hoặc tất cả)."""
    if not _has_db():
        return []
    with Session(get_engine()) as db:
        query = select(GrantRow).order_by(GrantRow.id)
        if source_id is not None:
            query = query.where(GrantRow.source_id == source_id)
        return [
            SourceGrant(id=g.id, source_id=g.source_id, user_id=g.user_id, department_id=g.department_id)
            for g in db.scalars(query)
        ]


def remove_grant(grant_id: int, actor: str) -> bool:
    """Thu hồi một quyền xem thêm."""
    if not _has_db():
        raise RegistryError(NEEDS_DATABASE)
    with Session(get_engine()) as db:
        removed = db.execute(delete(GrantRow).where(GrantRow.id == grant_id)).rowcount
        db.commit()
    if removed:
        auth.audit("source.revoke", actor, target=f"grant:{grant_id}")
    return bool(removed)


# ---------- Quyền xem: CỬA DUY NHẤT ----------


def get_visible_sources(user: UserContext) -> list[DataSource]:
    """Nguồn mà `user` được thấy. Admin: tất cả (kể cả nguồn tắt, để quản lý). Người khác: nguồn đang bật của phòng ban mình
    hoặc được cấp thêm (theo người hoặc theo phòng ban)."""
    if not _has_db():
        return [_memory_default()]
    with Session(get_engine()) as db:
        if user.role == "admin":
            return [_model(r) for r in db.scalars(select(SourceRow).order_by(SourceRow.name))]
        granted = select(GrantRow.source_id).where(
            or_(
                GrantRow.user_id == user.user_id if user.user_id is not None else False,
                GrantRow.department_id == user.department_id if user.department_id is not None else False,
            )
        )
        own = SourceRow.department_id == user.department_id if user.department_id is not None else False
        query = (
            select(SourceRow)
            .where(SourceRow.enabled.is_(True), or_(own, SourceRow.id.in_(granted)))
            .order_by(SourceRow.name)
        )
        return [_model(r) for r in db.scalars(query)]


def source_location(source: DataSource) -> Path:
    """Thư mục dữ liệu của nguồn `file`: thư mục nguồn của cấu hình, hoặc đường dẫn lấy từ `secret_ref` nếu có."""
    return Path(secrets.resolve(source.secret_ref)) if source.secret_ref else get_settings().sources_dir


def _signature(directory: Path) -> tuple:
    files = sorted(directory.glob("*")) if directory.exists() else []
    return tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file())


@lru_cache(maxsize=8)
def _discover_cached(directory: str, signature: tuple) -> tuple[dict, ...]:
    """Cấu trúc các file trong thư mục (không có dòng mẫu), nhớ tới khi file nguồn đổi."""
    labels = read_manifest(Path(directory))
    items = []
    for info in discover_sources(Path(directory)):
        item = info.model_dump()
        item["sample"] = []  # dòng mẫu không đi vào danh mục dùng chung (state, checkpoint, prompt)
        item["label"] = labels.get(info.name, {}).get("label", "")
        items.append(item)
    return tuple(items)


def _source_catalog(source: DataSource) -> list[dict]:
    """Bảng của một nguồn (đã lọc theo `allowed_tables`). Hiện hỗ trợ kind `file`; DuckDB/PostgreSQL qua connector (giai đoạn 4)."""
    if source.kind != "file":
        try:
            from src.services.connectors import catalog_of  # noqa: PLC0415 — giai đoạn 4 thêm connector

            return catalog_of(source)
        except ImportError:
            return []
    try:
        directory = source_location(source)
    except secrets.SecretError as exc:  # thiếu bí mật của nguồn: nguồn này tạm không dùng được, các nguồn khác vẫn chạy
        logger.warning("source unavailable", extra={"source": source.name, "reason": str(exc)[:200]})
        return []
    items = _discover_cached(str(directory.resolve()), _signature(directory))
    return [
        {
            **item,
            "source_id": source.id,
            "source_name": source.name,
            "source_kind": source.kind,
            "sensitivity": source.sensitivity,
            "llm_access": source.effective_llm_access,
            "restricted_columns": list(source.restricted_columns),
        }
        for item in items
        if source.allows_table(item["name"])
    ]


def visible_directories(user: UserContext) -> list[tuple[Path, set[str]]]:
    """(thư mục dữ liệu, tên bảng được phép) của các nguồn `file` mà `user` được thấy, cho các màn xem cấu trúc/hồ sơ."""
    out: list[tuple[Path, set[str]]] = []
    for source in get_visible_sources(user):
        if source.enabled and source.kind == "file":
            try:
                directory = source_location(source)
            except (
                secrets.SecretError
            ) as exc:  # nguồn cấu hình thiếu bí mật: bỏ qua nguồn này, không làm hỏng cả danh sách
                logger.warning("source skipped", extra={"source": source.name, "reason": str(exc)[:200]})
                continue
            names = {item["name"] for item in _source_catalog(source)}
            out.append((directory, names))
    return out


def visible_catalog(user: UserContext, source_ids: list[int] | None = None) -> list[dict]:
    """Danh mục bảng mà `user` được dùng (mọi nguồn đang bật mình thấy; `source_ids` để thu hẹp). Không có dòng dữ liệu."""
    seen: dict[str, dict] = {}
    for source in get_visible_sources(user):
        if not source.enabled or (source_ids is not None and source.id not in source_ids):
            continue
        for item in _source_catalog(source):
            seen.setdefault(item["name"], item)  # trùng tên bảng giữa hai nguồn: giữ nguồn đứng trước
    return list(seen.values())


def catalog_for(username_or_context: str | UserContext) -> list[dict]:
    """Tiện cho graph/CLI: danh mục của một người theo tên (hoặc UserContext đã có)."""
    user = username_or_context if isinstance(username_or_context, UserContext) else user_context(username_or_context)
    return visible_catalog(user)


def audit_access(
    user: UserContext | str,
    action: str,
    sources: list[DataSource | int],
    run_id: str = "",
    result: str = "ok",
    **detail: object,
) -> None:
    """Ghi AuditLog một lần truy cập nguồn: ai, hành động, nguồn nào, lần chạy nào, kết quả (không chứa dữ liệu nhạy cảm)."""
    name = user if isinstance(user, str) else user.name
    ids = [s.id if isinstance(s, DataSource) else s for s in sources]
    auth.audit(
        action,
        name,
        target=",".join(f"source:{i}" for i in ids)[:200],
        outcome=result,
        detail={"run_id": run_id, **detail},
    )


def view(source: DataSource, departments: dict[int, str], show_secret_ref: bool) -> SourceView:
    """Nguồn trả cho web: có tên phòng ban + mô tả mức truy cập; tên tham chiếu bí mật chỉ Admin thấy."""
    data = source.model_dump()
    data["secret_ref"] = source.secret_ref if show_secret_ref else ""
    effective = source.effective_llm_access
    return SourceView(
        **data,
        department_name=departments.get(source.department_id, ""),
        access_text=ACCESS_TEXT[effective],
        llm_access_effective=effective,
    )

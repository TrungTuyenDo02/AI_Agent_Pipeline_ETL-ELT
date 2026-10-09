"""Theo dõi cấu trúc bảng nguồn (CLAUDE.md mục 8): ảnh chụp cấu trúc, so sánh BẰNG CODE (không LLM), đề xuất sửa.

- Ảnh chụp mỗi nguồn: cột → kiểu, và giá trị của cột phân loại (ít giá trị khác nhau; đã che PII).
- Bản chuẩn (baseline) = ảnh chụp của lần chạy gần nhất được Reviewer DUYỆT. Chỉ ghi thêm, không sửa/xóa: bản chuẩn
  mới là một dòng mới (bảng `schema_snapshots`, PostgreSQL).
- Cách xử lý (người dùng chọn 2026-10-08): thêm cột / đổi kiểu / giá trị mới → cảnh báo KÈM đề xuất bản sửa cho
  Reviewer; xóa cột hoặc nghi đổi tên → chặn, Engineer xác nhận (KHÔNG tự đoán là cùng một cột).
- Đề xuất chỉ là gợi ý hiện trên màn duyệt; agent không tự sửa, không tự merge.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.config import get_settings
from src.services.auth import ID, Base, get_engine

logger = logging.getLogger(__name__)
DOC = JSON().with_variant(JSONB, "postgresql")
UNKNOWN_LABEL = "khong_ro"
MAX_RENAME_CANDIDATES = 10


class SchemaSnapshot(Base):
    """Bản chuẩn cấu trúc của một nguồn (chỉ ghi thêm; bản mới nhất là bản đang dùng)."""

    __tablename__ = "schema_snapshots"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True)
    origin: Mapped[str] = mapped_column(String(400), default="")  # đường dẫn file nguồn
    columns: Mapped[dict] = mapped_column(DOC)
    categories: Mapped[dict] = mapped_column(DOC)
    run_id: Mapped[str] = mapped_column(String(40), default="")
    approved_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Proposal(BaseModel):
    """Một đề xuất sửa (gợi ý do code dựng, Reviewer quyết)."""

    kind: str  # added | type_changed | new_values | removed | rename
    column: str
    message: str
    snippet: str = ""
    file: str = ""


class SourceChange(BaseModel):
    """Khác biệt của một nguồn so với bản chuẩn."""

    source: str
    has_baseline: bool = True
    added: dict[str, str] = Field(default_factory=dict)
    removed: dict[str, str] = Field(default_factory=dict)
    type_changed: dict[str, list[str]] = Field(default_factory=dict)  # cột → [kiểu cũ, kiểu mới]
    rename_candidates: list[list[str]] = Field(default_factory=list)  # [cột cũ, cột mới] cùng kiểu — CHỈ là nghi vấn
    new_values: dict[str, list[str]] = Field(default_factory=dict)  # cột phân loại → giá trị chưa có trong bản chuẩn
    proposals: list[Proposal] = Field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.type_changed or self.new_values)


class SchemaReport(BaseModel):
    """Kết quả so sánh mọi nguồn của một lần chạy (hoặc của thư mục nguồn lúc nhận)."""

    checked: bool = True
    note: str = ""
    changes: list[SourceChange] = Field(default_factory=list)
    blocking: bool = False  # có cột bị xóa / nghi đổi tên → phải có người xác nhận

    def summary(self) -> str:
        """Báo cáo ngắn, ví dụ: `shopee_orders: thêm coupon_code; xóa old_price`."""
        parts = []
        for change in self.changes:
            items = [f"thêm {c}" for c in change.added] + [f"xóa {c}" for c in change.removed]
            items += [f"đổi kiểu {c} ({a} → {b})" for c, (a, b) in change.type_changed.items()]
            items += [f"giá trị mới ở {c}: {', '.join(v[:3])}" for c, v in change.new_values.items()]
            if items:
                parts.append(f"{change.source}: {'; '.join(items)}")
        return " | ".join(parts) or ("Không đổi so với bản đã duyệt." if self.checked else self.note)


def source_origin(path: str) -> str:
    """Nơi nguồn nằm (đường dẫn file): bản chuẩn gắn với tên + nơi, hai thư mục dữ liệu khác nhau không lẫn nhau."""
    return Path(path).resolve().as_posix() if path else ""


def snapshot_from_profile(profile: dict, catalog: list[dict] | None = None) -> dict[str, dict]:
    """Ảnh chụp cấu trúc từ hồ sơ dữ liệu (P): cột → kiểu, cột phân loại → danh sách giá trị, nơi nguồn nằm."""
    paths = {item["name"]: item.get("path", "") for item in catalog or []}
    return {
        table: {
            "origin": source_origin(paths.get(table, "")),
            "columns": {c: str(info.get("type", "")) for c, info in data.get("columns", {}).items()},
            "categories": {
                c: info["categories"] for c, info in data.get("columns", {}).items() if info.get("categories")
            },
        }
        for table, data in profile.items()
    }


def _proposals(source: str, change: SourceChange) -> list[Proposal]:
    stg = f"models/staging/stg_{source}.sql"
    out = [
        Proposal(
            kind="added",
            column=c,
            file=stg,
            message=f'Cột mới "{c}" ({t}). Cần dùng thì thêm vào SELECT của staging; không cần thì ghi rõ là bỏ qua.',
            snippet=f'"{c}"',
        )
        for c, t in change.added.items()
    ]
    out += [
        Proposal(
            kind="type_changed",
            column=c,
            file=stg,
            message=f'Cột "{c}" đổi kiểu {old} → {new}. Đề xuất ép về kiểu cũ để model phía sau không đổi.',
            snippet=f'try_cast("{c}" AS {old}) AS "{c}"',
        )
        for c, (old, new) in change.type_changed.items()
    ]
    for c, values in change.new_values.items():
        listed = ", ".join(f"'{v}'" for v in values)
        out.append(
            Proposal(
                kind="new_values",
                column=c,
                file=stg,
                message=(
                    f'Cột phân loại "{c}" có giá trị mới: {listed}. Không tự loại dòng: thêm vào ánh xạ nếu người dùng '
                    f"xác nhận nghĩa của nó, còn lại đưa vào nhóm '{UNKNOWN_LABEL}'."
                ),
                snippet=f'CASE WHEN "{c}" IN ({listed}) THEN \'{UNKNOWN_LABEL}\' ELSE "{c}" END',
            )
        )
    renamed_old = {old for old, _ in change.rename_candidates}
    out += [
        Proposal(kind="rename", column=old, message=f'Có thể "{old}" đã đổi tên thành "{new}". Cần người xác nhận.')
        for old, new in change.rename_candidates
    ]
    out += [
        Proposal(kind="removed", column=c, message=f'Cột "{c}" ({t}) đã bị xóa khỏi nguồn. Pipeline dừng chờ xác nhận.')
        for c, t in change.removed.items()
        if c not in renamed_old
    ]
    return out


def diff_source(source: str, old: dict | None, new: dict) -> SourceChange:
    """So sánh một nguồn với bản chuẩn (code thuần). Không có bản chuẩn → lần đầu, không cảnh báo."""
    if old is None:
        return SourceChange(source=source, has_baseline=False)
    old_cols, new_cols = old.get("columns", {}), new.get("columns", {})
    change = SourceChange(
        source=source,
        added={c: t for c, t in new_cols.items() if c not in old_cols},
        removed={c: t for c, t in old_cols.items() if c not in new_cols},
        type_changed={c: [old_cols[c], t] for c, t in new_cols.items() if c in old_cols and old_cols[c] != t},
    )
    change.rename_candidates = [
        [r, a] for r, rt in change.removed.items() for a, at in change.added.items() if rt == at
    ][:MAX_RENAME_CANDIDATES]
    old_cats, new_cats = old.get("categories", {}), new.get("categories", {})
    for column, values in new_cats.items():
        if column in old_cats:
            fresh = [v for v in values if v not in set(old_cats[column])]
            if fresh:
                change.new_values[column] = fresh
    change.proposals = _proposals(source, change)
    return change


def build_report(baselines: dict[str, dict], current: dict[str, dict]) -> SchemaReport:
    """Báo cáo cho các nguồn của `current`; chặn khi có cột bị xóa (kể cả nghi đổi tên)."""
    changes = [diff_source(name, baselines.get(name), snap) for name, snap in sorted(current.items())]
    return SchemaReport(changes=changes, blocking=any(c.removed for c in changes))


# ---------- Lưu trữ bản chuẩn ----------


def latest_baselines(current: dict[str, dict]) -> dict[str, dict]:
    """Bản chuẩn mới nhất của từng nguồn cùng tên + cùng nơi (chưa có bản chuẩn thì không có trong kết quả)."""
    out: dict[str, dict] = {}
    with Session(get_engine()) as db:
        rows = db.scalars(
            select(SchemaSnapshot)
            .where(SchemaSnapshot.source_name.in_(sorted(current)))
            .order_by(SchemaSnapshot.created_at.desc(), SchemaSnapshot.id.desc())
        )
        for row in rows:
            if row.origin == current[row.source_name].get("origin", ""):
                out.setdefault(row.source_name, {"columns": row.columns, "categories": row.categories})
    return out


def save_baselines(snapshots: dict[str, dict], run_id: str, approved_by: str) -> int:
    """Reviewer duyệt lần chạy → ảnh chụp của nó thành bản chuẩn (dòng mới, không ghi đè)."""
    now = datetime.now(UTC)
    with Session(get_engine()) as db, db.begin():
        for name, snap in snapshots.items():
            db.add(
                SchemaSnapshot(
                    source_name=name,
                    origin=snap.get("origin", ""),
                    columns=snap.get("columns", {}),
                    categories=snap.get("categories", {}),
                    run_id=run_id,
                    approved_by=approved_by,
                    created_at=now,
                )
            )
    return len(snapshots)


def check_against_baselines(current: dict[str, dict]) -> SchemaReport:
    """So `current` với bản chuẩn; chưa cấu hình / không đọc được CSDL thì báo rõ là CHƯA kiểm (không im lặng)."""
    if not get_settings().database_url:
        return SchemaReport(checked=False, note="Chưa cấu hình DATABASE_URL nên chưa so được với bản đã duyệt.")
    try:
        baselines = latest_baselines(current)
    except Exception as exc:  # noqa: BLE001 — CSDL lỗi thì báo, không làm sập luồng
        logger.error("schema baseline read failed", extra={"error": type(exc).__name__})
        return SchemaReport(checked=False, note="Không đọc được bản cấu trúc đã duyệt (lỗi cơ sở dữ liệu).")
    return build_report(baselines, current)


def receipt_check(sources_dir: Path) -> SchemaReport:
    """Kiểm tra ngay lúc nhận: cột/kiểu của mọi file trong thư mục nguồn so với bản chuẩn (chưa xét giá trị)."""
    from src.agents.tools.duckdb_tools import discover_sources  # tránh vòng import khi graph nạp module này

    current = {
        info.name: {"origin": source_origin(info.path), "columns": dict(info.columns), "categories": {}}
        for info in discover_sources(sources_dir)
        if info.columns
    }
    report = check_against_baselines(current)
    for change in report.changes:  # lúc nhận chưa đọc giá trị → không so giá trị
        change.new_values = {}
        change.proposals = [p for p in change.proposals if p.kind != "new_values"]
    return report

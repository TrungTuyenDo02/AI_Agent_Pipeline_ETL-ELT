"""Phát hiện thay đổi cấu trúc nguồn (schema drift) — CLAUDE.md bản 2, giai đoạn 5.

Hệ thống KHÔNG ngăn được backend đổi cấu trúc mà không báo; nó chỉ có thể (1) phát hiện sớm, (2) làm pipeline hỏng to và rõ thay
vì sai lặng lẽ, (3) chỉ ra pipeline nào bị ảnh hưởng và đề xuất bản vá cho người duyệt. Không bao giờ tự tạo run, tự chạy hay tự merge.

- `capture_snapshot` / `check_source`: chụp cấu trúc (kiểu chuẩn hóa, cho phép rỗng, vị trí) qua bộ nạp, lưu phiên bản mới khi mã băm đổi,
  so với bản chuẩn (`is_baseline`) bằng `diff` (code thuần, luật ở `config/drift_rules.yaml`), ghi `SchemaChange`.
- `breaking` đang `open` chặn run (node `drift_gate`); `warning`/`info` cho chạy tiếp và hiện cảnh báo ở J1b.
- Cảnh báo thống kê (`compare_profiles`) chỉ là `warning`, không chặn. `PipelineDependency` cho biết cột nào pipeline dùng.
- Bản chuẩn cũ theo lần chạy được duyệt (`schema_snapshots`, node Vs) vẫn giữ: xem `schema_watch.py`.
"""

import difflib
import logging
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import sqlglot
import yaml
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, delete, func, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlglot import exp

from src.agents.tools.sql_tools import SqlCheckError, render_dbt_sql
from src.config import DRIFT_RULES_FILE, get_settings
from src.models.drift import SEVERITY_ORDER, ChangeDraft, DriftReport, SchemaChangeView
from src.models.sources import DataSource
from src.services import secrets
from src.services import source_registry as registry
from src.services.auth import ID, Base, get_engine
from src.services.connectors import ConnectorError, get_connector
from src.services.connectors.base import SourceConnector, TableSchema, normalize_type

logger = logging.getLogger(__name__)
DOC = JSON().with_variant(JSONB, "postgresql")
OTHER_SHAPES = "…khác"
SNAPSHOT_ATTEMPTS = 3  # chụp cấu trúc đồng thời: số lần thử lại khi vướng UNIQUE(source_id, table_name, version)
Tables = dict[str, dict[str, dict]]  # bảng → cột → {type, nullable, position}


class SourceSchemaSnapshot(Base):
    """Ảnh chụp cấu trúc một bảng của một nguồn (mỗi lần đổi một phiên bản mới; `is_baseline` = bản chuẩn đang dùng)."""

    __tablename__ = "source_schema_snapshots"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    table_name: Mapped[str] = mapped_column(String(160))
    version: Mapped[int] = mapped_column(Integer)
    columns: Mapped[dict] = mapped_column(DOC)
    fingerprint: Mapped[str] = mapped_column(String(64))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)


class SchemaChangeRow(Base):
    """Một thay đổi cấu trúc đã phát hiện."""

    __tablename__ = "schema_changes"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    table_name: Mapped[str] = mapped_column(String(160))
    from_version: Mapped[int] = mapped_column(Integer)
    to_version: Mapped[int] = mapped_column(Integer)
    change_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(12))
    detail: Mapped[str] = mapped_column(Text)
    hint: Mapped[str] = mapped_column(String(200), default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="open")
    acknowledged_by: Mapped[str] = mapped_column(String(64), default="")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProfileBaselineRow(Base):
    """Thống kê cơ sở của một bảng (số dòng, % rỗng, dạng giá trị, khoảng min/max cột không nhạy cảm); không có giá trị thật."""

    __tablename__ = "profile_baselines"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    table_name: Mapped[str] = mapped_column(String(160))
    profile: Mapped[dict] = mapped_column(DOC)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DependencyRow(Base):
    """Pipeline (lần chạy) dùng cột nào của nguồn nào."""

    __tablename__ = "pipeline_dependencies"

    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)
    source_name: Mapped[str] = mapped_column(String(160))
    table_name: Mapped[str] = mapped_column(String(160))
    column_name: Mapped[str] = mapped_column(String(160))


def _now() -> datetime:
    return datetime.now(UTC)


def _has_db() -> bool:
    return bool(get_settings().database_url)


# ---------- Luật ----------


@lru_cache(maxsize=2)
def load_rules(path: Path = DRIFT_RULES_FILE) -> dict:
    """Luật phân loại (config/drift_rules.yaml); đổi kiểu không nằm trong `safe_widening` coi là breaking."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "safe": {(a, b) for a, b in data.get("safe_widening", [])},
        "similarity": float(data.get("rename_name_similarity", 0.6)),
        "new_shape_share": float(data.get("new_shape_share", 5)),
        "range_shift_ratio": float(data.get("range_shift_ratio", 100)),
    }


# ---------- Chụp cấu trúc ----------


def table_meta(schema: TableSchema) -> dict[str, dict]:
    """Cấu trúc một bảng: cột → {kiểu chuẩn hóa, cho phép rỗng, vị trí}."""
    return {
        name: {"type": normalize_type(dtype), "nullable": schema.nullable.get(name, True), "position": index}
        for index, (name, dtype) in enumerate(schema.columns.items())
    }


def fingerprint_of(columns: dict[str, dict]) -> str:
    """Mã băm cấu trúc chuẩn hóa của một bảng (không phụ thuộc thứ tự khai báo)."""
    import hashlib

    canonical = ",".join(f"{c}:{m['type']}:{int(m['nullable'])}:{m['position']}" for c, m in sorted(columns.items()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def current_tables(connector: SourceConnector) -> Tables:
    """Cấu trúc hiện tại của mọi bảng được phép của nguồn (đọc qua bộ nạp; không đọc dòng dữ liệu)."""
    return {table: table_meta(connector.get_schema(table)) for table in connector.list_tables()}


def _latest(db: Session, source_id: int) -> dict[str, SourceSchemaSnapshot]:
    out: dict[str, SourceSchemaSnapshot] = {}
    for row in db.scalars(
        select(SourceSchemaSnapshot)
        .where(SourceSchemaSnapshot.source_id == source_id)
        .order_by(SourceSchemaSnapshot.version.asc())
    ):
        out[row.table_name] = row  # phiên bản cao nhất ghi đè
    return out


def _baselines(db: Session, source_id: int) -> dict[str, SourceSchemaSnapshot]:
    out: dict[str, SourceSchemaSnapshot] = {}
    for row in db.scalars(
        select(SourceSchemaSnapshot)
        .where(SourceSchemaSnapshot.source_id == source_id, SourceSchemaSnapshot.is_baseline.is_(True))
        .order_by(SourceSchemaSnapshot.version.asc())
    ):
        out[row.table_name] = row
    return out


def capture_snapshot(source: DataSource, tables: Tables | None = None) -> dict[str, SourceSchemaSnapshot]:
    """Chụp cấu trúc hiện tại và lưu phiên bản mới cho bảng nào đã đổi (mã băm khác bản gần nhất). Bảng chưa từng chụp: phiên bản 1 và
    là bản chuẩn. Trả về bản gần nhất của từng bảng."""
    current = tables if tables is not None else current_tables(get_connector(source))
    for attempt in range(1, SNAPSHOT_ATTEMPTS + 1):
        try:
            return _store_snapshot(source.id, current)
        except IntegrityError:
            # Hai tiến trình cùng chụp một nguồn: bên chậm vi phạm UNIQUE(source_id, table_name, version). Đọc lại bản mới nhất
            # rồi so lại (thường cấu trúc đã được bên kia ghi, không cần ghi thêm) thay vì báo lỗi.
            if attempt == SNAPSHOT_ATTEMPTS:
                raise
            logger.info("schema snapshot race, retrying", extra={"source_id": source.id, "attempt": attempt})
    raise AssertionError("unreachable")


def _store_snapshot(source_id: int, current: Tables) -> dict[str, SourceSchemaSnapshot]:
    with Session(get_engine()) as db, db.begin():
        latest = _latest(db, source_id)
        for table, columns in current.items():
            fingerprint = fingerprint_of(columns)
            previous = latest.get(table)
            if previous and previous.fingerprint == fingerprint:
                continue
            row = SourceSchemaSnapshot(
                source_id=source_id,
                table_name=table,
                version=(previous.version + 1) if previous else 1,
                columns=columns,
                fingerprint=fingerprint,
                captured_at=_now(),
                is_baseline=previous is None,
            )
            db.add(row)
            latest[table] = row
        db.flush()
        for row in latest.values():
            db.expunge(row)
        return latest


# ---------- So sánh ----------


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _rename_pairs(removed: dict[str, dict], added: dict[str, dict], threshold: float) -> list[tuple[str, str]]:
    """Cặp (cột cũ, cột mới) nghi đổi tên: cùng kiểu chuẩn hóa và cùng vị trí hoặc tên gần giống; mỗi cột chỉ ghép một lần."""
    pairs: list[tuple[str, str]] = []
    taken: set[str] = set()
    for old, old_meta in removed.items():
        candidates = [
            (new, _similar(old, new))
            for new, new_meta in added.items()
            if new not in taken
            and new_meta["type"] == old_meta["type"]
            and (new_meta["position"] == old_meta["position"] or _similar(old, new) >= threshold)
        ]
        if candidates:
            best = max(candidates, key=lambda pair: pair[1])[0]
            pairs.append((old, best))
            taken.add(best)
    return pairs


def diff(
    old: Tables, new: Tables, depended: set[tuple[str, str]] | None = None, rules: dict | None = None
) -> list[ChangeDraft]:
    """So cấu trúc cũ với mới (code thuần). `depended` = {(bảng, cột)} mà pipeline đang dùng: xóa cột đang dùng là `breaking`."""
    rules = rules or load_rules()
    depended = depended or set()
    drafts: list[ChangeDraft] = []
    for table in sorted(old):
        if table not in new:
            drafts.append(
                ChangeDraft(
                    table=table,
                    change_type="table_removed",
                    severity="breaking",
                    detail=f"Bảng {table} không còn ở nguồn.",
                )
            )
            continue
        before, after = old[table], new[table]
        removed = {c: m for c, m in before.items() if c not in after}
        added = {c: m for c, m in after.items() if c not in before}
        for old_name, new_name in _rename_pairs(removed, added, rules["similarity"]):
            drafts.append(
                ChangeDraft(
                    table=table, column=old_name, change_type="possible_rename", severity="breaking",
                    detail=f"Cột {table}.{old_name} biến mất và cột {new_name} cùng kiểu ({removed[old_name]['type']}) xuất hiện: có thể đã đổi tên.",
                    hint=f"possible_rename: {old_name} → {new_name}",
                )
            )  # fmt: skip
            removed.pop(old_name)
            added.pop(new_name)
        for column in removed:
            used = (table, column) in depended
            drafts.append(
                ChangeDraft(
                    table=table, column=column, change_type="column_removed", severity="breaking" if used else "warning",
                    detail=f"Cột {table}.{column} đã bị xóa" + (" và pipeline đang dùng cột này." if used else "; chưa có pipeline nào dùng."),
                )
            )  # fmt: skip
        for column, meta in added.items():
            drafts.append(
                ChangeDraft(
                    table=table,
                    column=column,
                    change_type="column_added",
                    severity="info",
                    detail=f"Cột mới {table}.{column} ({meta['type']}).",
                )
            )
        for column in sorted(set(before) & set(after)):
            drafts.extend(_column_changes(table, column, before[column], after[column], rules))
    return sorted(drafts, key=lambda d: (-SEVERITY_ORDER[d.severity], d.table, d.column, d.change_type))


def _column_changes(table: str, column: str, before: dict, after: dict, rules: dict) -> list[ChangeDraft]:
    out: list[ChangeDraft] = []
    if before["type"] != after["type"]:
        pair = (before["type"], after["type"])
        safe = pair in rules["safe"]
        narrowed = (pair[1], pair[0]) in rules["safe"]  # chiều ngược của mở rộng an toàn: có thể mất độ chính xác
        kind = "type_widened" if safe else "type_narrowed" if narrowed else "type_incompatible"
        note = (
            " (mở rộng an toàn)."
            if safe
            else " (thu hẹp, có thể mất độ chính xác)."
            if narrowed
            else " (không tương thích)."
        )
        out.append(
            ChangeDraft(
                table=table, column=column, change_type=kind, severity="warning" if safe else "breaking",
                detail=f"Cột {table}.{column} đổi kiểu {before['type']} → {after['type']}{note}",
            )
        )  # fmt: skip
    if before.get("nullable") is False and after.get("nullable", True):
        out.append(
            ChangeDraft(
                table=table, column=column, change_type="nullable_changed", severity="warning",
                detail=f"Cột {table}.{column} từ NOT NULL thành cho phép rỗng.",
            )
        )  # fmt: skip
    if before.get("nullable", True) and after.get("nullable", True) is False:
        out.append(
            ChangeDraft(
                table=table, column=column, change_type="nullable_tightened", severity="info",
                detail=f"Cột {table}.{column} từ cho phép rỗng thành NOT NULL.",
            )
        )  # fmt: skip
    return out


# ---------- Thống kê (chỉ cảnh báo, không chặn) ----------


def _slim_profile(profile: dict) -> dict:
    """Phần của hồ sơ dùng để so lần sau: số dòng và từng cột {null_pct, shapes, min, max}. Không có giá trị thật."""
    columns = {
        name: {k: info[k] for k in ("null_pct", "shapes", "min", "max", "sensitive") if k in info}
        for name, info in profile.get("columns", {}).items()
    }
    return {"rows": profile.get("rows", 0), "columns": columns}


def _as_float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def compare_profiles(table: str, old: dict, new: dict, rules: dict | None = None) -> list[ChangeDraft]:
    """So hồ sơ hiện tại với bản cơ sở của một bảng; chỉ sinh cảnh báo (`warning`)."""
    rules, settings = rules or load_rules(), get_settings()
    out: list[ChangeDraft] = []
    old_rows, new_rows = old.get("rows", 0), new.get("rows", 0)
    if old_rows > 0:
        ratio = float("inf") if new_rows == 0 else max(new_rows / old_rows, old_rows / new_rows)
        if ratio > settings.drift_rowcount_ratio:
            out.append(
                ChangeDraft(
                    table=table, change_type="stat_rowcount", severity="warning",
                    detail=f"Số dòng của {table} lệch {ratio:.1f} lần so với bản cơ sở ({old_rows:,} → {new_rows:,}).",
                )
            )  # fmt: skip
    for column, info in new.get("columns", {}).items():
        base = old.get("columns", {}).get(column)
        if base is None:
            continue
        delta = info.get("null_pct", 0) - base.get("null_pct", 0)
        if delta > settings.drift_null_pct_delta:
            out.append(
                ChangeDraft(
                    table=table, column=column, change_type="stat_null_increase", severity="warning",
                    detail=f"% rỗng của {table}.{column} tăng {delta:.1f} điểm phần trăm ({base.get('null_pct', 0)}% → {info.get('null_pct', 0)}%).",
                )
            )  # fmt: skip
        known = set(base.get("shapes", {}))
        fresh = [
            s
            for s, share in info.get("shapes", {}).items()
            if s not in known and s != OTHER_SHAPES and share > rules["new_shape_share"]
        ]
        if fresh and known:
            out.append(
                ChangeDraft(
                    table=table, column=column, change_type="stat_new_shape", severity="warning",
                    detail=f"Cột {table}.{column} xuất hiện dạng giá trị mới chiếm trên {rules['new_shape_share']:g}%: {', '.join(fresh[:3])}.",
                )
            )  # fmt: skip
        if not info.get("sensitive") and not base.get("sensitive"):
            old_max, new_max = _as_float(base.get("max")), _as_float(info.get("max"))
            if old_max and new_max and old_max > 0 and new_max > 0:
                ratio = max(new_max / old_max, old_max / new_max)
                if ratio >= rules["range_shift_ratio"]:
                    out.append(
                        ChangeDraft(
                            table=table, column=column, change_type="stat_range_shift", severity="warning",
                            detail=f"Khoảng giá trị của {table}.{column} lệch mạnh ({ratio:,.0f} lần): có thể đổi đơn vị.",
                            hint="có thể đổi đơn vị",
                        )
                    )  # fmt: skip
    return out


# ---------- Lưu thay đổi ----------


def _view(row: SchemaChangeRow, source_names: dict[int, str]) -> SchemaChangeView:
    return SchemaChangeView(
        id=row.id, source_id=row.source_id, source_name=source_names.get(row.source_id, ""), table=row.table_name,
        from_version=row.from_version, to_version=row.to_version, change_type=row.change_type, severity=row.severity,
        detail=row.detail, hint=row.hint or "", detected_at=row.detected_at, status=row.status,
        acknowledged_by=row.acknowledged_by or "",
    )  # fmt: skip


def _record(
    db: Session,
    source: DataSource,
    drafts: list[ChangeDraft],
    versions: dict[str, tuple[int, int]],
    scope: set[str] | None,
) -> list[SchemaChangeRow]:
    """Ghi thay đổi mới (bỏ qua cái đã `open` y hệt), đánh dấu `resolved` những thay đổi `open` không còn xuất hiện (nguồn đã đổi lại)."""
    existing = list(
        db.scalars(
            select(SchemaChangeRow).where(SchemaChangeRow.source_id == source.id, SchemaChangeRow.status == "open")
        )
    )
    current = {(d.table, d.change_type, d.detail) for d in drafts}
    for row in existing:
        in_scope = scope is None or row.table_name in scope
        if in_scope and (row.table_name, row.change_type, row.detail) not in current:
            row.status = "resolved"
    open_keys = {(r.table_name, r.change_type, r.detail) for r in existing if r.status == "open"}
    created = []
    for draft in drafts:
        if (draft.table, draft.change_type, draft.detail) in open_keys:
            continue
        before, after = versions.get(draft.table, (0, 0))
        row = SchemaChangeRow(
            source_id=source.id, table_name=draft.table, from_version=before, to_version=after, change_type=draft.change_type,
            severity=draft.severity, detail=draft.detail, hint=draft.hint, detected_at=_now(), status="open",
        )  # fmt: skip
        db.add(row)
        created.append(row)
    db.flush()
    return created


def _dependencies_of(db: Session, source_id: int) -> set[tuple[str, str]]:
    return {
        (r.table_name, r.column_name)
        for r in db.scalars(select(DependencyRow).where(DependencyRow.source_id == source_id))
    }


def check_source(
    source: DataSource, *, with_profile: bool = False, connector: SourceConnector | None = None
) -> tuple[list[SchemaChangeView], Tables]:
    """Kiểm tra một nguồn: chụp cấu trúc, so với bản chuẩn, ghi thay đổi mới. Trả (các thay đổi MỚI phát hiện, cấu trúc hiện tại).
    Nguồn không kiểm được (mất kết nối, thiếu bí mật): ném SecretError/ConnectorError cho bên gọi quyết định."""
    connector = connector or get_connector(source)
    tables = current_tables(connector)
    latest = capture_snapshot(source, tables)
    with Session(get_engine()) as db, db.begin():
        baselines = _baselines(db, source.id)
        old = {t: row.columns for t, row in baselines.items()}
        new = {t: tables[t] for t in tables if t in baselines}
        versions = {
            t: (baselines[t].version, latest[t].version if t in latest else baselines[t].version) for t in baselines
        }
        drafts = diff(old, new, _dependencies_of(db, source.id))
        scope = set(baselines)
        if with_profile:
            drafts += _profile_drafts(db, source, connector, [t for t in tables if t in baselines], versions)
        created = _record(db, source, drafts, versions, scope)
        names = {source.id: source.name}
        return [_view(row, names) for row in created], tables


def _profile_drafts(
    db: Session, source: DataSource, connector: SourceConnector, tables: list[str], versions: dict
) -> list[ChangeDraft]:
    """Cảnh báo thống kê: so hồ sơ hiện tại với bản cơ sở (chưa có thì lưu làm bản cơ sở, không cảnh báo)."""
    drafts: list[ChangeDraft] = []
    for table in tables:
        try:
            current = _slim_profile(connector.get_profile(table).model_dump())
        except (ConnectorError, secrets.SecretError) as exc:
            logger.warning("profile baseline skipped", extra={"table": table, "reason": str(exc)[:150]})
            continue
        base = db.scalar(
            select(ProfileBaselineRow)
            .where(ProfileBaselineRow.source_id == source.id, ProfileBaselineRow.table_name == table)
            .order_by(ProfileBaselineRow.id.desc())
            .limit(1)
        )
        if base is None:
            db.add(ProfileBaselineRow(source_id=source.id, table_name=table, profile=current, captured_at=_now()))
            continue
        drafts += compare_profiles(table, base.profile, current)
    return drafts


_RECENT: dict[int, tuple[float, list[SchemaChangeView], Tables]] = {}


def check_sources(
    sources: list[DataSource], *, with_profile: bool | Callable[[DataSource], bool] = False, cache_sec: float = 0
) -> DriftReport:
    """Kiểm tra nhiều nguồn rồi gom báo cáo: thay đổi mới, các `breaking` đang mở, cảnh báo đang mở. Nguồn không kiểm được vào
    `unreachable`. `cache_sec` > 0: nguồn vừa kiểm trong chừng đó giây thì dùng lại kết quả (kiểm tra trước mỗi lần chạy); 0 = luôn kiểm lại."""
    report = DriftReport()
    checked: list[DataSource] = []
    for source in sources:
        if not source.enabled:
            continue
        recent = _RECENT.get(source.id)
        try:
            if cache_sec > 0 and recent and time.monotonic() - recent[0] < cache_sec:
                created, tables = recent[1], recent[2]
            else:
                profile = with_profile(source) if callable(with_profile) else with_profile
                created, tables = check_source(source, with_profile=profile)
                _RECENT[source.id] = (
                    time.monotonic(),
                    [],
                    tables,
                )  # lần sau chỉ còn danh sách thay đổi đang mở, không "mới"
        except (ConnectorError, secrets.SecretError) as exc:
            logger.warning("drift check skipped", extra={"source": source.name, "reason": str(exc)[:150]})
            report.unreachable.append(source.name)
            continue
        report.new_changes += created
        report.tables[str(source.id)] = tables
        checked.append(source)
    report.checked_sources = len(checked)
    open_changes = list_changes([s.id for s in checked], status="open")
    report.open_breaking = [c for c in open_changes if c.severity == "breaking"]
    report.warnings = [c for c in open_changes if c.severity != "breaking"]
    return report


def forget_recent() -> None:
    """Xóa bộ nhớ đệm kiểm tra (sau khi xác nhận cấu trúc mới, hoặc trong test)."""
    _RECENT.clear()


def list_changes(
    source_ids: list[int], *, status: str | None = None, severity: str | None = None
) -> list[SchemaChangeView]:
    """Thay đổi của các nguồn (mới nhất trước), kèm pipeline bị ảnh hưởng (lần chạy dùng đúng bảng/cột đó)."""
    if not source_ids or not _has_db():
        return []
    names = {s.id: s.name for s in registry.list_sources()}
    with Session(get_engine()) as db:
        query = (
            select(SchemaChangeRow).where(SchemaChangeRow.source_id.in_(source_ids)).order_by(SchemaChangeRow.id.desc())
        )
        if status:
            query = query.where(SchemaChangeRow.status == status)
        if severity:
            query = query.where(SchemaChangeRow.severity == severity)
        rows = list(db.scalars(query.limit(500)))
        views = [_view(r, names) for r in rows]
        for view, row in zip(views, rows, strict=True):
            view.affected_pipelines = _affected(db, row)
    return views


def _affected(db: Session, row: SchemaChangeRow) -> list[dict]:
    """Lần chạy dùng bảng bị đổi (và đúng cột nếu thay đổi nêu cột); cột nằm trong `detail` nên so theo bảng + cột trong phụ thuộc."""
    query = select(DependencyRow.run_id, DependencyRow.column_name).where(
        DependencyRow.source_id == row.source_id, DependencyRow.table_name == row.table_name
    )
    pairs = db.execute(query).all()
    column = _column_of(row)
    runs = sorted({run for run, col in pairs if not column or col == column})
    return [{"run_id": run} for run in runs[:20]]


def _column_in(table: str, detail: str) -> str:
    """Cột mà `detail` nói tới (`Cột <bảng>.<cột> ...`); rỗng nếu thay đổi cấp bảng. Tên cột lấy tới khoảng trắng/dấu câu nên giữ
    được tên có gạch ngang (`\\w+` cắt cụt → bỏ sót pipeline bị ảnh hưởng); `(?<![\\w.])` thay `\\b` để bảng bắt đầu bằng ký tự
    lạ vẫn khớp. Tên bảng đã `re.escape`, mẫu không có lượng từ lồng nhau nên chạy tuyến tính."""
    match = re.search(rf"(?<![\w.]){re.escape(table)}\.([^\s(),;:]+)", detail)
    return match.group(1).rstrip(".") if match else ""


def _column_of(row: SchemaChangeRow) -> str:
    return _column_in(row.table_name, row.detail)


def acknowledge(source_id: int, user: str, *, change_id: int | None = None, table: str | None = None) -> int:
    """ "Tôi đã biết, dùng cấu trúc mới": các thay đổi `open` (một thay đổi, một bảng, hoặc cả nguồn) thành `acknowledged` và phiên bản
    mới nhất của các bảng đó thành bản chuẩn. Ghi AuditLog. Trả số thay đổi đã xác nhận."""
    with Session(get_engine()) as db, db.begin():
        query = select(SchemaChangeRow).where(SchemaChangeRow.source_id == source_id, SchemaChangeRow.status == "open")
        if change_id is not None:
            query = query.where(SchemaChangeRow.id == change_id)
        if table is not None:
            query = query.where(SchemaChangeRow.table_name == table)
        rows = list(db.scalars(query))
        tables = {r.table_name for r in rows}
        for row in rows:
            row.status, row.acknowledged_by, row.acknowledged_at = "acknowledged", user[:64], _now()
        latest = _latest(db, source_id)
        for name in tables:
            if name in latest:
                where = (SourceSchemaSnapshot.source_id == source_id, SourceSchemaSnapshot.table_name == name)
                db.execute(update(SourceSchemaSnapshot).where(*where).values(is_baseline=False))
                db.execute(
                    update(SourceSchemaSnapshot)
                    .where(SourceSchemaSnapshot.id == latest[name].id)
                    .values(is_baseline=True)
                )
            db.execute(
                delete(ProfileBaselineRow).where(
                    ProfileBaselineRow.source_id == source_id, ProfileBaselineRow.table_name == name
                )
            )
    registry.audit_access(user, "schema.acknowledge", [source_id], tables=sorted(tables), changes=len(rows))
    return len(rows)


def get_change(change_id: int) -> SchemaChangeView | None:
    """Một thay đổi theo id."""
    names = {s.id: s.name for s in registry.list_sources()}
    with Session(get_engine()) as db:
        row = db.get(SchemaChangeRow, change_id)
        if row is None:
            return None
        view = _view(row, names)
        view.affected_pipelines = _affected(db, row)
        return view


def _column_of_view(view: SchemaChangeView) -> str:
    """Cột mà một thay đổi nói tới (rỗng nếu thay đổi cấp bảng)."""
    return _column_in(view.table, view.detail)


# ---------- Phụ thuộc của pipeline ----------


def extract_dependencies(code_files: dict[str, str], catalog: list[dict]) -> list[tuple[int | None, str, str, str]]:
    """(source_id, tên nguồn, bảng, cột) mà code đã sinh dùng, phân tích bằng sqlglot trên SQL đã thay `source()`/`ref()`.

    Một file đọc nhiều bảng raw: cột được gán cho mọi bảng có cột trùng tên (có thể thừa, không bao giờ thiếu)."""
    by_table = {item["name"]: item for item in catalog}
    found: set[tuple[int | None, str, str, str]] = set()
    for path, sql in code_files.items():
        if not path.endswith(".sql") or not path.startswith(("models/staging/", "models/marts/")):
            continue
        try:
            tree = sqlglot.parse_one(render_dbt_sql(sql), read="duckdb")
        except (SqlCheckError, sqlglot.errors.ParseError):
            continue
        tables = {t.name for t in tree.find_all(exp.Table) if (t.db or "").lower() == "raw" and t.name in by_table}
        columns = {c.name for c in tree.find_all(exp.Column)} | {s.name for s in tree.find_all(exp.Star)}
        for table in tables:
            item = by_table[table]
            for column in columns:
                if column in item.get("columns", {}):
                    found.add((item.get("source_id"), item.get("source_name", ""), table, column))
    return sorted(found, key=lambda t: (t[1], t[2], t[3]))


def save_dependencies(run_id: str, dependencies: list[tuple[int | None, str, str, str]]) -> int:
    """Ghi phụ thuộc của một lần chạy (thay bản cũ của chính lần chạy đó)."""
    if not _has_db():
        return 0
    with Session(get_engine()) as db, db.begin():
        db.execute(delete(DependencyRow).where(DependencyRow.run_id == run_id))
        for source_id, source_name, table, column in dependencies:
            db.add(
                DependencyRow(
                    run_id=run_id, source_id=source_id, source_name=source_name, table_name=table, column_name=column
                )
            )
    return len(dependencies)


def run_dependencies(run_id: str) -> set[tuple[str, str]]:
    """{(bảng, cột)} mà một lần chạy dùng."""
    if not _has_db():
        return set()
    with Session(get_engine()) as db:
        return {
            (r.table_name, r.column_name)
            for r in db.scalars(select(DependencyRow).where(DependencyRow.run_id == run_id))
        }


# ---------- Kiểm tra trong lúc chạy ----------


def run_tables(sources: list[DataSource]) -> dict[str, Tables]:
    """Cấu trúc hiện tại các nguồn (khóa là id nguồn, dạng chuỗi để lưu vào state): chụp lúc bắt đầu lần chạy."""
    out: dict[str, Tables] = {}
    for source in sources:
        try:
            out[str(source.id)] = current_tables(get_connector(source))
        except (ConnectorError, secrets.SecretError):
            continue
    return out


def recheck_run(values: dict, run_id: str = "") -> DriftReport:
    """Ngay trước khi Reviewer duyệt: cấu trúc nguồn hiện tại so với cấu trúc lúc lần chạy bắt đầu. Trả các thay đổi `breaking` MỚI
    (không ghi vào bảng thay đổi). Không có ảnh chụp lúc chạy (nguồn không qua sổ, không có CSDL) → báo cáo rỗng."""
    start = (values.get("drift") or {}).get("tables") or {}
    report = DriftReport()
    if not start or not _has_db():
        return report
    sources = {str(s.id): s for s in registry.list_sources()}
    depended = run_dependencies(run_id or values.get("run_id", ""))
    for source_id, old in start.items():
        source = sources.get(source_id)
        if source is None:
            continue
        try:
            new = current_tables(get_connector(source))
        except (ConnectorError, secrets.SecretError):
            report.unreachable.append(source.name)
            continue
        report.checked_sources += 1
        used = {t: m for t, m in old.items() if any(t == d[0] for d in depended)} or old
        current = {t: new[t] for t in used if t in new}
        for draft in diff(used, current, depended):
            view = SchemaChangeView(
                id=0, source_id=source.id, source_name=source.name, table=draft.table, from_version=0, to_version=0,
                change_type=draft.change_type, severity=draft.severity, detail=draft.detail, hint=draft.hint,
                detected_at=_now(), status="open",
            )  # fmt: skip
            (report.open_breaking if draft.severity == "breaking" else report.warnings).append(view)
    return report


def counts_by_severity(changes: list[SchemaChangeView]) -> dict[str, int]:
    """Số thay đổi theo mức độ (cho tóm tắt trên web)."""
    counter = dict.fromkeys(("breaking", "warning", "info"), 0)
    for change in changes:
        counter[change.severity] += 1
    return counter


def total_changes() -> int:
    """Số thay đổi đang mở (dùng cho huy hiệu trên web)."""
    if not _has_db():
        return 0
    with Session(get_engine()) as db:
        return db.scalar(select(func.count(SchemaChangeRow.id)).where(SchemaChangeRow.status == "open")) or 0


_RECHECKS: dict[str, tuple[float, DriftReport]] = {}
RECHECK_TTL_SEC = (
    60  # màn duyệt hỏi lại mỗi vài giây: chỉ hỏi cơ sở dữ liệu nguồn tối đa mỗi phút một lần cho mỗi lần chạy
)


def recheck_cached(run_id: str, values: dict) -> DriftReport:
    """`recheck_run` có nhớ `RECHECK_TTL_SEC` giây theo lần chạy (dùng ở màn duyệt J2)."""
    hit = _RECHECKS.get(run_id)
    if hit and time.monotonic() - hit[0] < RECHECK_TTL_SEC:
        return hit[1]
    report = recheck_run(values, run_id)
    _RECHECKS[run_id] = (time.monotonic(), report)
    return report


def forget_rechecks() -> None:
    """Xóa bộ nhớ đệm kiểm lại (trong test hoặc sau khi xác nhận)."""
    _RECHECKS.clear()


BLOCKED_REVIEW = (
    "Cấu trúc nguồn đã đổi sau khi agent sinh code ({what}). Không duyệt được bản này: hãy từ chối kèm ghi chú hoặc "
    'nhờ Engineer bấm "Đề xuất bản vá" để chạy lại sandbox trên cấu trúc mới.'
)
MAX_PATCH_TEXT = 1800  # dưới trần INPUT_MAX_CHARS của cửa kiểm tra đầu vào


def patch_request_text(request_text: str, spec: dict, changes: list[SchemaChangeView]) -> str:
    """Yêu cầu cho run bản vá: yêu cầu gốc + đặc tả cũ (tóm tắt) + danh sách thay đổi cấu trúc. CHỈ cấu trúc, không có dữ liệu."""
    sources = ", ".join(s.get("name", "") for s in spec.get("sources", []))
    head = (
        f"[Bản vá do nguồn đổi cấu trúc] Cập nhật pipeline {spec.get('target', '')} (đọc từ {sources}). Yêu cầu gốc: "
    )
    lines = [f"- {c.detail}" + (f" ({c.hint})" if c.hint else "") for c in changes[:8]]
    tail = "\nThay đổi cấu trúc nguồn cần xử lý:\n" + "\n".join(lines)
    budget = MAX_PATCH_TEXT - len(head) - len(tail)
    return head + request_text.strip()[: max(budget, 200)] + tail

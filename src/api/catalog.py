"""Cấu trúc dữ liệu cho DE: bảng, schema cột, lineage, khóa nối (suy ra bằng code, 0 token)."""

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from src.agents import runner
from src.api.deps import CurrentUser, DataViewer, LoggedIn, run_for_user
from src.api.sources import user_context
from src.services import source_registry as registry
from src.services.catalog import (
    CatalogView,
    JoinInfo,
    TableInfo,
    TableProfile,
    profile_datasets,
    run_catalog,
    run_profile,
)
from src.services.jobs import get_jobs
from src.services.schema_watch import SchemaReport, receipt_check
from src.services.source_catalog import source_catalog, source_profile

NO_TABLE = "Không có bảng hoặc bộ dữ liệu này."

router = APIRouter(tags=["catalog"])


def _table_of(label: str) -> str:
    """`raw.bang.cot` → `bang`."""
    return label.removeprefix("raw.").rsplit(".", 1)[0]


def _visible_view(user: CurrentUser) -> CatalogView:
    """Bảng nguồn mà người này được thấy (mọi đường vào dữ liệu đi qua sổ nguồn), gộp từ các thư mục nguồn."""
    tables: list[TableInfo] = []
    joins: list[JoinInfo] = []
    seen: set[str] = set()
    for directory, names in registry.visible_directories(user_context(user)):
        view = source_catalog(directory)
        keep = {t.name for t in view.tables if t.name in names} - seen
        seen |= keep
        tables += [t for t in view.tables if t.name in keep]
        joins += [j for j in view.joins if _table_of(j.left) in keep and _table_of(j.right) in keep]
    return CatalogView(tables=tables, joins=joins)


@router.get("/catalog/sources", response_model=CatalogView)
def sources_catalog(user: LoggedIn) -> CatalogView:
    """Bảng nguồn bạn được thấy (chưa chạy pipeline), nhóm theo hệ thống, kèm số dòng/% rỗng/trùng khóa + gợi ý khóa nối."""
    return _visible_view(user)


@router.get("/catalog/schema-changes", response_model=SchemaReport)
def schema_changes(user: LoggedIn) -> SchemaReport:
    """Kiểm tra lúc nhận (mục 8): cột/kiểu của file nguồn bạn được thấy so với bản Reviewer đã duyệt."""
    merged = SchemaReport()
    for directory, names in registry.visible_directories(user_context(user)):
        report = receipt_check(directory)
        merged.checked = merged.checked and report.checked
        merged.note = merged.note or report.note
        merged.changes += [c for c in report.changes if c.source in names]
    merged.blocking = any(c.removed or c.rename_candidates for c in merged.changes)
    return merged


@router.get("/catalog/sources/profile", response_model=TableProfile)
def sources_profile(user: DataViewer, table: str = Query(..., max_length=128)) -> TableProfile:
    """Hồ sơ dữ liệu một bảng nguồn: chất lượng + phân bố từng cột, vấn đề, 50 dòng xem trước (đã che PII).

    Bảng không tồn tại và bảng ngoài quyền trả CÙNG một thông báo 404 (không lộ bảng có tồn tại hay không)."""
    for directory, names in registry.visible_directories(user_context(user)):
        if table in names:
            registry.audit_access(user.name, "catalog.profile", [], table=table)
            try:
                return source_profile(directory, table)
            except KeyError:
                break
    raise HTTPException(status_code=404, detail=NO_TABLE)


def _run_values(run_id: str, user: CurrentUser) -> dict:
    run_for_user(run_id, user)
    if get_jobs().busy(run_id):  # agent đang ghi sandbox: mở DuckDB lúc này làm hỏng bước chạy (khóa tệp)
        raise HTTPException(
            status_code=409, detail="Lần chạy đang xử lý, cấu trúc dữ liệu sẽ có khi tới bước chờ duyệt."
        )
    values = runner.get_values(run_id)
    if not values.get("workspace") or not Path(values["workspace"]).exists():
        raise HTTPException(status_code=409, detail="Lần chạy chưa nạp dữ liệu nên chưa có cấu trúc để hiển thị.")
    return values


@router.get("/runs/{run_id}/catalog", response_model=CatalogView)
def runs_catalog(run_id: str, user: LoggedIn) -> CatalogView:
    """Toàn cảnh một lần chạy: raw → staging → mart, kiểu cột, % rỗng, khóa, lineage, JOIN thật trong SQL."""
    return run_catalog(_run_values(run_id, user))


@lru_cache(maxsize=32)
def _cached_run_profile(run_id: str, table: str, dataset: str, stamp: int) -> TableProfile:
    return run_profile(runner.get_values(run_id), table, dataset)


@router.get("/runs/{run_id}/profile", response_model=TableProfile)
def runs_profile(
    run_id: str,
    user: DataViewer,
    table: str = Query(..., max_length=160),
    dataset: str = Query("sandbox", max_length=32),
) -> TableProfile:
    """Hồ sơ dữ liệu một bảng của lần chạy — cả staging/mart do code AI sinh — trên sandbox hoặc bộ dữ liệu thử."""
    datasets = profile_datasets(_run_values(run_id, user))
    if dataset not in datasets or not datasets[dataset].exists():
        raise HTTPException(status_code=404, detail=NO_TABLE)
    try:  # nhớ theo thời điểm sửa file DuckDB: chạy lại pipeline thì đo lại
        return _cached_run_profile(run_id, table, dataset, datasets[dataset].stat().st_mtime_ns)
    except KeyError:
        raise HTTPException(status_code=404, detail=NO_TABLE) from None

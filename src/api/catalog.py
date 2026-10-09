"""Cấu trúc dữ liệu cho DE: bảng, schema cột, lineage, khóa nối (suy ra bằng code, 0 token)."""

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from src.agents import runner
from src.api.deps import DataViewer, run_or_404
from src.config import get_settings
from src.services.catalog import CatalogView, TableProfile, profile_datasets, run_catalog, run_profile
from src.services.jobs import get_jobs
from src.services.schema_watch import SchemaReport, receipt_check
from src.services.source_catalog import source_catalog, source_profile

NO_TABLE = "Không có bảng hoặc bộ dữ liệu này."

router = APIRouter(tags=["catalog"])


@router.get("/catalog/sources", response_model=CatalogView)
def sources_catalog() -> CatalogView:
    """Bảng nguồn hiện có (chưa chạy pipeline), nhóm theo hệ thống, kèm số dòng/% rỗng/trùng khóa + gợi ý khóa nối."""
    return source_catalog(get_settings().sources_dir)


@router.get("/catalog/schema-changes", response_model=SchemaReport)
def schema_changes() -> SchemaReport:
    """Kiểm tra lúc nhận (mục 8): cột/kiểu của file trong thư mục nguồn so với bản Reviewer đã duyệt."""
    return receipt_check(get_settings().sources_dir)


@router.get("/catalog/sources/profile", response_model=TableProfile)
def sources_profile(_: DataViewer, table: str = Query(..., max_length=128)) -> TableProfile:
    """Hồ sơ dữ liệu một bảng nguồn: chất lượng + phân bố từng cột, vấn đề, 50 dòng xem trước (đã che PII)."""
    try:
        return source_profile(get_settings().sources_dir, table)
    except KeyError:
        raise HTTPException(status_code=404, detail=NO_TABLE) from None


def _run_values(run_id: str) -> dict:
    run_or_404(run_id)
    if get_jobs().busy(run_id):  # agent đang ghi sandbox: mở DuckDB lúc này làm hỏng bước chạy (khóa tệp)
        raise HTTPException(
            status_code=409, detail="Lần chạy đang xử lý, cấu trúc dữ liệu sẽ có khi tới bước chờ duyệt."
        )
    values = runner.get_values(run_id)
    if not values.get("workspace") or not Path(values["workspace"]).exists():
        raise HTTPException(status_code=409, detail="Lần chạy chưa nạp dữ liệu nên chưa có cấu trúc để hiển thị.")
    return values


@router.get("/runs/{run_id}/catalog", response_model=CatalogView)
def runs_catalog(run_id: str) -> CatalogView:
    """Toàn cảnh một lần chạy: raw → staging → mart, kiểu cột, % rỗng, khóa, lineage, JOIN thật trong SQL."""
    return run_catalog(_run_values(run_id))


@lru_cache(maxsize=32)
def _cached_run_profile(run_id: str, table: str, dataset: str, stamp: int) -> TableProfile:
    return run_profile(runner.get_values(run_id), table, dataset)


@router.get("/runs/{run_id}/profile", response_model=TableProfile)
def runs_profile(
    run_id: str,
    _: DataViewer,
    table: str = Query(..., max_length=160),
    dataset: str = Query("sandbox", max_length=32),
) -> TableProfile:
    """Hồ sơ dữ liệu một bảng của lần chạy — cả staging/mart do code AI sinh — trên sandbox hoặc bộ dữ liệu thử."""
    datasets = profile_datasets(_run_values(run_id))
    if dataset not in datasets or not datasets[dataset].exists():
        raise HTTPException(status_code=404, detail=NO_TABLE)
    try:  # nhớ theo thời điểm sửa file DuckDB: chạy lại pipeline thì đo lại
        return _cached_run_profile(run_id, table, dataset, datasets[dataset].stat().st_mtime_ns)
    except KeyError:
        raise HTTPException(status_code=404, detail=NO_TABLE) from None

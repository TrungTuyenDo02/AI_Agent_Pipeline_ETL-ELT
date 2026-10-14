"""Khung Extract chung: mỗi loại nguồn (file, duckdb, postgres) một bộ nạp cùng giao diện `SourceConnector`."""

import logging

from src.models.sources import DataSource
from src.services import secrets
from src.services.connectors.base import (
    ConnectorError,
    HealthResult,
    SampleNotAllowedError,
    SchemaFingerprint,
    SourceConnector,
    TableNotAllowedError,
    TableProfile,
    TableSchema,
    normalize_type,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ConnectorError",
    "HealthResult",
    "SampleNotAllowedError",
    "SchemaFingerprint",
    "SourceConnector",
    "TableNotAllowedError",
    "TableProfile",
    "TableSchema",
    "catalog_of",
    "get_connector",
    "normalize_type",
]


def get_connector(source: DataSource) -> SourceConnector:
    """Bộ nạp theo loại nguồn. `source` phải là nguồn ĐÃ được lọc quyền (từ `get_visible_sources`); connector không tự truy cập sổ."""
    if source.kind == "postgres":
        from src.services.connectors.postgres import (
            PostgresConnector,  # noqa: PLC0415 — tránh nạp psycopg khi không cần
        )

        return PostgresConnector(source)
    if source.kind == "duckdb":
        from src.services.connectors.duckdb_conn import DuckDBConnector  # noqa: PLC0415

        return DuckDBConnector(source)
    from src.services.connectors.file import FileConnector  # noqa: PLC0415

    return FileConnector(source)


def catalog_of(source: DataSource) -> list[dict]:
    """Danh mục bảng của một nguồn (đã lọc `allowed_tables`). Nguồn lỗi (thiếu bí mật, không kết nối được) → danh mục rỗng kèm
    cảnh báo log, không làm hỏng danh mục của các nguồn khác."""
    try:
        return get_connector(source).catalog()
    except (secrets.SecretError, ConnectorError) as exc:
        logger.warning("source unavailable", extra={"source": source.name, "reason": str(exc)[:200]})
        return []

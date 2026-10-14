"""Bộ nạp nguồn dạng tệp (CSV, JSON, Parquet, SQLite) trong một thư mục: logic "E0 Nhận nguồn" cũ nằm trong khung chung.

Vị trí thư mục: `secret_ref` (đường dẫn thư mục lấy từ bí mật) hoặc, nếu trống, `SOURCES_DIR` của cấu hình. Đây là một trong số ít
module được đọc thư mục nguồn trực tiếp (xem `tests/test_source_registry.py`).
"""

import logging
from functools import lru_cache
from pathlib import Path

import duckdb

from src.agents.tools.duckdb_tools import SourceInfo, discover_sources, load_sources
from src.agents.tools.source_stats import query_item, quote_ident
from src.config import get_settings
from src.models.sources import DataSource
from src.services import secrets
from src.services.company import read_manifest
from src.services.connectors.base import (
    HealthResult,
    SourceConnector,
    TableProfile,
    TableSchema,
    pseudonymize,
)
from src.services.profiling import cached_table_profile

logger = logging.getLogger(__name__)
HOME_NOT_FOUND = "Thư mục dữ liệu của nguồn không tồn tại hoặc không đọc được."


def location_of(source: DataSource) -> Path:
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


class FileConnector(SourceConnector):
    """Nguồn là thư mục các file; giữ nguyên hành vi nạp cũ (`ingest_sources`) kèm giới hạn dòng và băm cột nhạy cảm."""

    def __init__(self, source: DataSource) -> None:
        super().__init__(source)
        self._directory: Path | None = None

    def directory(self) -> Path:
        if self._directory is None:
            self._directory = location_of(self.source)
        return self._directory

    def _items(self) -> list[dict]:
        directory = self.directory()
        found = _discover_cached(str(directory.resolve()), _signature(directory))
        return [dict(item) for item in found if self.source.allows_table(item["name"])]

    def _item(self, table: str) -> dict:
        self.require_table(table)
        return next(i for i in self._items() if i["name"] == table)

    def catalog(self) -> list[dict]:
        return self._items()

    def list_tables(self) -> list[str]:
        return [i["name"] for i in self._items()]

    def get_schema(self, table: str) -> TableSchema:
        return TableSchema(name=table, columns=dict(self._item(table).get("columns", {})))

    def get_profile(self, table: str) -> TableProfile:
        item = self._item(table)
        profile = cached_table_profile(item, self.source.sensitivity, list(self.source.restricted_columns))
        return TableProfile(**profile)

    def _read_rows(self, table: str, n: int) -> tuple[list[str], list[tuple]]:
        item = self._item(table)
        names = list(item.get("columns", {}))
        if item.get("kind") in ("image", "pdf") or not names or n <= 0:
            return names, []
        selected = ", ".join(quote_ident(c) for c in names)
        return names, [tuple(r) for r in query_item(item, f"SELECT {selected} FROM src LIMIT {int(n)}")]

    def load_to_sandbox(
        self, tables: list[str], sandbox_conn: duckdb.DuckDBPyConnection, max_rows: int
    ) -> dict[str, int]:
        infos = [SourceInfo.model_validate(self._item(t)) for t in tables]
        counts = load_sources(sandbox_conn, infos, max_rows)
        for info in infos:
            if info.name in counts:
                pseudonymize(sandbox_conn, info.name, self.columns_to_hash(info.columns))
        return counts

    def health_check(self) -> HealthResult:
        try:
            directory = self.directory()
        except secrets.SecretError as exc:
            return HealthResult(ok=False, message=str(exc))
        if not directory.is_dir():
            return HealthResult(ok=False, message=HOME_NOT_FOUND)
        return HealthResult(ok=True, message=f"Đọc được thư mục dữ liệu ({len(self._items())} bảng được phép).")

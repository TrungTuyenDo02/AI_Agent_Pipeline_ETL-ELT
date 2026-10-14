"""Bộ nạp nguồn là một file DuckDB (`secret_ref` → đường dẫn file). Luôn mở CHỈ ĐỌC; nạp vào sandbox bằng ATTACH chỉ đọc."""

import logging
from pathlib import Path

import duckdb

from src.agents.tools.duckdb_tools import SAMPLE_SEED, connect_read, quote_path
from src.agents.tools.scrub import scrub_error
from src.models.sources import DataSource
from src.services import secrets
from src.services.connectors.base import (
    ConnectorError,
    HealthResult,
    SourceConnector,
    TableProfile,
    TableSchema,
    pseudonymize,
    quote,
)
from src.services.profiling import table_profile

logger = logging.getLogger(__name__)
SYSTEM_SCHEMAS = ("information_schema", "pg_catalog")


def display_name(schema: str, table: str) -> str:
    """Tên bảng trong danh mục: bảng ở schema `main` lấy tên trần, schema khác là `schema__bảng`."""
    return table if schema == "main" else f"{schema}__{table}"


class DuckDBConnector(SourceConnector):
    """Nguồn DuckDB (một file). Chỉ đọc, chỉ bảng trong `allowed_tables`."""

    def __init__(self, source: DataSource) -> None:
        super().__init__(source)
        self._tables: dict[str, tuple[str, str, dict[str, str]]] | None = None  # tên → (schema, bảng, cột → kiểu)
        self._nullable: dict[str, dict[str, bool]] = {}

    def path(self) -> Path:
        return Path(secrets.resolve(self.source.secret_ref))

    def _read(self) -> duckdb.DuckDBPyConnection:
        path = self.path()
        if not path.is_file():
            raise ConnectorError("File DuckDB của nguồn không tồn tại hoặc không đọc được.")
        try:
            return connect_read(path)
        except duckdb.Error as exc:
            raise ConnectorError(f"Không mở được file DuckDB của nguồn: {scrub_error(str(exc))[:150]}") from exc

    def _load_tables(self) -> dict[str, tuple[str, str, dict[str, str]]]:
        if self._tables is None:
            sql = (
                "SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.is_nullable FROM information_schema.columns c "
                "JOIN information_schema.tables t ON t.table_schema = c.table_schema AND t.table_name = c.table_name "
                "WHERE t.table_type = 'BASE TABLE' ORDER BY c.table_schema, c.table_name, c.ordinal_position"
            )
            found: dict[str, tuple[str, str, dict[str, str]]] = {}
            with self._read() as con:
                for schema, table, column, dtype, nullable in con.execute(sql).fetchall():
                    if schema in SYSTEM_SCHEMAS:
                        continue
                    name = display_name(schema, table)
                    if not (self.source.allows_table(name) or self.source.allows_table(table)):
                        continue
                    found.setdefault(name, (schema, table, {}))[2][column] = dtype
                    self._nullable.setdefault(name, {})[column] = str(nullable).upper() != "NO"
            self._tables = found
        return self._tables

    def list_tables(self) -> list[str]:
        return list(self._load_tables())

    def get_schema(self, table: str) -> TableSchema:
        self.require_table(table)
        columns = dict(self._load_tables()[table][2])
        return TableSchema(name=table, columns=columns, nullable=dict(self._nullable.get(table, {})))

    def catalog(self) -> list[dict]:
        return [
            {
                "name": name,
                "kind": "duckdb",
                "path": "",
                "table": f"{schema}.{table}",
                "columns": dict(columns),
                "sample": [],
                "label": "",
            }
            for name, (schema, table, columns) in self._load_tables().items()
        ]

    def _reference(self, table: str) -> str:
        schema, name, _ = self._load_tables()[table]
        return f"{quote(schema)}.{quote(name)}"

    def get_profile(self, table: str) -> TableProfile:
        self.require_table(table)
        item = {"name": table, "kind": "duckdb", "table": table, "columns": self.get_schema(table).columns}
        with self._read() as con:
            run = lambda sql: con.execute(f"WITH src AS (SELECT * FROM {self._reference(table)}) {sql}").fetchall()  # noqa: E731
            profile = table_profile(item, self.source.sensitivity, list(self.source.restricted_columns), query=run)
        return TableProfile(**profile)

    def row_count(self, table: str) -> int | None:
        self.require_table(table)
        with self._read() as con:
            return con.execute(f"SELECT count(*) FROM {self._reference(table)}").fetchone()[0]

    def _read_rows(self, table: str, n: int) -> tuple[list[str], list[tuple]]:
        self.require_table(table)
        names = list(self.get_schema(table).columns)
        if not names or n <= 0:
            return names, []
        with self._read() as con:
            selected = ", ".join(quote(c) for c in names)
            return names, con.execute(f"SELECT {selected} FROM {self._reference(table)} LIMIT {int(n)}").fetchall()

    def load_to_sandbox(
        self, tables: list[str], sandbox_conn: duckdb.DuckDBPyConnection, max_rows: int
    ) -> dict[str, int]:
        for table in tables:
            self.require_table(table)
        sandbox_conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
        sandbox_conn.execute(f"ATTACH {quote_path(self.path())} AS p113_source (READ_ONLY)")
        counts: dict[str, int] = {}
        try:
            for table in tables:
                reference = f"p113_source.{self._reference(table)}"
                query = f"SELECT * FROM {reference}"
                if sandbox_conn.execute(f"SELECT count(*) FROM {reference}").fetchone()[0] > max_rows:
                    query += f" USING SAMPLE reservoir({int(max_rows)} ROWS) REPEATABLE ({SAMPLE_SEED})"
                sandbox_conn.execute(f"CREATE OR REPLACE TABLE raw.{quote(table)} AS {query}")
                pseudonymize(sandbox_conn, table, self.columns_to_hash(self.get_schema(table).columns))
                counts[table] = sandbox_conn.execute(f"SELECT count(*) FROM raw.{quote(table)}").fetchone()[0]
        finally:
            sandbox_conn.execute("DETACH p113_source")
        return counts

    def health_check(self) -> HealthResult:
        try:
            with self._read() as con:
                con.execute("SELECT 1").fetchone()
            return HealthResult(ok=True, message=f"Mở được file DuckDB ({len(self.list_tables())} bảng được phép).")
        except (ConnectorError, secrets.SecretError) as exc:
            return HealthResult(ok=False, message=str(exc))
        except duckdb.Error as exc:
            return HealthResult(ok=False, message=f"Không đọc được file DuckDB: {scrub_error(str(exc))[:150]}")

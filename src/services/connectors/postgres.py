"""Bộ nạp nguồn PostgreSQL CHỈ ĐỌC (CLAUDE.md bản 2, giai đoạn 4).

Bảo đảm chỉ đọc nhiều lớp:
1. Mọi câu lệnh phải qua `check_select` (sqlglot) TRƯỚC khi tới cơ sở dữ liệu: đúng một câu SELECT, không `SELECT INTO`, không
   khóa dòng (`FOR UPDATE`), không hàm ghi/ngủ/đọc file (`nextval`, `pg_sleep`, `dblink`, ...), bảng phải nằm trong `allowed_tables`.
2. Mỗi giao dịch là `BEGIN READ ONLY` (`conn.read_only = True`): kể cả tài khoản có quyền ghi cũng không ghi được.
3. Thời hạn kết nối/truy vấn (`CONNECTOR_TIMEOUT_SEC`), giới hạn số dòng, chỉ bảng được phép.
Tài khoản kết nối nên chỉ có quyền SELECT (xem `scripts/seed_pg_sources.py`).
"""

import logging
import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import duckdb
import psycopg
import sqlglot
from psycopg.conninfo import make_conninfo
from sqlglot import exp

from src.agents.tools.duckdb_tools import SAMPLE_SEED
from src.agents.tools.scrub import scrub_error
from src.config import get_settings
from src.models.sources import DataSource
from src.services import secrets
from src.services.connectors.base import (
    ConnectorError,
    HealthResult,
    SourceConnector,
    TableProfile,
    TableSchema,
    normalize_type,
    pseudonymize,
    quote,
)
from src.services.profiling import table_profile

logger = logging.getLogger(__name__)
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
SYSTEM_SCHEMAS = ("pg_catalog", "information_schema", "pg_toast")
FORBIDDEN_FUNCTIONS = {
    "NEXTVAL", "SETVAL", "CURRVAL", "PG_SLEEP", "PG_READ_FILE", "PG_READ_BINARY_FILE", "PG_LS_DIR", "DBLINK", "DBLINK_EXEC",
    "LO_IMPORT", "LO_EXPORT", "LO_UNLINK", "SET_CONFIG", "PG_TERMINATE_BACKEND", "PG_CANCEL_BACKEND", "PG_RELOAD_CONF",
    "PG_ADVISORY_LOCK", "TXID_CURRENT",
}  # fmt: skip
SELECT_ONLY = "Chỉ cho phép một câu lệnh SELECT chỉ đọc; câu lệnh này bị từ chối trước khi tới cơ sở dữ liệu."
PROFILE_ROW_CAP = 200_000  # bảng lớn hơn chỉ đo trên chừng này dòng đầu
FETCH_BATCH = 2000
COLUMNS_SQL = (
    "SELECT table_schema, table_name, column_name, data_type, numeric_precision, numeric_scale "
    "FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast') "
    "ORDER BY table_schema, table_name, ordinal_position"
)


class ReadOnlyViolationError(ConnectorError):
    """Câu lệnh không phải SELECT chỉ đọc, hoặc đụng bảng ngoài danh sách được phép."""


def check_select(sql: str, allowed: set[str] | None = None) -> exp.Expression:
    """Kiểm tra một câu SQL TRƯỚC khi chạy (sqlglot, cú pháp PostgreSQL). Ném ReadOnlyViolationError nếu không phải đúng một
    câu SELECT chỉ đọc, hoặc nếu `allowed` được cho (tập tên bảng, thường và `schema.bảng`, viết thường) mà câu đọc bảng khác."""
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise ReadOnlyViolationError(SELECT_ONLY) from exc
    if len(statements) != 1:
        raise ReadOnlyViolationError(SELECT_ONLY)
    tree = statements[0]
    if not isinstance(tree, exp.Select | exp.Union | exp.Subquery) or tree.find(exp.Into) or tree.find(exp.Lock):
        raise ReadOnlyViolationError(SELECT_ONLY)
    for node in tree.walk():
        if isinstance(
            node, exp.Command | exp.Insert | exp.Update | exp.Delete | exp.Drop | exp.Create | exp.Alter | exp.Merge
        ):
            raise ReadOnlyViolationError(SELECT_ONLY)
        if isinstance(node, exp.Func):
            name = (node.sql_name() if not isinstance(node, exp.Anonymous) else str(node.this)).upper()
            if name in FORBIDDEN_FUNCTIONS:
                raise ReadOnlyViolationError(SELECT_ONLY)
    if allowed is not None:
        ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
        for table in tree.find_all(exp.Table):
            bare = table.name.lower()
            qualified = f"{table.db.lower()}.{bare}" if table.db else bare
            if bare in ctes and not table.db:
                continue
            if bare not in allowed and qualified not in allowed:
                raise ReadOnlyViolationError("Câu truy vấn đọc bảng ngoài danh sách được phép của nguồn.")
    return tree


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _duck_type(data_type: str, precision: int | None, scale: int | None) -> str:
    kind = normalize_type(data_type)
    if kind == "integer":
        return "BIGINT"
    if kind == "decimal":
        return f"DECIMAL({precision},{scale or 0})" if precision and precision <= 38 else "DOUBLE"
    return {"float": "DOUBLE", "boolean": "BOOLEAN", "date": "DATE", "timestamp": "TIMESTAMP"}.get(kind, "VARCHAR")


def _to_duck(value: object) -> object:
    if isinstance(value, Decimal | date | datetime | bool | int | float | str | None):
        return value
    return str(value)  # json, uuid, interval, mảng... đọc như chuỗi


class PostgresConnector(SourceConnector):
    """Nguồn PostgreSQL chỉ đọc. `connect` (tùy chọn) để test đưa kết nối giả vào."""

    def __init__(self, source: DataSource, connect: Callable[[], psycopg.Connection] | None = None) -> None:
        super().__init__(source)
        self._connect_override = connect
        self._tables: dict[str, dict] | None = None

    # ---------- Kết nối chỉ đọc ----------

    def _dsn(self) -> str:
        return secrets.resolve(self.source.secret_ref).replace("postgresql+psycopg://", "postgresql://", 1)

    def _connect(self) -> psycopg.Connection:
        """Kết nối chỉ đọc: mỗi giao dịch là `BEGIN READ ONLY`, kèm `statement_timeout` của giao dịch. Không dùng tham số khởi động
        `options` (bộ gom kết nối kiểu PgBouncer/Neon pooler từ chối)."""
        if self._connect_override:
            return self._connect_override()
        timeout = get_settings().connector_timeout_sec
        try:
            conn = psycopg.connect(make_conninfo(self._dsn(), connect_timeout=timeout), autocommit=False)
            conn.read_only = True
            conn.execute(f"SET LOCAL statement_timeout = {timeout * 1000}")  # mở giao dịch chỉ đọc đầu tiên
        except psycopg.Error as exc:
            raise ConnectorError(f"Không kết nối được tới PostgreSQL: {scrub_error(str(exc))[:150]}") from exc
        return conn

    def _allowed_names(self) -> set[str]:
        """Tên bảng được phép dạng so khớp (thường, viết thường): `bảng` và `schema.bảng`, `schema__bảng`."""
        names = set()
        for entry in self.source.allowed_tables:
            lowered = entry.lower()
            names |= {lowered, lowered.replace("__", ".")}
        return names

    def _select(self, sql: str, max_rows: int | None = None, *, system: bool = False) -> list[tuple]:
        """Chạy MỘT câu SELECT đã qua `check_select`. Câu đọc dữ liệu: bảng phải nằm trong `allowed_tables` (`*` = mọi bảng của
        nguồn); `system=True` cho câu đọc danh mục hệ thống do chính connector soạn. Lỗi cơ sở dữ liệu thành ConnectorError đã che giá trị."""
        restrict = not system and "*" not in self.source.allowed_tables
        check_select(sql, self._allowed_names() if restrict else None)
        with self._connect() as conn:
            try:
                cursor = conn.execute(sql)
                return cursor.fetchmany(max_rows) if max_rows else cursor.fetchall()
            except psycopg.Error as exc:
                raise ConnectorError(f"Truy vấn PostgreSQL lỗi: {scrub_error(str(exc))[:150]}") from exc

    # ---------- Danh mục, cấu trúc ----------

    def _load_tables(self) -> dict[str, dict]:
        if self._tables is None:
            current = self._select("SELECT current_schema()", system=True)[0][0]
            found: dict[str, dict] = {}
            for schema, table, column, dtype, precision, scale in self._select(COLUMNS_SQL, system=True):
                if schema in SYSTEM_SCHEMAS or not IDENT_RE.match(table) or not IDENT_RE.match(column):
                    continue
                name = table if schema == current else f"{schema}__{table}"
                if not (
                    self.source.allows_table(name)
                    or self.source.allows_table(f"{schema}.{table}")
                    or self.source.allows_table(table)
                ):
                    continue
                entry = found.setdefault(name, {"schema": schema, "table": table, "columns": {}, "meta": {}})
                entry["columns"][column] = dtype
                entry["meta"][column] = (precision, scale)
            self._tables = found
        return self._tables

    def list_tables(self) -> list[str]:
        return list(self._load_tables())

    def get_schema(self, table: str) -> TableSchema:
        self.require_table(table)
        return TableSchema(name=table, columns=dict(self._load_tables()[table]["columns"]))

    def catalog(self) -> list[dict]:
        return [
            {
                "name": name, "kind": "postgres", "path": "", "table": f'{info["schema"]}.{info["table"]}',
                "columns": dict(info["columns"]), "sample": [], "label": "",
            }
            for name, info in self._load_tables().items()
        ]  # fmt: skip

    def _reference(self, table: str) -> str:
        info = self._load_tables()[table]
        return f"{quote(info['schema'])}.{quote(info['table'])}"

    # ---------- Hồ sơ, mẫu ----------

    def get_profile(self, table: str) -> TableProfile:
        self.require_table(table)
        item = {"name": table, "kind": "postgres", "table": table, "columns": self.get_schema(table).columns}
        reference = self._reference(table)
        run = lambda sql: self._select(f"WITH src AS (SELECT * FROM {reference} LIMIT {PROFILE_ROW_CAP}) {sql}")  # noqa: E731
        profile = table_profile(item, self.source.sensitivity, list(self.source.restricted_columns), query=run)
        return TableProfile(**profile)

    def row_count(self, table: str) -> int | None:
        self.require_table(table)
        estimate = self._estimated_rows(table)
        if estimate >= 0:  # reltuples chưa có (-1) khi bảng chưa được ANALYZE
            return estimate
        return int(self._select(f"SELECT count(*) FROM {self._reference(table)}")[0][0])

    def _read_rows(self, table: str, n: int) -> tuple[list[str], list[tuple]]:
        self.require_table(table)
        names = list(self.get_schema(table).columns)
        if not names or n <= 0:
            return names, []
        selected = ", ".join(quote(c) for c in names)
        return names, self._select(f"SELECT {selected} FROM {self._reference(table)} LIMIT {int(n)}", n)

    # ---------- Nạp vào sandbox ----------

    def _estimated_rows(self, table: str) -> int:
        info = self._load_tables()[table]
        sql = (
            "SELECT c.reltuples::bigint FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            f"WHERE n.nspname = {_literal(info['schema'])} AND c.relname = {_literal(info['table'])}"
        )
        rows = self._select(sql, system=True)
        return int(rows[0][0]) if rows and rows[0][0] is not None else -1

    def _column_expression(self, name: str, dtype: str) -> str:
        kind = normalize_type(dtype)
        column = quote(name)
        if "with time zone" in dtype.lower():
            return f"({column} AT TIME ZONE 'UTC')"
        if kind in ("json", "other"):
            return f"CAST({column} AS TEXT)"
        return column

    def load_to_sandbox(
        self, tables: list[str], sandbox_conn: duckdb.DuckDBPyConnection, max_rows: int
    ) -> dict[str, int]:
        sandbox_conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
        counts: dict[str, int] = {}
        for table in tables:
            self.require_table(table)
            info = self._load_tables()[table]
            columns = info["columns"]
            definition = ", ".join(f"{quote(c)} {_duck_type(t, *info['meta'][c])}" for c, t in columns.items())
            sandbox_conn.execute(f"CREATE OR REPLACE TABLE raw.{quote(table)} ({definition})")
            selected = ", ".join(self._column_expression(c, t) for c, t in columns.items())
            sample = ""
            estimate = self._estimated_rows(table)
            if estimate > max_rows:  # bảng lớn: lấy mẫu có hạt giống cố định, rồi chặn cứng bằng LIMIT
                percent = min(100.0, max(0.01, 100.0 * max_rows * 1.2 / estimate))
                sample = f" TABLESAMPLE BERNOULLI ({percent:.4f}) REPEATABLE ({SAMPLE_SEED})"
            sql = f"SELECT {selected} FROM {self._reference(table)}{sample} LIMIT {int(max_rows)}"
            check_select(sql, None)
            placeholders = ", ".join("?" for _ in columns)
            with self._connect() as conn:
                try:
                    with conn.cursor(name="p113_load") as cursor:
                        cursor.itersize = FETCH_BATCH
                        cursor.execute(sql)
                        while batch := cursor.fetchmany(FETCH_BATCH):
                            sandbox_conn.executemany(
                                f"INSERT INTO raw.{quote(table)} VALUES ({placeholders})",
                                [[_to_duck(v) for v in row] for row in batch],
                            )
                except psycopg.Error as exc:
                    raise ConnectorError(f"Nạp bảng từ PostgreSQL lỗi: {scrub_error(str(exc))[:150]}") from exc
            pseudonymize(sandbox_conn, table, self.columns_to_hash(columns))
            counts[table] = sandbox_conn.execute(f"SELECT count(*) FROM raw.{quote(table)}").fetchone()[0]
        return counts

    def health_check(self) -> HealthResult:
        try:
            self._select("SELECT 1", system=True)
            return HealthResult(ok=True, message=f"Kết nối được PostgreSQL ({len(self.list_tables())} bảng được phép).")
        except (ConnectorError, secrets.SecretError) as exc:
            return HealthResult(ok=False, message=str(exc))

"""Nạp bộ dữ liệu `P113 Retail` (giả lập) vào một PostgreSQL để thử PostgresConnector, kèm tài khoản chỉ có quyền SELECT.

Dùng với dịch vụ `sources-db` của docker compose (profile `dev-sources`, KHÔNG bật mặc định):

    docker compose --profile dev-sources up -d sources-db
    python scripts/seed_pg_sources.py --dsn postgresql://postgres:<mật khẩu>@127.0.0.1:5434/p113_retail \\
        --reader p113_reader --reader-password <mật khẩu đọc>

Sau đó đăng ký nguồn kind=postgres với `secret_ref` (vd `conn_retail_pg`) và đặt biến môi trường
`P113_SECRET_CONN_RETAIL_PG=postgresql://p113_reader:<mật khẩu đọc>@127.0.0.1:5434/p113_retail` trên máy chủ (xem docs/RUNBOOK.md).
Mật khẩu chỉ truyền bằng tham số/biến môi trường, không ghi vào file nào của repo.
"""

import argparse
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import duckdb
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.tools.duckdb_tools import SourceInfo, discover_sources, read_expr  # noqa: E402
from src.models.spec import SourceRef  # noqa: E402
from src.services.seed import SeedConfig, generate_sources  # noqa: E402

PG_TYPES = {
    "BIGINT": "BIGINT",
    "DOUBLE": "DOUBLE PRECISION",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
    "BOOLEAN": "BOOLEAN",
}
BATCH = 2000


def pg_type(duck_type: str) -> str:
    """Kiểu DuckDB của nguồn → kiểu PostgreSQL (cột phức tạp thành TEXT)."""
    upper = duck_type.upper()
    if upper.startswith("DECIMAL"):
        return upper.replace("DECIMAL", "NUMERIC")
    return PG_TYPES.get(upper, "TEXT")


def _rows(info: SourceInfo) -> tuple[list[str], list[tuple]]:
    """Đọc toàn bộ dòng của một nguồn (DuckDB cho CSV/JSON/Parquet, sqlite3 cho SQLite), giữ đúng kiểu cột."""
    if info.kind == "sqlite":
        with closing(sqlite3.connect(info.path)) as lite:
            return list(info.columns), lite.execute(f'SELECT * FROM "{info.table}"').fetchall()
    with duckdb.connect() as con:
        relation = con.sql(f"SELECT * FROM {read_expr(SourceRef(name=info.name, kind=info.kind, path=info.path))}")
        return list(relation.columns), relation.fetchall()


def seed_schema(dsn: str, schema: str, sources: list[SourceInfo], tables: list[str] | None = None) -> dict[str, int]:
    """Tạo `schema` (nếu chưa có) và nạp các nguồn dạng bảng vào đó; trả số dòng mỗi bảng."""
    counts: dict[str, int] = {}
    with psycopg.connect(dsn, autocommit=True) as conn:
        if schema != "public":
            conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        for info in sources:
            if info.kind not in ("csv", "json", "parquet", "sqlite") or (tables and info.name not in tables):
                continue
            names, rows = _rows(info)
            columns = sql.SQL(", ").join(
                sql.SQL("{} {}").format(sql.Identifier(c), sql.SQL(pg_type(info.columns.get(c, "VARCHAR"))))
                for c in names
            )
            target = sql.Identifier(schema, info.name)
            conn.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(target))
            conn.execute(sql.SQL("CREATE TABLE {} ({})").format(target, columns))
            insert = sql.SQL("INSERT INTO {} VALUES ({})").format(
                target, sql.SQL(", ").join(sql.Placeholder() for _ in names)
            )
            with conn.cursor() as cursor:
                for start in range(0, len(rows), BATCH):
                    cursor.executemany(
                        insert,
                        [
                            [v if v is None or isinstance(v, int | float | str | bool) else str(v) for v in row]
                            for row in rows[start : start + BATCH]
                        ],
                    )
            counts[info.name] = len(rows)
    return counts


def grant_reader(dsn: str, schema: str, role: str, password: str) -> None:
    """Tài khoản đọc: chỉ LOGIN + SELECT trên các bảng của `schema` (cần tài khoản có quyền tạo role)."""
    with psycopg.connect(dsn, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role]).fetchone()
        verb = "ALTER" if exists else "CREATE"
        conn.execute(
            sql.SQL(verb + " ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                sql.Identifier(role), sql.Literal(password)
            )
        )
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(schema), sql.Identifier(role)))
        conn.execute(
            sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(role)
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dsn", required=True, help="chuỗi kết nối của tài khoản có quyền tạo bảng")
    parser.add_argument("--schema", default="public")
    parser.add_argument("--profile", choices=("basic", "company"), default="company")
    parser.add_argument("--reader", help="tên tài khoản chỉ đọc cần tạo (tùy chọn)")
    parser.add_argument("--reader-password", help="mật khẩu của tài khoản chỉ đọc")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        generate_sources(SeedConfig(out_dir=Path(tmp), profile=args.profile))
        counts = seed_schema(args.dsn, args.schema, discover_sources(Path(tmp)))
    print(f"Đã nạp {len(counts)} bảng vào schema {args.schema}: {sum(counts.values())} dòng.")
    if args.reader:
        if not args.reader_password:
            parser.error("--reader cần --reader-password")
        grant_reader(args.dsn, args.schema, args.reader, args.reader_password)
        print(f"Đã tạo tài khoản chỉ đọc {args.reader} (chỉ SELECT trên schema {args.schema}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

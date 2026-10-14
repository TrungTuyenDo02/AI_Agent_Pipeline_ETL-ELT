"""Số liệu nguồn cho Planner (code, 0 token) thay cho dòng mẫu: CLAUDE.md 2.3, LLM chỉ thấy cấu trúc + con số.

- `source_stats`: số dòng, cột ít giá trị (chỉ số lượng), khóa lặp và khóa lặp mà nội dung khác nhau.
- `column_values`: giá trị thật (đã che PII) của một cột ít giá trị — CHỈ để hiện cho người chọn ở J1, không gửi LLM.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import duckdb

from src.agents.nodes.profiler import CATEGORY_MAX, KEY_NAME_RE
from src.agents.tools.duckdb_tools import read_expr
from src.agents.tools.pii import mask_value
from src.models.spec import SourceRef

TABULAR = ("csv", "json", "parquet", "sqlite")


def query_item(item: dict, sql: str) -> list[tuple]:
    """Chạy `sql` (bảng nguồn gọi là `src`) trên file nguồn; SQLite đọc bằng sqlite3 (cú pháp SQL chung)."""
    if item["kind"] == "sqlite":
        with closing(sqlite3.connect(f"file:{Path(item['path']).as_posix()}?mode=ro", uri=True)) as conn:
            table = item["table"].replace('"', '""')
            return conn.execute(f'WITH src AS (SELECT * FROM "{table}") {sql}').fetchall()
    ref = SourceRef(name=item["name"], kind=item["kind"], path=item["path"])
    with duckdb.connect() as con:
        return con.execute(f"WITH src AS (SELECT * FROM {read_expr(ref)}) {sql}").fetchall()


def quote_ident(column: str) -> str:
    return '"' + column.replace('"', '""') + '"'


def source_stats(item: dict) -> dict:
    """Con số về một nguồn dạng bảng (không có giá trị nào của dữ liệu)."""
    columns = list(item.get("columns", {}))
    if item.get("kind") not in TABULAR or not columns:
        return {}
    counts = ", ".join(f"count(DISTINCT {quote_ident(c)})" for c in columns)
    rows, *distinct = query_item(item, f"SELECT count(*), {counts} FROM src")[0]
    by_column = dict(zip(columns, distinct, strict=True))
    stats: dict = {"rows": rows}
    few = {c: n for c, n in by_column.items() if 1 < n <= CATEGORY_MAX and not KEY_NAME_RE.match(c)}
    if few:
        stats["few_values"] = few  # cột phân loại: chỉ số giá trị khác nhau
    keys = [c for c in columns if KEY_NAME_RE.match(c)]
    if keys:
        key = max(keys, key=lambda c: by_column[c])
        repeated = query_item(
            item,
            f"SELECT count(*) FROM (SELECT {quote_ident(key)} FROM src WHERE {quote_ident(key)} IS NOT NULL "
            f"GROUP BY 1 HAVING count(*) > 1) t",
        )[0][0]
        stats.update(key_column=key, repeated_keys=repeated)
        if repeated:
            differing = query_item(
                item,
                f"SELECT count(*) FROM (SELECT {quote_ident(key)} FROM (SELECT DISTINCT * FROM src) d "
                f"WHERE {quote_ident(key)} IS NOT NULL GROUP BY 1 HAVING count(*) > 1) t",
            )[0][0]
            stats["repeated_keys_differing"] = differing  # khóa lặp mà các dòng không giống hệt nhau
    return stats


def with_stats(catalog: list[dict]) -> list[dict]:
    """Bổ sung `stats` cho nguồn chưa có (danh mục có thể đến từ state, eval hoặc API)."""
    return [item if "stats" in item else {**item, "stats": source_stats(item)} for item in catalog]


def column_values(catalog: list[dict], column_ref: str) -> tuple[list[str], bool]:
    """Giá trị khác nhau của `nguồn.cột` (≤ CATEGORY_MAX, đã che PII) để người chọn → (giá trị, đã chuẩn hóa).

    Cột có cách viết chỉ khác hoa/thường/khoảng trắng (' open', 'OPEN') thì gộp theo upper(trim(...)).
    Rỗng nếu không dùng được (không thấy cột, quá nhiều hoặc chỉ một giá trị).
    """
    source, _, column = column_ref.partition(".")
    item = next((i for i in catalog if i.get("name") == source and i.get("kind") in TABULAR), None)
    if not item or column not in item.get("columns", {}):
        return [], False
    col = quote_ident(column)
    raw, normalized = query_item(item, f"SELECT count(DISTINCT {col}), count(DISTINCT upper(trim({col}))) FROM src")[0]
    expr = f"upper(trim({col}))" if raw > normalized else col
    sql = f"SELECT DISTINCT {expr} FROM src WHERE {col} IS NOT NULL LIMIT {CATEGORY_MAX + 1}"
    values = sorted({str(mask_value(r[0])) for r in query_item(item, sql)})
    return (values, raw > normalized) if 2 <= len(values) <= CATEGORY_MAX else ([], False)

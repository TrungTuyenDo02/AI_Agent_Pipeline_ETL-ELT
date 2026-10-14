"""Hồ sơ thống kê một bảng nguồn dành cho LLM (CLAUDE.md bản 2, mục 3.3): số đếm và DẠNG giá trị, không có giá trị thật.

Chỉ `llm_context.build_llm_context` dùng module này. Mức `profile` được thấy: số dòng, % rỗng, số giá trị khác nhau, tỷ lệ trùng
khóa, dạng giá trị (chữ số → 9, chữ cái → a/A) và phân bố các dạng. Quy tắc cột nhạy cảm (tên gợi ý thông tin cá nhân, admin đánh
dấu `restricted_columns`, hoặc giá trị có dạng email/số điện thoại): chỉ có số đếm và dạng giá trị, KHÔNG có min/max, KHÔNG có
giá trị phổ biến. Danh sách giá trị phổ biến chỉ có cho cột phân loại ít giá trị (≤ 10, lặp lại ≥ 3 lần) của nguồn `low`.
"""

from collections import Counter
from functools import lru_cache
from pathlib import Path

from src.agents.nodes.profiler import DATE_NAME_RE, KEY_NAME_RE, MONEY_NAME_RE
from src.agents.tools.pii import looks_like_pii, mask_value, sensitive_column, value_shape
from src.agents.tools.source_stats import TABULAR, query_item, quote_ident, source_stats

VALUE_COUNTS = 1000  # số giá trị phổ biến nhất đem tính dạng giá trị
TOP_SHAPES = 5
CATEGORY_MAX_DISTINCT = 10
CATEGORY_MIN_REPEAT = 3  # trung bình mỗi giá trị lặp ≥ chừng này lần mới coi là cột phân loại (không phải mã định danh)
PII_VALUE_SHARE = 0.05  # ≥ 5% giá trị có dạng email/số điện thoại → coi là cột nhạy cảm dù tên không gợi ý
RANGE_PARSE_RATE = 0.95
NUMERIC_TYPES = ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UBIGINT", "DOUBLE", "FLOAT", "REAL", "DECIMAL")
DATE_TYPES = ("DATE", "TIMESTAMP")
OTHER_SHAPES = "…khác"


def _round(value: float) -> float:
    return round(value, 1)


def _shapes(counts: list[tuple[str, int]], non_null: int) -> dict[str, float]:
    """Phân bố dạng giá trị (% của số giá trị khác rỗng), tối đa TOP_SHAPES dạng, phần còn lại gộp vào `…khác`."""
    totals: Counter = Counter()
    for value, count in counts:
        totals[value_shape(value)] += count
    seen = sum(totals.values()) or 1
    ordered = totals.most_common()
    shown = {shape: _round(100 * count / seen) for shape, count in ordered[:TOP_SHAPES]}
    rest = sum(count for _, count in ordered[TOP_SHAPES:])
    if rest:
        shown[OTHER_SHAPES] = _round(100 * rest / seen)
    return shown


def _value_counts(item: dict, column: str) -> list[tuple[str, int]]:
    col = quote_ident(column)
    sql = (
        f"SELECT CAST({col} AS VARCHAR) AS v, count(*) AS c FROM src WHERE {col} IS NOT NULL "
        f"GROUP BY 1 ORDER BY c DESC, v LIMIT {VALUE_COUNTS}"
    )
    return [(str(v), int(c)) for v, c in query_item(item, sql)]


def _fmt(value: object) -> str:
    """Số nguyên đọc dưới dạng double (1.0) hiển thị gọn (1)."""
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def _value_range(item: dict, column: str, dtype: str) -> dict:
    """min/max cho cột số hoặc ngày (chỉ gọi với cột không nhạy cảm). Cột chuỗi (CSV) chỉ có khoảng khi ≥ 95% đọc được."""
    col = quote_ident(column)
    kind = dtype.upper()
    if kind.startswith(NUMERIC_TYPES) or kind.startswith(DATE_TYPES):
        low, high = query_item(item, f"SELECT min({col}), max({col}) FROM src")[0]
        return {"min": _fmt(low), "max": _fmt(high)} if low is not None else {}
    if item.get("kind") == "sqlite":
        return {}
    for cast in ("double", "date"):
        total, parsed, low, high = query_item(
            item,
            f"SELECT count({col}), count(try_cast({col} AS {cast})), min(try_cast({col} AS {cast})), "
            f"max(try_cast({col} AS {cast})) FROM src",
        )[0]
        if total and parsed / total >= RANGE_PARSE_RATE and low is not None:
            return {"min": _fmt(low), "max": _fmt(high)}
    return {}


def _column_profile(item: dict, column: str, dtype: str, stats: tuple[int, int, int], settings: tuple) -> dict:
    total, filled, distinct = stats
    sensitivity, restricted = settings
    counts = _value_counts(item, column)
    info: dict = {
        "type": dtype,
        "null_pct": _round(100 * (total - filled) / total) if total else 0.0,
        "distinct": distinct,
    }
    sensitive = sensitive_column(column, restricted)
    if counts and sum(c for v, c in counts if looks_like_pii(v)) / max(1, sum(c for _, c in counts)) >= PII_VALUE_SHARE:
        sensitive = True
    if counts:
        info["shapes"] = _shapes(counts, filled)
    if sensitive:
        info["sensitive"] = True  # chỉ số đếm + dạng giá trị
        return info
    info.update(_value_range(item, column, dtype))
    plain = not (
        KEY_NAME_RE.match(column) or MONEY_NAME_RE.search(column) or DATE_NAME_RE.search(column)
    )  # mã, tiền, ngày: không liệt kê giá trị
    categorical = plain and 1 < distinct <= CATEGORY_MAX_DISTINCT and filled >= CATEGORY_MIN_REPEAT * distinct
    if sensitivity == "low" and categorical and len(counts) == distinct:
        info["top_values"] = {str(mask_value(v)): _round(100 * c / filled) for v, c in counts}
    return info


def table_profile(item: dict, sensitivity: str = "medium", restricted: tuple[str, ...] | list[str] = ()) -> dict:
    """Hồ sơ thống kê an toàn của một bảng nguồn (dict `item` của danh mục). Rỗng nếu không phải bảng (ảnh/PDF)."""
    columns = dict(item.get("columns", {}))
    if item.get("kind") not in TABULAR or not columns:
        return {}
    base = source_stats(item)  # rows, few_values (số lượng), key_column, repeated_keys, repeated_keys_differing
    names = list(columns)
    counts = ", ".join(f"count({quote_ident(c)}), count(DISTINCT {quote_ident(c)})" for c in names)
    total, *rest = query_item(item, f"SELECT count(*), {counts} FROM src")[0]
    profile = {**base, "rows": total, "columns": {}}
    for index, name in enumerate(names):
        filled, distinct = rest[2 * index], rest[2 * index + 1]
        profile["columns"][name] = _column_profile(
            item, name, columns[name], (total, filled, distinct), (sensitivity, tuple(restricted))
        )
    key = base.get("key_column")
    if key and profile["columns"].get(key, {}).get("distinct"):
        distinct_keys = profile["columns"][key]["distinct"]
        profile["duplicate_key_pct"] = _round(100 * base.get("repeated_keys", 0) / distinct_keys)
    return profile


def _key(item: dict) -> tuple:
    path = Path(item.get("path", ""))
    stat = path.stat() if path.exists() else None
    return item.get("name"), str(path), stat.st_mtime_ns if stat else 0, stat.st_size if stat else 0


@lru_cache(maxsize=64)
def _cached(key: tuple, columns: tuple, kind: str, table: str, path: str, sensitivity: str, restricted: tuple) -> dict:
    item = {"name": key[0], "kind": kind, "table": table, "path": path, "columns": dict(columns)}
    return table_profile(item, sensitivity, restricted)


def cached_table_profile(item: dict, sensitivity: str, restricted: list[str]) -> dict:
    """Như `table_profile`, nhớ kết quả tới khi file nguồn đổi (planner chạy nhiều vòng không đo lại)."""
    return _cached(
        _key(item),
        tuple(sorted(item.get("columns", {}).items())),
        item.get("kind", ""),
        item.get("table", ""),
        item.get("path", ""),
        sensitivity,
        tuple(sorted(restricted)),
    )


def masked_sample(item: dict, rows: int, restricted: tuple[str, ...] | list[str] = ()) -> list[dict]:
    """Tối đa `rows` dòng đã che: cột nhạy cảm chỉ còn dạng giá trị, cột khác đi qua `pii.mask_value`. Cố định thứ tự (không ngẫu nhiên)."""
    if item.get("kind") not in TABULAR or not item.get("columns"):
        return []
    names = list(item["columns"])
    selected = ", ".join(quote_ident(c) for c in names)
    result = query_item(item, f"SELECT {selected} FROM src LIMIT {int(rows)}")
    out = []
    for row in result:
        out.append(
            {
                name: value_shape(str(value))
                if sensitive_column(name, restricted) and value is not None
                else mask_value(value if isinstance(value, str | int | float | type(None)) else str(value))
                for name, value in zip(names, row, strict=True)
            }
        )
    return out

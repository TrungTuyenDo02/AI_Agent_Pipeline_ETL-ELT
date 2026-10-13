"""P Soi dữ liệu (code): kiểu cột, % rỗng, số dòng, trùng khóa, định dạng ngày/tiền (+ biểu thức DuckDB đọc đúng); mẫu đã che PII.

Nhận diện phải có bằng chứng trong dữ liệu: điều code không chứng minh được (vd `03/04/2026` là dd/mm hay mm/dd)
thì giữ cách đọc mặc định cũ và ghi vào `uncertain` để người duyệt thấy, không đoán im lặng.
"""

import re
from pathlib import Path

import duckdb

from src.agents.nodes.common import sandbox_db
from src.agents.state import PipelineState
from src.agents.tools.duckdb_tools import RAW_SCHEMA, connect_read, read_catalog
from src.agents.tools.pii import mask_value

DATE_PATTERNS = {
    "dd/mm/yyyy": re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    "dd/mm/yyyy hh:mm:ss": re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}(:\d{2})?$"),
    "mm/dd/yyyy hh:mm AM/PM": re.compile(r"^\d{2}/\d{2}/\d{4} \d{1,2}:\d{2} [AP]M$"),
    "yyyy-mm-dd": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "yyyy-mm-dd hh:mm:ss": re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$"),
    "yyyy-mm-ddThh:mm:ss+07:00": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"),
    "yyyymmdd": re.compile(r"^(19|20)\d{6}$"),
}
# Định dạng cần try_strptime (DuckDB không tự đọc); ISO thì try_cast đọc được
STRPTIME_FORMATS = {
    "dd/mm/yyyy": ("%d/%m/%Y",),
    "dd/mm/yyyy hh:mm:ss": ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"),
    "mm/dd/yyyy": ("%m/%d/%Y",),
    "mm/dd/yyyy hh:mm:ss": ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"),
    "mm/dd/yyyy hh:mm AM/PM": ("%m/%d/%Y %I:%M %p",),
    "yyyymmdd": ("%Y%m%d",),
}
TIME_FORMATS = {
    "dd/mm/yyyy hh:mm:ss",
    "mm/dd/yyyy hh:mm:ss",
    "mm/dd/yyyy hh:mm AM/PM",
    "yyyy-mm-dd hh:mm:ss",
    "yyyy-mm-ddThh:mm:ss+07:00",
}
# `xx/xx/yyyy` (24 giờ): mẫu chỉ khớp hình dạng, thứ tự ngày/tháng do bằng chứng quyết định (day_month_evidence)
MONTH_FIRST = {"dd/mm/yyyy": "mm/dd/yyyy", "dd/mm/yyyy hh:mm:ss": "mm/dd/yyyy hh:mm:ss"}
SLASH_DATE_RE = r"^\d{2}/\d{2}/\d{4}( \d{2}:\d{2}(:\d{2})?)?$"
MONEY_PATTERNS = {
    "vnd_dot (1.075.000)": re.compile(r"^\d{1,3}(\.\d{3})+$"),
    "comma (1,075,000)": re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$"),
    "plain number": re.compile(r"^\d+(\.\d{1,2})?$"),  # "125.000" là kiểu VND, không phải số thập phân
    "suffix k (1075k)": re.compile(r"^\d+k$"),
    "currency text (1.075.000đ)": re.compile(r"^[\d.,]+ ?(đ|VND|vnd)$"),
}
MONEY_NAME_RE = re.compile(r"amount|total|price|revenue|vnd|spend|cost|fee", re.I)
KEY_NAME_RE = re.compile(r"^(id|.*_id)$", re.I)
DATE_NAME_RE = re.compile(r"date|time|day|_at$|_on$|_ts$", re.I)
SAMPLE_VALUES = 1000  # số giá trị khác nhau đem dò định dạng (định dạng hiếm vẫn lọt vào mẫu)
# Cột phân loại: chuỗi có ít giá trị khác nhau (không phải khóa/ngày/tiền). Danh sách giá trị chỉ để so cấu trúc
# giữa các lần chạy (mục 8) — KHÔNG gửi LLM và không phải danh sách giá trị hợp lệ (mục 9: do người/đặc tả quyết).
CATEGORY_MAX = 12


def _formats(values: list[str], patterns: dict[str, re.Pattern]) -> list[str]:
    return sorted({name for v in values for name, p in patterns.items() if p.match(v)})


def day_month_evidence(con: duckdb.DuckDBPyConnection, ref: str, column: str) -> dict[str, int]:
    """Đếm trên CẢ cột: số đầu > 12 chỉ có thể là ngày (dd/mm), số thứ hai > 12 thì là mm/dd; cả hai ≤ 12 thì chưa rõ."""
    col = f'"{column}"'
    first, second = f"try_cast(substr({col}, 1, 2) AS INT)", f"try_cast(substr({col}, 4, 2) AS INT)"
    sql = (
        f"SELECT count(*) FILTER ({first} > 12 AND {second} <= 12), count(*) FILTER ({second} > 12 AND {first} <= 12), "
        f"count(*) FILTER ({first} <= 12 AND {second} <= 12) FROM {ref} WHERE regexp_matches({col}, '{SLASH_DATE_RE}')"
    )
    day_first, month_first, unclear = con.execute(sql).fetchone()
    return {"day_first": day_first, "month_first": month_first, "unclear": unclear}


def resolve_day_month(formats: list[str], evidence: dict[str, int]) -> tuple[list[str], list[str]]:
    """Chọn thứ tự ngày/tháng theo bằng chứng → (định dạng, điều chưa chắc). Không có bằng chứng: giữ dd/mm như cũ."""
    day, month, unclear = evidence["day_first"], evidence["month_first"], evidence["unclear"]
    if month and not day:
        return sorted(MONTH_FIRST.get(f, f) for f in formats), []
    if month and day:
        both = sorted({*formats, *(MONTH_FIRST[f] for f in formats if f in MONTH_FIRST)})
        note = f"Lẫn dd/mm ({day} giá trị) và mm/dd ({month} giá trị) trong cùng cột"
        tail = f"; {unclear} giá trị có ngày và tháng đều ≤ 12 đang đọc theo dd/mm." if unclear else "."
        return both, [note + tail]
    if unclear and not day:
        return formats, [f"Không giá trị nào cho biết thứ tự ngày/tháng ({unclear} giá trị); đang đọc theo dd/mm."]
    return formats, []


def date_expression(column: str, formats: list[str]) -> str:
    """Biểu thức đọc ngày nhiều định dạng: try_strptime từng định dạng lạ + try_cast cho ISO; có giờ thì giữ giờ."""
    col = f'"{column}"'
    parts = [f"try_strptime({col}, '{fmt}')" for name in formats for fmt in STRPTIME_FORMATS.get(name, ())]
    if "yyyy-mm-ddThh:mm:ss+07:00" in formats:
        parts.append(f"try_strptime(left({col}, 19), '%Y-%m-%dT%H:%M:%S')")  # giữ giờ địa phương, bỏ phần múi giờ
    iso = f"try_cast({col} as timestamp)"
    expression = f"coalesce({', '.join([*parts, iso])})" if parts else iso
    return expression if set(formats) & TIME_FORMATS else f"{expression}::date"


def money_expression(column: str, formats: list[str]) -> str:
    """Biểu thức đọc tiền dạng chuỗi; lẫn nhiều kiểu viết thì dùng CASE chịu được mọi kiểu đã gặp."""
    col = f'"{column}"'
    if formats == ["vnd_dot (1.075.000)"]:
        return f"try_cast(replace({col}, '.', '') as bigint)"
    if formats == ["comma (1,075,000)"]:
        return f"try_cast(replace({col}, ',', '') as double)"
    if set(formats) <= {"plain number"}:
        return f"try_cast({col} as double)" if formats else ""
    return (
        f"CASE WHEN regexp_matches(trim({col}), '^[0-9]+k$') THEN try_cast(regexp_extract({col}, '[0-9]+') as bigint) * 1000 "
        f"WHEN regexp_matches(trim({col}), '^[0-9]+[.][0-9]{{1,2}}$') THEN cast(try_cast(trim({col}) as double) as bigint) "
        f"ELSE try_cast(regexp_replace({col}, '[^0-9]', '', 'g') as bigint) END"
    )


def parse_expression(column: str, profile: dict) -> str:
    """Biểu thức DuckDB đọc đúng cột chuỗi theo định dạng đã phát hiện (gợi ý cho Coder/Tester, đã chạy thử)."""
    if profile.get("date_formats"):
        return date_expression(column, profile["date_formats"])
    return money_expression(column, profile.get("money_formats", []))


def _variants(con: duckdb.DuckDBPyConnection, ref: str, column: str) -> int:
    """Số giá trị khác nhau chỉ vì hoa/thường/khoảng trắng (ví dụ 'ST001', 'st001', ' ST001')."""
    raw, normalized = con.execute(
        f'SELECT count(DISTINCT "{column}"), count(DISTINCT upper(trim("{column}"))) FROM {ref}'
    ).fetchone()
    return raw - normalized


def _column_profile(con: duckdb.DuckDBPyConnection, table: str, column_type: tuple[str, str]) -> dict:
    column, dtype = column_type
    ref = f'{RAW_SCHEMA}."{table}"'
    total, filled, distinct = con.execute(
        f'SELECT count(*), count("{column}"), count(DISTINCT "{column}") FROM {ref}'
    ).fetchone()
    sample_sql = f'SELECT DISTINCT "{column}" FROM {ref} WHERE "{column}" IS NOT NULL LIMIT {SAMPLE_VALUES}'
    texts = [str(r[0]) for r in con.execute(sample_sql).fetchall()]
    profile = {
        "type": dtype,
        "nulls": total - filled,
        "null_pct": round(100 * (total - filled) / total, 2) if total else 0.0,
        "distinct": distinct,
        "examples": [mask_value(v) for v in texts[:3]],
    }
    if dtype == "VARCHAR":
        profile.update(text_hints(con, (ref, column), texts))
        if _is_category(column, profile):
            profile["categories"] = sorted({str(mask_value(v)) for v in texts})
    return profile


def _is_category(column: str, profile: dict) -> bool:
    """Chuỗi ít giá trị, không phải khóa/ngày/tiền (vd trạng thái, giới tính, kênh bán)."""
    special = KEY_NAME_RE.match(column) or MONEY_NAME_RE.search(column) or profile.get("date_formats")
    return 0 < profile["distinct"] <= CATEGORY_MAX and not special


def text_hints(con: duckdb.DuckDBPyConnection, ref_column: tuple[str, str], texts: list[str]) -> dict:
    """Cột chuỗi: định dạng ngày/tiền + biểu thức đọc đúng (kèm số giá trị vẫn không đọc được);
    biến thể hoa/thường/khoảng trắng → gợi ý chuẩn hóa trước khi nối hoặc khử trùng."""
    ref, column = ref_column
    dates = _formats(texts, DATE_PATTERNS)
    hints: dict = {"date_formats": dates if DATE_NAME_RE.search(column) else [d for d in dates if d != "yyyymmdd"]}
    if any(f in MONTH_FIRST for f in hints["date_formats"]):
        hints["date_order"] = day_month_evidence(con, ref, column)
        hints["date_formats"], uncertain = resolve_day_month(hints["date_formats"], hints["date_order"])
        if uncertain:
            hints["uncertain"] = uncertain
    if MONEY_NAME_RE.search(column):
        hints["money_formats"] = _formats(texts, MONEY_PATTERNS)
    if expression := parse_expression(column, hints):
        hints["duckdb_parse"] = expression
        failed = f'SELECT count(*) FROM {ref} WHERE "{column}" IS NOT NULL AND ({expression}) IS NULL'
        hints["parse_failures"] = con.execute(failed).fetchone()[0]
    if (variants := _variants(con, ref, column)) > 0:
        hints["case_variants"] = variants
        hints["normalize"] = f'upper(trim("{column}"))'
    return hints


def _key_column(columns: dict[str, dict], rows: int) -> str:
    keys = [name for name, info in columns.items() if KEY_NAME_RE.match(name)]
    return max(keys, key=lambda k: columns[k]["distinct"], default="") if rows else (keys[0] if keys else "")


def profile_table(db: Path, table: str, columns: dict[str, str]) -> dict:
    """Hồ sơ một bảng raw."""
    with connect_read(db) as con:
        rows = con.execute(f'SELECT count(*) FROM {RAW_SCHEMA}."{table}"').fetchone()[0]
        cols = {name: _column_profile(con, table, (name, dtype)) for name, dtype in columns.items()}
    key = _key_column(cols, rows)
    return {
        "rows": rows,
        "columns": cols,
        "key_column": key,
        "duplicate_keys": rows - cols[key]["distinct"] - cols[key]["nulls"] if key else 0,
        "money_columns": [n for n in cols if MONEY_NAME_RE.search(n)],
    }


def profiler_node(state: PipelineState) -> dict:
    """Soi mọi bảng raw trong sandbox."""
    db = sandbox_db(state)
    raw = read_catalog(db).get(RAW_SCHEMA, {})
    return {"profile": {table: profile_table(db, table, columns) for table, columns in raw.items()}}

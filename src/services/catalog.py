"""Cấu trúc dữ liệu cho DE (code thuần, 0 token): bảng, schema cột, lineage và khóa nối giữa các bảng.

- Bảng nguồn trước khi chạy pipeline: xem `src/services/source_catalog.py`.
- `run_catalog`: một lần chạy — bảng raw (kiểu, % rỗng, khóa, trùng khóa) + model staging/mart sinh ra (cột, kiểu
  bằng DuckDB DESCRIBE) + lineage (bảng nào đọc bảng nào) + điều kiện JOIN thật trong SQL (sqlglot).
- `profile_relation` / `run_profile`: hồ sơ dữ liệu kiểu Power Query / Tableau Prep cho người (DE, Reviewer) — chất
  lượng từng cột (hợp lệ / lỗi / rỗng), phân bố giá trị, vấn đề phát hiện bằng luật code, vài dòng xem trước đã che
  PII. Chạy trên bảng raw lẫn staging/mart do code AI sinh, trên sandbox hoặc bộ dữ liệu thử (dirty...).
  Chỉ trả về cho giao diện: không lưu, không ghi log, không gửi LLM.
"""

import re
from pathlib import Path

import duckdb
from pydantic import BaseModel

from src.agents.nodes.profiler import MONEY_NAME_RE, SAMPLE_VALUES, text_hints
from src.agents.tools.duckdb_tools import RAW_SCHEMA, connect_read, describe_query, read_catalog
from src.agents.tools.injection_scan import scan_text
from src.agents.tools.pii import mask_value
from src.agents.tools.sql_tools import (
    SOURCE_RE,
    SqlCheckError,
    expand_models,
    inline_refs,
    join_keys,
    parse_single_select,
    referenced_tables,
    render_dbt_sql,
)


class ColumnInfo(BaseModel):
    """Một cột: tên, kiểu, % rỗng (nếu đã soi), có phải khóa không."""

    name: str
    type: str = ""
    null_pct: float | None = None
    is_key: bool = False


class TableInfo(BaseModel):
    """Một bảng trong sơ đồ."""

    id: str  # raw.<bảng> hoặc main.<model>
    name: str
    layer: str  # source | staging | mart
    columns: list[ColumnInfo]
    rows: int | None = None
    duplicate_keys: int | None = None
    file: str = ""  # đường dẫn model dbt (nếu là model sinh ra)
    group: str = ""  # hệ thống nguồn (CRM, ERP, POS...) theo systems.yml
    description: str = ""  # mô tả bảng (systems.yml)


class JoinInfo(BaseModel):
    """Quan hệ giữa hai cột của hai bảng."""

    left: str
    right: str
    how: str  # inner/left/... (JOIN thật) hoặc "gợi ý" (đoán theo tên cột)
    model: str = ""  # model chứa JOIN này
    match_pct: float | None = None  # % giá trị bên trái tìm thấy bên phải (đo bằng DuckDB; phần còn lại là mồ côi)


class LineageEdge(BaseModel):
    """`source` được đọc bởi `target`."""

    source: str
    target: str


class CatalogView(BaseModel):
    """Toàn cảnh cấu trúc dữ liệu cho màn hình DE."""

    tables: list[TableInfo]
    lineage: list[LineageEdge] = []
    joins: list[JoinInfo] = []


def _raw_table(name: str, columns: dict[str, str], profile: dict) -> TableInfo:
    stats = profile.get(name, {})
    col_stats, key = stats.get("columns", {}), stats.get("key_column", "")
    return TableInfo(
        id=f"{RAW_SCHEMA}.{name}",
        name=name,
        layer="source",
        columns=[
            ColumnInfo(name=c, type=t, null_pct=col_stats.get(c, {}).get("null_pct"), is_key=c == key)
            for c, t in columns.items()
        ],
        rows=stats.get("rows"),
        duplicate_keys=stats.get("duplicate_keys"),
    )


class ModelSql(BaseModel):
    """Một model dbt đã render (Jinja → tên bảng thật)."""

    path: str
    name: str
    sql: str


def _models(code_files: dict[str, str]) -> list[ModelSql]:
    models = []
    for path, sql in code_files.items():
        if path.startswith("models/") and path.endswith(".sql"):
            try:
                models.append(ModelSql(path=path, name=Path(path).stem, sql=render_dbt_sql(sql)))
            except SqlCheckError:
                continue  # Jinja lạ đã bị V1 chặn; không vẽ
    return models


def _model_table(model: ModelSql, db: Path, expanded: dict[str, str], grain: list[str]) -> TableInfo:
    columns = describe_query(db, inline_refs(model.sql, expanded))
    layer = "staging" if "/staging/" in model.path else "mart"
    return TableInfo(
        id=f"main.{model.name}",
        name=model.name,
        layer=layer,
        columns=[ColumnInfo(name=c, type=t, is_key=layer == "mart" and c in grain) for c, t in columns.items()],
        file=model.path,
    )


def _relations(model: ModelSql) -> tuple[list[LineageEdge], list[JoinInfo]]:
    try:
        tree = parse_single_select(model.sql)
    except SqlCheckError:
        return [], []
    target = f"main.{model.name}"
    edges = [LineageEdge(source=s, target=target) for s in referenced_tables(tree)]
    joins = [JoinInfo(left=a, right=b, how=how, model=target) for a, b, how in join_keys(tree)]
    return edges, joins


def run_catalog(values: dict) -> CatalogView:
    """Toàn cảnh một lần chạy: raw + staging + mart, lineage, JOIN thật."""
    db = Path(values["workspace"]) / "sandbox.duckdb"
    raw = read_catalog(db).get(RAW_SCHEMA, {}) if db.exists() else {}
    tables = [_raw_table(name, cols, values.get("profile", {})) for name, cols in raw.items()]
    models = _models(values.get("code_files", {}))
    expanded = expand_models({m.name: m.sql for m in models})
    grain = values.get("spec", {}).get("grain", [])
    tables += [_model_table(m, db, expanded, grain) for m in models] if db.exists() else []
    target, rows = values.get("spec", {}).get("target"), values.get("sandbox", {}).get("target_rows")
    tables = [t.model_copy(update={"rows": rows}) if t.id == f"main.{target}" else t for t in tables]
    lineage, joins = [], []
    for model in models:
        edges, pairs = _relations(model)
        lineage += edges
        joins += pairs
    return CatalogView(tables=tables, lineage=lineage, joins=joins)


# ---------- Hồ sơ dữ liệu: mỗi cột (chất lượng + phân bố), mỗi bảng (vấn đề + dòng xem trước) ----------

NUMBER_TYPES = re.compile(
    r"^(BIGINT|INTEGER|HUGEINT|SMALLINT|TINYINT|UBIGINT|UINTEGER|DOUBLE|FLOAT|REAL|DECIMAL)", re.I
)
DATE_TYPES = re.compile(r"^(DATE|TIMESTAMP)", re.I)
PREVIEW_ROWS = 50
TOP_VALUES = 6
BINS = 12
NEAR_UNIQUE = 0.9  # khác nhau / có giá trị ≥ mức này (và nhiều giá trị) → không liệt kê giá trị hay gặp
NULL_WARN_PCT = 20.0
# Nhóm "không rõ" chứa giá trị lạ (mục 9, quy tắc 10 của prompt Codegen) và các tên hay gặp khác của nó
UNKNOWN_BUCKETS = ("khong_ro", "other", "unknown")


class ValueCount(BaseModel):
    """Một cột trong biểu đồ phân bố: nhãn (giá trị hoặc đầu khoảng) và số dòng."""

    label: str
    count: int


class ColumnProfile(BaseModel):
    """Hồ sơ một cột. Hợp lệ = có giá trị − chuỗi rỗng − không đọc được."""

    name: str
    type: str
    kind: str  # number | date | text | bool | nested (STRUCT/LIST/JSON)
    is_key: bool = False
    filled: int = 0
    nulls: int = 0
    blank: int = 0  # chuỗi rỗng / toàn khoảng trắng
    invalid: int = 0  # chuỗi dạng ngày/tiền mà biểu thức đọc của bộ soi P không đọc được
    case_variants: int = 0  # số giá trị chỉ khác hoa/thường/khoảng trắng
    formats: list[str] = []  # cách viết ngày/tiền phát hiện được trong cột chuỗi
    uncertain: list[str] = []  # điều bộ soi P không chứng minh được từ dữ liệu (vd thứ tự ngày/tháng)
    distinct: int = 0
    minimum: str | None = None
    maximum: str | None = None
    mean: float | None = None
    zeros: int = 0  # số dòng bằng 0 (cột số)
    top: list[ValueCount] = []  # giá trị hay gặp (đã che PII)
    other: int = 0  # số dòng còn lại ngoài `top`
    bins: list[ValueCount] = []  # phân bố số / ngày theo khoảng đều
    near_unique: bool = False
    flags: list[str] = []  # dấu hiệu prompt injection / bí mật trong giá trị mẫu (chỉ cảnh báo)


class ProfileIssue(BaseModel):
    """Vấn đề phát hiện bằng luật code (không để LLM chấm)."""

    level: str  # fail | warn | info
    column: str = ""
    text: str


class TableProfile(BaseModel):
    """Hồ sơ một bảng cho màn "Hồ sơ dữ liệu"."""

    id: str = ""
    name: str = ""
    layer: str = ""
    rows: int
    columns: list[ColumnProfile]
    preview: list[list[str | None]]  # mỗi dòng theo đúng thứ tự `columns`
    issues: list[ProfileIssue] = []
    duplicate_keys: int | None = None
    keys: list[str] = []
    rows_in: int | None = None  # staging: số dòng bảng nguồn (đối chiếu vào → ra, mục 9)
    dataset: str = "sandbox"
    datasets: list[str] = []
    file: str = ""


def _kind(dtype: str) -> str:
    if NUMBER_TYPES.match(dtype):
        return "number"
    if DATE_TYPES.match(dtype):
        return "date"
    if dtype.upper() == "BOOLEAN":
        return "bool"
    return "text" if dtype.upper() == "VARCHAR" else "nested"


def _shown(value: object) -> str | None:
    return None if value is None else str(mask_value(str(value)))


def _top(con: duckdb.DuckDBPyConnection, ref: str, col: str, column: ColumnProfile) -> None:
    rows = con.execute(
        f"SELECT CAST({col} AS VARCHAR), count(*) FROM {ref} WHERE {col} IS NOT NULL "
        f"GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT {TOP_VALUES}"
    ).fetchall()
    column.top = [ValueCount(label=_shown(v) or "", count=n) for v, n in rows]
    column.other = column.filled - sum(n for _, n in rows)


def _bins(con: duckdb.DuckDBPyConnection, ref: str, value: str, column: ColumnProfile) -> None:
    """Chia [min, max] thành BINS khoảng đều; `value` là biểu thức số (ngày → epoch giây)."""
    low, high = con.execute(f"SELECT min({value}), max({value}) FROM {ref}").fetchone()
    if low is None or high is None or low == high:
        return
    width = (high - low) / BINS
    counts = dict(
        con.execute(
            f"SELECT least(CAST(floor(({value} - {low}) / {width}) AS INTEGER), {BINS - 1}), count(*) "
            f"FROM {ref} WHERE {value} IS NOT NULL GROUP BY 1"
        ).fetchall()
    )
    starts = [low + i * width for i in range(BINS)]
    if column.kind == "date":
        labels = [str(con.execute("SELECT to_timestamp(?)::date", [s]).fetchone()[0]) for s in starts]
    else:
        labels = [f"{s:,.6g}" for s in starts]
    column.bins = [ValueCount(label=label, count=counts.get(i, 0)) for i, label in enumerate(labels)]


def _column(con: duckdb.DuckDBPyConnection, ref: str, name_type: tuple[str, str]) -> ColumnProfile:
    name, dtype = name_type
    col = f'"{name}"'
    column = ColumnProfile(name=name, type=dtype, kind=_kind(dtype))
    total, column.filled, column.distinct = con.execute(
        f"SELECT count(*), count({col}), count(DISTINCT {col}) FROM {ref}"
    ).fetchone()
    column.nulls = total - column.filled
    column.near_unique = column.distinct > BINS and column.distinct >= NEAR_UNIQUE * max(column.filled, 1)
    if column.kind in ("number", "date"):
        low, high, mean = con.execute(
            f"SELECT min({col}), max({col}), {'avg(' + col + ')' if column.kind == 'number' else 'NULL'} FROM {ref}"
        ).fetchone()
        column.minimum, column.maximum = _shown(low), _shown(high)
        column.mean = None if mean is None else round(float(mean), 4)
        if column.kind == "number":
            column.zeros = con.execute(f"SELECT count(*) FROM {ref} WHERE {col} = 0").fetchone()[0]
        if column.distinct > BINS:  # ít giá trị (cờ 0/1, số lượng 1..6) → đếm từng giá trị thay vì chia khoảng
            _bins(con, ref, f"epoch({col})" if column.kind == "date" else f"CAST({col} AS DOUBLE)", column)
    if column.kind == "text":
        column.blank = con.execute(f"SELECT count(*) FROM {ref} WHERE trim({col}) = ''").fetchone()[0]
        sample = f"SELECT DISTINCT {col} FROM {ref} WHERE {col} IS NOT NULL LIMIT {SAMPLE_VALUES}"
        values = [str(r[0]) for r in con.execute(sample).fetchall()]
        hints = text_hints(con, (ref, name), values)
        column.flags = scan_text(*values)
        column.invalid, column.case_variants = hints.get("parse_failures", 0), hints.get("case_variants", 0)
        column.formats = hints.get("date_formats", []) + hints.get("money_formats", [])
        column.uncertain = hints.get("uncertain", [])
    _top(con, ref, col, column)
    if (column.near_unique or column.bins) and not _placeholder(column, total):
        column.top, column.other = [], 0  # dạng mã / đã có biểu đồ khoảng: chỉ giữ khi lộ giá trị giữ chỗ
    return column


def _placeholder(column: ColumnProfile, rows: int) -> ValueCount | None:
    """Một giá trị lặp lại bất thường trong cột nhiều giá trị (vd ngày sinh 1900-01-01, SKU-999999): giá trị giữ chỗ?"""
    if column.distinct <= 3 * BINS or len(column.top) < 2:
        return None
    first, second = column.top[0], column.top[1]
    return first if first.count >= 4 * max(second.count, 1) and first.count >= 0.005 * rows else None


def _duplicates(con: duckdb.DuckDBPyConnection, ref: str, keys: list[str]) -> int:
    """Số dòng thừa theo khóa / grain (dòng thứ 2 trở đi của mỗi nhóm trùng)."""
    group = ", ".join(f'"{k}"' for k in keys)
    sql = f"SELECT coalesce(sum(n - 1), 0) FROM (SELECT count(*) n FROM {ref} GROUP BY {group} HAVING n > 1)"
    return int(con.execute(sql).fetchone()[0])


def _column_issues(column: ColumnProfile, rows: int) -> list[ProfileIssue]:
    name = column.name
    if rows and not column.filled:
        return [ProfileIssue(level="fail", column=name, text="Toàn bộ cột rỗng (NULL).")]
    out = []
    if rows and (pct := round(100 * column.nulls / rows, 1)) >= NULL_WARN_PCT:
        out.append(ProfileIssue(level="warn", column=name, text=f"{pct}% dòng rỗng (NULL)."))
    if column.invalid:
        text = f"{column.invalid} giá trị không đọc được thành ngày/số tiền."
        out.append(ProfileIssue(level="fail", column=name, text=text))
    if column.blank:
        out.append(ProfileIssue(level="warn", column=name, text=f"{column.blank} ô là chuỗi rỗng '' (khác NULL)."))
    if column.case_variants:
        text = f"{column.case_variants} giá trị chỉ khác hoa/thường/khoảng trắng — nên chuẩn hóa upper(trim(...))."
        out.append(ProfileIssue(level="warn", column=name, text=text))
    out += [ProfileIssue(level="warn", column=name, text=note) for note in column.uncertain]
    if len(column.formats) > 1:
        text = f"Lẫn {len(column.formats)} cách viết: {', '.join(column.formats)} — đã có biểu thức đọc từ bộ soi P."
        out.append(ProfileIssue(level="info", column=name, text=text))
    if odd := _placeholder(column, rows):
        text = (
            f"Giá trị '{odd.label}' lặp {odd.count} lần, nhiều bất thường — có thể là giá trị giữ chỗ (thiếu dữ liệu)."
        )
        out.append(ProfileIssue(level="warn", column=name, text=text))
    money = column.kind == "number" and MONEY_NAME_RE.search(name)
    if money and (column.minimum or "").startswith("-"):
        out.append(ProfileIssue(level="info", column=name, text=f"Có số tiền âm (nhỏ nhất {column.minimum})."))
    if money and column.zeros:
        text = f"{column.zeros} dòng có số tiền bằng 0 — xem là hàng tặng, lỗi nhập hay thiếu dữ liệu."
        out.append(ProfileIssue(level="warn", column=name, text=text))
    if column.flags:
        text = (
            f"Giá trị mẫu đáng ngờ ({', '.join(column.flags)}): có thể là lệnh cài vào dữ liệu để điều khiển agent "
            "(prompt injection) hoặc bí mật bị lộ. Kiểm tra nguồn trước khi chạy."
        )
        out.append(ProfileIssue(level="warn", column=name, text=text))
    for bucket in (v for v in column.top if v.label in UNKNOWN_BUCKETS):
        text = (
            f"{bucket.count} dòng vào nhóm '{bucket.label}' (giá trị lạ / không rõ) — xem có cần bổ sung giá trị "
            "vào đặc tả."
        )
        out.append(ProfileIssue(level="info", column=name, text=text))
    return out


def profile_relation(db: Path, ref: str, keys: list[str] | None = None) -> TableProfile:
    """Đo hồ sơ của `ref` (bảng, hoặc `(SELECT ...) AS q`) qua kết nối chỉ-đọc; `keys` = khóa/grain để đếm trùng."""
    with connect_read(db) as con:
        described = con.execute(f"DESCRIBE SELECT * FROM {ref}").fetchall()
        rows = con.execute(f"SELECT count(*) FROM {ref}").fetchone()[0]
        columns = [_column(con, ref, (r[0], str(r[1]))) for r in described]
        preview = con.execute(f"SELECT * FROM {ref} LIMIT {PREVIEW_ROWS}").fetchall()
        keys = [k for k in keys or [] if k in {c.name for c in columns}]
        duplicates = _duplicates(con, ref, keys) if keys else None
    for column in columns:
        column.is_key = column.name in keys
    issues = [issue for column in columns for issue in _column_issues(column, rows)]
    if duplicates:
        issues.insert(0, ProfileIssue(level="fail", text=f"{duplicates} dòng trùng khóa ({', '.join(keys)})."))
    if rows == 0:
        issues.insert(0, ProfileIssue(level="warn", text="Bảng không có dòng nào."))
    return TableProfile(
        rows=rows,
        columns=columns,
        preview=[[_shown(v) for v in row] for row in preview],
        issues=issues,
        duplicate_keys=duplicates,
        keys=keys,
    )


def _rows_in(db: Path, sql: str) -> int | None:
    """Staging đọc đúng một bảng nguồn → số dòng nguồn để đối chiếu vào/ra."""
    sources = {m.group(2) for m in SOURCE_RE.finditer(sql)}
    if len(sources) != 1:
        return None
    with connect_read(db) as con:
        return con.execute(f'SELECT count(*) FROM {RAW_SCHEMA}."{sources.pop()}"').fetchone()[0]


def profile_datasets(values: dict) -> dict[str, Path]:
    """Nơi có thể soi: sandbox (dữ liệu nguồn) + các bộ dữ liệu thử của E2 (bỏ `large`: chỉ để đo tốc độ)."""
    found = {"sandbox": Path(values["workspace"]) / "sandbox.duckdb"}
    found |= {n: Path(p) for n, p in values.get("datasets", {}).items() if n != "large" and Path(p).exists()}
    return found


def run_profile(values: dict, table_id: str, dataset: str = "sandbox") -> TableProfile:
    """Hồ sơ một bảng của lần chạy: raw, hoặc model staging/mart do code AI sinh (chạy SQL đã nhúng ref).

    KeyError nếu không có bảng / bộ dữ liệu này.
    """
    datasets = profile_datasets(values)
    db = datasets[dataset]
    schema, _, name = table_id.partition(".")
    meta: dict = {"id": table_id, "name": name, "dataset": dataset, "datasets": list(datasets)}
    if schema == RAW_SCHEMA:
        if name not in read_catalog(db).get(RAW_SCHEMA, {}):
            raise KeyError(table_id)
        key = values.get("profile", {}).get(name, {}).get("key_column", "")
        result = profile_relation(db, f'{RAW_SCHEMA}."{name}"', [key] if key else [])
        return result.model_copy(update={**meta, "layer": "source"})
    models = {m.name: m for m in _models(values.get("code_files", {}))}
    if schema != "main" or name not in models:
        raise KeyError(table_id)
    model = models[name]
    sql = inline_refs(model.sql, expand_models({m.name: m.sql for m in models.values()}))
    layer = "staging" if "/staging/" in model.path else "mart"
    grain = values.get("spec", {}).get("grain", []) if layer == "mart" else []
    result = profile_relation(db, f"({sql}) AS q", grain)
    update = {**meta, "layer": layer, "file": model.path}
    rows_in = _rows_in(db, values.get("code_files", {}).get(model.path, "")) if layer == "staging" else None
    if rows_in is not None:
        update["rows_in"] = rows_in
        if rows_in != result.rows:
            change = "mất" if result.rows < rows_in else "thêm"
            text = (
                f"Đối chiếu số dòng: vào {rows_in}, ra {result.rows} ({change} {abs(rows_in - result.rows)} dòng) — "
                "cần lý do ghi rõ (khử trùng, lọc theo đặc tả), không được loại dòng im lặng."
            )
            result.issues.insert(0, ProfileIssue(level="warn", text=text))
    return result.model_copy(update=update)

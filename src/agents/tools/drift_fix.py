"""Sửa tất định SQL dbt khi nguồn đổi cấu trúc (bản vá nhanh, 0 token, không LLM).

Hai phép sửa, đều làm trên cây cú pháp sqlglot chứ không thay chuỗi:
- `rename`: cột nguồn đổi tên → mọi tham chiếu tới cột đó (trong các câu SELECT đọc đúng bảng nguồn) đổi theo; cột nằm thẳng ở danh sách
  chọn được đặt bí danh bằng tên CŨ (`ordered_at AS order_date`) để model phía sau và bảng đích không phải đổi gì. Đây là nguyên tắc
  "lớp staging là lớp đệm": mọi biến động của nguồn được hấp thụ ở một chỗ.
- `cast`: kiểu cột nguồn đổi → ép về kiểu cũ ngay ở staging (`try_cast(col AS <kiểu cũ>)`), phần còn lại của pipeline vẫn thấy kiểu cũ.

Kết quả không được tin: sau khi sửa, V1 (đúng tên bảng/cột, biên dịch thử) và V2 (dbt build + test) chạy lại như mọi bản code khác.
Không sửa được an toàn (Jinja lạ, lỗi cú pháp, không có gì để đổi) thì trả `None` để bên gọi chuyển cho AI hoặc người.
"""

import re

from sqlglot import exp

from src.agents.tools.sql_tools import (
    CONFIG_RE,
    DIALECT,
    JINJA_COMMENT_RE,
    REF_RE,
    SOURCE_RE,
    SqlCheckError,
    parse_single_select,
)
from src.models.drift import FixStep

# Kiểu chuẩn hóa (connectors.base.normalize_type) → kiểu SQL DuckDB dùng khi ép về kiểu cũ. Kiểu "other" không có: bản vá chuyển cho AI.
SQL_TYPES = {
    "integer": "BIGINT",
    "decimal": "DECIMAL(38,10)",
    "float": "DOUBLE",
    "string": "VARCHAR",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
    "json": "JSON",
}


def reads_table(sql: str, table: str) -> bool:
    """File dbt có đọc thẳng bảng nguồn `table` qua `source()` không."""
    return any(m.group(2) == table for m in SOURCE_RE.finditer(sql))


def uses_column(sql: str, column: str) -> bool:
    return bool(column) and re.search(rf"\b{re.escape(column)}\b", sql, re.IGNORECASE) is not None


def files_to_fix(files: dict[str, str], table: str, column: str) -> list[str]:
    """File SQL staging/test đọc thẳng bảng nguồn và có nhắc tới cột (model mart đọc gián tiếp qua `ref` nên không cần sửa)."""
    return sorted(
        path
        for path, sql in files.items()
        if path.endswith(".sql")
        and not path.endswith("_castable.sql")  # test ép kiểu do Testgen dựng lại theo hồ sơ mới, không cần vá
        and path.startswith(("models/staging/", "tests/"))
        and reads_table(sql, table)
        and uses_column(sql, column)
    )


def _identifier(name: str, like: exp.Expression) -> exp.Identifier:
    quoted = like.this.quoted if isinstance(like.this, exp.Identifier) else None
    return exp.to_identifier(name, quoted=quoted)


def _matching_columns(select: exp.Select, table: str, name: str) -> list[exp.Column]:
    """Cột `name` trong ĐÚNG câu SELECT này (không tính câu con) và thuộc bảng nguồn `table`: có tiền tố bí danh của bảng, hoặc không có
    tiền tố khi câu SELECT chỉ đọc một bảng (nhiều bảng mà không tiền tố thì không đoán được cột thuộc bảng nào: bỏ qua)."""
    tables = [t for t in select.find_all(exp.Table) if t.find_ancestor(exp.Select) is select]
    aliases = {t.alias or t.name for t in tables if t.name == table}
    if not aliases:
        return []
    found = []
    for column in select.find_all(exp.Column):
        if column.find_ancestor(exp.Select) is not select or column.name != name:
            continue
        if (column.table and column.table in aliases) or (not column.table and len(tables) == 1):
            found.append(column)
    return found


def _is_projection(column: exp.Column, select: exp.Select) -> bool:
    return column.parent is select and column.arg_key == "expressions"


def _rename(tree: exp.Expression, table: str, step: FixStep) -> None:
    for select in list(tree.find_all(exp.Select)):
        for column in _matching_columns(select, table, step.old):
            renamed = column.copy()
            renamed.set("this", _identifier(step.new, column))
            if _is_projection(column, select):
                column.replace(exp.alias_(renamed, step.old, quoted=column.this.quoted))  # giữ tên cột đầu ra
            else:
                column.replace(renamed)


def _cast(tree: exp.Expression, table: str, step: FixStep) -> None:
    data_type = exp.DataType.build(step.sql_type, dialect=DIALECT)
    for select in list(tree.find_all(exp.Select)):
        for column in _matching_columns(select, table, step.column):
            parent = column.parent
            if isinstance(parent, exp.Cast | exp.TryCast) and parent.args.get("to") == data_type:
                continue  # đã ép đúng kiểu này
            wrapped = exp.TryCast(this=column.copy(), to=data_type.copy())
            if _is_projection(column, select):
                column.replace(exp.alias_(wrapped, step.column, quoted=column.this.quoted))
            else:
                column.replace(wrapped)


def rewrite(sql: str, table: str, steps: list[FixStep]) -> tuple[str, bool] | None:
    """(SQL dbt sau khi áp lần lượt các bước, có đổi gì không), hoặc None nếu không sửa được an toàn (Jinja lạ, lỗi cú pháp).
    Giữ nguyên `config()`; `source()`/`ref()` được trả lại. "Không đổi gì" khi cột đã được ép đúng kiểu sẵn, hoặc không tìm thấy tham chiếu."""
    config = "".join(m.group(0) + "\n" for m in CONFIG_RE.finditer(sql))
    body = CONFIG_RE.sub("", JINJA_COMMENT_RE.sub("", sql))
    sources = {(m.group(1), m.group(2)) for m in SOURCE_RE.finditer(body)}
    refs = set(REF_RE.findall(body))
    text = SOURCE_RE.sub(lambda m: f"{m.group(1)}.{m.group(2)}", body)
    text = REF_RE.sub(lambda m: f"main.{m.group(1)}", text)
    if "{{" in text or "{%" in text:
        return None
    try:
        tree = parse_single_select(text.strip().rstrip(";"))
    except SqlCheckError:
        return None
    before = tree.sql(dialect=DIALECT)
    for step in steps:
        if step.kind == "rename":
            _rename(tree, table, step)
        else:
            _cast(tree, table, step)
    if tree.sql(dialect=DIALECT) == before:
        return sql, False
    out = tree.sql(dialect=DIALECT, pretty=True)
    for schema, name in sources:
        pattern = rf'\b{re.escape(schema)}\.(?:"{re.escape(name)}"|{re.escape(name)}(?!\w))'
        out = re.sub(pattern, lambda _m, s=schema, n=name: f"{{{{ source('{s}', '{n}') }}}}", out)
    for name in refs:
        pattern = rf'\bmain\.(?:"{re.escape(name)}"|{re.escape(name)}(?!\w))'
        out = re.sub(pattern, lambda _m, n=name: f"{{{{ ref('{n}') }}}}", out)
    return f"{config}{out}\n", True

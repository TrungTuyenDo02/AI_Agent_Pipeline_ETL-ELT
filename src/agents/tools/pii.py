"""Che thông tin cá nhân (email, số điện thoại) trước khi đưa mẫu dữ liệu cho LLM hoặc hiển thị."""

import re

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_RE = re.compile(r"(?<!\d)(\+?84|0)(\d{2})\d{4,6}(\d{2})(?!\d)")
# Số điện thoại có dấu ngăn (0320.958027, 091 234 5678, 0912-345-678): bỏ dấu rồi che như trên
SPLIT_PHONE_RE = re.compile(r"(?<![\w.*])(\+?84|0)[ .-]?\d(?:[ .-]?\d){7,9}(?![\w*])")


def _mask_split_phone(match: re.Match) -> str:
    digits = re.sub(r"\D", "", match.group())
    head = len(match.group(1).lstrip("+")) + 2
    return f"{'+' if match.group().startswith('+') else ''}{digits[:head]}******{digits[-2:]}"


def mask_text(value: str) -> str:
    """Che email thành `a***@domain` và số điện thoại thành `09******12` (cả khi viết có dấu chấm/cách/gạch)."""
    masked = EMAIL_RE.sub(r"\1***@\2", value)
    masked = PHONE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}******{m.group(3)}", masked)
    return SPLIT_PHONE_RE.sub(_mask_split_phone, masked)


def mask_value(value: object) -> object:
    """Che giá trị nếu là chuỗi; kiểu khác giữ nguyên."""
    return mask_text(value) if isinstance(value, str) else value


def mask_rows(rows: list[dict]) -> list[dict]:
    """Che mọi ô chuỗi trong danh sách dòng."""
    return [{key: mask_value(val) for key, val in row.items()} for row in rows]


QUOTED_RE = re.compile(r"'((?:[^'\n]|'')*)'")
SQL_ECHO_RE = re.compile(r"^\s*LINE \d+:")  # DuckDB in lại câu SQL (code do LLM viết, không phải dữ liệu)
SHAPE_LIMIT = 40


def value_shape(value: str) -> str:
    """Hình dạng giá trị: chữ số → 9, chữ cái → a/A, giữ dấu câu ('25/13/2026' → '99/99/9999')."""
    shape = re.sub(r"\d", "9", value)
    shape = re.sub(r"[^\W\d_]", lambda m: "A" if m.group().isupper() else "a", shape)
    return shape[:SHAPE_LIMIT] + ("…" if len(shape) > SHAPE_LIMIT else "")


def mask_literals(text: str) -> str:
    """Thông báo lỗi gửi LLM (CLAUDE.md 2.3): giá trị trong nháy đơn chỉ còn hình dạng.

    Giữ nguyên dòng DuckDB in lại câu SQL và chuỗi định dạng có `%` (vd '%d/%m/%Y') vì đó là code, không phải dữ liệu.
    """

    def _line(line: str) -> str:
        if SQL_ECHO_RE.match(line):
            return line
        return QUOTED_RE.sub(lambda m: m.group(0) if "%" in m.group(1) else f"'{value_shape(m.group(1))}'", line)

    return "\n".join(_line(line) for line in text.splitlines())

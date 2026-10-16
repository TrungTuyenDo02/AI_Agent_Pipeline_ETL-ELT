"""Làm sạch thông báo lỗi TRƯỚC khi đưa vào prompt (CLAUDE.md bản 2, mục 0.5 và 3.4).

Lỗi từ dbt/DuckDB/Postgres hay in lại giá trị dữ liệu thật ("không ép được chuỗi 'abc@x.com' sang số"). `scrub_error` thay
các giá trị đó bằng `<đã che>`, GIỮ tên cột/bảng và loại lỗi để LLM vẫn sửa được code. Mọi chỗ đưa lỗi vào prompt (vòng sửa
lỗi, cứu hộ, test, optimizer, ghi chú lỗi) phải đi qua `prompt_error()`; bản lỗi gốc chỉ hiển thị cho người có quyền xem.
"""

import re

from src.agents.tools.pii import EMAIL_RE, PHONE_RE, SPLIT_PHONE_RE

MASK = "<đã che>"
SQL_ECHO_RE = re.compile(r"^\s*LINE \d+:")  # DuckDB in lại câu SQL (code do LLM viết, không phải dữ liệu)
MAX_ERROR_CHARS = 1500

# Đường dẫn tuyệt đối chứa tên người dùng: giữ phần còn lại của đường dẫn (vị trí file vẫn hữu ích khi sửa lỗi)
USER_PATH_RE = re.compile(r"((?:[A-Za-z]:[\\/]+Users[\\/]+)|(?:/home/)|(?:/Users/))([^\\/\s'\"]+)", re.IGNORECASE)
# Postgres: `Key (email)=(a@b.com) already exists.`, `Failing row contains (1, abc, ...)`
PG_KEY_RE = re.compile(r"(Key \([^)]*\)=)\((.*?)\)(?= |\.|$)", re.IGNORECASE)
PG_ROW_RE = re.compile(r"(Failing row contains )\((.*)\)", re.IGNORECASE)
# Giá trị đi sau cụm báo lỗi kiểu ép kiểu/phân tích (dấu nháy đơn hoặc kép): "...for type integer: "abc"", "Could not convert string 'x'"
VALUE_AFTER_RE = re.compile(
    r"(?i)((?:(?:convert|cast|parse|invalid input syntax|invalid value|invalid date|invalid timestamp|out of range)"
    r"[^'\"\n]{0,60}?|(?:string|value|literal|input|text|number)\s+))(['\"])((?:(?!\2).)*)\2"
)
QUOTED_RE = re.compile(r"'((?:[^'\n]|'')*)'")
MONEY_RE = re.compile(r"(?<![\w.])\d{1,3}(?:[.,]\d{3})+(?![\w])")
LONG_NUMBER_RE = re.compile(r"(?<![\w.])\d{6,}(?![\w])")


def _mask_value_after(match: re.Match) -> str:
    quote = match.group(2) if "%" not in match.group(3) else None
    if quote is None:  # chuỗi định dạng như '%d/%m/%Y' là code, không phải dữ liệu
        return match.group(0)
    return f"{match.group(1)}{MASK}"


def _mask_quoted(match: re.Match) -> str:
    return match.group(0) if "%" in match.group(1) else MASK


def _scrub_line(line: str) -> str:
    if SQL_ECHO_RE.match(line):
        return line
    line = USER_PATH_RE.sub(lambda m: f"{m.group(1)}{MASK}", line)
    line = PG_KEY_RE.sub(lambda m: f"{m.group(1)}({MASK})", line)
    line = PG_ROW_RE.sub(lambda m: f"{m.group(1)}({MASK})", line)
    line = VALUE_AFTER_RE.sub(_mask_value_after, line)
    line = QUOTED_RE.sub(_mask_quoted, line)
    line = EMAIL_RE.sub(MASK, line)
    line = SPLIT_PHONE_RE.sub(MASK, PHONE_RE.sub(MASK, line))
    line = MONEY_RE.sub(MASK, line)
    return LONG_NUMBER_RE.sub(MASK, line)


def scrub_error(text: str) -> str:
    """Thay giá trị dữ liệu trong thông báo lỗi bằng `<đã che>` (chuỗi trong dấu nháy, email, số điện thoại, số dài, tiền,
    `Key (cột)=(giá trị)` của Postgres, tên người dùng trong đường dẫn). Câu SQL do DuckDB in lại (dòng `LINE n:`) và chuỗi định
    dạng có `%` được giữ nguyên vì là code."""
    return "\n".join(_scrub_line(line) for line in str(text or "").splitlines())


def prompt_error(text: str, limit: int = MAX_ERROR_CHARS) -> str:
    """Cửa DUY NHẤT đưa thông báo lỗi vào prompt: đã làm sạch và cắt gọn."""
    return scrub_error(text)[:limit]

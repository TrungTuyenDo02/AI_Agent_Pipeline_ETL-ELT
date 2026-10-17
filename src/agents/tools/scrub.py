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
DATE_RE = re.compile(r"(?<![\w/.-])\d{1,4}[/-]\d{1,2}[/-]\d{1,4}(?![\w/-])")
TIME_RE = re.compile(r"(?<![\w:])\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?![\w:])")
# Nháy kép: tên định danh (cột, bảng, ràng buộc) giữ nguyên; có khoảng trắng, dấu hai chấm, chữ có dấu... là giá trị (`Duplicate key "id: 4521"`)
DOUBLE_QUOTED_RE = re.compile(r'"([^"\n]*)"')
IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*(?:\.[A-Za-z_][A-Za-z0-9_$]*)*")
ROW_VALUES_RE = re.compile(r"(?i)(\brow\s*:\s*)\S.*$")  # `row: Tran Thi B, 4521`: phần sau là giá trị của dòng
# Giá trị KHÔNG có nháy sau cụm báo lỗi: "convert string Nguyen Van A to INT32", "duplicate key 4521 violates", "value 875 exceeds"
_NOT_VALUE = (
    r"to|is|in|for|of|as|the|a|an|not|cannot|can't|must|out|value|violates|exceeds|was|has|at|on|from|with|and|or|"
    r"constraint|column|columns|field|type|should|already|exists"
)
UNQUOTED_VALUE_RE = re.compile(
    rf"(?i)\b((?:convert|parse|cast)\s+(?:string|date|timestamp|time|value)|value|literal|key)\s+(?!(?:{_NOT_VALUE})\b)"
    r"([^\s'\"(<][^,;\n]{0,80}?)"
    r"(?=\s+(?:to|is|in|for|cannot|can't|could|violates|exceeds|according|when|as|was|does|did|has)\b|[,;]|\s*$)"
)
SHORT_NUMBER_RE = re.compile(r"(?<![\w.:/-])\d{3,}(?![\w.:/-])")
# Số đứng cạnh các từ này là vị trí/số đếm (cấu trúc), không phải giá trị dữ liệu
COUNT_BEFORE = frozenset(
    "line row rows col column position pos char character offset byte index version got attempt step page dòng cột lần".split()
)
COUNT_AFTER = frozenset(
    "results result rows row records errors error failures tests models columns bytes ms s seconds giây dòng lần".split()
)


def _mask_value_after(match: re.Match) -> str:
    quote = match.group(2) if "%" not in match.group(3) else None
    if quote is None:  # chuỗi định dạng như '%d/%m/%Y' là code, không phải dữ liệu
        return match.group(0)
    return f"{match.group(1)}{MASK}"


def _mask_quoted(match: re.Match) -> str:
    return match.group(0) if "%" in match.group(1) else MASK


def _mask_double_quoted(match: re.Match) -> str:
    value = match.group(1)
    return match.group(0) if IDENTIFIER_RE.fullmatch(value) or "%" in value else MASK


def _mask_short_numbers(line: str) -> str:
    """Số từ 3 chữ số (mã, số tiền nhỏ) là giá trị, trừ khi đứng cạnh từ chỉ vị trí/số đếm (`line 120`, `Got 1532 results`)."""

    def replace(match: re.Match) -> str:
        before = re.findall(r"[^\W\d]+", line[: match.start()])
        after = re.match(r"\s*([^\W\d]+)", line[match.end() :])
        if (before and before[-1].lower() in COUNT_BEFORE) or (after and after.group(1).lower() in COUNT_AFTER):
            return match.group(0)
        return MASK

    return SHORT_NUMBER_RE.sub(replace, line)


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
    line = LONG_NUMBER_RE.sub(MASK, line)
    line = DATE_RE.sub(MASK, TIME_RE.sub(MASK, line))
    line = DOUBLE_QUOTED_RE.sub(_mask_double_quoted, line)
    line = ROW_VALUES_RE.sub(lambda m: f"{m.group(1)}{MASK}", line)
    line = UNQUOTED_VALUE_RE.sub(lambda m: f"{m.group(1)} {MASK}", line)
    return _mask_short_numbers(line)


def scrub_error(text: str) -> str:
    """Thay giá trị dữ liệu trong thông báo lỗi bằng `<đã che>`: chuỗi trong nháy đơn, nháy kép không phải tên định danh, giá trị
    không nháy sau `convert string`/`value`/`key`, phần sau `row:`, email, số điện thoại, tiền, ngày giờ, số từ 3 chữ số (trừ số
    dòng/vị trí/số đếm), `Key (cột)=(giá trị)` của Postgres, tên người dùng trong đường dẫn. Câu SQL do DuckDB in lại (dòng
    `LINE n:`), tên cột/bảng và chuỗi định dạng có `%` được giữ nguyên vì là code. Vẫn là luật theo mẫu: thông báo lỗi kiểu lạ
    có thể lọt, nên bộ test giữ một kho thông báo lỗi mẫu (`tests/test_scrub.py`)."""
    return "\n".join(_scrub_line(line) for line in str(text or "").splitlines())


def prompt_error(text: str, limit: int = MAX_ERROR_CHARS) -> str:
    """Cửa DUY NHẤT đưa thông báo lỗi vào prompt: đã làm sạch và cắt gọn."""
    return scrub_error(text)[:limit]

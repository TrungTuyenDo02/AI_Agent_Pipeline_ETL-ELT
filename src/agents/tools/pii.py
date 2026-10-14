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


SHAPE_LIMIT = 40


def value_shape(value: str) -> str:
    """Hình dạng giá trị: chữ số → 9, chữ cái → a/A, giữ dấu câu ('25/13/2026' → '99/99/9999')."""
    shape = re.sub(r"\d", "9", value)
    shape = re.sub(r"[^\W\d_]", lambda m: "A" if m.group().isupper() else "a", shape)
    return shape[:SHAPE_LIMIT] + ("…" if len(shape) > SHAPE_LIMIT else "")


SENSITIVE_NAME_RE = re.compile(
    r"(e?mail|phone|sdt|dien_?thoai|mobile|\btel\b|address|dia_?chi|full_?name|first_?name|last_?name|"
    r"(customer|client|user|person|employee|staff|contact|owner|recipient|receiver|buyer|member)_?name|ho_?ten|^name$|"
    r"cccd|cmnd|passport|national_?id|\bssn\b|tax_?(code|id)|\bmst\b|birth|\bdob\b|ngay_?sinh|password|passwd|"
    r"secret|token|card_?(no|num)|account_?(no|num)|iban|salary|\bluong\b|income|ip_?addr)",
    re.IGNORECASE,
)


def sensitive_column(name: str, restricted: tuple[str, ...] | list[str] = ()) -> bool:
    """Cột nhạy cảm: tên gợi ý thông tin cá nhân (email, số điện thoại, họ tên, địa chỉ, ...) hoặc admin đánh dấu thêm
    (`restricted`: `cột` hoặc `bảng.cột`). Chỉ xét TÊN; việc dò giá trị nằm ở `looks_like_pii`."""
    column = name.rsplit(".", 1)[-1].lower()
    marked = {r.lower() for r in restricted}
    return bool(SENSITIVE_NAME_RE.search(column)) or column in marked or name.lower() in marked


def looks_like_pii(value: object) -> bool:
    """Giá trị có dạng email hoặc số điện thoại."""
    text = str(value)
    return bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or SPLIT_PHONE_RE.search(text))

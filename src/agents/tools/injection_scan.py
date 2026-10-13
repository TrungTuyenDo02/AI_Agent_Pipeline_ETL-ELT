"""Quét văn bản có dấu hiệu prompt injection hoặc bí mật (code thuần, 0 token) — CHỈ CẢNH BÁO, không chặn.

Dùng cho chữ sẽ tới tay LLM mà không do người dùng gõ trực tiếp: giá trị trong dữ liệu nguồn, mục sổ lỗi chờ duyệt.
Đây là lớp phụ dựa trên từ khóa (dễ né, có thể báo nhầm). Chốt chặn thật vẫn là: thẻ <data> không thể bị đóng sớm
(`llm.neutralize_data_tags`), V1 kiểm code sinh ra, và người duyệt.
"""

import re
import unicodedata

# Ký tự vô hình (zero-width, BOM, soft hyphen) hay dùng để chèn giữa chữ cho né bộ lọc từ khóa
INVISIBLE_RE = re.compile("[\u00ad\u200b-\u200f\u2060-\u2064\ufeff]")

INJECTION_PATTERNS = [
    (r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}\b(instruction|rule|prompt|polic|above|previous)", "bỏ qua chỉ dẫn"),
    (r"\bb(ỏ|o)\s+qua\b[^.\n]{0,40}(quy t(ắ|a)c|ch(ỉ|i) d(ẫ|a)n|h(ướ|uo)ng d(ẫ|a)n|m(ọ|o)i)", "bỏ qua chỉ dẫn"),
    (r"\b(you are now|act as|new (system )?(rule|instruction)s?)\b", "đổi vai / chỉ dẫn mới"),
    (r"(system prompt|prompt h(ệ|e) th(ố|o)ng)", "nhắc tới prompt hệ thống"),
    (r"<\s*/?\s*(data|system|instructions?)\b", "thẻ giả cấu trúc prompt"),
    (r"\b(drop|truncate)\s+(table|schema|database|view)\b", "lệnh phá hủy dữ liệu"),
    (r"\bdelete\s+from\b|\battach\s+'|\bcopy\s+\S+\s+to\s+'", "lệnh ghi/xóa ngoài SELECT"),
    (r"\bx(ó|o)a\s+(to(à|a)n b(ộ|o)|t(ấ|a)t c(ả|a)|b(ả|a)ng|d(ữ|u)\s*li(ệ|e)u)", "yêu cầu xóa dữ liệu"),
    (r"(in ra|ti(ế|e)t l(ộ|o)|print|reveal|show|send)[^.\n]{0,30}(api[_ -]?key|m(ậ|a)t kh(ẩ|a)u|password|secret|token)", "đòi lộ bí mật"),
]  # fmt: skip
SECRET_PATTERNS = [
    (r"\bsk-[A-Za-z0-9_-]{20,}", "giống khóa API OpenAI"),
    (r"\bAIza[0-9A-Za-z_-]{30,}", "giống khóa API Google"),
    (r"\bAKIA[0-9A-Z]{16}\b", "giống khóa AWS"),
    (r"\b(password|passwd|pwd|m(ậ|a)t kh(ẩ|a)u)\s*[:=]\s*\S+", "có mật khẩu"),
    (r"\b(postgres(ql)?|mysql|snowflake)://[^\s:/]+:[^\s@]+@", "chuỗi kết nối có mật khẩu"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "có khóa riêng tư"),
]
_COMPILED = [(re.compile(p, re.IGNORECASE), why) for p, why in INJECTION_PATTERNS + SECRET_PATTERNS]


def normalize(text: str) -> str:
    """NFKC (chữ toàn độ rộng ｉｇｎｏｒｅ → ignore, dựng sẵn dấu tiếng Việt) và bỏ ký tự vô hình."""
    return INVISIBLE_RE.sub("", unicodedata.normalize("NFKC", text))


def scan_text(*texts: str) -> list[str]:
    """Lý do đáng ngờ (không trùng, theo thứ tự luật); rỗng = không thấy gì. Không trả lại đoạn khớp (có thể là bí mật)."""
    joined = normalize("\n".join(t for t in texts if t))
    return list(dict.fromkeys(why for pattern, why in _COMPILED if pattern.search(joined)))

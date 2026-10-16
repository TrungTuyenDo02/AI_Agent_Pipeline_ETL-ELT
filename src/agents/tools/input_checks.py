"""Kiểm tra đầu vào BẰNG CODE (0 token) trước khi vào Planner: tầng 0 luật cố định, tầng 1 đối chiếu danh mục nghiệp vụ.

- Tầng 0: rỗng, quá ngắn/dài, ít chữ/số, lặp ký tự, gõ bừa trên bàn phím, mẫu tấn công prompt đơn giản.
- Tầng 1: yêu cầu phải nhắc tới ít nhất một từ khóa nghiệp vụ (tên bảng/cột/thuật ngữ, có bảng đồng nghĩa) hoặc một
  động từ nghiệp vụ. Không thấy gì → `unclear` (tầng 2 xử lý ở `input_gate`; hàm ở đây không gọi LLM).
- Mẫu tấn công, động từ, đồng nghĩa nằm ở `config/input_gate.yaml` (đổi file, không đổi code).
- Chuẩn hóa tiếng Việt khi so khớp: bỏ dấu, chữ thường, bỏ ký tự thừa.
"""

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

GateStatus = Literal["ok", "rejected", "unclear", "needs_info"]
KEYBOARD_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
KEYBOARD_NOT_MASH = {"erty"}  # có trong từ thật (property, liberty)
MASH_LENGTH = 4
MIN_ALNUM_RATIO = 0.6
MAX_SAME_CHAR_RATIO = 0.6
VOWELS = set("aeiouy")
MIN_KEYWORD_LENGTH = 3  # từ đơn ngắn hơn (to, ai, ban...) trùng từ thường ngày nên không tự là từ khóa
MAX_MATCHED_SHOWN = 5
FALLBACK_EXAMPLES = (
    "Gộp dữ liệu đơn hàng 3 nguồn, tính doanh thu theo ngày",
    "Làm sạch bảng khách hàng: bỏ dòng trùng, chuẩn hóa số điện thoại",
    "Tối ưu truy vấn chậm đọc bảng đơn hàng",
)

EXAMPLES_HEADER = "\nVí dụ yêu cầu hợp lệ:\n"
REWRITE_MESSAGE = (
    "Mình chưa chắc yêu cầu này nhằm tạo hay tối ưu bảng dữ liệu nào. Bạn viết lại giúp mình, nêu rõ bảng/nguồn "
    "và việc cần làm."
)
MESSAGES = {
    "empty": "Bạn chưa nhập yêu cầu.",
    "too_short": "Yêu cầu quá ngắn (cần ít nhất {min} ký tự). Hãy nói rõ bạn cần bảng dữ liệu gì, từ nguồn nào.",
    "too_long": "Yêu cầu quá dài (tối đa {max} ký tự). Hãy rút gọn, chỉ giữ phần cần tạo hoặc tối ưu.",
    "attack": (
        "Yêu cầu có phần cố đổi chỉ dẫn của hệ thống hoặc lấy thông tin bí mật (khóa, mật khẩu, biến môi trường), "
        "hệ thống không thực hiện. Hãy mô tả công việc dữ liệu bạn cần."
    ),
    "nonsense": "Tôi chưa hiểu yêu cầu này. Hãy viết thành câu rõ nghĩa: bạn muốn tạo hoặc tối ưu bảng dữ liệu gì, từ nguồn nào.",
    "unclear": (
        "Yêu cầu chưa nhắc tới dữ liệu hay công việc nào hệ thống hỗ trợ (gộp, tính, làm sạch, tối ưu truy vấn trên "
        "các nguồn đã đăng ký). Hãy nêu rõ bảng/nguồn và việc cần làm."
    ),
    "off_topic": "Yêu cầu này nằm ngoài phạm vi của hệ thống (chỉ viết và tối ưu pipeline dữ liệu ELT/ETL).",
}
OFF_TOPIC_CONFIDENCE = (
    0.8  # từ chối thẳng chỉ khi tầng 2 rất chắc là lạc đề (chặn nhầm gây khó chịu hơn tốn thêm vài đồng)
)
MIN_PASS_CONFIDENCE = 0.5  # nhãn pipeline/optimize dưới mức này coi như chưa rõ
# Ô còn thiếu → cụm từ cố định trong câu hỏi bổ sung (không gọi LLM soạn câu hỏi, không lặp lại chữ do LLM trả về)
MISSING_PHRASES = {
    "source": "dữ liệu lấy từ bảng hoặc nguồn nào",
    "metric": "cần tính chỉ số gì (ví dụ doanh thu, số đơn)",
    "grain": "tính theo đơn vị nào (ngày, tháng, khách hàng, sản phẩm...)",
    "filter": "điều kiện lọc (ví dụ chỉ đơn đã giao)",
    "target": "tên bảng kết quả mong muốn",
}
NONSENSE_CODES = {"low_alnum", "repetitive", "keyboard_mash", "gibberish"}


class GateResult(BaseModel):
    """Kết luận của một tầng kiểm tra. `message` tiếng Việt, kèm ví dụ hợp lệ khi bị chặn/chưa rõ."""

    status: GateStatus
    tier: int = 0  # 0 luật cố định, 1 danh mục nghiệp vụ, 2 bộ phân loại model nhỏ
    code: str = ""  # mã lý do (empty, too_short, attack, no_business_term, ...)
    message: str = ""
    matched: list[str] = Field(default_factory=list)  # từ khóa nghiệp vụ đã khớp (tầng 1)
    missing: list[str] = Field(default_factory=list)  # ô còn thiếu (tầng 2)
    examples: list[str] = Field(default_factory=list)
    label: str = ""  # nhãn của tầng 2 (pipeline|optimize|off_topic|unclear)
    confidence: float = 0.0
    cached: bool = False


@dataclass(frozen=True)
class GateRules:
    """Nội dung `config/input_gate.yaml` đã biên dịch."""

    attacks: tuple[re.Pattern, ...]
    vowelless_ok: frozenset[str]
    verbs: tuple[str, ...]
    synonyms: tuple[frozenset[str], ...]
    generic: frozenset[str]
    always: frozenset[str]


# ---------- Chuẩn hóa ----------


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt (đ → d)."""
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def fold(text: str) -> str:
    """Chữ thường, bỏ dấu, gọn khoảng trắng; GIỮ dấu câu (cho mẫu tấn công có `.env`)."""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


def normalize(text: str) -> str:
    """Chữ thường, bỏ dấu, mọi ký tự không phải chữ/số thành một khoảng trắng (`shopee_orders` → `shopee orders`)."""
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(text).lower()).strip()


def request_hash(text: str) -> str:
    """Băm câu đã chuẩn hóa: khóa bộ nhớ đệm, không giữ nội dung yêu cầu."""
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


# ---------- Luật ----------


@lru_cache(maxsize=4)
def load_rules(path: Path) -> GateRules:
    """Đọc và biên dịch luật; mẫu regex sai báo lỗi ngay khi khởi động (không im lặng bỏ qua)."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return GateRules(
        attacks=tuple(re.compile(p) for p in data.get("attack_patterns", [])),
        vowelless_ok=frozenset(data.get("vowelless_ok", [])),
        verbs=tuple(normalize(v) for v in data.get("business_verbs", [])),
        synonyms=tuple(frozenset(normalize(w) for w in group) for group in data.get("synonyms", [])),
        generic=frozenset(data.get("generic_tokens", [])),
        always=frozenset(normalize(w) for w in data.get("always_keywords", [])),
    )


# ---------- Tầng 0 ----------


def _reject(code: str, text: str, **fmt: object) -> GateResult:
    key = "nonsense" if code in NONSENSE_CODES else code
    return GateResult(
        status="rejected", tier=0, code=code, message=MESSAGES[key].format(**fmt) if fmt else MESSAGES[key]
    )


def _is_attack(text: str, rules: GateRules) -> bool:
    folded = fold(text)
    return any(p.search(folded) for p in rules.attacks)


def _is_repetitive(compact: str) -> bool:
    """Một ký tự chiếm quá nửa, ít ký tự khác nhau, hoặc một cụm ngắn lặp lại (aaaaaa, hahaha, abcabcabc)."""
    if len(compact) < 4:
        return False
    top = max(compact.count(c) for c in set(compact))
    if top / len(compact) > MAX_SAME_CHAR_RATIO:
        return True
    if len(set(compact)) <= 3 and len(compact) >= 8:
        return True
    return bool(re.fullmatch(r"(.{1,4}?)\1{2,}", compact))


def _has_keyboard_mash(tokens: list[str]) -> bool:
    grams = {
        row[i : i + MASH_LENGTH] for row in KEYBOARD_ROWS for i in range(len(row) - MASH_LENGTH + 1)
    } - KEYBOARD_NOT_MASH
    grams |= {g[::-1] for g in grams}
    return any(len(t) >= MASH_LENGTH and any(g in t for g in grams) for t in tokens)


def _gibberish_token(token: str, rules: GateRules) -> bool:
    """Từ dài ≥ 5 chữ cái mà gần như không có nguyên âm (sdkjhg, xcvbnm) và không phải viết tắt kỹ thuật."""
    if len(token) < 5 or not token.isalpha() or token in rules.vowelless_ok:
        return False
    vowels = sum(c in VOWELS for c in token)
    return vowels == 0 or vowels / len(token) < 0.2 or re.search(r"[^aeiouy]{6,}", token) is not None


def tier0(text: str, rules: GateRules, min_chars: int, max_chars: int) -> GateResult | None:
    """Luật cố định; None = qua tầng 0."""
    stripped = text.strip()
    if not stripped:
        return _reject("empty", text)
    if len(stripped) < min_chars:
        return _reject("too_short", text, min=min_chars)
    if len(stripped) > max_chars:
        return _reject("too_long", text, max=max_chars)
    if _is_attack(stripped, rules):
        return _reject("attack", text)
    compact = re.sub(r"\s+", "", stripped.lower())
    if sum(c.isalnum() for c in compact) / len(compact) < MIN_ALNUM_RATIO:
        return _reject("low_alnum", text)
    if _is_repetitive(compact):
        return _reject("repetitive", text)
    tokens = normalize(stripped).split()
    if _has_keyboard_mash(tokens):
        return _reject("keyboard_mash", text)
    words = [t for t in tokens if t.isalpha() and len(t) >= 3]
    if words and sum(_gibberish_token(t, rules) for t in words) / len(words) >= 0.5:
        return _reject("gibberish", text)
    return None


# ---------- Tầng 1 ----------


def _variants(token: str) -> set[str]:
    """Số ít/số nhiều đơn giản (order ↔ orders)."""
    return {token, token[:-1]} if token.endswith("s") and len(token) > 3 else {token, token + "s"}


def business_keywords(terms: Iterable[str], rules: GateRules, phrases: Iterable[str] = ()) -> frozenset[str]:
    """Bộ từ khóa nghiệp vụ từ tên bảng, tên cột, thuật ngữ: cụm đầy đủ + từng từ (bỏ từ quá chung chung) + số ít/nhiều,
    rồi mở rộng theo bảng đồng nghĩa (chạm một từ của nhóm thì cả nhóm là từ khóa).

    `phrases` (nhãn nhóm bảng như "Cửa hàng", "Bán hàng"): chỉ nhận nguyên cụm, không tách từng từ vì các từ đơn
    ("của", "bán") là từ thường ngày."""
    found: set[str] = {normalize(p) for p in phrases if " " in normalize(p)} | set(rules.always)
    for term in terms:
        words = normalize(term).split()
        if len(words) > 1 and any(w not in rules.generic for w in words):
            found.add(" ".join(words))
        for word in words:
            if word not in rules.generic and len(word) >= MIN_KEYWORD_LENGTH and not word.isdigit():
                found |= _variants(word)
    for group in rules.synonyms:
        if found & group:
            found |= group
    return frozenset(found)


def terms_from_catalog(catalog: list[dict]) -> tuple[list[str], list[str]]:
    """(tên nguồn/bảng + tên cột, nhãn nhóm) của danh mục (dict có `name`, `columns`, tùy chọn `label`)."""
    terms: list[str] = []
    labels: list[str] = []
    for item in catalog:
        terms.append(str(item.get("name", "")))
        if item.get("label"):
            labels.append(str(item["label"]))
        terms.extend(str(c) for c in item.get("columns", {}))
    return [t for t in terms if t], sorted(set(labels))


def _contains_phrase(padded: str, phrase: str) -> bool:
    return f" {phrase} " in padded


def tier1(text: str, keywords: frozenset[str], rules: GateRules) -> GateResult:
    """Cho qua khi thấy ≥ 1 từ khóa nghiệp vụ hoặc 1 động từ nghiệp vụ; không thấy → `unclear`."""
    normalized = normalize(text)
    padded = f" {normalized} "
    tokens = set(normalized.split())
    matched = sorted(
        {k for k in keywords if (k in tokens if " " not in k else _contains_phrase(padded, k))},
        key=lambda k: (-len(k), k),
    )
    verbs = [v for v in rules.verbs if _contains_phrase(padded, v)]
    if matched or verbs:
        return GateResult(status="ok", tier=1, code="business_term", matched=[*matched, *verbs][:MAX_MATCHED_SHOWN])
    return GateResult(status="unclear", tier=1, code="no_business_term")


def check_input(text: str, keywords: frozenset[str], rules: GateRules, min_chars: int, max_chars: int) -> GateResult:
    """Tầng 0 rồi tầng 1 (thuần, không gọi LLM)."""
    return tier0(text, rules, min_chars, max_chars) or tier1(text, keywords, rules)


# ---------- Thông điệp ----------


def suggest_examples(catalog: list[dict], limit: int = 3) -> list[str]:
    """2–3 ví dụ yêu cầu hợp lệ dựng từ danh mục thật (bảng có thật, không bịa); danh mục rỗng thì dùng ví dụ mẫu."""
    names = [str(i["name"]) for i in catalog if i.get("name")]
    if len(names) < 2:
        return list(FALLBACK_EXAMPLES[:limit])
    orders = [n for n in names if re.search(r"order|don", n, re.I)] or names
    pair = orders[:3]
    examples = [f"Gộp dữ liệu {', '.join(pair)} và tính doanh thu theo ngày"]
    other = next((n for n in names if n not in pair), names[0])
    examples.append(f"Làm sạch bảng {other}: bỏ dòng trùng, chuẩn hóa ngày và số tiền")
    examples.append(f"Tối ưu truy vấn chậm đọc bảng {pair[0]}")
    return examples[:limit]


def with_message(result: GateResult, examples: list[str]) -> GateResult:
    """Gắn thông điệp lịch sự + ví dụ cho kết quả chưa `ok` (tầng 0 đã có `message`; `unclear` thì dùng câu chung)."""
    if result.status == "ok":
        return result
    message = result.message or MESSAGES.get(result.code, MESSAGES["unclear"])
    if result.code == "no_business_term":
        message = MESSAGES["unclear"]
    tail = EXAMPLES_HEADER + "\n".join(f"- {e}" for e in examples) if examples else ""
    return result.model_copy(update={"message": message + tail, "examples": examples})


# ---------- Tầng 2: quyết định từ kết quả bộ phân loại (thuần, không gọi LLM) ----------


def missing_question(missing: list[str]) -> str:
    """Câu hỏi bổ sung theo mẫu cố định, ghép từ các ô còn thiếu (chỉ nhận ô thuộc danh sách cho phép)."""
    asked = [MISSING_PHRASES[m] for m in dict.fromkeys(missing) if m in MISSING_PHRASES]
    items = "; ".join(f"({i}) {text}" for i, text in enumerate(asked, start=1))
    return f"Yêu cầu của bạn đúng hướng nhưng còn thiếu thông tin. Bạn bổ sung giúp: {items}."


def decide_tier2(label: str, confidence: float, missing: list[str], examples: list[str]) -> GateResult:
    """Quy tắc quyết định của tầng 2.

    - `off_topic` và chắc ≥ 0.8 → từ chối kèm gợi ý;
    - `pipeline`/`optimize` chắc ≥ 0.5: có ô thiếu → hỏi bằng mẫu câu cố định, không thiếu → cho qua Planner;
    - còn lại (unclear, độ tin cậy thấp) → KHÔNG từ chối thẳng: xin người dùng viết lại kèm ví dụ.
    """
    base = {"tier": 2, "label": label, "confidence": confidence, "examples": examples}
    if label == "off_topic" and confidence >= OFF_TOPIC_CONFIDENCE:
        return with_message(GateResult(status="rejected", code="off_topic", **base), examples)
    if label in ("pipeline", "optimize") and confidence >= MIN_PASS_CONFIDENCE:
        asked = [m for m in dict.fromkeys(missing) if m in MISSING_PHRASES]
        if not asked:
            return GateResult(status="ok", code=label, **base)
        return GateResult(status="needs_info", code="missing", message=missing_question(asked), missing=asked, **base)
    text = REWRITE_MESSAGE + EXAMPLES_HEADER + "\n".join(f"- {e}" for e in examples)
    return GateResult(status="needs_info", code="rewrite", message=text, **base)

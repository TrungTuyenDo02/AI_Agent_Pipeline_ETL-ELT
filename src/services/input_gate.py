"""Cửa kiểm tra đầu vào (dịch vụ): ghép tầng 0–1 (code) với danh mục nghiệp vụ, tầng 2 (model nhỏ) cho câu còn lại.

API và CLI gọi `precheck` TRƯỚC khi tạo lần chạy (tầng 0–1, 0 token; bị chặn thì không tạo gì); node `input_gate` của graph
gọi `evaluate` (cùng luật + tầng 2 khi tầng 1 chưa chắc). Danh mục nghiệp vụ chỉ lấy tên bảng/cột/nhãn; prompt tầng 2 chỉ
chứa tên bảng và câu yêu cầu, không bao giờ có dòng dữ liệu.
"""

import hashlib
import logging
import threading
from collections import OrderedDict
from functools import lru_cache

from pydantic import ValidationError

from src.agents.tools.input_checks import (
    GateResult,
    GateRules,
    business_keywords,
    check_input,
    decide_tier2,
    load_rules,
    normalize,
    request_hash,
    suggest_examples,
    terms_from_catalog,
    with_message,
)
from src.config import GATE_TASK, get_settings
from src.models.llm_outputs import GateOutput
from src.services import glossary, llm, source_registry

logger = logging.getLogger(__name__)
MAX_TABLES_SENT = 60  # chỉ gửi TÊN bảng, tối đa chừng này để prompt không phình
MAX_REQUEST_CHARS = 2000


def rules() -> GateRules:
    """Luật đã biên dịch từ `config/input_gate.yaml` (đường dẫn trong cấu hình)."""
    return load_rules(get_settings().input_gate_file)


def gate_catalog(state_catalog: list[dict] | None = None, requester: str = "") -> list[dict]:
    """Danh mục dùng cho cửa kiểm tra: danh mục trong state nếu có; nếu không thì các bảng mà `requester` được thấy trong sổ nguồn
    (chỉ tên bảng, tên cột, nhãn; không có dòng dữ liệu)."""
    if state_catalog:
        return [{k: item.get(k) for k in ("name", "kind", "columns", "label") if k in item} for item in state_catalog]
    return [
        {k: item.get(k) for k in ("name", "kind", "columns", "label") if k in item}
        for item in source_registry.catalog_for(requester)
    ]


class ResultCache:
    """Bộ nhớ đệm FIFO nhỏ: khóa = (băm câu đã chuẩn hóa, dấu vân tay danh mục). Không giữ nội dung yêu cầu."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._items: OrderedDict[tuple[str, str], GateResult] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: tuple[str, str]) -> GateResult | None:
        with self._lock:
            hit = self._items.get(key)
        return hit.model_copy(update={"cached": True}) if hit else None

    def put(self, key: tuple[str, str], result: GateResult) -> None:
        if self._size <= 0:
            return
        with self._lock:
            self._items[key] = result.model_copy(update={"cached": False})
            while len(self._items) > self._size:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


@lru_cache
def _cache(size: int) -> ResultCache:
    return ResultCache(size)


def result_cache() -> ResultCache:
    """Bộ nhớ đệm dùng chung của tiến trình."""
    return _cache(get_settings().input_gate_cache_size)


def catalog_fingerprint(keywords: frozenset[str]) -> str:
    """Dấu vân tay bộ từ khóa: danh mục đổi thì kết quả cũ không còn dùng."""
    return hashlib.sha1("|".join(sorted(keywords)).encode("utf-8")).hexdigest()[:16]  # noqa: S324 — không phải bảo mật


MIN_GLOSSARY_WORD = 5  # từ đơn ngắn ("kênh", "đồng", "sàn") quá thường ngày: chỉ nhận cụm nhiều chữ hoặc từ đơn đủ dài


def glossary_keywords(phrases: list[str], ruleset: GateRules) -> frozenset[str]:
    """Từ khóa nhận diện từ từ điển nghiệp vụ: cả cụm (không tách từng chữ như tên cột) để không làm lọt câu lạc đề."""
    found = set()
    for phrase in phrases:
        key = normalize(phrase)
        if " " in key or (len(key) >= MIN_GLOSSARY_WORD and key not in ruleset.generic):
            found.add(key)
    return frozenset(found)


def static_check(text: str, catalog: list[dict], glossary_terms: list[str] | None = None) -> GateResult:
    """Tầng 0 + tầng 1 (có bộ nhớ đệm), kèm thông điệp và ví dụ lấy từ danh mục thật khi bị chặn/chưa rõ.

    `glossary_terms`: thuật ngữ + từ đồng nghĩa của từ điển nghiệp vụ, cũng là từ khóa nhận diện (giai đoạn 6).
    """
    settings = get_settings()
    ruleset = rules()
    terms, labels = terms_from_catalog(catalog)
    keywords = business_keywords(terms, ruleset, labels) | glossary_keywords(glossary_terms or [], ruleset)
    key = (request_hash(text), catalog_fingerprint(keywords))
    cache = result_cache()
    if hit := cache.get(key):
        return hit
    result = check_input(text, keywords, ruleset, settings.input_min_chars, settings.input_max_chars)
    result = with_message(result, suggest_examples(catalog)) if result.status != "ok" else result
    cache.put(key, result)
    return result


def precheck(text: str, catalog: list[dict] | None = None, requester: str = "") -> GateResult:
    """Dùng ở API/CLI trước khi tạo lần chạy: chỉ tầng 0–1 (0 token).

    `rejected` thì chặn ngay; `ok` và `unclear` đều cho tạo lần chạy (`unclear` sẽ qua tầng 2 ở node `input_gate`).
    """
    return static_check(text, gate_catalog(catalog, requester), glossary.keyword_terms(requester))


def tier2(text: str, catalog: list[dict]) -> tuple[GateResult, list[dict]]:
    """Tầng 2: hỏi model nhỏ nhãn của yêu cầu → (kết luận, mục `llm_usage`). Sai cấu trúc thì thử lại tối đa 1 lần,
    vẫn sai thì coi là `unclear` (xin viết lại). Lỗi gọi LLM (mạng, hạn mức, vượt trần token) được ném lên cho runner báo."""
    examples = suggest_examples(catalog)
    variables = {
        "tables": llm.to_json([str(i["name"]) for i in catalog][:MAX_TABLES_SENT]),
        "request": text.strip()[:MAX_REQUEST_CHARS],
    }
    usage: list[dict] = []
    for _ in range(2):
        response = llm.call_llm(GATE_TASK, variables)  # qua module để test/eval đếm hoặc thay được
        usage.append(response.usage.model_dump())
        try:
            out = GateOutput.model_validate(llm.parse_json_output(response.text))
        except (llm.LLMOutputError, ValidationError) as exc:
            logger.warning("input gate tier 2 output invalid", extra={"error": str(exc)[:200]})
            continue
        return decide_tier2(out.label, out.confidence, list(out.missing), examples), usage
    return decide_tier2("unclear", 0.0, [], examples), usage


def evaluate(text: str, catalog: list[dict] | None = None, requester: str = "") -> tuple[GateResult, list[dict]]:
    """Cửa đầy đủ cho node graph: tầng 0–1, và tầng 2 khi tầng 1 trả `unclear`. Trả (kết luận, `llm_usage` mới).

    Kết quả tầng 2 cũng nhớ theo (băm câu, dấu vân tay danh mục): câu giống hệt không tốn thêm token.
    """
    items = gate_catalog(catalog, requester)
    extra = glossary.keyword_terms(requester)
    static = static_check(text, items, extra)
    if static.status != "unclear":
        return static, []
    terms, labels = terms_from_catalog(items)
    keywords = business_keywords(terms, rules(), labels) | glossary_keywords(extra, rules())
    key = (f"t2:{request_hash(text)}", catalog_fingerprint(keywords))
    cache = result_cache()
    if hit := cache.get(key):
        return hit, []
    result, usage = tier2(text, items)
    cache.put(key, result)
    return result, usage

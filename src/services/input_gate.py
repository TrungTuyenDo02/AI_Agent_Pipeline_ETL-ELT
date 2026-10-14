"""Cửa kiểm tra đầu vào (dịch vụ): ghép tầng 0–1 (code) với danh mục nghiệp vụ, nhớ kết quả cho câu giống hệt.

API và CLI gọi `precheck` TRƯỚC khi tạo lần chạy (0 token, bị chặn thì không tạo gì); node `input_gate` của graph gọi
`evaluate` (cùng luật, thêm tầng 2 ở giai đoạn 2). Danh mục nghiệp vụ chỉ lấy tên bảng/cột/nhãn, không bao giờ lấy dữ liệu.
"""

import hashlib
import threading
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

from src.agents.tools.duckdb_tools import discover_sources
from src.agents.tools.input_checks import (
    GateResult,
    GateRules,
    business_keywords,
    check_input,
    load_rules,
    request_hash,
    suggest_examples,
    terms_from_catalog,
    with_message,
)
from src.config import get_settings
from src.services.company import read_manifest


def rules() -> GateRules:
    """Luật đã biên dịch từ `config/input_gate.yaml` (đường dẫn trong cấu hình)."""
    return load_rules(get_settings().input_gate_file)


def _signature(directory: Path) -> tuple:
    files = sorted(directory.glob("*")) if directory.exists() else []
    return tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file())


@lru_cache(maxsize=4)
def _directory_catalog(directory: str, signature: tuple) -> tuple[dict, ...]:
    """Tên + cột + nhãn các nguồn trong thư mục (bỏ dòng mẫu); nhớ tới khi file nguồn đổi."""
    path = Path(directory)
    labels = read_manifest(path)
    return tuple(
        {"name": i.name, "kind": i.kind, "columns": dict(i.columns), "label": labels.get(i.name, {}).get("label", "")}
        for i in discover_sources(path)
    )


def gate_catalog(state_catalog: list[dict] | None = None) -> list[dict]:
    """Danh mục dùng cho cửa kiểm tra: danh mục trong state nếu có, nếu không thì thư mục nguồn."""
    if state_catalog:
        return [{k: item.get(k) for k in ("name", "kind", "columns", "label") if k in item} for item in state_catalog]
    directory = get_settings().sources_dir
    return list(_directory_catalog(str(directory.resolve()), _signature(directory)))


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


def static_check(text: str, catalog: list[dict]) -> GateResult:
    """Tầng 0 + tầng 1 (có bộ nhớ đệm), kèm thông điệp và ví dụ lấy từ danh mục thật khi bị chặn/chưa rõ."""
    settings = get_settings()
    ruleset = rules()
    terms, labels = terms_from_catalog(catalog)
    keywords = business_keywords(terms, ruleset, labels)
    key = (request_hash(text), catalog_fingerprint(keywords))
    cache = result_cache()
    if hit := cache.get(key):
        return hit
    result = check_input(text, keywords, ruleset, settings.input_min_chars, settings.input_max_chars)
    result = with_message(result, suggest_examples(catalog)) if result.status != "ok" else result
    cache.put(key, result)
    return result


def precheck(text: str, catalog: list[dict] | None = None) -> GateResult:
    """Dùng ở API/CLI trước khi tạo lần chạy. Giai đoạn 1: yêu cầu `unclear` coi như bị chặn kèm gợi ý viết lại."""
    result = static_check(text, gate_catalog(catalog))
    if result.status == "unclear":
        return result.model_copy(update={"status": "rejected"})
    return result

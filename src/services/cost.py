"""Ước tính chi phí gọi LLM theo bảng giá công khai (USD / 1 triệu token).

Giá chỉ là ước tính để so sánh; kiểm tra lại trang giá của nhà cung cấp trước khi báo cáo.
"""

# Giá chuẩn (ngữ cảnh ≤200k), đối chiếu trang giá chính thức OpenAI và Google ngày 2026-10-02.
PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-6-luna": (0.10, 0.50),  # giá sau đợt giảm 50% (openrouter.ai, venturebeat.com, tra 2026-10-13)
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-5.6-terra": (2.00, 12.00),
    "gpt-5.6-sol": (4.00, 20.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),  # trang giá Anthropic, Haiku 4.5; tra lại trước khi báo cáo
    "claude-opus-5-5": (4.00, 20.00),  # trang giá Anthropic (bản lưu 2026-09-25), token suy luận tính như đầu ra
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-3.8-flash": (0.75, 3.75),  # giá giới thiệu, Google báo tăng gấp đôi từ 01/2027 (tra 2026-10-13)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1": (2.00, 8.00),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Chi phí ước tính; model không có trong bảng giá thì trả 0.0.

    Token trúng cache vẫn tính đủ giá đầu vào (chưa xác minh giá cache từng model) → ước tính cao hơn thực tế.
    """
    price_in, price_out = PRICES_PER_MILLION.get(model, (0.0, 0.0))
    return round((input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6)


def compute_cost_usd(seconds: float, cost_per_hour_usd: float) -> float:
    """Quy đổi thời gian máy chạy query thành tiền (dùng cho cổng hòa vốn của optimizer)."""
    return seconds / 3600 * cost_per_hour_usd


def cache_hit_rate(usages: list[dict]) -> float | None:
    """Tỉ lệ token đầu vào trúng cache trên các lần gọi THẬT; None nếu chưa có lần gọi thật nào (mock = mô phỏng)."""
    real = [u for u in usages if not u.get("simulated")]
    total = sum(u.get("input_tokens", 0) for u in real)
    return round(sum(u.get("cached_tokens", 0) for u in real) / total, 4) if total else None


def usage_breakdown(usages: list[dict]) -> dict:
    """Token, chi phí, thời gian gọi LLM theo node + tỉ lệ trúng cache (panel "Chi phí và thời gian" trên web).

    `simulated` = có lần gọi mock: số token/chi phí khi đó là mô phỏng, web phải ghi rõ.
    """
    rows: dict[str, dict] = {}
    for u in usages:
        row = rows.setdefault(
            u.get("task", "?"),
            {"task": u.get("task", "?"), "calls": 0, "input_tokens": 0, "output_tokens": 0, "cached_tokens": 0,
             "cost_usd": 0.0, "seconds": 0.0},
        )  # fmt: skip
        row["calls"] += 1
        for key in ("input_tokens", "output_tokens", "cached_tokens"):
            row[key] += u.get(key, 0)
        row["cost_usd"] = round(row["cost_usd"] + u.get("cost_usd", 0.0), 6)
        row["seconds"] = round(row["seconds"] + u.get("latency_ms", 0.0) / 1000, 2)
    return {
        "rows": list(rows.values()),
        "cache_hit_rate": cache_hit_rate(usages),
        "simulated": any(u.get("simulated") for u in usages),
    }

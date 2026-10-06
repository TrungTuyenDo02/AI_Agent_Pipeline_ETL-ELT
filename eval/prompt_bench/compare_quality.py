"""U1 giai đoạn 2 — so chất lượng golden giữa prompt cũ (v1) và prompt mới, cùng LLM thật.

Đọc eval/results/golden_agent_v1.json (prompt v1, 2026-10-02) và golden_agent.json (lần chạy mới nhất),
ghi eval/results/prompt_quality.md. Chất lượng giảm ở chỉ số nào thì ghi rõ "GIẢM" để hoàn tác phần gây giảm.

    python eval/prompt_bench/compare_quality.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "eval" / "results"
PROMPTS = ROOT / "src" / "prompts"


def prompt_versions() -> str:
    """Phiên bản hiện tại của từng prompt, đọc từ dòng `version:` đầu file."""
    found = []
    for path in sorted(PROMPTS.glob("*.md")):
        match = re.search(r"version:\s*(\d+)", path.read_text(encoding="utf-8"))
        found.append(f"{path.stem} v{match.group(1) if match else '?'}")
    return ", ".join(found)


def load(name: str) -> dict:
    """Đọc một file kết quả golden."""
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def metrics(data: dict) -> dict:
    """Chỉ số chất lượng + chi phí của một lần chạy golden."""
    rows = data["rows"]
    clear = [r for r in rows if r["case"] != "g10_ambiguous_request"]
    ambiguous = [r for r in rows if r["case"] == "g10_ambiguous_request"]
    has_cache = all("cached_tokens" in r for r in rows)
    total_in = sum(r.get("input_tokens", 0) for r in rows)
    return {
        "Kết quả đúng": sum(r["ok"] for r in rows),
        "Đạt ngay lần đầu (0 lỗi V1/V2)": sum(r["ok"] and r["v_failures"] == 0 for r in rows),
        "Chọn đúng ELT/ETL": sum(r["mode_ok"] for r in rows),
        "Ca rõ mà vẫn hỏi (càng ít càng tốt)": sum(r["asked"] > 0 for r in clear),
        "Hỏi làm rõ ở ca mơ hồ (g10)": sum(r["asked"] > 0 for r in ambiguous),
        "Tổng vòng sửa (lỗi V1/V2)": sum(r["v_failures"] for r in rows),
        "Token trung bình mỗi ca": round(sum(r["tokens"] for r in rows) / len(rows)),
        "Chi phí trung bình mỗi ca (USD)": round(sum(r["cost_usd"] for r in rows) / len(rows), 6),
        "Thời gian trung bình (s)": round(sum(r["seconds"] for r in rows) / len(rows), 1),
        "Tỉ lệ token vào trúng cache": (
            f"{sum(r['cached_tokens'] for r in rows) / total_in:.1%}" if has_cache and total_in else "— (chưa ghi)"
        ),
        "_n": len(rows),
    }


HIGHER_BETTER = {"Kết quả đúng", "Đạt ngay lần đầu (0 lỗi V1/V2)", "Chọn đúng ELT/ETL", "Hỏi làm rõ ở ca mơ hồ (g10)"}
LOWER_BETTER = {"Ca rõ mà vẫn hỏi (càng ít càng tốt)", "Tổng vòng sửa (lỗi V1/V2)"}


def verdict(name: str, old: object, new: object) -> str:
    """Nhận xét: chỉ chỉ số chất lượng mới có GIẢM/tốt hơn; chi phí chỉ ghi chênh lệch."""
    if not isinstance(old, int | float) or not isinstance(new, int | float):
        return ""
    if name in HIGHER_BETTER:
        return "GIẢM" if new < old else ("tốt hơn" if new > old else "giữ nguyên")
    if name in LOWER_BETTER:
        return "GIẢM" if new > old else ("tốt hơn" if new < old else "giữ nguyên")
    return f"{(new - old) / old * 100:+.1f}%".replace(".", ",") if old else ""


def main() -> None:
    """Ghi bảng so sánh."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    old_data, new_data = load("golden_agent_v1.json"), load("golden_agent.json")
    old, new = metrics(old_data), metrics(new_data)
    lines = [
        "# Chất lượng golden: prompt v1 so với prompt mới (U1 giai đoạn 2)",
        "",
        f"- Cũ: prompt v1 (tiếng Việt, JSON tả bằng lời), chạy 2026-10-02 • {old_data['provider']}/{old_data['model']}",
        f"- Mới: {prompt_versions()} (tiếng Anh, structured output, ngữ cảnh gọn) • {new_data['provider']}/{new_data['model']}",
        f"- {new['_n']} ca golden, chấm bằng code (so expected.csv). Mỗi phiên bản chạy **một lần**: LLM có dao động, "
        "chênh 1 ca chưa đủ kết luận.",
        "- Lưu ý: lần chạy cũ trước khi có bước duyệt kế hoạch J1b; eval tự đồng ý kế hoạch nên không đổi số lần gọi LLM.",
        "",
        "| Chỉ số | v1 | Mới | Nhận xét |",
        "|---|---:|---:|---|",
    ]
    for name in old:
        if name != "_n":
            lines.append(f"| {name} | {old[name]} | {new[name]} | {verdict(name, old[name], new[name])} |")
    lines += [
        "",
        "## Từng ca",
        "",
        "| Ca | v1: đúng / hỏi / lỗi V | Mới: đúng / hỏi / lỗi V | Chi tiết mới |",
        "|---|---|---|---|",
    ]
    old_rows = {r["case"]: r for r in old_data["rows"]}
    for r in new_data["rows"]:
        o = old_rows.get(r["case"], {})
        fmt = lambda x: f"{'✓' if x.get('ok') else '✗'} / {x.get('asked', '—')} / {x.get('v_failures', '—')}"  # noqa: E731
        lines.append(f"| {r['case']} | {fmt(o)} | {fmt(r)} | {str(r['detail'])[:90].replace('|', '/')} |")
    (RESULTS / "prompt_quality.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:22]))


if __name__ == "__main__":
    main()

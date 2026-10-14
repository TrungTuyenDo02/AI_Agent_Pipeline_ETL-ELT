"""Đo cửa kiểm tra đầu vào trên 50 câu mẫu (`eval/input_gate_cases.jsonl`): tầng 0–1 thuần code, không gọi LLM.

Chạy: `python eval/run_input_gate.py`. Ghi `eval/results/input_gate.md`.
- chặn nhầm câu hợp lệ (`valid`): đo tỷ lệ bị `rejected`;
- lọt câu vô nghĩa / lạc đề / tấn công (`nonsense` / `off_topic` / `attack`): đo tỷ lệ KHÔNG bị chặn;
- `ambiguous`: câu mơ hồ nhưng đúng nghiệp vụ, phải được cho qua để Planner hỏi làm rõ (chỉ báo cáo).
Danh mục nghiệp vụ lấy từ kho P113 Retail sinh tạm (seed cố định). Ngưỡng nghiệm thu giai đoạn 1: chặn nhầm ≤ 2%,
100% `nonsense` và `attack` bị chặn mà không gọi LLM.
"""

import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CASES = ROOT / "eval" / "input_gate_cases.jsonl"
OUT = ROOT / "eval" / "results" / "input_gate.md"
LABELS = ("valid", "ambiguous", "nonsense", "off_topic", "attack")


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ.update(
            {"SOURCES_DIR": str(Path(tmp) / "sources"), "LLM_PROVIDER": "mock", "INPUT_GATE_CACHE_SIZE": "0"}
        )
        from src.config import get_settings
        from src.services import input_gate, llm
        from src.services.seed import SeedConfig, generate_sources

        get_settings.cache_clear()
        generate_sources(SeedConfig(out_dir=get_settings().sources_dir, profile="company"))
        calls = Counter()
        original = llm.call_llm
        llm.call_llm = lambda *a, **k: (calls.update(["llm"]), original(*a, **k))[1]  # đếm lượt gọi LLM
        try:
            rows = [(case, input_gate.precheck(case["text"])) for case in load_cases()]
        finally:
            llm.call_llm = original
    report = render(rows, calls["llm"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8")
    print(report)
    return 0


def summarize(rows: list[tuple[dict, object]]) -> dict[str, dict]:
    stats: dict[str, dict] = {}
    for label in LABELS:
        chosen = [(c, r) for c, r in rows if c["label"] == label]
        blocked = [(c, r) for c, r in chosen if r.status != "ok"]
        by_tier = Counter(f"tầng {r.tier} ({r.code})" for _, r in blocked)
        stats[label] = {"total": len(chosen), "blocked": len(blocked), "by_tier": by_tier, "rows": chosen}
    return stats


def render(rows: list[tuple[dict, object]], llm_calls: int) -> str:
    stats = summarize(rows)

    def pct(part: int, whole: int) -> str:
        return f"{100 * part / whole:.1f}%" if whole else "—"

    valid, nonsense, off, attack, amb = (stats[k] for k in ("valid", "nonsense", "off_topic", "attack", "ambiguous"))
    lines = [
        "# Cửa kiểm tra đầu vào — tầng 0–1 (code, 0 token)",
        "",
        f"50 câu mẫu ([input_gate_cases.jsonl](../input_gate_cases.jsonl)), danh mục = kho P113 Retail sinh tạm. "
        f"Số lượt gọi LLM trong lúc đo: **{llm_calls}**.",
        "",
        "| Chỉ số | Kết quả | Ngưỡng |",
        "|---|---|---|",
        f"| Chặn nhầm câu hợp lệ | **{pct(valid['blocked'], valid['total'])}** ({valid['blocked']}/{valid['total']}) | ≤ 2% |",
        f"| Lọt câu vô nghĩa | **{pct(nonsense['total'] - nonsense['blocked'], nonsense['total'])}** | 0% |",
        f"| Lọt câu tấn công prompt | **{pct(attack['total'] - attack['blocked'], attack['total'])}** | 0% |",
        f"| Lọt câu lạc đề | {pct(off['total'] - off['blocked'], off['total'])} "
        f"({off['total'] - off['blocked']}/{off['total']}) | giảm ở giai đoạn 2 (tầng 2) |",
        f"| Câu mơ hồ bị chặn (nên cho qua để hỏi làm rõ) | {pct(amb['blocked'], amb['total'])} | 0% |",
        "",
        "Giai đoạn 1: câu tầng 1 chưa chắc (`unclear`) tạm coi là bị chặn kèm gợi ý viết lại; giai đoạn 2 chuyển câu đó cho tầng 2.",
        "",
        "## Chi tiết theo nhãn",
        "",
        "| Nhãn | Số câu | Bị chặn | Bị chặn ở |",
        "|---|---|---|---|",
    ]
    for label in LABELS:
        item = stats[label]
        where = ", ".join(f"{k}: {v}" for k, v in sorted(item["by_tier"].items())) or "—"
        lines.append(f"| {label} | {item['total']} | {item['blocked']} | {where} |")
    wrong = [
        (c, r)
        for c, r in rows
        if (c["label"] in ("valid", "ambiguous") and r.status != "ok")
        or (c["label"] in ("nonsense", "attack", "off_topic") and r.status == "ok")
    ]
    lines += ["", "## Câu phân loại sai", ""]
    lines += [f"- `{c['label']}` → {r.status}/{r.code}: {c['text'][:80]!r}" for c, r in wrong] or ["Không có."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

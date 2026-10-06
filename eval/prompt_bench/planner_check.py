"""Kiểm nhanh riêng Planner trên 12 ca golden (rẻ hơn chạy golden đầy đủ): có hỏi thừa không, chọn đúng ELT/ETL không.

Chỉ lượt Planner đầu tiên (chưa trả lời câu nào). Dùng khi sửa prompt planner, trước khi chạy lại golden đầy đủ.
Cần khóa LLM thật; mock không có ý nghĩa.

    python eval/prompt_bench/planner_check.py --repeat 2
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.nodes.planner import planner_node  # noqa: E402
from src.agents.tools.duckdb_tools import discover_sources  # noqa: E402
from src.config import get_settings  # noqa: E402

GOLDEN = ROOT / "eval" / "datasets" / "golden"
RESULTS = ROOT / "eval" / "results"


def check_case(case: Path) -> dict:
    """Một lượt Planner cho một ca golden."""
    meta = yaml.safe_load((case / "meta.yaml").read_text(encoding="utf-8"))
    state = {
        "request_text": (case / "request.txt").read_text(encoding="utf-8").strip(),
        "source_catalog": [s.model_dump() for s in discover_sources(case / "sources")],
    }
    result = planner_node(state)
    spec = result.get("spec") or {}
    questions = [q["question"] for q in spec.get("questions", [])]
    usage = result.get("llm_usage", [{}])[0]
    return {
        "case": case.name,
        "expect_questions": bool(meta.get("expect_questions")),
        "asked": questions,
        "question_ok": bool(questions) == bool(meta.get("expect_questions")),
        "mode": spec.get("mode", "—"),
        "mode_ok": spec.get("mode") == meta.get("expected_mode"),
        "cost_usd": usage.get("cost_usd", 0.0),
        "error": "; ".join(result.get("spec_errors", [])),
    }


def main() -> None:
    """Chạy `repeat` lượt trên mọi ca, ghi eval/results/planner_check.md."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    get_settings.cache_clear()
    cases = sorted(p for p in GOLDEN.iterdir() if (p / "meta.yaml").exists())
    rows = [check_case(case) | {"round": i + 1} for i in range(args.repeat) for case in cases]
    for r in rows:
        mark = "✓" if r["question_ok"] and r["mode_ok"] else "✗"
        print(f"{mark} lượt {r['round']} {r['case']}: mode {r['mode']}, hỏi {len(r['asked'])} {r['asked']}", flush=True)
    n = len(rows)
    lines = [
        "# Kiểm nhanh Planner trên golden",
        "",
        f"- Ngày chạy: {date.today().isoformat()} • {get_settings().llm_provider}/{get_settings().model_for('planner')} "
        f"• {args.repeat} lượt × {len(cases)} ca • chỉ lượt Planner đầu",
        "",
        f"**Hỏi đúng (rõ thì không hỏi, mơ hồ thì hỏi): {sum(r['question_ok'] for r in rows)}/{n} • "
        f"đúng ELT/ETL: {sum(r['mode_ok'] for r in rows)}/{n} • chi phí {sum(r['cost_usd'] for r in rows):.4f} USD**",
        "",
        "| Lượt | Ca | Kỳ vọng hỏi | Câu hỏi | Mode | Đúng |",
        "|---:|---|---|---|---|---|",
    ]
    for r in rows:
        asked = "; ".join(r["asked"]).replace("|", "/") or "—"
        ok = "✓" if r["question_ok"] and r["mode_ok"] else "✗"
        lines.append(
            f"| {r['round']} | {r['case']} | {'có' if r['expect_questions'] else 'không'} | {asked} | {r['mode']} | {ok} |"
        )
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "planner_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / "planner_check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(lines[4])


if __name__ == "__main__":
    main()

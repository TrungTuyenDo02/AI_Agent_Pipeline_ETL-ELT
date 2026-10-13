"""So sánh model LLM cho Optimizer (E4) trên cùng bộ truy vấn chậm TPC-H (CLAUDE.md mục 12–13: đổi model phải có số đo).

Ép Optimizer bỏ qua luật tất định và sqlglot để MỌI ứng viên đều do LLM viết, nên đây là phép đo riêng của phần LLM
(khác tpch_benchmark.md, nơi 10/11 ca được luật cố định giải). V3 vẫn quyết định áp dụng: kết quả phải giống hệt và nhanh hơn
ngưỡng. Gọi LLM thật, tốn tiền: mỗi lần chạy in tổng chi phí.

    python eval/benchmarks/tpch/ab_optimizer.py --model anthropic:claude-opus-5-5:medium --label opus
    python eval/benchmarks/tpch/ab_optimizer.py --model openai:gpt-5.6-terra --label terra
    python eval/benchmarks/tpch/ab_optimizer.py --report opus terra     # ghép báo cáo từ các lần đã chạy
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "eval" / "results" / "ab_optimizer"
REPORT = ROOT / "eval" / "results" / "ab_optimizer.md"


def _models_file(spec: str) -> Path:
    """Bản sao config/models.yaml với model của optimizer thay bằng `provider:name[:effort]`."""
    provider, name, *effort = spec.split(":")
    data = yaml.safe_load((ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    choice = {"provider": provider, "name": name}
    if effort:
        choice["effort"] = effort[0]
    data["models"]["optimizer"] = choice
    path = Path(tempfile.mkdtemp()) / "models.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def run(spec: str, label: str, sf: float, attempts: int, only: list[str]) -> None:
    os.environ.update(
        {"MODELS_FILE": str(_models_file(spec)), "LLM_PROVIDER": "openai", "LLM_FALLBACK": "none", "OPT_MAX_ATTEMPTS": str(attempts)}
    )
    from eval.benchmarks.tpch.run_tpch import SLOW_DIR, prepare_db, run_one
    from src.agents.nodes import optimizer
    from src.config import get_settings

    optimizer.DETERMINISTIC_SOURCES.clear()  # chỉ đo LLM
    settings = get_settings()
    db = prepare_db(sf)
    rows = []
    for path in sorted(SLOW_DIR.glob("*.sql")):
        if only and path.stem not in only:
            continue
        r = run_one(db, path)
        rep = r["report"]
        rows.append(
            {
                "query": r["name"],
                "decision": rep.decision,
                "gain_pct": rep.improvement_pct,
                "attempts": rep.attempts,
                "llm_calls": r["llm_calls"],
                "cost_usd": getattr(rep, "llm_cost_usd", 0.0),
                "reason": rep.reason[:160],
            }
        )
        print(rows[-1], flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = round(sum(x["cost_usd"] for x in rows), 4)
    (OUT_DIR / f"{label}.json").write_text(
        json.dumps(
            {"label": label, "model": spec, "date": date.today().isoformat(), "sf": sf, "attempts": attempts,
             "bench_runs": settings.opt_bench_runs, "total_cost_usd": total, "rows": rows},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Đã ghi {OUT_DIR / (label + '.json')} • tổng chi phí LLM: {total} USD")


def report(labels: list[str]) -> None:
    runs = [json.loads((OUT_DIR / f"{label}.json").read_text(encoding="utf-8")) for label in labels]
    queries = [row["query"] for row in runs[0]["rows"]]
    lines = [
        "# A/B model cho Optimizer (E4) trên TPC-H",
        "",
        f"- Ngày đo: {runs[0]['date']} • sf={runs[0]['sf']} • tối đa {runs[0]['attempts']} lần thử/query • "
        f"trung vị {runs[0]['bench_runs']} lần đo • **chỉ ứng viên do LLM viết** (bỏ luật cố định và sqlglot) • mỗi cấu hình chạy 1 lần.",
        "- \"Bản đúng và nhanh hơn ngưỡng\" = qua V3 (kết quả giống hệt) và nhanh hơn ≥ 15%. \"Áp dụng\" còn phải qua cổng chi phí (tiết kiệm/năm > chi phí gọi LLM); trên TPC-H nhỏ cổng này loại nhiều ca dù bản viết lại tốt. Chi phí = số token thật × bảng giá trong src/services/cost.py.",
        "",
        "| Model | Bản đúng và nhanh hơn ngưỡng | Áp dụng (qua cổng chi phí) | Cải thiện trung vị | Số lần gọi LLM | Tổng chi phí (USD) |",
        "|---|---|---|---|---|---|",
    ]
    for run_ in runs:
        applied = [r for r in run_["rows"] if r["decision"] == "applied"]
        good = [r for r in run_["rows"] if r["gain_pct"] is not None and r["gain_pct"] >= 15]  # đã qua V3 (giống hệt) và đủ nhanh
        gains = sorted(r["gain_pct"] for r in good)
        median = f"{gains[len(gains) // 2]:.1f}%" if gains else "—"
        calls = sum(r["llm_calls"] for r in run_["rows"])
        total_rows = len(run_["rows"])
        lines.append(
            f"| {run_['model']} | {len(good)}/{total_rows} | {len(applied)}/{total_rows} | {median} | {calls} | {run_['total_cost_usd']} |"
        )
    lines += ["", "## Từng query", "", "| Query | " + " | ".join(r["model"] for r in runs) + " |", "|---|" + "---|" * len(runs)]
    for query in queries:
        cells = []
        for run_ in runs:
            row = next((r for r in run_["rows"] if r["query"] == query), None)
            cells.append("—" if row is None else f"{row['decision']}" + (f" ({row['gain_pct']}%)" if row["gain_pct"] is not None else ""))
        lines.append(f"| {query} | " + " | ".join(cells) + " |")
    lines += ["", "Giới hạn: 1 lần chạy mỗi model, chưa lặp lại; thời gian query dao động giữa các lần đo; chỉ 13 query TPC-H, "
              "chưa phản ánh query thật của doanh nghiệp."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi {REPORT}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="provider:name[:effort], ví dụ anthropic:claude-opus-5-5:medium")
    parser.add_argument("--label")
    parser.add_argument("--sf", type=float, default=0.1)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--only", nargs="*", default=[], help="chỉ chạy các query có tên này")
    parser.add_argument("--report", nargs="*", help="ghép báo cáo từ các nhãn đã chạy")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.report:
        report(args.report)
    elif args.model and args.label:
        run(args.model, args.label, args.sf, args.attempts, args.only)
    else:
        parser.error("cần --model và --label, hoặc --report")


if __name__ == "__main__":
    main()

"""Mốc baseline "viết tay, không tối ưu" trên TPC-H (CLAUDE.md mục 2.9 và 13): mọi cải tiến của Optimizer so với mốc này.

Mốc 100% = chính truy vấn chậm viết tay trong eval/benchmarks/tpch/slow/*.sql, chạy trên DuckDB local với cùng dữ liệu.
Ba số đo cho mỗi truy vấn, trước và sau tối ưu:
- thời gian: trung vị N lần chạy (sau 1 lần khởi động), mili-giây;
- dữ liệu quét: số dòng DuckDB đọc từ bảng (`cumulative_rows_scanned`); byte đọc (`total_bytes_read`) luôn 0 trên DuckDB local nên không dùng;
- chi phí tính toán ước tính/tháng = giây × OPT_RUNS_PER_MONTH × OPT_COMPUTE_COST_PER_HOUR_USD / 3600 (giả định, không phải hóa đơn thật).

"Sau tối ưu" chạy bằng LLM mô phỏng (luật cố định + sqlglot, 0 token); ca cần LLM thật nằm ở ab_optimizer.py.

    python eval/baseline/tpch_baseline.py --sf 0.1 --runs 7
"""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["LLM_PROVIDER"] = "mock"  # mốc phải tái lập được: không gọi LLM thật

import duckdb  # noqa: E402

from eval.benchmarks.tpch.run_tpch import HEADER_RE, SLOW_DIR, prepare_db  # noqa: E402
from src.agents.nodes.optimizer import OptimizeJob, optimize_standalone  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.services.cost import compute_cost_usd  # noqa: E402

OUT_JSON = ROOT / "eval" / "results" / "tpch_baseline.json"
OUT_MD = ROOT / "eval" / "results" / "tpch_baseline.md"


def measure(db: Path, sql: str, runs: int) -> dict:
    """Thời gian trung vị + dòng/byte quét của một truy vấn (đọc-chỉ, một kết nối riêng)."""
    con = duckdb.connect(str(db), read_only=True)
    try:
        con.execute(sql).fetchall()  # khởi động, không tính
        times = []
        for _ in range(runs):
            start = time.perf_counter()
            con.execute(sql).fetchall()
            times.append((time.perf_counter() - start) * 1000)
        profile = Path(tempfile.mkdtemp()) / "profile.json"
        con.execute("PRAGMA enable_profiling='json'")
        con.execute(f"PRAGMA profiling_output='{profile.as_posix()}'")
        con.execute(sql).fetchall()
        con.execute("PRAGMA disable_profiling")
        data = json.loads(profile.read_text(encoding="utf-8"))
    finally:
        con.close()
    return {
        "median_ms": round(statistics.median(times), 3),
        "rows_scanned": int(data.get("cumulative_rows_scanned", 0)),
        "bytes_read": int(data.get("total_bytes_read", 0)),
    }


def monthly_cost(median_ms: float) -> float:
    settings = get_settings()
    seconds = median_ms / 1000 * settings.opt_runs_per_month
    return round(compute_cost_usd(seconds, settings.opt_compute_cost_per_hour_usd), 6)


def pct(after: float, before: float) -> str:
    return f"{100 * after / before:.0f}%" if before else "—"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", type=float, default=0.1)
    parser.add_argument("--runs", type=int, default=7)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    db = prepare_db(args.sf)
    rows = []
    for path in sorted(SLOW_DIR.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        sql = "\n".join(line for line in text.splitlines() if not HEADER_RE.match(line.strip())).strip().rstrip(";")
        before = measure(db, sql, args.runs)
        report, _ = optimize_standalone(OptimizeJob(sql=sql, datasets={"small": str(db), "large": str(db)}))
        applied = report.decision == "applied"
        after = measure(db, report.proposed_sql, args.runs) if applied else before
        rows.append(
            {
                "query": path.stem,
                "decision": report.decision,
                "before": {**before, "cost_month_usd": monthly_cost(before["median_ms"])},
                "after": {**after, "cost_month_usd": monthly_cost(after["median_ms"])},
            }
        )
        print(rows[-1]["query"], rows[-1]["decision"], pct(after["median_ms"], before["median_ms"]), flush=True)

    settings = get_settings()
    sums = {
        side: {key: sum(r[side][key] for r in rows) for key in ("median_ms", "rows_scanned", "bytes_read", "cost_month_usd")}
        for side in ("before", "after")
    }
    OUT_JSON.write_text(
        json.dumps({"date": date.today().isoformat(), "sf": args.sf, "runs": args.runs, "rows": rows, "totals": sums}, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Baseline TPC-H: truy vấn viết tay không tối ưu = 100%",
        "",
        f"- Ngày đo: {date.today().isoformat()} • sf={args.sf} • DuckDB local • trung vị {args.runs} lần (sau 1 lần khởi động) • 1 lần chạy cả bộ.",
        "- Mốc 100% = truy vấn chậm viết tay (`eval/benchmarks/tpch/slow/`). Cột \"Sau\" = % so với mốc, tối ưu bằng luật cố định + sqlglot (LLM mô phỏng, 0 token).",
        f"- Chi phí ước tính/tháng = giây × {settings.opt_runs_per_month} lần/tháng × {settings.opt_compute_cost_per_hour_usd} USD/giờ tính toán (**giả định**, không phải hóa đơn).",
        "- \"Dữ liệu quét\" = số dòng DuckDB đọc từ bảng. Số byte đọc từ đĩa (`total_bytes_read`) luôn bằng 0 vì DuckDB local đã đọc sẵn vào bộ nhớ, nên KHÔNG dùng làm số đo (chỉ lưu trong JSON).",
        "",
        "| Query | Quyết định | Thời gian trước (ms) | Sau | Dòng quét trước | Sau | Chi phí/tháng trước (USD) | Sau |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        b, a = r["before"], r["after"]
        lines.append(
            f"| {r['query']} | {r['decision']} | {b['median_ms']} | {pct(a['median_ms'], b['median_ms'])} | {b['rows_scanned']:,} | "
            f"{pct(a['rows_scanned'], b['rows_scanned'])} | "
            f"{b['cost_month_usd']} | {pct(a['cost_month_usd'], b['cost_month_usd'])} |"
        )
    b, a = sums["before"], sums["after"]
    lines += [
        f"| **Tổng** | | {b['median_ms']:.1f} | {pct(a['median_ms'], b['median_ms'])} | {b['rows_scanned']:,} | "
        f"{pct(a['rows_scanned'], b['rows_scanned'])} | "
        f"{b['cost_month_usd']:.5f} | {pct(a['cost_month_usd'], b['cost_month_usd'])} |",
        "",
        "Giới hạn: dữ liệu TPC-H nhỏ (sf 0,1) nên tiền tuyệt đối rất nhỏ, chỉ tỉ lệ có ý nghĩa; mỗi truy vấn đo một lần chạy; "
        "chưa so với DE làm tay (xem PROTOCOL.md) và chưa chạy trên kho dữ liệu đám mây thật.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi {OUT_MD}")


if __name__ == "__main__":
    main()

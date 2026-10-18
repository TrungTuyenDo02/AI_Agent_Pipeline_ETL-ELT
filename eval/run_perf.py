"""Bộ eval hiệu năng cố định (Optimize.md bước 2): độ đúng, điểm nghẽn, tối ưu, thời gian trước/sau, độ ổn định.

Mỗi ca ở `eval/benchmarks/perf/cases.yaml` chạy đúng đường thật: dựng workspace từ template → `dbt build` trên sandbox DuckDB
(số đo từng model) → báo cáo điểm nghẽn top N → so bảng đích với đáp án đóng băng → optimizer (luật → sqlglot → LLM) trên model
đích. Thêm 13 ca TPC-H viết chậm (`eval/benchmarks/tpch/slow`, mặc định sf 0.1, dùng lại dữ liệu đã tải; không có thì ghi
"chưa đo"). Luôn chạy LLM_PROVIDER=mock (bỏ qua .env) trừ khi có `--allow-real-llm` (tốn tiền: báo ước tính trước khi chạy).

    python eval/run_perf.py                     # 7 ca perf + TPC-H sf 0.1, 1 lượt
    python eval/run_perf.py --repeat 2          # chạy 2 lượt, kiểm kết luận và trung vị có ổn định không
    python eval/run_perf.py --only range_join --no-tpch --rows 200000
    python eval/run_perf.py --freeze            # đóng băng đáp án kỳ vọng từ câu SQL tham chiếu (chỉ khi đổi ca)

Đầu ra: eval/results/<eval_id>/summary.md, cases.csv, details.json.
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from math import isclose
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "benchmarks" / "tpch"))

from src.agents.nodes.optimizer import OptimizeJob, optimize_standalone  # noqa: E402
from src.agents.tools.bottleneck import analyze_bottlenecks, execution_findings, matching_timing  # noqa: E402
from src.agents.tools.dbt_tools import prepare_workspace, run_dbt_build, write_sources_yml  # noqa: E402
from src.agents.tools.duckdb_tools import benchmark_query, run_query  # noqa: E402
from src.agents.tools.slow_patterns import detect_slow_patterns  # noqa: E402
from src.agents.tools.sql_tools import render_dbt_sql  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.models.evidence import QueryMetrics  # noqa: E402

PERF_DIR = ROOT / "eval" / "benchmarks" / "perf"
EXPECTED_DIR = PERF_DIR / "expected"
RESULTS = ROOT / "eval" / "results"
CONCLUSIONS = ("correct", "bottleneck_hit", "decision", "kept_result")  # so giữa các lượt để biết có ổn định không
NOT_MEASURED = "chưa đo"


def load_cases(only: list[str]) -> dict:
    spec = yaml.safe_load((PERF_DIR / "cases.yaml").read_text(encoding="utf-8"))
    spec["cases"] = [c for c in spec["cases"] if not only or c["id"] in only]
    return spec


def make_data(db: Path, spec: dict, rows: int) -> None:
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        for name, sql in spec["data"]["tables"].items():
            con.execute(f"CREATE OR REPLACE TABLE raw.{name} AS {sql.format(rows=rows)}")


def rows_of(db: Path, sql: str) -> list[list[str]]:
    """Kết quả dạng bảng chuỗi (số thực giữ đủ chữ số), sắp xếp để so không phụ thuộc thứ tự dòng."""
    rows = [[repr(v) if isinstance(v, float) else str(v) for v in row] for row in run_query(db, sql).rows]
    return sorted(rows, key=_sort_key)


def _sort_key(row: list[str]) -> list[str]:
    return [f"{float(v):.2f}" if _is_float(v) else v for v in row]


def _is_float(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return "." in text or "e" in text.lower()


def same_rows(a: list[list[str]] | None, b: list[list[str]] | None) -> bool:
    """Bằng nhau từng ô; số thực so có dung sai (cộng song song lệch ở chữ số cuối)."""
    if a is None or b is None or len(a) != len(b):
        return False
    return all(
        len(x) == len(y) and all(u == v or (_is_float(u) and _is_float(v) and isclose(float(u), float(v), rel_tol=1e-9))
                                 for u, v in zip(x, y, strict=True))
        for x, y in zip(sorted(a, key=_sort_key), sorted(b, key=_sort_key), strict=True)
    )  # fmt: skip


def read_expected(case_id: str) -> list[list[str]] | None:
    path = EXPECTED_DIR / f"{case_id}.csv"
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.reader(f))[1:]


def freeze(spec: dict, work: Path, rows: int) -> None:
    """Đóng băng đáp án: chạy câu SQL tham chiếu (viết độc lập) trên bộ large."""
    db = work / "freeze.duckdb"
    make_data(db, spec, rows)
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    for case in spec["cases"]:
        result = run_query(db, case["reference"])
        with (EXPECTED_DIR / f"{case['id']}.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(result.columns)
            writer.writerows(rows_of(db, case["reference"]))
        print(f"đã đóng băng {case['id']}", flush=True)


def noise_of(db: Path, sql: str, runs: int) -> tuple[float | None, dict, dict]:
    """Đo bản gốc hai lần: độ lệch trung vị giữa hai lần (%) là ngưỡng nhiễu của ca."""
    first, second = benchmark_query(db, sql, runs), benchmark_query(db, sql, runs)
    low = min(first.median_ms, second.median_ms)
    pct = round(100 * abs(first.median_ms - second.median_ms) / low, 1) if low else None
    return pct, first.model_dump(), second.model_dump()


def optimization_row(sql: str, datasets: dict[str, str], runs: int, signals: list | None = None) -> dict:
    """Optimizer trên SQL gốc; tự kiểm lại (ngoài V3) bản áp dụng có giữ kết quả bản gốc không trên mọi bộ."""
    noise, first, _ = noise_of(Path(datasets["large"]), sql, runs)
    job = OptimizeJob(sql=sql, datasets=datasets, bench="large", signals=signals or [])
    report, usages = optimize_standalone(job)
    kept = None
    if report.decision == "applied":
        kept = all(
            same_rows(rows_of(Path(db), sql), rows_of(Path(db), report.proposed_sql)) for db in datasets.values()
        )
    gain = report.improvement_pct
    before, after = report.before or QueryMetrics.model_validate(first), report.after  # bỏ qua sớm: lần đo nhiễu
    return {
        "decision": report.decision,
        "reason": report.reason,
        "attempts": report.attempts,
        "rejected": [c.dataset for c in report.equivalence if not c.equal],
        "signal": [s.rule for s in signals or []],  # bằng chứng thực thi đã dùng (khi sqlglot không thấy mẫu)
        "findings": [f.rule for f in report.findings],
        "before_ms": before.median_ms if before else None,
        "before_iqr_ms": before.spread_ms if before else None,
        "after_ms": after.median_ms if after else None,
        "after_iqr_ms": after.spread_ms if after else None,
        "gain_pct": gain,
        "noise_pct": noise,
        # Chỉ tính là cải thiện khi đã áp dụng (V3 + IQR) VÀ lợi ích vượt nhiễu đo lại bản gốc
        "improved": bool(report.decision == "applied" and gain is not None and noise is not None and gain > noise),
        "kept_result": kept,
        "llm_calls": len(usages),
        "tokens": sum(u.input_tokens + u.output_tokens for u in usages),
        "llm_cost_usd": round(sum(u.cost_usd for u in usages), 6),
    }


def run_case(case: dict, spec: dict, work: Path, rows: int) -> dict:
    settings = get_settings()
    workspace = prepare_workspace(f"perf-{case['id']}")
    db, small = workspace / "sandbox.duckdb", work / f"{case['id']}-small.duckdb"
    make_data(db, spec, rows)
    make_data(small, spec, spec["data"]["rows"]["small"])
    write_sources_yml(workspace, list(spec["data"]["tables"]))
    models = {**spec["decoys"], case["target"]: case["sql"]}
    for name, sql in models.items():
        (workspace / "models" / "marts" / f"{name}.sql").parent.mkdir(parents=True, exist_ok=True)
        (workspace / "models" / "marts" / f"{name}.sql").write_text(sql, encoding="utf-8")
    build = run_dbt_build(workspace)
    timings = [
        {"model": r.unique_id.rsplit(".", 1)[-1], "status": r.status, "execute_ms": r.execute_ms}
        for r in build.results
        if r.unique_id.startswith("model.")
    ]
    row = {"id": case["id"], "kind": "perf", "pattern": case["pattern"], "dbt_ok": build.ok}
    if not build.ok:
        return {**row, "correct": False, "detail": build.log_tail[-300:]}
    sandbox = {"dbt_invocation": build.invocation_id, "model_timings": timings, "wall_ms": build.elapsed_ms}
    perf = analyze_bottlenecks(workspace, db, sandbox, settings.perf_top_n, settings.perf_analyze_sec)
    expected, actual = read_expected(case["id"]), rows_of(db, f'SELECT * FROM main."{case["target"]}"')
    sql = render_dbt_sql(case["sql"])
    # Cùng điều kiện như graph: báo cáo khớp model + phiên bản SQL và trong top N, rồi EXPLAIN trên bộ sẽ đo (large)
    matched = matching_timing(workspace, sandbox, case["target"], case["sql"], settings.perf_top_n) is not None
    signals = (
        execution_findings(db, sql, settings.opt_signal_min_ms, settings.perf_analyze_sec)
        if matched and not detect_slow_patterns(sql)
        else []
    )
    wanted = case["bottleneck"]
    found = {f.model: f for f in perf.findings}
    hit = None
    if wanted["model"]:
        finding = found.get(wanted["model"])
        hit = bool(finding and finding.analyzed and finding.operator.startswith(tuple(wanted["operators"])))
    return {
        **row,
        "correct": same_rows(actual, expected),
        "detail": "chưa đóng băng đáp án (chạy --freeze)" if expected is None else "",
        "model_total_ms": perf.model_total_ms,
        "dbt_wall_ms": perf.dbt_wall_ms,
        "dag_wall_ms": None,  # chưa chạy Airflow thật
        "top_models": [f"{f.model}:{f.operator or '?'}" for f in perf.findings],
        "bottleneck_expected": f"{wanted['model']}:{'/'.join(wanted['operators'])}" if wanted["model"] else "—",
        "bottleneck_hit": hit,
        "analysis_ms": perf.analysis_ms,
        **optimization_row(sql, {"small": str(small), "large": str(db)}, settings.opt_bench_runs, signals),
    }


def tpch_rows(sf: float) -> list[dict]:
    """13 ca TPC-H viết chậm: đúng với truy vấn chuẩn? optimizer giữ kết quả? (điểm nghẽn: không gán nhãn → không chấm)."""
    try:
        import run_tpch

        db = run_tpch.prepare_db(sf)
    except (duckdb.Error, OSError) as exc:
        return [{"id": f"tpch_sf{sf}", "kind": "tpch", "correct": None, "detail": f"{NOT_MEASURED}: {exc}"[:200]}]
    rows = []
    for path in sorted(run_tpch.SLOW_DIR.glob("*.sql")):
        meta = run_tpch.parse_header(path.read_text(encoding="utf-8"))
        text = path.read_text(encoding="utf-8")
        sql = "\n".join(line for line in text.splitlines() if not run_tpch.HEADER_RE.match(line.strip())).strip()
        reference = run_tpch.reference_sql(db, int(meta["reference"].split(":")[1]))
        correct = same_rows(rows_of(db, reference), rows_of(db, sql.rstrip(";")))
        opt = optimization_row(sql.rstrip(";"), {"large": str(db)}, get_settings().opt_bench_runs)
        rows.append({"id": path.stem, "kind": "tpch", "pattern": meta.get("pattern", ""), "correct": correct, **opt})
        print(f"{'✓' if correct else '✗'} {path.stem}: {opt['decision']}", flush=True)
    return rows


def stability(rounds: list[list[dict]]) -> dict:
    """So các lượt: kết luận (đúng/sai, điểm nghẽn, quyết định, giữ kết quả) giống nhau? trung vị bản gốc lệch trong ngưỡng
    nhiễu đo được? Ngưỡng nhiễu = max(IQR của hai lượt, độ lệch giữa hai lần đo bản gốc trong cùng lượt)."""
    if len(rounds) < 2:
        return {"checked": False, "stable": None, "note": "chỉ 1 lượt: chưa kiểm độ ổn định (dùng --repeat 2)"}
    conclusions, timings = [], []
    for row in rounds[0]:
        for other in [next((r for r in rnd if r["id"] == row["id"]), {}) for rnd in rounds[1:]]:
            if changed := [k for k in CONCLUSIONS if row.get(k) != other.get(k)]:
                conclusions.append(f"{row['id']}: {', '.join(changed)}")
            a, b = row.get("before_ms"), other.get("before_ms")
            if a is None or b is None:
                continue
            noise = max(
                row.get("before_iqr_ms") or 0,
                other.get("before_iqr_ms") or 0,
                *[(r.get("noise_pct") or 0) / 100 * r["before_ms"] for r in (row, other)],
            )
            if abs(a - b) > noise:
                timings.append(f"{row['id']}: before_ms {a}→{b} (ngưỡng nhiễu {round(noise, 3)} ms)")
    stable = not conclusions and not timings
    return {
        "checked": True,
        "stable": stable,
        "note": "ổn định" if stable else "kết quả chưa ổn định",
        "conclusions_stable": not conclusions,
        "timings_stable": not timings,
        "differences": conclusions + timings,
    }


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        return out.stdout.strip() or "nogit"
    except OSError:
        return "nogit"


def _cell(value: object) -> str:
    if value is None:
        return NOT_MEASURED
    if isinstance(value, bool):
        return "đạt" if value else "không đạt"
    return "; ".join(map(str, value)) if isinstance(value, list) else str(value)


COLUMNS = [
    "id", "kind", "correct", "bottleneck_expected", "top_models", "bottleneck_hit", "signal", "decision", "kept_result",
    "before_ms", "before_iqr_ms", "after_ms", "after_iqr_ms", "gain_pct", "noise_pct", "improved",
    "model_total_ms", "dbt_wall_ms", "dag_wall_ms", "llm_calls", "tokens", "llm_cost_usd", "reason", "detail",
]  # fmt: skip


def summarize(rows: list[dict], stable: dict, meta: dict) -> dict:
    perf = [r for r in rows if r["kind"] == "perf"]
    labelled = [r for r in perf if r.get("bottleneck_hit") is not None]
    measured = [r for r in rows if r.get("correct") is not None]
    applied = [r for r in rows if r.get("decision") == "applied"]
    return {
        **meta,
        "cases": len(rows),
        "correct": f"{sum(bool(r['correct']) for r in measured)}/{len(measured)}",
        "bottleneck_in_top_n": f"{sum(bool(r['bottleneck_hit']) for r in labelled)}/{len(labelled)}",
        "applied": len(applied),
        "kept_result": f"{sum(r.get('kept_result') is True for r in applied)}/{len(applied)}",
        "improved_beyond_noise": sum(bool(r.get("improved")) for r in rows),
        "skipped": sum(r.get("decision") == "skipped" for r in rows),
        "llm_cost_usd": round(sum(r.get("llm_cost_usd") or 0 for r in rows), 6),
        "stability": stable,
        "accepted": bool(measured)
        and all(r["correct"] for r in measured)
        and all(r["bottleneck_hit"] for r in labelled)
        and all(r.get("kept_result") is not False for r in applied)
        and stable.get("stable") is not False,
    }


def write_outputs(out: Path, rows: list[dict], rounds: list[list[dict]], summary: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "cases.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows([[_cell(r.get(c)) for c in COLUMNS] for r in rows])
    details = {"summary": summary, "rounds": rounds}
    (out / "details.json").write_text(json.dumps(details, ensure_ascii=False, indent=1), encoding="utf-8")
    llm = (
        "không đánh giá năng lực LLM (LLM_PROVIDER=mock: code sinh tất định, tỷ lệ 100% không phải bằng chứng chất lượng)"
        if summary["provider"] == "mock"
        else "chưa chạy trong bộ này: cần chạy golden agent bằng LLM thật, báo ước tính chi phí trước"
    )
    stable = summary["stability"]
    lines = [
        f"# Eval hiệu năng `{summary['eval_id']}`",
        "",
        f"- Provider: `{summary['provider']}` · commit `{summary['commit']}` · {summary['started']} · luồng đo DuckDB:"
        f" {summary['threads'] or 'mặc định'} · {summary['runs']} lần đo + 1 khởi động · ca perf {summary['rows']:,} dòng",
        f"- Đúng kết quả kỳ vọng (đáp án đóng băng / truy vấn chuẩn TPC-H): **{summary['correct']}**",
        f"- Đúng model + toán tử điểm nghẽn trong top {summary['top_n']}: **{summary['bottleneck_in_top_n']}**",
        f"- Bản tối ưu được áp dụng: {summary['applied']} · giữ kết quả bản gốc (tự kiểm lại): **{summary['kept_result']}**"
        f" · nhanh hơn vượt nhiễu: {summary['improved_beyond_noise']} · giữ nguyên: {summary['skipped']}",
        f"- Chi phí LLM: {summary['llm_cost_usd']} USD",
        f"- Độ ổn định ({len(rounds)} lượt): **{stable['note']}**"
        + (
            f" (kết luận: {'giống nhau' if stable['conclusions_stable'] else 'khác nhau'};"
            f" thời gian: {'trong ngưỡng nhiễu' if stable['timings_stable'] else 'lệch quá ngưỡng nhiễu'})"
            if stable["checked"]
            else ""
        ),
        *[f"  - {d}" for d in stable.get("differences", [])],
        f"- DAG do agent sinh (tỷ lệ qua lần đầu, qua đủ kiểm tra bắt buộc, số vòng sửa): {llm}",
        f"- Nghiệm thu: **{'đạt' if summary['accepted'] else 'chưa đạt'}**",
        "",
        'Phạm vi: "đúng trên bộ thử", "nhanh hơn trong môi trường đo" (sandbox DuckDB local). Thời gian toàn DAG: chưa đo.',
        "",
        "| Ca | Loại | Đúng | Điểm nghẽn kỳ vọng | Top model:toán tử | Trúng | Quyết định | Giữ kết quả | Trước (IQR) ms |"
        " Sau (IQR) ms | Lợi % | Nhiễu % | Lý do |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        before = f"{_cell(r.get('before_ms'))} ({_cell(r.get('before_iqr_ms'))})"
        after = f"{_cell(r.get('after_ms'))} ({_cell(r.get('after_iqr_ms'))})"
        cells = [r["id"], r["kind"], _cell(r.get("correct")), _cell(r.get("bottleneck_expected", "—")),
                 _cell(r.get("top_models", [])), "—" if r.get("bottleneck_expected", "—") == "—" else _cell(r.get("bottleneck_hit")),
                 _cell(r.get("decision")), _cell(r.get("kept_result")) if r.get("decision") == "applied" else "—",
                 before, after, _cell(r.get("gain_pct")), _cell(r.get("noise_pct")),
                 (r.get("reason") or r.get("detail") or "").replace("|", "/")[:160]]  # fmt: skip
        lines.append("| " + " | ".join(cells) + " |")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeat", type=int, default=1, help="số lượt chạy (2 để kiểm độ ổn định)")
    parser.add_argument("--only", nargs="*", default=[], help="chỉ chạy các ca perf có id này")
    parser.add_argument("--rows", type=int, help="số dòng bộ large (mặc định theo cases.yaml)")
    parser.add_argument("--no-tpch", action="store_true", help="bỏ 13 ca TPC-H")
    parser.add_argument("--sf", type=float, default=0.1, help="kích thước TPC-H (0.1 mặc định; 1 để chạy bổ sung)")
    parser.add_argument("--threads", type=int, default=2, help="số luồng DuckDB cố định khi đo")
    parser.add_argument("--freeze", action="store_true", help="đóng băng đáp án kỳ vọng rồi thoát")
    parser.add_argument("--out", type=Path, default=RESULTS, help="thư mục cha của eval/results/<eval_id>/")
    parser.add_argument("--allow-real-llm", action="store_true", help="cho phép gọi LLM thật (tốn tiền)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    spec = load_cases(args.only)
    rows_large = args.rows or spec["data"]["rows"]["large"]
    with tempfile.TemporaryDirectory(prefix="p113-perf-eval-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp)
        if args.freeze:
            freeze(spec, work, rows_large)
            return 0
        os.environ.update({"WORKSPACES_DIR": str(work / "workspaces"), "OPT_BENCH_THREADS": str(args.threads)})
        if not args.allow_real_llm:  # mặc định không tốn tiền: bỏ qua LLM_PROVIDER trong .env
            os.environ.update({"LLM_PROVIDER": "mock", "LLM_FALLBACK": "none"})
        get_settings.cache_clear()
        settings = get_settings()
        started = datetime.now()
        rounds = []
        for i in range(args.repeat):
            rows = []
            for case in spec["cases"]:
                rows.append(run_case(case, spec, work, rows_large))
                shutil.rmtree(work / "workspaces" / f"perf-{case['id']}", ignore_errors=True)
                print(f"[lượt {i + 1}] {'✓' if rows[-1]['correct'] else '✗'} {case['id']}", flush=True)
            rounds.append(rows + ([] if args.no_tpch else tpch_rows(args.sf)))
        eval_id = f"perf-{started:%Y%m%d-%H%M%S}-{git_sha()}-{settings.llm_provider}"
        meta = {
            "eval_id": eval_id,
            "provider": settings.llm_provider,
            "commit": git_sha(),
            "started": started.isoformat(timespec="seconds"),
            "threads": args.threads,
            "runs": settings.opt_bench_runs,
            "rows": rows_large,
            "top_n": settings.perf_top_n,
        }
        summary = summarize(rounds[-1], stability(rounds), meta)
        write_outputs(args.out / eval_id, rounds[-1], rounds, summary)
    print(
        json.dumps(
            {k: summary[k] for k in ("eval_id", "correct", "bottleneck_in_top_n", "accepted")}, ensure_ascii=False
        )
    )
    print(f"Kết quả: {args.out / eval_id}")
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())

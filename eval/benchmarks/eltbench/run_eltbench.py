"""Chạy ELT-Bench-Verified (10 pipeline nhẹ nhất) trên hệ thống P-113. Dữ liệu có sẵn ở eval/datasets/eltbench/.

Bốn chế độ:
- `--mode selfcheck`: nạp từng bảng kết quả đúng (có kiểu, như bảng agent sinh ra) rồi chấm chính nó → phải khớp hết.
  Bộ chấm phải qua bước này trước khi chấm agent. Không cần LLM.
- `--mode reference`: chạy model dbt chuẩn (nếu có) qua E0 nạp nguồn + V1 an toàn, so với bảng kết quả đúng.
  Dùng để kiểm chứng bộ chấm (nạp dữ liệu, kiểu dữ liệu, cách so) trước khi chấm agent. Không cần LLM.
- `--mode agent`: mỗi model một lần chạy trọn luồng (yêu cầu = mô tả trong data_model.yaml), tự duyệt (chỉ cho eval),
  rồi so bảng đích với bảng kết quả đúng. Chỉ có ý nghĩa với LLM thật; với `mock` ghi "không áp dụng (mô phỏng)".
  Mỗi model lưu vào eval/results/eltbench_runs/<đợt>/<task>__<model>/: output.parquet (bảng đích), models/ (SQL dbt
  agent sinh), meta.json (trạng thái, token, chi phí…). Điểm luôn tính từ các file đã lưu này.
- `--regrade <đợt>`: chấm lại một đợt đã lưu bằng bộ chấm hiện tại — 0 token, không chạy lại agent.

    python eval/benchmarks/eltbench/run_eltbench.py --mode selfcheck
    python eval/benchmarks/eltbench/run_eltbench.py --mode reference
    python eval/benchmarks/eltbench/run_eltbench.py --mode agent --provider openai
    python eval/benchmarks/eltbench/run_eltbench.py --regrade 2026-10-02_1327
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path

import duckdb
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from gt_compare import compare_to_ground_truth  # noqa: E402

from src.agents import runner  # noqa: E402
from src.agents.nodes.safety import check_sql  # noqa: E402
from src.agents.runner import ResumeRequest, RunOutcome  # noqa: E402
from src.agents.tools.duckdb_tools import discover_sources, ingest_sources, read_catalog, run_query  # noqa: E402
from src.agents.tools.sql_tools import render_dbt_sql  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.models.evidence import ReviewDecision  # noqa: E402

DATA_DIR = ROOT / "eval" / "datasets" / "eltbench"
WORK_DIR = ROOT / "data" / "eltbench_work"  # sandbox tạm (git-ignored)
REFERENCE_DIR = HERE / "reference"
REPORT = ROOT / "eval" / "results" / "eltbench_report.md"
RUNS_DIR = ROOT / "eval" / "results" / "eltbench_runs"  # đầu ra đã lưu của từng đợt chạy agent
META_KEYS = ("run_id", "status", "auto_answers", "fix_attempts", "rescue", "tokens", "cost_usd", "seconds")
KNOWN_ISSUES = HERE / "known_issues.yaml"
LOW_CONFIDENCE_ROWS = 5  # bảng đúng ≤ 5 dòng: khớp có thể do may, mức tin cậy thấp
EVAL_USER, EVAL_REVIEWER = "eltbench-eval", "eltbench-auto-reviewer"


def task_names() -> list[str]:
    """Danh sách task đã chọn."""
    return [t["name"] for t in yaml.safe_load((HERE / "tasks.yaml").read_text(encoding="utf-8"))["tasks"]]


def models_of(task: str) -> list[dict]:
    """Các model (bảng đích) cần xây của một task, kèm mô tả cột."""
    return yaml.safe_load((DATA_DIR / task / "data_model.yaml").read_text(encoding="utf-8"))["models"]


def known_issues() -> dict[tuple[str, str], frozenset[str]]:
    """(task, model) → cột đề yêu cầu nhưng bảng đúng không có (lỗi benchmark, xem known_issues.yaml)."""
    items = yaml.safe_load(KNOWN_ISSUES.read_text(encoding="utf-8"))["issues"]
    return {(i["task"], i["model"]): frozenset(c.lower() for c in i["columns_in_spec_not_in_truth"]) for i in items}


def ground_truth_path(task: str, model: str) -> Path:
    """Đường dẫn bảng kết quả đúng của một model."""
    return DATA_DIR / task / "ground_truth" / f"{model}.csv"


def ground_truth_rows(task: str, model: str) -> int:
    """Số dòng của bảng kết quả đúng."""
    with duckdb.connect() as con:
        path = ground_truth_path(task, model).as_posix()
        return con.sql(f"SELECT count(*) FROM read_csv('{path}', header = true, all_varchar = true)").fetchone()[0]


def grade(task: str, model: str, columns: list[str], rows: list[tuple]) -> dict:
    """Chấm hai cách: nghiêm (gồm lỗi benchmark) và bỏ cột lỗi benchmark. Kèm cờ model có lỗi benchmark."""
    path = ground_truth_path(task, model)
    ok, detail = compare_to_ground_truth(columns, rows, path)
    ignored = known_issues().get((task, model), frozenset())
    ok_lenient = compare_to_ground_truth(columns, rows, path, ignored)[0] if ignored else ok
    return {"ok": ok, "known_issue": bool(ignored), "ok_if_issue_ignored": ok_lenient, "detail": detail}


def check_ground_truth(task: str, model: str) -> dict:
    """Tự kiểm bộ chấm: nạp bảng đúng có kiểu (DuckDB tự nhận kiểu, như bảng agent sinh ra) rồi chấm chính nó."""
    with duckdb.connect() as con:
        path = ground_truth_path(task, model).as_posix()
        rel = con.sql(f"SELECT * FROM read_csv('{path}', header = true, sample_size = -1)")
        columns, rows = rel.columns, rel.fetchall()
    ok, detail = compare_to_ground_truth(columns, rows, ground_truth_path(task, model))
    return {"task": task, "model": model, "gt_rows": len(rows), "ok": ok, "detail": detail}


def run_selfcheck() -> list[dict]:
    """Chế độ selfcheck cho mọi model có bảng kết quả đúng."""
    return [
        check_ground_truth(task, model["name"])
        for task in task_names()
        for model in models_of(task)
        if ground_truth_path(task, model["name"]).exists()
    ]


def request_text(model: dict) -> str:
    """Yêu cầu bằng lời cho Planner, dựng từ data_model.yaml (giữ nguyên mô tả gốc tiếng Anh)."""
    columns = "\n".join(f"- {c['name']}: {str(c.get('description', '')).strip()}" for c in model.get("columns", []))
    return (
        f"Xây bảng đích `{model['name']}` từ các bảng nguồn có sẵn. Mô tả: {model.get('description', '')}\n"
        f"Các cột đầu ra (giữ đúng tên cột):\n{columns}"
    )


def load_task_db(task: str) -> Path:
    """Nạp nguồn của task vào một sandbox tạm (qua E0) — dùng cho chế độ reference."""
    work = WORK_DIR / task
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    db = work / "sandbox.duckdb"
    ingest_sources(db, discover_sources(DATA_DIR / task / "sources"))
    return db


def check_reference(task: str, sql_path: Path, db: Path) -> dict:
    """Model chuẩn → V1 → chạy → so bảng đúng."""
    sql = sql_path.read_text(encoding="utf-8")
    issues = check_sql(sql, read_catalog(db))[0]
    if issues:
        return {"task": task, "model": sql_path.stem, "ok": False, "detail": "V1 chặn: " + "; ".join(issues)[:200]}
    result = run_query(db, render_dbt_sql(sql))
    ok, detail = compare_to_ground_truth(result.columns, result.rows, ground_truth_path(task, sql_path.stem))
    return {"task": task, "model": sql_path.stem, "ok": ok, "detail": detail}


def run_reference() -> list[dict]:
    """Chế độ reference cho mọi task có model chuẩn."""
    rows = []
    for task in task_names():
        sql_files = sorted((REFERENCE_DIR / task).glob("*.sql"))
        db = load_task_db(task) if sql_files else None
        rows += [check_reference(task, path, db) for path in sql_files]
    return rows


def _drive(outcome: RunOutcome) -> tuple[RunOutcome, int]:
    """Đi qua các điểm dừng: J1 chọn đáp án đầu (ghi lại số lần), J1b đồng ý, cứu hộ → dừng, J2 → tự duyệt (chỉ cho eval)."""
    auto_answers = 0
    while outcome.pending:
        kind = outcome.pending["kind"]
        if kind == "clarify":
            auto_answers += len(outcome.pending["questions"])
            value = {"answers": {q["id"]: q["options"][0] for q in outcome.pending["questions"]}}
        elif kind == "plan":
            value = {"decision": "approve"}
        elif kind == "rescue":
            value = {"action": "abort"}
        else:
            decision = ReviewDecision(run_id=outcome.run_id, reviewer=EVAL_REVIEWER, decision="approve", note="eval")
            return runner.submit_review(decision, "reviewer"), auto_answers
        outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind=kind, value=value))
    return outcome, auto_answers


def save_output(batch: Path, task: str, model: str, meta: dict, workspace: Path, target: str) -> None:
    """Lưu đầu ra một lần chạy: meta.json, SQL dbt agent sinh (models/), bảng đích (output.parquet nếu đã duyệt)."""
    out = batch / f"{task}__{model}"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for path in (workspace / "models").rglob("*"):
        if path.suffix in (".sql", ".yml"):
            (out / "models" / path.relative_to(workspace / "models")).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, out / "models" / path.relative_to(workspace / "models"))
    meta = {"task": task, "model": model, "target": target, "error": "", **meta}
    if meta["status"] == "approved":
        try:
            with duckdb.connect(str(workspace / "sandbox.duckdb"), read_only=True) as con:
                con.sql(f'SELECT * FROM main."{target}"').write_parquet(str(out / "output.parquet"))
        except duckdb.Error as exc:
            meta["error"] = f"Không đọc được bảng đích: {str(exc).splitlines()[0][:150]}"
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def grade_saved(folder: Path) -> dict:
    """Chấm một model từ đầu ra đã lưu (dùng chung cho chế độ agent và --regrade)."""
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    task, model = meta["task"], meta["model"]
    row = {"task": task, "model": model, **{k: meta.get(k, "") for k in META_KEYS}}
    row |= {"gt_rows": ground_truth_rows(task, model), "ok": False, "known_issue": (task, model) in known_issues()}
    row |= {"ok_if_issue_ignored": False, "detail": meta.get("error", "")}
    output = folder / "output.parquet"
    if meta["status"] == "approved" and output.exists():
        with duckdb.connect() as con:
            rel = con.sql(f"SELECT * FROM read_parquet('{output.as_posix()}')")
            row |= grade(task, model, rel.columns, rel.fetchall())
    elif meta["status"] == "approved" and not row["detail"]:
        row["detail"] = "Thiếu output.parquet"
    return row


def regrade(batch: Path) -> list[dict]:
    """Chấm lại mọi model của một đợt đã lưu, theo thứ tự trong tasks.yaml."""
    order = {(t, m["name"]): i for i, (t, m) in enumerate((t, m) for t in task_names() for m in models_of(t))}
    rows = [grade_saved(meta.parent) for meta in batch.glob("*/meta.json")]
    return sorted(rows, key=lambda r: order.get((r["task"], r["model"]), len(order)))


def run_agent_model(task: str, model: dict, batch: Path) -> dict:
    """Một lần chạy trọn luồng cho một model, lưu đầu ra, rồi chấm từ file đã lưu."""
    os.environ["SOURCES_DIR"] = str(DATA_DIR / task / "sources")
    get_settings.cache_clear()
    start = time.perf_counter()
    outcome, auto_answers = _drive(runner.start_run(request_text(model), EVAL_USER))
    values = runner.get_values(outcome.run_id)
    meta = {
        "run_id": outcome.run_id,
        "status": str(outcome.status),
        "auto_answers": auto_answers,
        "fix_attempts": values.get("fix_attempts", 0),
        "rescue": values.get("rescue_count", 0),
        "tokens": sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in values.get("llm_usage", [])),
        "cost_usd": sum(u.get("cost_usd", 0.0) for u in values.get("llm_usage", [])),
        "seconds": round(time.perf_counter() - start, 1),
    }
    target = values.get("spec", {}).get("target", "")
    save_output(batch, task, model["name"], meta | {"error": outcome.error or ""}, Path(values["workspace"]), target)
    return grade_saved(batch / f"{task}__{model['name']}")


def new_batch() -> Path:
    """Thư mục cho một đợt chạy agent, kèm batch.json (ngày, provider/model)."""
    settings = get_settings()
    batch = RUNS_DIR / datetime.now().strftime("%Y-%m-%d_%H%M")
    batch.mkdir(parents=True, exist_ok=True)
    info = {"date": date.today().isoformat(), "provider_model": f"{settings.llm_provider}/{settings.models_summary}"}
    (batch / "batch.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return batch


def run_agent() -> list[dict]:
    """Chế độ agent cho mọi model có bảng kết quả đúng; trả các dòng đã chấm."""
    batch, rows = new_batch(), []
    for task in task_names():
        for model in models_of(task):
            if ground_truth_path(task, model["name"]).exists():
                rows.append(run_agent_model(task, model, batch))
                print(f"{'✓' if rows[-1]['ok'] else '✗'} {task}.{model['name']}: {rows[-1]['detail']}", flush=True)
    write_report("agent", rows, batch)
    return rows


def _header(mode: str, batch: Path | None) -> list[str]:
    settings = get_settings()
    if batch is None:
        when, who = date.today().isoformat(), "không dùng LLM (0 token)"
        if mode == "agent":
            who = f"{settings.llm_provider}/{settings.models_summary}"
    else:
        info = json.loads((batch / "batch.json").read_text(encoding="utf-8"))
        when, who = info["date"], info["provider_model"]
    lines = [
        f"# ELT-Bench-Verified — chế độ `{mode}`",
        "",
        f"- Ngày chạy: {when} • provider/model: {who}",
        "- Dữ liệu: 10 pipeline nhẹ nhất (eval/benchmarks/eltbench/tasks.yaml); ELT-Bench-Verified, CC BY-SA 4.0.",
    ]
    if batch is not None:
        relative = batch.relative_to(ROOT).as_posix()
        lines.append(f"- Đầu ra đã lưu: `{relative}/` • chấm bằng bộ chấm hiện tại ngày {date.today().isoformat()}")
    return [*lines, ""]


def summary_lines(rows: list[dict]) -> list[str]:
    """Hai số (gồm / không gồm model lỗi benchmark), độ tin cậy theo số dòng, cách trả lời câu hỏi làm rõ."""
    passed = sum(r["ok"] for r in rows)
    lines = [f"**Khớp bảng kết quả đúng: {passed}/{len(rows)} model**", ""]
    if not rows or "known_issue" not in rows[0]:
        return lines
    clean = [r for r in rows if not r["known_issue"]]
    issue_rows = [r for r in rows if r["known_issue"]]
    small = [r for r in rows if r["gt_rows"] <= LOW_CONFIDENCE_ROWS]
    return lines + [
        f"- **Gồm** {len(issue_rows)} model lỗi benchmark (chấm nghiêm, như benchmark gốc): {passed}/{len(rows)}",
        f"- **Không gồm** (bỏ {len(issue_rows)} model ở known_issues.yaml khỏi mẫu số): "
        f"{sum(r['ok'] for r in clean)}/{len(clean)}",
        f"- Nếu bỏ qua cột lỗi benchmark thay vì bỏ model: {sum(r['ok_if_issue_ignored'] for r in rows)}/{len(rows)}",
        f"- Độ tin cậy thấp: {len(small)}/{len(rows)} bảng đúng có ≤ {LOW_CONFIDENCE_ROWS} dòng "
        f"(khớp trong số đó: {sum(r['ok'] for r in small)}/{len(small)}). Cột `gt_rows` = số dòng bảng đúng.",
        "- Câu hỏi làm rõ (J1): bộ chạy tự chọn **đáp án đầu tiên** (`options[0]`) cho mọi câu (cột `auto_answers`). "
        "Đây là đo *agent khi người trả lời bừa*, không phải *agent có người thật trả lời*.",
        "",
    ]


def write_report(mode: str, rows: list[dict], batch: Path | None = None) -> None:
    """Ghi báo cáo (chỉ số đo thật). Đợt agent: ghi cả <đợt>/report.md và eltbench_agent.md (bản mới nhất)."""
    lines = _header(mode, batch)
    if mode == "agent" and get_settings().is_mock:
        lines.append("Không áp dụng (mô phỏng): LLM mock chỉ có câu trả lời viết sẵn cho kịch bản doanh thu ngày.")
    else:
        lines += summary_lines(rows)
        keys = [k for k in rows[0] if k not in ("task", "model")] if rows else []
        lines += ["| Task | Model | " + " | ".join(keys) + " |", "|---|---|" + "---|" * len(keys)]
        lines += [f"| {r['task']} | {r['model']} | " + " | ".join(str(r[k]) for k in keys) + " |" for r in rows]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = REPORT.with_name(f"eltbench_{mode}.md")
    for path in [report] + ([batch / "report.md"] if batch else []):
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Đã ghi {path}")


def main() -> None:
    """Chạy theo chế độ đã chọn."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=("selfcheck", "reference", "agent"), default="reference")
    parser.add_argument("--provider", choices=("mock", "openai", "google"), help="Ghi đè LLM_PROVIDER")
    parser.add_argument("--regrade", metavar="ĐỢT", help="Chấm lại đợt đã lưu trong eval/results/eltbench_runs/")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
    get_settings.cache_clear()
    if not DATA_DIR.exists():
        sys.exit(
            "Chưa có dữ liệu. Chạy trước: python eval/benchmarks/eltbench/import_eltbench.py --src <thư mục tải về>"
        )
    if args.regrade:
        batch = RUNS_DIR / args.regrade
        if not (batch / "batch.json").exists():
            sys.exit(f"Không thấy đợt {batch}")
        write_report("agent", regrade(batch), batch)
    elif args.mode == "agent":
        if get_settings().is_mock:
            write_report("agent", [])
        else:
            run_agent()
    else:
        write_report(args.mode, run_selfcheck() if args.mode == "selfcheck" else run_reference())


if __name__ == "__main__":
    main()

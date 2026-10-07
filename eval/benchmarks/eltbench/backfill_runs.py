"""Lưu lại đầu ra của một đợt agent đã chạy TRƯỚC khi có B2 (từ workspace còn trên đĩa), để `--regrade` chấm lại 0 token.

Ghép mỗi dòng của báo cáo cũ (eltbench_agent.md) với lần chạy trong data/app.db: cùng requester `eltbench-eval`,
cùng nguyên văn yêu cầu (request_text của đúng task), trong khung giờ của đợt; lấy lần mới nhất. Trạng thái trong DB
phải khớp báo cáo cũ, nếu không thì dừng. Số đo (token, chi phí, giây, auto_answers) lấy nguyên từ báo cáo cũ.

    python eval/benchmarks/eltbench/backfill_runs.py --old-report eval/results/eltbench_agent.md \\
        --since 2026-10-02T13:27 --until 2026-10-02T14:40 --batch 2026-10-02_1327
"""

import argparse
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_eltbench  # noqa: E402

from src.agents import runner  # noqa: E402
from src.config import get_settings  # noqa: E402


def parse_report(text: str) -> tuple[str, str, dict[tuple[str, str], dict]]:
    """(ngày, provider/model, {(task, model): số đo}) từ báo cáo agent cũ."""
    when = re.search(r"Ngày chạy: (\S+)", text).group(1)
    who = re.search(r"provider/model: (.+)", text).group(1).strip()
    header, rows = None, {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[:2] == ["Task", "Model"]:
            header = cells
        elif header and len(cells) == len(header) and not cells[0].startswith("---"):
            item = dict(zip(header, cells, strict=True))
            rows[(item["Task"], item["Model"])] = item
    return when, who, rows


def find_run(con: sqlite3.Connection, request: str, since: str, until: str) -> tuple[str, str]:
    """(run_id, trạng thái) của lần chạy mới nhất có đúng yêu cầu trong khung giờ."""
    found = con.execute(
        "SELECT id, status FROM runs WHERE requester = ? AND request_text = ? AND created_at >= ? AND created_at < ? "
        "ORDER BY created_at DESC LIMIT 1",
        (run_eltbench.EVAL_USER, request, since, until),
    ).fetchone()
    if not found:
        sys.exit(f"Không thấy lần chạy cho yêu cầu: {request[:80]}")
    return found


def main() -> None:
    """Ghép báo cáo cũ với lần chạy, lưu đầu ra vào eval/results/eltbench_runs/<đợt>/."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old-report", type=Path, required=True)
    parser.add_argument("--since", required=True, help="ISO, vd 2026-10-02T13:27")
    parser.add_argument("--until", required=True)
    parser.add_argument("--batch", required=True, help="tên thư mục đợt")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = args.old_report.read_text(encoding="utf-8")
    when, who, old = parse_report(text)
    batch = run_eltbench.RUNS_DIR / args.batch
    batch.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.old_report, batch / "report_original.md")
    info = {"date": when, "provider_model": who, "backfilled_from": args.old_report.as_posix()}
    (batch / "batch.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    models = {(t, m["name"]): m for t in run_eltbench.task_names() for m in run_eltbench.models_of(t)}
    with sqlite3.connect(get_settings().store_path) as con:
        for (task, name), item in old.items():
            run_id, status = find_run(con, run_eltbench.request_text(models[(task, name)]), args.since, args.until)
            if status != item["status"]:
                sys.exit(f"{task}.{name}: DB ghi {status}, báo cáo cũ ghi {item['status']}")
            values = runner.get_values(run_id)
            meta = {"run_id": run_id, "status": status, "error": item["detail"] if status != "approved" else ""}
            meta |= {k: json.loads(item[k].lower()) for k in run_eltbench.META_KEYS if k not in ("run_id", "status")}
            target = values.get("spec", {}).get("target", "")
            run_eltbench.save_output(batch, task, name, meta, Path(values["workspace"]), target)
            print(f"✓ {task}.{name} ← {run_id}")
    print(f"Đã lưu {len(old)} model vào {batch}")


if __name__ == "__main__":
    main()

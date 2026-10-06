"""So thời gian agent với DE làm tay (eval/baseline/human_baseline.csv) và đo công Reviewer từ kho lần chạy.

Dùng trong eval/run_eval.py (mục 2–3 của report.md). Chỉ dùng số đã đo: ô trống hoặc chưa có dữ liệu ghi `—`.
"""

import csv
import difflib
import sqlite3
from collections.abc import Callable
from pathlib import Path
from statistics import median

BASELINE_CSV = Path(__file__).resolve().parent / "human_baseline.csv"
COLUMNS = ["case_id", "người_làm", "kinh_nghiệm", "phút", "ghi_chú", "ngày"]
AUTO_REVIEWER_SUFFIX = "-auto-reviewer"  # tài khoản tự duyệt của eval/ELT-Bench: không phải công người thật


def _number(text: str) -> float | None:
    try:
        return float(text.replace(",", ".")) if text.strip() else None
    except ValueError:
        return None


def load_baseline(path: Path = BASELINE_CSV) -> list[dict]:
    """Các dòng DE đã đo (có case_id và số phút hợp lệ); dòng trống hoặc sai số bị bỏ qua."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"{path.name}: tiêu đề phải là {','.join(COLUMNS)} (đang là {reader.fieldnames})")
        rows = []
        for raw in reader:
            minutes = _number(raw.get("phút") or "")
            case_id = (raw.get("case_id") or "").strip()
            if case_id and minutes is not None and minutes > 0:
                rows.append(
                    {**raw, "case_id": case_id, "phút": minutes, "kinh_nghiệm": _number(raw["kinh_nghiệm"] or "")}
                )
        return rows


def per_case(rows: list[dict]) -> dict[str, dict]:
    """Mỗi ca: trung vị số phút, số người làm, khoảng kinh nghiệm."""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["case_id"], []).append(row)
    result = {}
    for case_id, items in grouped.items():
        years = sorted(r["kinh_nghiệm"] for r in items if r["kinh_nghiệm"] is not None)
        span = "—" if not years else f"{years[0]:g}" if years[0] == years[-1] else f"{years[0]:g}–{years[-1]:g}"
        result[case_id] = {"minutes": median(r["phút"] for r in items), "people": len(items), "experience": span}
    return result


def _fmt_minutes(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}".replace(".", ",")


def compare_lines(human: dict[str, dict], agent: dict | None) -> list[str]:
    """Bảng từng ca: thời gian agent, DE làm tay, tỉ lệ agent / DE."""
    agent_rows = {r["case"]: r for r in (agent or {}).get("rows", [])}
    cases = sorted(set(agent_rows) | set(human))
    lines = [
        "| Ca | Agent (phút) | DE làm tay (phút, trung vị) | Số DE | Kinh nghiệm (năm) | Agent / DE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for case in cases:
        a = agent_rows.get(case)
        agent_min = a["seconds"] / 60 if a else None
        h = human.get(case)
        ratio = f"{agent_min / h['minutes']:.2f}".replace(".", ",") if agent_min is not None and h else "—"
        note = "" if not a or a.get("ok") else " (sai)"
        lines.append(
            f"| {case} | {_fmt_minutes(agent_min)}{note} | {_fmt_minutes(h['minutes'] if h else None)} | "
            f"{h['people'] if h else '—'} | {h['experience'] if h else '—'} | {ratio} |"
        )
    return lines


def summary_ratio(human: dict[str, dict], agent: dict | None) -> str:
    """Tổng thời gian agent / tổng thời gian DE trên các ca có cả hai số đo."""
    agent_rows = {r["case"]: r for r in (agent or {}).get("rows", [])}
    both = [c for c in human if c in agent_rows]
    if not both:
        return "— (chưa có DE làm tay)"
    agent_total = sum(agent_rows[c]["seconds"] / 60 for c in both)
    human_total = sum(human[c]["minutes"] for c in both)
    return f"{agent_total / human_total:.2f} ({len(both)} ca)".replace(".", ",")


def changed_lines(before: dict[str, str], after: dict[str, str]) -> int:
    """Số dòng thêm + xóa giữa hai bộ file (file mới/xóa tính toàn bộ dòng)."""
    total = 0
    for path in set(before) | set(after):
        old, new = before.get(path, "").splitlines(), after.get(path, "").splitlines()
        diff = difflib.unified_diff(old, new, lineterm="", n=0)
        total += sum(1 for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---")))
    return total


def reviewer_effort(runs: list[dict]) -> dict:
    """Công Reviewer từ các lần chạy có người duyệt thật.

    Mỗi phần tử: {"decisions": ["reject", "approve", ...] theo thời gian, "changed_lines": int | None}.
    """
    decided = [r for r in runs if r["decisions"]]
    if not decided:
        return {"runs": 0, "approved_first": None, "avg_changed_lines": None, "rejected_runs": 0, "who": ""}
    rejected = [r for r in decided if "reject" in r["decisions"]]
    measured = [r["changed_lines"] for r in rejected if r.get("changed_lines") is not None]
    return {
        "runs": len(decided),
        "approved_first": sum(r["decisions"][0] == "approve" for r in decided) / len(decided),
        "avg_changed_lines": sum(measured) / len(measured) if measured else None,
        "rejected_runs": len(rejected),
        "who": ", ".join(sorted({f"{r['reviewer']} {r['day']}" for r in decided if r.get("reviewer")})),
    }


def collect_reviews(store_path: Path, get_values: Callable[[str], dict] | None = None) -> list[dict]:
    """Quyết định J2 của người thật (bỏ tài khoản tự duyệt) theo lần chạy, kèm số dòng đổi sau lần từ chối gần nhất."""
    if not store_path.exists():
        return []
    with sqlite3.connect(f"file:{store_path.as_posix()}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "SELECT run_id, reviewer, decision, decided_at FROM reviews ORDER BY decided_at, id"
        ).fetchall()
    by_run: dict[str, list[str]] = {}
    who: dict[str, tuple[str, str]] = {}
    for run_id, reviewer, decision, decided_at in rows:
        if not str(reviewer).endswith(AUTO_REVIEWER_SUFFIX):
            by_run.setdefault(run_id, []).append(str(decision))
            who[run_id] = (str(reviewer), str(decided_at)[:10])
    runs = []
    for run_id, decisions in by_run.items():
        lines = None
        if "reject" in decisions and get_values is not None:
            values = get_values(run_id)
            current = {**values.get("code_files", {}), **values.get("test_files", {})}
            lines = changed_lines(values.get("previous_files", {}), current) if values.get("previous_files") else None
        reviewer, day = who[run_id]
        runs.append(
            {"run_id": run_id, "decisions": decisions, "changed_lines": lines, "reviewer": reviewer, "day": day}
        )
    return runs


def reviewer_lines(effort: dict) -> list[str]:
    """Dòng bảng công Reviewer."""
    if not effort["runs"]:
        return ["| Công Reviewer | — (chưa có quyết định của người duyệt thật) |"]
    rate = f"{effort['approved_first']:.0%}"
    avg = effort["avg_changed_lines"]
    changed = "—" if avg is None else f"{avg:.0f} dòng / lần chạy bị từ chối ({effort['rejected_runs']} lần chạy)"
    source = f"; người duyệt và ngày: {effort['who']}" if effort.get("who") else ""
    return [
        f"| Công Reviewer: duyệt ngay vòng đầu | {rate} ({effort['runs']} lần chạy có người duyệt thật{source}) |",
        f"| Công Reviewer: số dòng code đổi sau khi từ chối | {changed} |",
    ]

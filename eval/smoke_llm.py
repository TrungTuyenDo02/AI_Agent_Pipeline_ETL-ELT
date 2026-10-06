"""U2 — thử LLM thật sớm (`make smoke-llm`): 3 yêu cầu golden chạy qua Planner (+ tự trả lời J1) → Codegen.

Ghi mỗi lần gọi: model, provider THỰC SỰ trả lời (google = OpenAI lỗi, đã chuyển dự phòng), token vào/ra,
`cached_tokens`, chi phí ước tính, thời gian. Code sinh ra được kiểm thêm bằng V1 (code, 0 token) để biết có dùng được.
Kho lưu trữ/sổ lỗi/workspace dùng thư mục tạm riêng (data/eval_work/smoke_llm), không lẫn dữ liệu thật.
Cần khóa trong .env (LLM_PROVIDER=openai); với mock chỉ ghi "mô phỏng".

    python eval/smoke_llm.py
"""

import json
import os
import shutil
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "eval_work" / "smoke_llm"
os.environ.update(
    {
        "STORE_PATH": str(WORK / "app.db"),
        "CHECKPOINT_PATH": str(WORK / "checkpoints.db"),
        "WORKSPACES_DIR": str(WORK / "workspaces"),
        "LANGCHAIN_TRACING_V2": "false",
    }
)
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from src.agents.nodes.codegen import codegen_node  # noqa: E402
from src.agents.nodes.ingest import ingest_node  # noqa: E402
from src.agents.nodes.planner import planner_node  # noqa: E402
from src.agents.nodes.profiler import profiler_node  # noqa: E402
from src.agents.nodes.safety import run_safety_checks  # noqa: E402
from src.agents.nodes.spec_check import check_spec  # noqa: E402
from src.agents.nodes.testgen import generic_tests  # noqa: E402
from src.agents.tools.duckdb_tools import discover_sources  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.models.spec import PipelineSpec  # noqa: E402
from src.services.cost import cache_hit_rate  # noqa: E402

CASES = ("g01_three_sources", "g06_one_to_many_join", "g09_customer_dimension")
GOLDEN = ROOT / "eval" / "datasets" / "golden"
RESULTS = ROOT / "eval" / "results"
MAX_PLAN_ROUNDS = 3


def _choose(question: dict, prefer: list[str]) -> str:
    for option in question["options"]:
        if any(word.lower() in option.lower() for word in prefer):
            return option
    return question["options"][0]


def plan(state: dict, prefer: list[str]) -> list[dict]:
    """Planner ⇄ J1 (tự chọn đáp án như eval) cho tới khi hết câu hỏi hoặc hết lượt; trả các lần gọi LLM."""
    calls: list[dict] = []
    for _ in range(MAX_PLAN_ROUNDS):
        result = planner_node(state)
        calls += result.pop("llm_usage", [])
        state.update(result)
        questions = state.get("spec", {}).get("questions") or []
        if not questions:
            break
        chosen = {q["id"]: _choose(q, prefer) for q in questions}
        state["answers"] = {**state.get("answers", {}), **chosen}
        state["answered"] = [
            *state.get("answered", []),
            *({"id": q["id"], "question": q["question"], "answer": chosen[q["id"]]} for q in questions),
        ]
    return calls


def run_case(case: str) -> dict:
    """Một yêu cầu: Planner → V0 → nạp nguồn → soi dữ liệu → Codegen → V1."""
    folder = GOLDEN / case
    meta = yaml.safe_load((folder / "meta.yaml").read_text(encoding="utf-8"))
    state: dict = {
        "run_id": f"smoke-{case}",
        "request_text": (folder / "request.txt").read_text(encoding="utf-8").strip(),
        "requester": "smoke",
        "source_catalog": [s.model_dump() for s in discover_sources(folder / "sources")],
    }
    started = time.perf_counter()
    usage = plan(state, meta.get("clarify_prefer", []))
    spec_errors = check_spec(state.get("spec", {}), state["source_catalog"])
    row: dict = {
        "case": case,
        "plan_rounds": state.get("plan_rounds", 0),
        "spec_errors": spec_errors,
        "questions": [f"{a['question']} → {a['answer']}" for a in state.get("answered", [])],
    }
    if not spec_errors:
        state.update(ingest_node(state))
        state.update(profiler_node(state))
        generated = codegen_node(state)
        usage += generated.get("llm_usage", [])
        state["code_files"] = generated["code_files"]
        state["test_files"] = generic_tests(PipelineSpec.model_validate(state["spec"]))
        issues = run_safety_checks(state)
        row.update(files=sorted(state["code_files"]), v1_issues=issues[:3], v1_passed=not issues)
    row.update(seconds=round(time.perf_counter() - started, 1), calls=usage)
    return row


def write_report(rows: list[dict]) -> None:
    """eval/results/smoke_llm.md + .json: chỉ số đo thật."""
    settings = get_settings()
    calls = [c for r in rows for c in r["calls"]]
    simulated = any(c.get("simulated") for c in calls)
    rate = cache_hit_rate(calls)
    lines = [
        "# Smoke test LLM thật (U2)",
        "",
        f"- Ngày chạy: {date.today().isoformat()} • provider/model cấu hình: {settings.llm_provider}/{settings.models_summary}",
        f"- Structured output: {'bật' if settings.llm_structured_output else 'tắt'} • prompt v2 • 3 yêu cầu golden (dữ liệu nhỏ).",
        "- Luồng: Planner (tự chọn đáp án J1 như eval) → V0 → nạp nguồn → soi dữ liệu → Codegen → V1 (code, 0 token).",
        "- Chi phí là ƯỚC TÍNH theo bảng giá trong `src/services/cost.py`, chưa trừ giảm giá cache.",
    ]
    if simulated:
        lines.append("- **MÔ PHỎNG (mock)**: token = 0, không phản ánh LLM thật.")
    lines += [
        "",
        "| Ca | Lượt Planner | V0 | V1 | Thời gian |",
        "|---|---:|---|---|---:|",
    ]
    for r in rows:
        v0 = "đạt" if not r["spec_errors"] else "✗ " + "; ".join(r["spec_errors"])[:80]
        v1 = "—" if "v1_passed" not in r else ("đạt" if r["v1_passed"] else "✗ " + "; ".join(r["v1_issues"])[:100])
        lines.append(f"| {r['case']} | {r['plan_rounds']} | {v0} | {v1} | {r['seconds']} s |")
    asked = [(r["case"], q) for r in rows for q in r.get("questions", [])]
    lines += ["", "Câu hỏi làm rõ Planner đặt ra (ca golden đều đã nói rõ, kỳ vọng không hỏi):", ""]
    lines += [f"- {case}: {q}" for case, q in asked] or ["- (không hỏi câu nào)"]
    lines += [
        "",
        "| Ca | Bước | Provider trả lời | Model | Token vào | Trúng cache | Token ra | Chi phí (USD) | Thời gian |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        for c in r["calls"]:
            lines.append(
                f"| {r['case']} | {c['task']} | {c['provider']} | {c['model']} | {c['input_tokens']} | "
                f"{c.get('cached_tokens', 0)} | {c['output_tokens']} | {c['cost_usd']:.6f} | {c['latency_ms'] / 1000:.1f} s |"
            )
    total_in = sum(c["input_tokens"] for c in calls)
    total_out = sum(c["output_tokens"] for c in calls)
    fallback = sum(c["provider"] == "google" and settings.llm_provider == "openai" for c in calls)
    lines += [
        "",
        f"**Tổng:** {len(calls)} lần gọi • {total_in} token vào • {total_out} token ra • "
        f"{sum(c['cost_usd'] for c in calls):.6f} USD • tỉ lệ token vào trúng cache: "
        f"{'—' if rate is None else f'{rate:.1%}'} • số lần phải chuyển dự phòng Gemini: {fallback}",
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "smoke_llm.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {"provider": settings.llm_provider, "models": settings.models_summary, "rows": rows}
    (RESULTS / "smoke_llm.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    """Chạy 3 ca và ghi báo cáo."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    shutil.rmtree(WORK, ignore_errors=True)
    get_settings.cache_clear()
    rows = []
    for case in CASES:
        rows.append(run_case(case))
        r = rows[-1]
        print(f"{case}: V0 {'đạt' if not r['spec_errors'] else r['spec_errors']} • V1 {r.get('v1_passed', '—')} "
              f"• {[(c['task'], c['provider'], c['input_tokens'], c.get('cached_tokens'), c['output_tokens']) for c in r['calls']]}",
              flush=True)  # fmt: skip
    write_report(rows)
    print(f"Đã ghi {RESULTS / 'smoke_llm.md'}")


if __name__ == "__main__":
    main()

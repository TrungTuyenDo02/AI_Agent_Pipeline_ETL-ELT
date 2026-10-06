"""Đo token của prompt từng node (offline, không cần khóa) trên 3 ca golden có đầu ra LLM thật.

Phần tĩnh = system prompt (giống hệt mọi lần gọi, OpenAI cache được khi ≥ 1024 token).
Phần động = user prompt (dữ liệu của lần chạy). Biến được dựng bằng CHÍNH hàm của node trên sandbox thật
(nạp nguồn golden → soi dữ liệu), spec/code lấy từ fixture (đầu ra thật của LLM, xem extract_fixtures.py).

Đếm bằng tiktoken `o200k_base` (bộ mã của họ GPT-4o/GPT-5) — số gần đúng, chưa gồm vài token khung tin nhắn.

    python eval/prompt_bench/measure_tokens.py --label before
    python eval/prompt_bench/measure_tokens.py --label after     # ghi thêm cột "sau" vào cùng báo cáo
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.nodes.codegen import codegen_variables  # noqa: E402
from src.agents.nodes.common import SANDBOX_DB  # noqa: E402
from src.agents.nodes.optimizer import ProposalInput, optimizer_variables  # noqa: E402
from src.agents.nodes.planner import planner_variables  # noqa: E402
from src.agents.nodes.profiler import profiler_node  # noqa: E402
from src.agents.nodes.testgen import blind_inputs  # noqa: E402
from src.agents.tools.duckdb_tools import discover_sources, ingest_sources  # noqa: E402
from src.agents.tools.sql_tools import render_dbt_sql  # noqa: E402
from src.models.evidence import Finding  # noqa: E402
from src.services.llm import LLMRequest, render_prompt, to_json  # noqa: E402
from src.services.prompt_tokens import count_tokens as count  # noqa: E402
from src.services.prompt_tokens import schema_tokens  # noqa: E402

FIXTURES = HERE / "fixtures"
RESULTS = ROOT / "eval" / "results"
CACHE_MIN_TOKENS = 1024
NODES = ("planner", "codegen", "codegen_retry", "testgen", "optimizer")


def _sandbox(fixture: dict, workdir: Path) -> dict:
    """Nạp nguồn golden vào sandbox tạm + dựng bảng staging (để optimizer EXPLAIN được); trả state tối thiểu."""
    case_dir = Path("eval/datasets/golden") / fixture["case"] / "sources"  # đường dẫn tương đối: giống mọi máy
    wanted = {s["name"] for s in fixture["spec"]["sources"]}
    catalog = [info for info in discover_sources(case_dir) if info.name in wanted]
    db = workdir / SANDBOX_DB
    ingest_sources(db, catalog)
    with duckdb.connect(str(db)) as con:
        for path, sql in fixture["code_files"].items():
            if path.startswith("models/staging/"):
                con.execute(f"CREATE TABLE main.{Path(path).stem} AS {render_dbt_sql(sql)}")
    state = {"workspace": str(workdir), "request_text": fixture["request_text"], "spec": fixture["spec"]}
    state["profile"] = profiler_node(state)["profile"]
    state["source_catalog"] = [info.model_dump() for info in discover_sources(case_dir)]
    return state


def variables_by_node(fixture: dict, state: dict) -> dict[str, dict[str, str]]:
    """Biến prompt của từng node ở lần gọi đầu (và vòng sửa nếu fixture có lỗi thật)."""
    out = {
        "planner": planner_variables(state, state["source_catalog"], last_round=False),
        "codegen": codegen_variables(state),
        "testgen": {**blind_inputs(state), "previous_tests": "(chưa có)", "test_errors": "(không có)"},
    }
    if fixture["retry_error"]:
        retry_state = {**state, "code_files": fixture["code_files"]}
        retry_state["safety"] = {"passed": False, "issues": fixture["retry_error"].splitlines()}
        out["codegen_retry"] = codegen_variables(retry_state)
    job = ProposalInput(
        sql=fixture["optimizer"]["sql"],
        findings=[Finding.model_validate(f) for f in fixture["optimizer"]["findings"]],
        bench_db=str(Path(state["workspace"]) / SANDBOX_DB),
    )
    out["optimizer"] = optimizer_variables(job)
    return out


def measure_case(fixture: dict) -> dict[str, dict]:
    """{node: {static, dynamic, total}} cho một ca."""
    workdir = Path(tempfile.mkdtemp(prefix="p113-prompt-"))
    try:
        state = _sandbox(fixture, workdir)
        rows = {}
        for node, variables in variables_by_node(fixture, state).items():
            task = "codegen" if node == "codegen_retry" else node
            system, user = render_prompt(LLMRequest(task=task, variables=variables))
            static = count(system) + schema_tokens(task)
            rows[node] = {"static": static, "dynamic": count(user), "total": static + count(user)}
        return rows
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:,.0f}".replace(",", ".")


def _avg(snapshot: dict, node: str, key: str) -> float | None:
    values = [case[node][key] for case in snapshot["cases"].values() if node in case]
    return sum(values) / len(values) if values else None


def _pct(before: float | None, after: float | None) -> str:
    if not before or after is None:
        return "—"
    return f"{(after - before) / before * 100:+.1f}%".replace(".", ",")


def render_report(data: dict) -> str:
    """Báo cáo markdown: bảng chi tiết từng snapshot + bảng trước/sau theo node."""
    lines = [
        "# Token của prompt theo node (đo offline)",
        "",
        "- Đếm bằng tiktoken `o200k_base`; số gần đúng, chưa gồm vài token khung tin nhắn của API.",
        "- Phần tĩnh = system prompt + JSON Schema đầu ra gửi kèm (nếu bật structured output; ước tính bằng",
        "  JSON gọn của schema, API có thể đóng gói khác một chút). Phần động = dữ liệu của lần chạy.",
        f"- OpenAI chỉ cache khi phần đầu giống hệt ≥ {CACHE_MIN_TOKENS} token: cột `cache?` cho biết phần tĩnh có đủ dài.",
        "- 3 ca golden (g01 gộp 3 nguồn, g06 nối một-nhiều, g09 bảng chiều). Spec/code trong fixture là đầu ra",
        "  thật của gpt-5.6-luna ngày 2026-10-02; `codegen_retry` chỉ có ở ca có lỗi thật (g09).",
        "- Chỉ đo token ĐẦU VÀO. Token đầu ra và chất lượng (đúng/sai, pass lần đầu, số vòng sửa) cần khóa LLM:",
        "  — (chưa đo, U1 giai đoạn 2).",
        "",
    ]
    snapshots = data["snapshots"]
    if "before" in snapshots and "after" in snapshots:
        before, after = snapshots["before"], snapshots["after"]
        lines += [
            "## Trước / sau (trung bình các ca)",
            "",
            "| Node | Tĩnh trước | Tĩnh sau | Δ tĩnh | Động trước | Động sau | Δ động | Tổng trước | Tổng sau | Δ tổng |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for node in NODES:
            b = [_avg(before, node, k) for k in ("static", "dynamic", "total")]
            a = [_avg(after, node, k) for k in ("static", "dynamic", "total")]
            cells = []
            for i in range(3):
                cells += [_fmt(b[i]), _fmt(a[i]), _pct(b[i], a[i])]
            lines.append(f"| {node} | " + " | ".join(cells) + " |")
        lines.append("")
    for label, snap in snapshots.items():
        lines += [
            f"## Chi tiết `{label}` ({snap['date']}, prompt {snap['versions']})",
            "",
            "| Ca | Node | Tĩnh | Động | Tổng | cache? |",
            "|---|---|---:|---:|---:|---|",
        ]
        for case, nodes in snap["cases"].items():
            for node in NODES:
                if node in nodes:
                    r = nodes[node]
                    cache = "có" if r["static"] >= CACHE_MIN_TOKENS else "không"
                    lines.append(
                        f"| {case} | {node} | {_fmt(r['static'])} | {_fmt(r['dynamic'])} | {_fmt(r['total'])} | {cache} |"
                    )
        lines.append("")
    real = data.get("real_usage", {})
    if real:
        lines += [
            "## Token đầu vào thật của OpenAI ở lần chạy gốc (prompt bản cũ hơn, chỉ để đối chiếu cách đếm)",
            "",
            "| Ca | Lần gọi (task: input/output) |",
            "|---|---|",
        ]
        for case, usage in real.items():
            calls = ", ".join(f"{u['task']}: {u['input_tokens']}/{u['output_tokens']}" for u in usage)
            lines.append(f"| {case} | {calls} |")
        lines.append("")
    return "\n".join(lines)


def prompt_versions() -> str:
    """`task=version` lấy từ dòng `version:` đầu mỗi file prompt (chưa có thì `?`)."""
    out = []
    for path in sorted((ROOT / "src" / "prompts").glob("*.md")):
        first = path.read_text(encoding="utf-8").splitlines()[:3]
        version = next((ln.split("version:", 1)[1].strip() for ln in first if "version:" in ln), "?")
        out.append(f"{path.stem}={version}")
    return ", ".join(out)


def main() -> None:
    """Đo và ghi eval/results/prompt_tokens.{json,md}."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", default="after", help="Tên snapshot (before/after)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    os.chdir(ROOT)
    fixtures = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIXTURES.glob("*.json"))]
    out_json = RESULTS / "prompt_tokens.json"
    data = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else {"snapshots": {}}
    cases = {f["case"]: measure_case(f) for f in fixtures}
    data["snapshots"][args.label] = {"date": date.today().isoformat(), "versions": prompt_versions(), "cases": cases}
    data["real_usage"] = {f["case"]: f["real_usage"] for f in fixtures}
    RESULTS.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (RESULTS / "prompt_tokens.md").write_text(render_report(data), encoding="utf-8")
    print(to_json(cases))


if __name__ == "__main__":
    main()

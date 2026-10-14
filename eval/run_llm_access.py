"""So hai mức truy cập dữ liệu của LLM (`schema_only` và `profile`) trên 12 ca golden, KHÔNG gọi LLM (0 token, 0 USD).

Chạy: `python eval/run_llm_access.py`. Ghi `eval/results/llm_access.md`.
Đo thật bằng code:
- số token của ngữ cảnh dữ liệu mà Planner và Codegen/Testgen nhận ở từng mức (tiktoken, đúng chuỗi JSON gửi đi);
- kiểm tra không giá trị thật nào của nguồn xuất hiện trong ngữ cảnh (email, điện thoại, họ tên, mã định danh, số tiền ở dạng chuỗi).
KHÔNG đo được ở đây: độ đúng của agent theo từng mức (cần LLM thật, tốn tiền). Lệnh đo ghi ở cuối báo cáo.
"""

import csv
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GOLDEN = ROOT / "eval" / "datasets" / "golden"
OUT = ROOT / "eval" / "results" / "llm_access.md"
LEVELS = ("schema_only", "profile")
SENSITIVE_COLUMN = re.compile(r"email|phone|name|address|customer|order_id|total|amount|id$", re.I)
# Ví dụ cố định nằm trong tên định dạng tiền của bước Soi dữ liệu ("vnd_dot (1.075.000)"): là hằng của code, không phải dữ liệu
CODE_CONSTANTS = {"1.075.000", "1,075,000", "1075k"}


def source_values(directory: Path) -> set[str]:
    """Giá trị thật đáng ngờ nhất của các file CSV trong ca golden (đủ dài để không trùng ngẫu nhiên)."""
    values: set[str] = set()
    for file in directory.glob("*.csv"):
        with file.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                values |= {v for k, v in row.items() if k and SENSITIVE_COLUMN.search(k) and v and len(v) >= 7}
    return values - CODE_CONSTANTS


def measure_case(case: Path, level: str, count_tokens) -> dict:
    """Token và rò rỉ của ngữ cảnh dữ liệu ở mức `level` cho một ca golden (dữ liệu của chính ca đó)."""
    from src.agents.nodes.profiler import profiler_node
    from src.agents.tools.duckdb_tools import SourceInfo, ingest_sources
    from src.config import get_settings
    from src.services.llm_context import build_llm_context

    os.environ.update({"SOURCES_DIR": str(case / "sources"), "LLM_ACCESS_DEFAULT": level, "DATABASE_URL": ""})
    get_settings.cache_clear()
    ctx = build_llm_context("eval")
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "sandbox.duckdb"
        ingest_sources(db, [SourceInfo.model_validate(i) for i in ctx.catalog])
        profile = profiler_node({"workspace": tmp})["profile"]
    planner = json.dumps(ctx.planner_catalog(), ensure_ascii=False, separators=(",", ":"))
    build = json.dumps(ctx.build_profile(profile), ensure_ascii=False, separators=(",", ":"))
    leaked = sorted(v for v in source_values(case / "sources") if v in planner or v in build)
    return {
        "tables": len(ctx.tables),
        "planner": count_tokens(planner),
        "build": count_tokens(build),
        "leaked": leaked,
        "levels": sorted({t.access for t in ctx.tables}),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from src.services.prompt_tokens import count_tokens

    cases = sorted(p for p in GOLDEN.iterdir() if (p / "sources").is_dir())
    rows = {case.name: {lv: measure_case(case, lv, count_tokens) for lv in LEVELS} for case in cases}
    report = render(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8")
    print(report)
    return 0


def render(rows: dict) -> str:
    def total(level: str, key: str) -> int:
        return sum(r[level][key] for r in rows.values())

    leaks = {lv: sum(len(r[lv]["leaked"]) for r in rows.values()) for lv in LEVELS}
    lines = [
        "# Mức truy cập dữ liệu của LLM: `schema_only` so với `profile`",
        "",
        f"{len(rows)} ca golden ([eval/datasets/golden](../datasets/golden)), mỗi ca dùng dữ liệu nguồn của chính nó (đăng ký ở sổ nguồn mặc định, "
        "độ nhạy cảm `medium`). **Không gọi LLM**: chỉ đo ngữ cảnh dữ liệu mà code đưa vào prompt (tiktoken `o200k_base`, đúng chuỗi JSON gửi đi).",
        "",
        "| Chỉ số | `schema_only` | `profile` (mặc định) |",
        "|---|---|---|",
        f"| Token ngữ cảnh Planner (tổng 12 ca) | {total('schema_only', 'planner')} | {total('profile', 'planner')} |",
        f"| Token hồ sơ cho Codegen/Testgen (tổng 12 ca) | {total('schema_only', 'build')} | {total('profile', 'build')} |",
        f"| Giá trị thật lọt vào ngữ cảnh | **{leaks['schema_only']}** | **{leaks['profile']}** |",
        "",
        "## Từng ca",
        "",
        "| Ca | Bảng | Planner `schema_only` | Planner `profile` | Hồ sơ `schema_only` | Hồ sơ `profile` | Lọt |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, row in rows.items():
        s, p = row["schema_only"], row["profile"]
        leak = len(s["leaked"]) + len(p["leaked"])
        lines.append(
            f"| {name} | {s['tables']} | {s['planner']} | {p['planner']} | {s['build']} | {p['build']} | {leak} |"
        )
    lines += [
        "",
        "## Chưa đo: độ đúng của agent theo từng mức",
        "",
        'Câu hỏi "`profile` có giúp Planner sinh phép làm sạch đúng hơn `schema_only` không" cần chạy agent bằng LLM thật. '
        "Theo lựa chọn của người dùng, đợt này chỉ dùng chế độ mô phỏng (LLM giả không đọc ngữ cảnh nên cho cùng kết quả ở hai mức), nên **độ đúng chưa được đo**.",
        "Lệnh đo (ước tính ≈ 12 ca × 0,0045 USD × 2 mức ≈ 0,11 USD, theo chi phí golden 2026-10-08):",
        "",
        "```bash",
        "LLM_PROVIDER=openai LLM_ACCESS_DEFAULT=schema_only python eval/run_eval.py --with-llm",
        "LLM_PROVIDER=openai LLM_ACCESS_DEFAULT=profile python eval/run_eval.py --with-llm",
        "```",
        "",
        "Tiêu chí nghiệm thu của CLAUDE.md (giai đoạn 3): độ đúng ở `profile` không thấp hơn trước khi đổi (golden 12/12 ngày 2026-10-08).",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

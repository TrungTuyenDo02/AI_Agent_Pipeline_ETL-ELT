"""Đo từ điển nghiệp vụ (CLAUDE.md bản 2, giai đoạn 6) KHÔNG gọi LLM (0 token, 0 USD).

Chạy: `python eval/run_glossary.py`. Ghi `eval/results/glossary.md`. Đo thật bằng code:
- số thuật ngữ cần thiết mà bộ chọn từ khóa đưa tới Planner ở 5 ca golden mới (g13–g17, yêu cầu viết bằng thuật ngữ, không nêu trạng thái);
- thuật ngữ thừa đưa vào 12 ca golden cũ (yêu cầu đã nêu rõ điều kiện);
- token prompt Planner khi có thuật ngữ so với khi không có (tiktoken `o200k_base`, đúng prompt sẽ gửi).
KHÔNG đo được ở đây: độ đúng của agent trước/sau (cần LLM thật, tốn tiền). Lệnh đo ghi ở cuối báo cáo.
"""

import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.update({"DATABASE_URL": "", "LLM_PROVIDER": "mock", "LLM_FALLBACK": "none"})

GOLDEN = ROOT / "eval" / "datasets" / "golden"
OUT = ROOT / "eval" / "results" / "glossary.md"
STATIC_DELTA = (
    52  # token tĩnh thêm của planner v10 so với v9 (đo bằng tests/test_prompts/test_budget.py: 1.316 → 1.368)
)
MAX_INCREASE_PCT = 15.0


def prompt_tokens(case: Path, with_glossary: bool) -> tuple[int, list[str]]:
    """Token của prompt Planner (system + user) cho một ca golden, và các thuật ngữ được đưa vào."""
    from src.agents.nodes.planner import planner_variables
    from src.agents.tools.duckdb_tools import SourceInfo, discover_sources
    from src.config import get_settings
    from src.services import glossary
    from src.services.llm import LLMRequest, render_prompt
    from src.services.llm_context import build_llm_context
    from src.services.prompt_tokens import count_tokens

    os.environ["SOURCES_DIR"] = str(case / "sources")
    get_settings.cache_clear()
    catalog = [SourceInfo.model_validate(i.model_dump()).model_dump() for i in discover_sources(case / "sources")]
    ctx = build_llm_context("eval", catalog=catalog, glossary=True)
    state = {"request_text": (case / "request.txt").read_text(encoding="utf-8").strip()}
    variables = planner_variables(state, ctx, last_round=False)
    chosen = [e["term"] for e in ctx.glossary_for(state["request_text"])]
    if not with_glossary:
        variables["glossary"] = "(không có)"
    system, user = render_prompt(LLMRequest(task="planner", variables=variables))
    del glossary
    return count_tokens(system) + count_tokens(user), chosen


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from src.services import glossary

    cases = sorted(p for p in GOLDEN.iterdir() if (p / "sources").is_dir())
    rows = []
    for case in cases:
        meta = yaml.safe_load((case / "meta.yaml").read_text(encoding="utf-8")) or {}
        wanted = [str(t) for t in meta.get("glossary", [])]
        with_terms, chosen = prompt_tokens(case, True)
        without, _ = prompt_tokens(case, False)
        rows.append({"id": case.name, "wanted": wanted, "chosen": chosen, "with": with_terms, "without": without})
    new = [r for r in rows if r["wanted"]]
    old = [r for r in rows if not r["wanted"]]
    hits = sum(t in r["chosen"] for r in new for t in r["wanted"])
    needed = sum(len(r["wanted"]) for r in new)
    extra_old = sum(len(r["chosen"]) for r in old)
    v9_total = sum(r["without"] for r in rows) - STATIC_DELTA * len(rows)
    v10_total = sum(r["with"] for r in rows)
    increase = 100 * (v10_total - v9_total) / v9_total
    report = render(rows, hits, needed, extra_old, increase, len(glossary.seed_terms()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8")
    print(report)
    return 0 if increase <= MAX_INCREASE_PCT and hits == needed else 1


def render(rows: list[dict], hits: int, needed: int, extra_old: int, increase: float, terms: int) -> str:
    new = [r for r in rows if r["wanted"]]
    lines = [
        "# Từ điển nghiệp vụ: đo không gọi LLM",
        "",
        f"{len(rows)} ca golden ([eval/datasets/golden](../datasets/golden)): 12 ca cũ + {len(new)} ca mới có yêu cầu viết bằng thuật ngữ "
        f"công ty, không nêu trạng thái (g13–g17). Từ điển mẫu: {terms} thuật ngữ cho P113 Retail ([config/glossary_seed.yaml](../../config/glossary_seed.yaml)). "
        "**Không gọi LLM**: chỉ đo phần code (chọn thuật ngữ, kích thước prompt).",
        "",
        "| Chỉ số | Kết quả | Tiêu chí |",
        "|---|---|---|",
        f"| Thuật ngữ cần thiết tới được Planner (ca mới) | **{hits}/{needed}** | tất cả |",
        f"| Thuật ngữ đưa vào 12 ca cũ (đã nêu rõ điều kiện, không bắt buộc) | {extra_old} | thông tin, không phải lỗi |",
        f"| Token prompt Planner tăng (v10 có thuật ngữ so với v9, trung bình {len(rows)} ca) | **{increase:+.1f}%** | ≤ {MAX_INCREASE_PCT:.0f}% |",
        "",
        "## Từng ca",
        "",
        "| Ca | Thuật ngữ cần | Thuật ngữ được đưa vào | Token (v10 không có thuật ngữ) | Token (v10 có thuật ngữ) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {', '.join(r['wanted']) or '—'} | {', '.join(r['chosen']) or '—'} | {r['without']} | {r['with']} |"
        )
    lines += [
        "",
        f"Token v9 ước tính = token v10 không có thuật ngữ − {STATIC_DELTA} (phần tĩnh thêm của khối `glossary` và quy tắc 16).",
        "",
        "## Chưa đo: độ đúng của agent trước/sau khi có từ điển",
        "",
        'Câu hỏi "có từ điển thì Planner đoán đúng điều kiện (trạng thái, trùng đơn, đơn vị) hơn không" cần chạy agent bằng LLM thật. '
        "Theo lựa chọn của người dùng, đợt này chỉ dùng chế độ mô phỏng (LLM giả không đọc ngữ cảnh), nên **độ đúng chưa được đo**.",
        "Lệnh đo (ước tính ≈ 5 ca mới × 2 lần × 0,0045 USD ≈ 0,05 USD, theo chi phí golden 2026-10-08):",
        "",
        "```bash",
        "# trước: GLOSSARY_MAX_TERMS=0 (không đưa thuật ngữ vào prompt); sau: mặc định",
        "LLM_PROVIDER=openai GLOSSARY_MAX_TERMS=0 python eval/run_eval.py --with-llm",
        "LLM_PROVIDER=openai python eval/run_eval.py --with-llm",
        "```",
        "",
        "Tiêu chí nghiệm thu của CLAUDE.md (giai đoạn 6): độ đúng sau ≥ trước; token prompt Planner tăng ≤ 15%.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

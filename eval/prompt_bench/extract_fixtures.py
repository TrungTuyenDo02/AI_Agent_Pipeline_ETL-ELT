"""Trích fixture đo token từ các lần chạy golden THẬT (openai) còn trong checkpoint trên máy.

Chỉ chạy một lần trên máy có `data/checkpoints.db`; kết quả commit vào `fixtures/` để ai cũng đo lại được.
Fixture giữ đầu ra thật của LLM (spec, code) — không viết tay. Lỗi vòng sửa lấy từ sổ lỗi (`data/app.db`).

    python eval/prompt_bench/extract_fixtures.py
"""

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from src.agents import runner  # noqa: E402
from src.config import get_settings  # noqa: E402

# Ca golden → run_id của lần chạy openai (gpt-5.6-luna/terra) ngày 2026-10-02 đã được duyệt
RUNS = {
    "g01_three_sources": "0c62d7dc73",
    "g06_one_to_many_join": "7adeb19058",
    "g09_customer_dimension": "cb06b661f9",
}


def _error_text(signature: str) -> str:
    with sqlite3.connect(get_settings().store_path) as con:
        row = con.execute("SELECT description FROM error_entries WHERE signature = ?", (signature,)).fetchone()
    return row[0] if row else ""


def _relative_sources(spec: dict) -> dict:
    """Đường dẫn nguồn tuyệt đối của máy → tương đối với repo (đo token như nhau trên mọi máy)."""
    sources = [{**s, "path": Path(s["path"]).relative_to(ROOT).as_posix()} for s in spec["sources"]]
    return {**spec, "sources": sources}


def fixture_of(case: str, run_id: str) -> dict:
    """Phần state cần để dựng lại biến prompt của mọi node."""
    values = runner.get_values(run_id)
    signatures = values.get("error_signatures", [])
    return {
        "case": case,
        "run_id": run_id,
        "request_text": values["request_text"],
        "spec": _relative_sources(values["spec"]),
        "code_files": {k: v for k, v in values["code_files"].items() if k.endswith(".sql") or k.endswith(".py")},
        "optimizer": {
            "sql": values["optimization"]["original_sql"],
            "findings": values["optimization"]["findings"],
        },
        "retry_error": _error_text(signatures[0]) if signatures else "",
        "real_usage": [
            {k: u[k] for k in ("task", "model", "input_tokens", "output_tokens")} for u in values["llm_usage"]
        ],
    }


def main() -> None:
    """Ghi fixtures/<ca>.json."""
    out = HERE / "fixtures"
    out.mkdir(exist_ok=True)
    for case, run_id in RUNS.items():
        path = out / f"{case}.json"
        path.write_text(json.dumps(fixture_of(case, run_id), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"đã ghi {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""V2 như một máy dò: cấy lỗi giả vào pipeline ĐÚNG rồi chạy đúng V1 + V2 (dbt build + test) của hệ thống.

Hai pipeline gốc:
- `revenue_3_sources`: gộp 3 nguồn, doanh thu ngày (mock tất định, dữ liệu giả lập seed 42) — eval/mutation/mutants.yaml.
- `join_g06`: nối một-nhiều (code thật của gpt-5.6-luna, nguồn golden g06, kỳ vọng = reference.sql) — v2_mutants/.

Kho/sổ lỗi/workspace dùng thư mục tạm riêng (data/eval_work/mutation) nhờ import run_mutation TRƯỚC mọi module src.
"""

import copy
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "eval" / "mutation"))

import run_mutation  # noqa: E402  — đặt biến môi trường (thư mục tạm) trước khi nạp cấu hình

from src.agents.nodes.ingest import ingest_node  # noqa: E402
from src.agents.nodes.profiler import profiler_node  # noqa: E402
from src.agents.nodes.testgen import generic_tests, reconcile_test  # noqa: E402
from src.agents.tools.duckdb_tools import discover_sources  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.models.spec import PipelineSpec  # noqa: E402

GOLDEN_G06 = ROOT / "eval" / "datasets" / "golden" / "g06_one_to_many_join"
FIXTURE_G06 = ROOT / "eval" / "prompt_bench" / "fixtures" / "g06_one_to_many_join.json"


def build_join_base() -> dict:
    """Pipeline g06 đúng: nạp nguồn golden, code thật của LLM, test tất định + đối soát với SQL chuẩn.

    `references` trong spec gốc bị LLM điền thành nguồn gốc cột (không phải khóa ngoại tới model) → sinh test
    `relationships` tới model không tồn tại; bỏ đi để đo đúng khả năng bắt lỗi của phần đối soát.
    """
    fixture = json.loads(FIXTURE_G06.read_text(encoding="utf-8"))
    spec_data = {**fixture["spec"]}
    spec_data["output_columns"] = [{**c, "references": ""} for c in spec_data["output_columns"]]
    state: dict = {
        "run_id": "v2-join-base",
        "request_text": fixture["request_text"],
        "requester": "eval",
        "spec": spec_data,
        "source_catalog": [s.model_dump() for s in discover_sources(GOLDEN_G06 / "sources")],
    }
    state.update(ingest_node(state))
    state.update(profiler_node(state))
    spec = PipelineSpec.model_validate(spec_data)
    expected = (GOLDEN_G06 / "reference.sql").read_text(encoding="utf-8")
    tests = {**generic_tests(spec), f"tests/assert_{spec.target}_reconciles.sql": reconcile_test(spec, expected)}
    state.update(code_files=fixture["code_files"], test_files=tests)
    return state


def run_base(name: str, base: dict, mutants: list[run_mutation.Mutant]) -> dict:
    """Kiểm pipeline gốc đạt rồi chạy từng đột biến; trả {base, sanity, rows}."""
    sanity = run_mutation.verify(copy.deepcopy(base))
    if sanity.caught:
        return {"base": name, "sanity": f"pipeline gốc KHÔNG đạt ({sanity.by}: {sanity.detail})", "rows": []}
    rows = run_mutation.run_all(base, mutants)
    return {"base": name, "sanity": f"pipeline gốc đạt ({sanity.detail})", "rows": [{**r, "base": name} for r in rows]}


def load_mutants(path: Path) -> list[run_mutation.Mutant]:
    """Đọc danh sách đột biến từ yaml."""
    return [run_mutation.Mutant.model_validate(m) for m in yaml.safe_load(path.read_text(encoding="utf-8"))["mutants"]]


def run_all() -> list[dict]:
    """Chạy cả hai pipeline gốc."""
    get_settings.cache_clear()
    revenue = run_base(
        "revenue_3_sources",
        run_mutation.build_base(),
        load_mutants(ROOT / "eval/mutation/mutants.yaml") + load_mutants(HERE / "v2_mutants" / "revenue_extra.yaml"),
    )
    join = run_base("join_g06", build_join_base(), load_mutants(HERE / "v2_mutants" / "join_g06.yaml"))
    return [revenue, join]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for result in run_all():
        print(result["base"], result["sanity"])

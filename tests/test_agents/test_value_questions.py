"""CLAUDE.md 2.3: Planner chỉ thấy con số do code đếm; câu hỏi về giá trị một cột do code điền giá trị thật cho người
tick (J1), LLM chỉ nhận giá trị người đã chọn."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from src.agents.nodes.clarify import valid_answers
from src.agents.nodes.planner import with_value_options
from src.agents.tools.duckdb_tools import discover_sources
from src.agents.tools.source_stats import column_values, source_stats, with_stats
from src.models.spec import ClarifyQuestion, PipelineSpec

API = "/api/v1"


def _csv_catalog(tmp_path: Path, text: str) -> list[dict]:
    (tmp_path / "orders.csv").write_text(text, encoding="utf-8")
    return [info.model_dump() for info in discover_sources(tmp_path)]


def test_source_stats_counts_without_values(tmp_path: Path):
    catalog = _csv_catalog(
        tmp_path,
        "order_id,status,amount\n1,Done,10\n1,Done,10\n2,open,5\n2, OPEN,6\n3,Cancelled,7\n",
    )
    stats = source_stats(catalog[0])
    assert stats == {
        "rows": 5,
        "few_values": {"status": 4, "amount": 4},
        "key_column": "order_id",
        "repeated_keys": 2,
        "repeated_keys_differing": 1,  # khóa 1 lặp y hệt; khóa 2 lặp với nội dung khác
    }
    assert "Done" not in str(stats) and "sample" not in with_stats(catalog)[0]["stats"]


def test_column_values_groups_case_variants(tmp_path: Path):
    catalog = _csv_catalog(tmp_path, "order_id,status\n1,Done\n2,open\n3, OPEN\n4,Cancelled\n")
    assert column_values(catalog, "orders.status") == (["CANCELLED", "DONE", "OPEN"], True)
    assert column_values(catalog, "orders.missing") == ([], False)
    assert column_values(catalog, "other.status") == ([], False)


def _spec(questions: list[dict]) -> PipelineSpec:
    return PipelineSpec.model_validate(
        {
            "request_text": "doanh thu ngày",
            "sources": [{"name": "orders", "kind": "csv", "path": "x"}],
            "target": "fct_x",
            "grain": ["d"],
            "output_columns": [{"name": "d", "type": "DATE"}],
            "questions": questions,
        }
    )


def test_planner_replaces_llm_options_with_real_values(tmp_path: Path):
    catalog = _csv_catalog(tmp_path, "order_id,status\n1,COMPLETED\n2,CANCELLED\n3,RETURNED\n")
    fallback = ["Chỉ đơn hoàn tất", "Mọi đơn trừ đơn hủy"]
    spec = _spec(
        [
            {"id": "q1", "question": "Trạng thái nào tính?", "options": fallback, "column": "orders.status"},
            {"id": "q2", "question": "Cột lạ?", "options": fallback, "column": "orders.nope"},
        ]
    )
    first, second = with_value_options(spec, catalog).questions
    assert first.options == ["CANCELLED", "COMPLETED", "RETURNED"] and first.multiple and not first.normalized
    assert second.options == fallback and second.column == "" and not second.multiple  # không thấy cột: giữ như cũ


QUESTIONS = [
    ClarifyQuestion(id="single", question="Giữ đơn trùng?", options=["Giữ", "Bỏ"]),
    ClarifyQuestion(
        id="status",
        question="Trạng thái nào tính?",
        options=["CANCELLED", "COMPLETED", "IT'S"],
        column="orders.status",
        multiple=True,
        normalized=True,
    ),
]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (["COMPLETED", "IT'S"], """orders: upper(trim("status")) IN ('COMPLETED', 'IT''S')"""),
        ("COMPLETED", """orders: upper(trim("status")) IN ('COMPLETED')"""),  # eval/CLI tự chọn lựa chọn đầu
        (["IT'S", "COMPLETED", "IT'S"], """orders: upper(trim("status")) IN ('COMPLETED', 'IT''S')"""),
        (["COMPLETED", "PAID"], None),  # giá trị không có trong danh sách
        ([], None),
    ],
)
def test_multiple_answer_becomes_explicit_condition(value, expected):
    got = valid_answers(QUESTIONS, {"answers": {"single": "Giữ", "status": value}})
    assert got.get("single") == "Giữ" and got.get("status") == expected


def test_single_question_still_needs_exact_option():
    assert valid_answers(QUESTIONS, {"answers": {"single": ["Giữ"], "nope": "x"}}) == {}


async def test_answers_api_accepts_list_for_multiple_question(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from src.api import runs
    from src.services.store import get_store

    run_id = get_store().create_run("doanh thu", client.username).id
    resumed = {}
    pending = {"kind": "clarify", "questions": [q.model_dump() for q in QUESTIONS]}
    monkeypatch.setattr(runs, "_pending", lambda _run_id, _kind: pending)

    def fake_resume(run_id: str, kind: str, value: dict, _user) -> runs.Accepted:
        resumed.update(kind=kind, value=value)
        return runs.Accepted(run_id=run_id, status="running", message="ok")

    monkeypatch.setattr(runs, "_resume", fake_resume)
    body = {"answers": {"single": "Bỏ", "status": ["COMPLETED"]}}
    assert (await client.post(f"{API}/runs/{run_id}/answers", json=body)).status_code == 202
    assert resumed == {"kind": "clarify", "value": body}  # J1 tự kiểm và định dạng lại khi chạy tiếp
    bad = {"answers": {"single": "Bỏ", "status": ["PAID"]}}
    assert (await client.post(f"{API}/runs/{run_id}/answers", json=bad)).status_code == 422

"""Cửa kiểm tra đầu vào, tầng 2 (CLAUDE.md bản 2, giai đoạn 2): bộ phân loại model nhỏ, mẫu câu hỏi cố định, chi phí."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from src.agents import runner
from src.agents.runner import ResumeRequest
from src.agents.tools import input_checks as ic
from src.config import get_settings
from src.models.schemas import LLMUsage, RunStatus
from src.services import input_gate as gate
from src.services import llm_mock
from src.services.jobs import get_jobs
from src.services.store import get_store

API = "/api/v1"
CATALOG = [
    {"name": "shopee_orders", "kind": "csv", "columns": {"order_id": "VARCHAR", "total_amount": "VARCHAR"}},
    {"name": "tiki_orders", "kind": "json", "columns": {"id": "VARCHAR", "grand_total": "DOUBLE"}},
]
EXAMPLES = ["Gộp dữ liệu a và b", "Làm sạch bảng c", "Tối ưu truy vấn d"]
VAGUE = (
    "Cho tôi số liệu bán hàng tuần trước nhé"  # tầng 0–1 không thấy từ khóa nào; mock tầng 2 → pipeline, thiếu nguồn
)


@pytest.fixture(autouse=True)
def _empty_cache():
    """Bộ nhớ đệm kết quả nằm trong tiến trình: mỗi test bắt đầu trống để đếm đúng số lượt gọi và token."""
    gate.result_cache().clear()


def test_off_topic_confident_is_rejected_with_examples():
    result = ic.decide_tier2("off_topic", 0.9, [], EXAMPLES)
    assert result.status == "rejected" and result.code == "off_topic" and "Làm sạch bảng c" in result.message


def test_off_topic_unsure_is_not_rejected_outright():
    """Chặn nhầm gây khó chịu hơn tốn thêm vài đồng: chưa chắc thì xin viết lại, không từ chối thẳng."""
    result = ic.decide_tier2("off_topic", 0.6, [], EXAMPLES)
    assert result.status == "needs_info" and result.code == "rewrite" and "Ví dụ yêu cầu hợp lệ" in result.message


@pytest.mark.parametrize(("label", "confidence"), [("unclear", 0.9), ("pipeline", 0.3), ("optimize", 0.49)])
def test_unclear_or_low_confidence_asks_to_rewrite(label: str, confidence: float):
    assert ic.decide_tier2(label, confidence, [], EXAMPLES).code == "rewrite"


def test_business_request_with_nothing_missing_passes():
    assert ic.decide_tier2("pipeline", 0.7, [], EXAMPLES).status == "ok"
    assert ic.decide_tier2("optimize", 0.8, [], EXAMPLES).status == "ok"


def test_missing_fields_use_fixed_template_not_llm_text():
    result = ic.decide_tier2("pipeline", 0.7, ["source", "grain", "bia dat"], EXAMPLES)  # ô lạ bị bỏ
    assert result.status == "needs_info" and result.missing == ["source", "grain"]
    assert "(1) dữ liệu lấy từ bảng hoặc nguồn nào; (2) tính theo đơn vị nào" in result.message
    assert "bia dat" not in result.message


def _spy_llm(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    from src.services import llm

    calls: list[dict] = []
    real = llm.call_llm
    monkeypatch.setattr(
        llm, "call_llm", lambda task, variables: (calls.append({"task": task, **variables}), real(task, variables))[1]
    )
    return calls


def test_evaluate_calls_tier2_only_for_unclear_and_caches_it(monkeypatch: pytest.MonkeyPatch):
    gate.result_cache().clear()
    calls = _spy_llm(monkeypatch)
    assert gate.evaluate("Gộp shopee_orders, tính doanh thu", CATALOG)[1] == []  # tầng 1 đủ: không gọi LLM
    assert gate.evaluate("asdfghjkl qwerty", CATALOG)[1] == [] and calls == []
    first, usage = gate.evaluate("Hôm nay thời tiết Hà Nội thế nào?", CATALOG)
    assert first.status == "rejected" and first.tier == 2 and [c["task"] for c in calls] == ["input_gate"]
    assert [u["task"] for u in usage] == ["input_gate"] and usage[0]["simulated"]
    again, usage_again = gate.evaluate("hôm nay THỜI TIẾT hà nội thế nào", CATALOG)  # cùng câu sau chuẩn hóa
    assert again.status == "rejected" and again.cached and usage_again == [] and len(calls) == 1


def test_tier2_prompt_has_table_names_and_request_but_no_data(monkeypatch: pytest.MonkeyPatch):
    calls = _spy_llm(monkeypatch)
    catalog = [{**CATALOG[0], "sample": [{"email": "khach1@example.com"}], "stats": {"rows": 3}}]
    gate.tier2(VAGUE, catalog)
    assert set(calls[0]) == {"task", "tables", "request"} and "khach1@example.com" not in str(calls[0])
    assert "shopee_orders" in calls[0]["tables"]


def test_invalid_output_retries_once_then_asks_to_rewrite(mock_llm, monkeypatch: pytest.MonkeyPatch):
    mock_llm("input_gate", {"label": "pipeline", "confidence": "rất cao", "missing": []})  # sai kiểu
    calls = _spy_llm(monkeypatch)
    result, usage = gate.tier2(VAGUE, CATALOG)
    assert len(calls) == 2 and len(usage) == 2  # thử lại đúng 1 lần
    assert result.status == "needs_info" and result.code == "rewrite"


def test_mock_classifier_is_deterministic_rules():
    def run(text: str) -> dict:
        return llm_mock.mock_input_gate({"request": text, "tables": '["shopee_orders"]'})

    assert run("Hôm nay thời tiết thế nào")["label"] == "off_topic"
    assert run("Truy vấn này chạy chậm quá")["label"] == "optimize"
    assert run(VAGUE) == {"label": "pipeline", "confidence": 0.7, "missing": ["source"]}
    assert run("Số liệu bán hàng trong shopee_orders")["missing"] == []
    assert run("hmm không biết nữa")["label"] == "unclear"


def test_graph_rejects_off_topic_after_tier2_and_records_its_cost(seeded_sources: Path):
    outcome = runner.start_run("Hôm nay thời tiết Hà Nội thế nào?", "alice")
    assert outcome.status == RunStatus.REJECTED_INPUT and "Ví dụ yêu cầu hợp lệ" in outcome.error
    values = runner.get_values(outcome.run_id)
    assert [u["task"] for u in values["llm_usage"]] == ["input_gate"]
    assert get_store().get_run(outcome.run_id).summary["llm_calls"] == 1


def _input(run_id: str, **value: str) -> runner.RunOutcome:
    return runner.resume_run(ResumeRequest(run_id=run_id, kind="input", value=value))


@pytest.mark.slow
def test_graph_asks_for_missing_info_then_continues_to_planner(seeded_sources: Path):
    outcome = runner.start_run(VAGUE, "alice")
    assert outcome.status == RunStatus.WAITING_INPUT and outcome.pending["kind"] == "input"
    assert outcome.pending["missing"] == ["source"]
    assert "(1) dữ liệu lấy từ bảng hoặc nguồn nào" in outcome.pending["message"]
    outcome = _input(outcome.run_id, action="send", text="Dùng bảng shopee_orders, tính doanh thu theo ngày")
    assert outcome.status == RunStatus.WAITING_CLARIFICATION, outcome.error  # đã qua cửa, Planner hỏi làm rõ (J1)
    values = runner.get_values(outcome.run_id)
    assert values["clarify_rounds"] == 1 and "shopee_orders" in values["request_text"]
    assert values["input_gate"]["status"] == "ok"


def test_graph_hands_over_to_human_after_max_clarify_rounds(seeded_sources: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAX_CLARIFY_ROUNDS", "1")
    get_settings.cache_clear()
    try:
        outcome = runner.start_run(VAGUE, "alice")
        outcome = _input(outcome.run_id, action="send", text="Số liệu thôi, chưa nghĩ ra thêm gì cả")  # vẫn thiếu nguồn
        assert outcome.status == RunStatus.FAILED and "kỹ sư dữ liệu" in outcome.error
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_user_can_abort_at_input_step(seeded_sources: Path):
    outcome = runner.start_run(VAGUE, "alice")
    outcome = _input(outcome.run_id, action="abort")
    assert outcome.status == RunStatus.FAILED and "Đã dừng" in outcome.error


async def test_api_input_step_flow(client: AsyncClient, seeded_sources: Path):
    created = await client.post(f"{API}/runs", json={"request_text": VAGUE})
    assert created.status_code == 202  # tầng 0–1 chưa chắc nhưng không chặn: tầng 2 quyết định
    run_id = created.json()["run_id"]
    get_jobs().wait(run_id)
    detail = (await client.get(f"{API}/runs/{run_id}")).json()
    assert detail["record"]["status"] == "waiting_input" and detail["pending"]["kind"] == "input"
    assert any(s["id"] == "input_gate" and s["state"] == "human" for s in detail["stages"])
    empty = await client.post(f"{API}/runs/{run_id}/input", json={"action": "send", "text": "  "})
    assert empty.status_code == 422 and "bổ sung" in empty.json()["detail"]
    assert (await client.post(f"{API}/runs/{run_id}/input", json={"action": "abort"})).status_code == 202
    get_jobs().wait(run_id)
    assert (await client.get(f"{API}/runs/{run_id}")).json()["record"]["status"] == "failed"
    wrong = await client.post(f"{API}/runs/{run_id}/input", json={"action": "abort"})
    assert wrong.status_code == 409  # không còn chờ bước này


@pytest.mark.slow
def test_tier2_tokens_count_toward_run_budget(seeded_sources: Path, monkeypatch: pytest.MonkeyPatch):
    usage = LLMUsage(task="x", provider="mock", model="mock", input_tokens=300, simulated=True)
    monkeypatch.setattr(llm_mock, "_usage", lambda task: usage.model_copy(update={"task": task}))
    monkeypatch.setenv("RUN_TOKEN_BUDGET", "250")
    get_settings.cache_clear()
    try:
        outcome = runner.start_run(VAGUE, "alice")  # tầng 2 dùng 300 token
        assert outcome.status == RunStatus.WAITING_INPUT
        outcome = _input(outcome.run_id, action="send", text="Dùng bảng shopee_orders")
        assert outcome.status == RunStatus.FAILED and "RUN_TOKEN_BUDGET" in outcome.error  # Planner bị chặn
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

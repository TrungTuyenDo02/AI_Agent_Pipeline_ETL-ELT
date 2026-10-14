"""Chạy lại từ bước lỗi: LLM lỗi tạm thời → lần chạy FAILED nhưng còn checkpoint → chạy lại, đi tiếp, không làm lại từ đầu."""

import pytest
from httpx import AsyncClient

from src.agents.nodes import planner
from src.services.jobs import get_jobs
from src.services.llm import LLMCallError

API = "/api/v1"
REQUEST = {"request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày"}


async def test_failed_run_can_be_retried_from_the_failed_step(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, seeded_sources
):
    real = planner.call_llm
    calls = {"n": 0}

    def flaky(task: str, variables: dict[str, str]):
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMCallError("Gọi OpenAI thất bại (APITimeoutError). Kiểm tra khóa, mạng và hạn mức.")
        return real(task, variables)

    monkeypatch.setattr(planner, "call_llm", flaky)
    run_id = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    get_jobs().wait(run_id)
    failed = (await client.get(f"{API}/runs/{run_id}")).json()
    assert failed["record"]["status"] == "failed" and "APITimeoutError" in failed["record"]["summary"]["error"]
    assert failed["retryable"] is True

    accepted = await client.post(f"{API}/runs/{run_id}/retry")
    assert accepted.status_code == 202
    get_jobs().wait(run_id)
    after = (await client.get(f"{API}/runs/{run_id}")).json()
    assert after["record"]["status"] == "waiting_clarification" and after["retryable"] is False  # đi tiếp tới câu hỏi
    assert calls["n"] == 2  # planner chạy lại đúng một lần, không lặp phần đã xong


async def test_retry_is_refused_when_nothing_to_retry(client: AsyncClient, login, seeded_sources):
    created = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    get_jobs().wait(created)
    refused = await client.post(f"{API}/runs/{created}/retry")  # đang chờ làm rõ, không phải lỗi
    assert refused.status_code == 409 and "lỗi" in refused.json()["detail"]
    assert (await client.post(f"{API}/runs/khong-co/retry")).status_code == 404
    reviewer = await login("reviewer")
    assert (await reviewer.post(f"{API}/runs/{created}/retry")).status_code == 403  # chỉ Engineer

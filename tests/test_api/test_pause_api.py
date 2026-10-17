"""Tạm dừng / tiếp tục lần chạy thật (ADR 0016), chạy với LLM mock.

Node planner được "chặn cửa" (threading.Event) để biết chắc yêu cầu tạm dừng đến lúc node ĐANG chạy.
"""

import asyncio
import threading
from collections.abc import Iterator

import pytest
from httpx import AsyncClient

from src.agents import runner
from src.agents.nodes import planner
from src.config import get_settings
from src.models.schemas import RunStatus
from src.services import auth
from src.services.jobs import get_jobs
from src.services.llm import LLMCallError
from src.services.store import get_store

API = "/api/v1"
REQUEST = {"request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày"}


class Gate:
    """Chặn lời gọi LLM của planner tới khi test mở cửa; đếm số lần gọi."""

    def __init__(self, fail: bool = False) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self.fail = fail
        self.real = planner.call_llm

    def __call__(self, task: str, variables: dict[str, str]):
        self.calls += 1
        self.entered.set()
        assert self.release.wait(30), "test quên mở cửa"
        if self.fail:
            raise LLMCallError("Gọi OpenAI thất bại (APITimeoutError).")
        return self.real(task, variables)


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> Iterator[Gate]:
    g = Gate()
    monkeypatch.setattr(planner, "call_llm", g)
    yield g
    g.release.set()  # không để luồng nền kẹt nếu test lỗi giữa chừng


async def _detail(client: AsyncClient, run_id: str) -> dict:
    return (await client.get(f"{API}/runs/{run_id}")).json()


async def _paused_run(client: AsyncClient, gate: Gate) -> str:
    """Lần chạy bị tạm dừng ngay sau planner (planner đã chạy đúng 1 lần, clarify chưa chạy)."""
    run_id = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    assert gate.entered.wait(30)
    accepted = await client.post(f"{API}/runs/{run_id}/pause")
    assert accepted.status_code == 202 and accepted.json()["status"] == "pausing"
    gate.release.set()
    get_jobs().wait(run_id)
    return run_id


async def test_pause_while_node_runs_finishes_node_then_stops_before_next(client: AsyncClient, gate, seeded_sources):
    run_id = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    assert gate.entered.wait(30)
    accepted = await client.post(f"{API}/runs/{run_id}/pause")
    assert accepted.status_code == 202
    assert "vẫn có thể phát sinh chi phí AI" in accepted.json()["message"]
    pausing = await _detail(client, run_id)
    assert pausing["record"]["status"] == "running" and pausing["record"]["pause_requested"] is True
    listed = {r["id"]: r for r in (await client.get(f"{API}/runs")).json()}
    assert listed[run_id]["pause_requested"] is True  # danh sách cũng thấy "đang chờ tạm dừng"

    gate.release.set()
    get_jobs().wait(run_id)
    paused = await _detail(client, run_id)
    assert paused["record"]["status"] == "paused" and paused["record"]["pause_requested"] is False
    assert paused["busy"] is False and paused["pending"] is None  # luồng nền đã trả lại, không chờ trong vòng lặp
    assert gate.calls == 1  # planner chạy xong đúng một lần
    assert runner._next_nodes(run_id) == ["clarify"]  # node kế tiếp chưa chạy
    assert "planner" in [e["node"] for e in paused["events"]] and "clarify" not in [e["node"] for e in paused["events"]]
    assert any(s["detail"] == "tạm dừng trước bước này" for s in paused["stages"])
    actions = [(a.action, a.target) for a in auth.recent_audit(50)]
    assert ("run.pause", run_id) in actions and ("run.paused", run_id) in actions

    resumed = await client.post(f"{API}/runs/{run_id}/resume")
    assert resumed.status_code == 202
    get_jobs().wait(run_id)
    after = await _detail(client, run_id)
    assert after["record"]["status"] == "waiting_clarification"  # đi tiếp đúng chỗ: clarify hỏi câu hỏi
    assert gate.calls == 1  # không gọi lại AI cho kết quả planner đã lưu
    assert ("run.resume", run_id) in [(a.action, a.target) for a in auth.recent_audit(50)]


async def test_pause_while_queued_never_starts(client: AsyncClient, gate, seeded_sources):
    first = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]  # chiếm luồng nền duy nhất (SQLite)
    assert gate.entered.wait(30)
    queued = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    assert (await _detail(client, queued))["queue_position"] == 1
    assert (await client.post(f"{API}/runs/{queued}/pause")).status_code == 202
    gate.release.set()
    get_jobs().wait(first)
    get_jobs().wait(queued)
    assert (await _detail(client, queued))["record"]["status"] == "paused"
    assert gate.calls == 1  # chỉ lần chạy đầu gọi planner
    assert runner.get_values(queued) == {}  # graph của lần chạy xếp hàng chưa nhận gì

    assert (await client.post(f"{API}/runs/{queued}/resume")).status_code == 202
    get_jobs().wait(queued)
    assert (await _detail(client, queued))["record"]["status"] == "waiting_clarification"
    assert gate.calls == 2


async def test_repeated_and_concurrent_pause_resume(client: AsyncClient, gate, seeded_sources):
    run_id = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    assert gate.entered.wait(30)
    twice = await asyncio.gather(*(client.post(f"{API}/runs/{run_id}/pause") for _ in range(3)))
    assert all(r.status_code == 202 for r in twice)
    gate.release.set()
    get_jobs().wait(run_id)
    again = await client.post(f"{API}/runs/{run_id}/pause")  # đã tạm dừng: bấm lặp không lỗi, không đổi gì
    assert again.status_code == 202 and again.json()["status"] == "paused"

    both = await asyncio.gather(*(client.post(f"{API}/runs/{run_id}/resume") for _ in range(2)))
    assert sorted(r.status_code for r in both) == [202, 409]  # chỉ một lần được chạy tiếp
    get_jobs().wait(run_id)
    assert (await _detail(client, run_id))["record"]["status"] == "waiting_clarification"
    assert gate.calls == 1


async def test_pause_resume_denied_for_others(client: AsyncClient, login, gate, seeded_sources):
    run_id = await _paused_run(client, gate)
    reviewer, admin, other = await login("reviewer"), await login("admin"), await login("engineer")
    for who in (reviewer, admin):  # không mở rộng quyền Reviewer/Admin
        assert (await who.post(f"{API}/runs/{run_id}/resume")).status_code == 403
        assert (await who.post(f"{API}/runs/{run_id}/pause")).status_code == 403
    for path in ("pause", "resume"):  # Engineer khác: không thấy (404) hoặc không phải người tạo (403)
        assert (await other.post(f"{API}/runs/{run_id}/{path}")).status_code in (403, 404)
    assert (await client.post(f"{API}/runs/khong-co/pause")).status_code == 404
    assert (await _detail(client, run_id))["record"]["status"] == "paused"


async def test_paused_run_survives_restart(client: AsyncClient, gate, seeded_sources):
    run_id = await _paused_run(client, gate)
    runner._graph.cache_clear()  # như khởi động lại: graph + kết nối checkpoint mới
    assert get_store().fail_interrupted_runs() == 0  # lần chạy đã tạm dừng giữ nguyên, không bị đánh lỗi
    assert (await _detail(client, run_id))["record"]["status"] == "paused"
    assert (await client.post(f"{API}/runs/{run_id}/resume")).status_code == 202
    get_jobs().wait(run_id)
    assert (await _detail(client, run_id))["record"]["status"] == "waiting_clarification"
    assert gate.calls == 1


def test_restart_while_pausing_becomes_paused_not_failed():
    store = get_store()
    pausing, plain = store.create_run("chờ tạm dừng", "eng"), store.create_run("đang chạy", "eng")
    assert store.request_pause(pausing.id, "eng") is True
    assert store.request_pause(pausing.id, "eng") is True  # bấm lặp: vẫn một dòng
    assert store.get_run(pausing.id).pause_requested is True
    store.fail_interrupted_runs()
    assert store.get_run(pausing.id).status == RunStatus.PAUSED
    assert "khởi động lại" in store.get_run(pausing.id).summary["notice"]
    assert store.get_run(plain.id).status == RunStatus.FAILED


@pytest.mark.parametrize("final", [RunStatus.APPROVED, RunStatus.FAILED, RunStatus.WAITING_REVIEW])
def test_final_status_is_never_overwritten_by_pending_pause(final: RunStatus):
    store = get_store()
    run = store.create_run("xong đúng lúc bấm tạm dừng", "eng")
    assert store.request_pause(run.id, "eng") is True
    store.update_run(run.id, final, {"error": ""})  # lần chạy tự xong / lỗi / tới bước chờ người
    record = store.get_run(run.id)
    assert record.status == final and record.pause_requested is False
    assert store.take_pause(run.id) is False  # yêu cầu cũ đã bị bỏ, không làm dừng lượt sau
    assert store.request_pause(run.id, "eng") is False  # không còn chạy: không nhận yêu cầu mới


async def test_run_failing_during_pause_stays_failed(client: AsyncClient, gate, seeded_sources):
    gate.fail = True
    run_id = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    assert gate.entered.wait(30)
    assert (await client.post(f"{API}/runs/{run_id}/pause")).status_code == 202
    gate.release.set()
    get_jobs().wait(run_id)
    failed = await _detail(client, run_id)
    assert failed["record"]["status"] == "failed" and failed["record"]["pause_requested"] is False
    assert failed["retryable"] is True  # dùng đường "chạy lại từ bước lỗi" như cũ, không thành "đã tạm dừng"


async def test_pause_refused_when_waiting_or_done(client: AsyncClient, seeded_sources):
    run_id = (await client.post(f"{API}/runs", json=REQUEST)).json()["run_id"]
    get_jobs().wait(run_id)
    assert (await _detail(client, run_id))["record"]["status"] == "waiting_clarification"
    refused = await client.post(f"{API}/runs/{run_id}/pause")  # đang chờ người: giữ trạng thái chờ
    assert refused.status_code == 409
    assert (await _detail(client, run_id))["record"]["status"] == "waiting_clarification"
    assert (await client.post(f"{API}/runs/{run_id}/resume")).status_code == 409  # không phải "đã tạm dừng"


async def test_resume_refused_when_budget_or_limits_hit(
    client: AsyncClient, gate, monkeypatch: pytest.MonkeyPatch, seeded_sources
):
    run_id = await _paused_run(client, gate)
    settings = get_settings()
    monkeypatch.setattr(settings, "run_token_budget", 1)  # mock vẫn đếm token: planner đã dùng > 1
    over = await client.post(f"{API}/runs/{run_id}/resume")
    assert over.status_code == 409 and "RUN_TOKEN_BUDGET" in over.json()["detail"]
    monkeypatch.setattr(settings, "run_token_budget", 0)
    monkeypatch.setattr(settings, "max_active_runs_per_user", 0)  # chạm giới hạn số lần chạy cùng lúc
    limited = await client.post(f"{API}/runs/{run_id}/resume")
    assert limited.status_code == 429
    assert (await _detail(client, run_id))["record"]["status"] == "paused"  # không đổi gì khi bị từ chối
    assert gate.calls == 1

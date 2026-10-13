"""CLAUDE.md mục 14: lần chạy kẹt sau khi khởi động lại (14.1), giới hạn lần chạy cùng lúc + vị trí hàng đợi (14.2),
trần chi phí LLM theo người/ngày và cảnh báo model thiếu giá (14.3)."""

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from src.config import Settings
from src.models.schemas import RunStatus
from src.services import doctor, jobs
from src.services.jobs import JobLimitError, JobQueue, check_limits
from src.services.store import INTERRUPTED, Store, get_store

API = "/api/v1"


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "app.db")


def test_interrupted_runs_marked_failed_on_startup(store: Store):
    stuck = store.create_run("doanh thu", "an")
    waiting = store.create_run("khách hàng", "an")
    store.update_run(waiting.id, RunStatus.WAITING_REVIEW, {"target": "fct_x"})
    assert store.fail_interrupted_runs() == 1
    failed = store.get_run(stuck.id)
    assert failed.status == RunStatus.FAILED and failed.summary["error"] == INTERRUPTED
    assert store.get_run(waiting.id).status == RunStatus.WAITING_REVIEW  # đang chờ người: giữ nguyên
    assert store.fail_interrupted_runs() == 0


def test_spent_today_counts_real_cost_of_today_only(store: Store):
    for cost, simulated in ((0.4, False), (0.3, False), (9.0, True)):
        run = store.create_run("x", "an")
        store.update_run(run.id, RunStatus.WAITING_REVIEW, {"cost_usd": cost, "simulated": simulated})
    old = store.create_run("x", "an")
    store.update_run(old.id, RunStatus.APPROVED, {"cost_usd": 5.0})
    yesterday = (datetime.now(UTC) - timedelta(days=2)).isoformat(timespec="seconds")
    with store.engine.begin() as conn:
        conn.execute(text("UPDATE runs SET created_at=:t WHERE id=:id"), {"t": yesterday, "id": old.id})
    other = store.create_run("x", "binh")
    store.update_run(other.id, RunStatus.APPROVED, {"cost_usd": 2.0})
    assert store.spent_today("an") == pytest.approx(0.7)  # bỏ lần mô phỏng, lần hôm trước, người khác


def _settings(monkeypatch: pytest.MonkeyPatch, **values) -> None:
    settings = Settings(**{"max_active_runs_per_user": 2, "llm_daily_budget_usd": 1.0, **values})
    monkeypatch.setattr(jobs, "get_settings", lambda: settings)


def test_budget_blocks_real_llm_but_not_mock(monkeypatch: pytest.MonkeyPatch):
    run = get_store().create_run("x", "chi_tieu")
    get_store().update_run(run.id, RunStatus.APPROVED, {"cost_usd": 1.2})
    _settings(monkeypatch, llm_provider="openai")
    with pytest.raises(JobLimitError, match="chạm trần 1.00 USD"):
        check_limits("chi_tieu", active=0)
    check_limits("nguoi_khac", active=0)  # người khác chưa tiêu gì
    _settings(monkeypatch, llm_provider="mock")
    check_limits("chi_tieu", active=0)  # mô phỏng không tốn tiền
    with pytest.raises(JobLimitError, match="tối đa 2"):
        check_limits("chi_tieu", active=2)


def test_queue_counts_active_runs_per_owner_and_position(tmp_path: Path):
    queue = JobQueue(tmp_path / "timings.json")
    gate = threading.Event()
    ids = [get_store().create_run("x", "an").id for _ in range(3)]

    def job(_sink):
        gate.wait(10)

    for run_id, owner in zip(ids, ("an", "an", "binh"), strict=True):
        queue.submit(run_id, job, actor=owner, owner=owner)
    try:
        assert [queue.position(r) for r in ids] == [0, 1, 2]  # một luồng: lần đầu đang chạy, sau đó xếp hàng
        with pytest.raises(JobLimitError):
            queue.check("an")
        queue.check("an", run_id=ids[0])  # chạy tiếp chính lần chạy đó không tính trùng
        queue.check("binh")
    finally:
        gate.set()
        for run_id in ids:
            queue.wait(run_id)
    assert queue.position(ids[0]) is None
    queue.check("an")


async def test_create_run_returns_429_when_limit_reached(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    def refuse(owner: str, run_id: str = "") -> None:
        raise JobLimitError("Bạn đang có 2 lần chạy đang chờ hoặc đang chạy (tối đa 2).")

    monkeypatch.setattr(jobs.get_jobs(), "check", refuse)
    before = len(get_store().list_runs(100))
    response = await client.post(f"{API}/runs", json={"request_text": "Gộp đơn hàng 3 nguồn"})
    assert response.status_code == 429 and "tối đa 2" in response.json()["detail"]
    assert len(get_store().list_runs(100)) == before  # bị chặn trước khi tạo: không để lại lần chạy treo


def test_doctor_warns_when_model_has_no_price(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    path = tmp_path / "models.yaml"
    table = {
        "models": {t: {"provider": "openai", "name": "model-chua-co-gia"} for t in ("planner", "codegen", "testgen")},
        "fallback": {"provider": "google", "name": "gemini-3.8-flash"},
    }
    table["models"]["optimizer"] = {"provider": "openai", "name": "gpt-6-luna"}
    path.write_text(json.dumps(table), encoding="utf-8")  # JSON cũng là YAML hợp lệ
    settings = Settings(llm_provider="openai", openai_api_key="sk-test-" + "x" * 20, models_file=path)
    monkeypatch.setattr(doctor, "get_settings", lambda: settings)
    check = next(r for r in doctor.run_checks() if r.name == "Bảng giá LLM")
    assert check.level == "warn" and "model-chua-co-gia" in check.message and "gpt-6-luna" not in check.message

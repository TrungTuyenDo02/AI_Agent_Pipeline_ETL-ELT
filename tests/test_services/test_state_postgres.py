"""Lưu trạng thái trên PostgreSQL (Neon): chỉ chạy khi TEST_DATABASE_URL là PostgreSQL (CI/máy có Neon test)."""

import uuid
from pathlib import Path

import pytest

from src.config import Settings
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL.startswith("postgresql"), reason="cần TEST_DATABASE_URL là PostgreSQL"
)


@pytest.fixture
def postgres_backend(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    settings = Settings(state_backend="postgres", run_workers=2, store_path=tmp_path / "unused.db")
    monkeypatch.setattr("src.services.state_db.get_settings", lambda: settings)
    monkeypatch.setattr("src.services.store.get_settings", lambda: settings)
    return settings


def test_store_roundtrip_and_order(postgres_backend):
    from src.models.schemas import RunStatus
    from src.services.store import Store

    store = Store(postgres_backend.store_path)
    user = f"u{uuid.uuid4().hex[:8]}"
    first = store.create_run("một", user)
    second = store.create_run("hai", user)
    store.update_run(first.id, RunStatus.WAITING_REVIEW, {"cost_usd": 0.1})
    assert store.get_run(first.id).summary == {"cost_usd": 0.1}
    ids = [r.id for r in store.list_runs(50)]
    assert ids.index(second.id) < ids.index(first.id)  # lần tạo sau xếp trước, kể cả cùng giây
    assert store.spent_today(user) == pytest.approx(0.1)
    assert store.ping()


def test_error_memory_upsert_on_postgres(postgres_backend):
    from src.models.evidence import ErrorEntry
    from src.services.error_memory import ErrorMemory

    memory = ErrorMemory(postgres_backend.store_path)
    signature = uuid.uuid4().hex[:12]
    entry = ErrorEntry(code="UNKNOWN", signature=signature, description="lỗi thử")
    memory.record(entry)
    again = memory.record(entry)
    assert again.occurrences == 2 and not again.approved
    assert memory.approve(again.id, "sửa thử") and memory.approved_hints(signature, "UNKNOWN")
    assert memory.discard(again.id)


def test_agent_memory_on_postgres(postgres_backend):
    from src.services.agent_memory import AgentMemory

    memory = AgentMemory(postgres_backend.store_path)
    account = f"u{uuid.uuid4().hex[:8]}"
    item = memory.add(account, "preference", f"thử {uuid.uuid4().hex}", "r1")
    assert item.status == "pending" and memory.approved(account) == []
    assert memory.approve(account, item.id) and len(memory.approved(account)) == 1
    assert memory.approved("nguoi-khac") == []
    assert memory.discard(account, item.id)


def test_postgres_checkpointer_persists_graph_state(postgres_backend, monkeypatch: pytest.MonkeyPatch):
    from src.agents import runner

    monkeypatch.setattr(runner, "get_settings", lambda: postgres_backend)
    monkeypatch.setattr(runner, "_graph", runner._graph.__wrapped__)  # tránh dùng lại graph SQLite đã cache
    monkeypatch.setattr(runner, "_postgres_pool", runner._postgres_pool.__wrapped__)
    graph = runner.get_graph()
    config = {"configurable": {"thread_id": f"t{uuid.uuid4().hex[:8]}"}}
    assert graph.get_state(config).values == {}  # đọc được bảng checkpoint (đã có quyền)


def test_cost_ledger_reservation_is_atomic_on_postgres(postgres_backend, monkeypatch: pytest.MonkeyPatch):
    """READ COMMITTED: hai job cùng đọc "còn tiền" vẫn không được giữ quá trần (UPDATE có điều kiện, ADR 0014)."""
    import threading

    from src.services import cost_ledger
    from src.services.cost_ledger import BudgetDeniedError, CostLedger

    limits = Settings(llm_daily_budget_usd=0.5)
    monkeypatch.setattr(cost_ledger, "get_settings", lambda: limits)
    book = CostLedger(postgres_backend.store_path)
    owner = f"u{uuid.uuid4().hex[:8]}"
    ok, denied = [], []

    def worker() -> None:
        try:
            ok.append(
                book.reserve(
                    owner=owner,
                    run_id="",
                    task="codegen",
                    provider="openai",
                    model="gpt-6-luna",
                    estimate_usd=0.1,
                    ttl_sec=60,
                )  # fmt: skip
            )
        except BudgetDeniedError:
            denied.append(1)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ok) == 5 and len(denied) == 5
    assert book.spent_today(owner) == pytest.approx(0.5)
    for call_id in ok:
        book.release(call_id)
    assert book.spent_today(owner) == 0.0

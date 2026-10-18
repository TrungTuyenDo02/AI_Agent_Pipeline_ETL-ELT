"""Test API Phase 7 (mock, không cần khóa): tạo yêu cầu → J1 → bản duyệt → duyệt; cấu trúc dữ liệu; sổ lỗi; lỗi thân thiện.

Chạy nền thật (hàng đợi một luồng); test chờ bằng `get_jobs().wait(run_id)`.
"""

import io
import zipfile
from pathlib import Path

import pytest
from httpx import AsyncClient

from src.services.jobs import get_jobs

API = "/api/v1"
REQUEST = {"request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày"}


async def _create_and_answer(client: AsyncClient) -> str:
    """Engineer (client) tạo yêu cầu, trả lời J1 bằng lựa chọn đầu, đồng ý kế hoạch J1b, chờ tới bản duyệt."""
    created = await client.post(f"{API}/runs", json=REQUEST)
    assert created.status_code == 202
    run_id = created.json()["run_id"]
    get_jobs().wait(run_id)
    detail = (await client.get(f"{API}/runs/{run_id}")).json()
    assert detail["record"]["status"] == "waiting_clarification" and detail["pending"]["kind"] == "clarify"
    answers = {q["id"]: q["options"][0] for q in detail["pending"]["questions"]}
    assert (await client.post(f"{API}/runs/{run_id}/answers", json={"answers": answers})).status_code == 202
    get_jobs().wait(run_id)
    plan = (await client.get(f"{API}/runs/{run_id}")).json()
    assert plan["record"]["status"] == "waiting_plan_review" and plan["pending"]["steps"]
    blank = await client.post(f"{API}/runs/{run_id}/plan", json={"decision": "revise"})
    assert blank.status_code == 422 and "ghi chú" in blank.json()["detail"]
    assert (await client.post(f"{API}/runs/{run_id}/plan", json={"decision": "approve"})).status_code == 202
    get_jobs().wait(run_id)
    return run_id


@pytest.mark.slow
async def test_full_flow_engineer_then_reviewer(client: AsyncClient, login, seeded_sources: Path):
    """Engineer tạo yêu cầu, Reviewer xem bằng chứng và duyệt; Engineer không duyệt được."""
    run_id = await _create_and_answer(client)
    detail = (await client.get(f"{API}/runs/{run_id}")).json()
    assert detail["record"]["status"] == "waiting_review" and detail["busy"] is False
    assert detail["current"] is None  # rảnh: không có node nào đang chạy
    assert all("finished_at" in e for e in detail["events"])
    assert detail["spec"]["target"] == "fct_daily_revenue" and detail["evidence"]["measured"]
    assert detail["spec"]["plan"] and detail["spec"]["plan_summary"]  # kế hoạch đã duyệt vẫn xem lại được
    assert any(e["node"] == "sandbox_run" and e["ok"] for e in detail["events"])
    files = (await client.get(f"{API}/runs/{run_id}/files")).json()
    assert "models/marts/fct_daily_revenue.sql" in files["code_files"] and files["test_files"]
    assert detail["answered"] and detail["answered"][0]["answer"]
    download = await client.get(f"{API}/runs/{run_id}/download")
    assert download.status_code == 200 and download.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(download.content)).namelist()
    assert f"p113-{run_id}/models/marts/fct_daily_revenue.sql" in names
    assert not any(n.endswith(".duckdb") or "/datasets/" in n or n.endswith("profiles.yml") for n in names)
    assert run_id in [r["id"] for r in (await client.get(f"{API}/reviews/queue")).json()]
    assert (await client.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})).status_code == 403
    reviewer = await login("reviewer")
    review = await reviewer.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})
    assert review.status_code == 202
    get_jobs().wait(run_id)
    assert (await client.get(f"{API}/runs/{run_id}")).json()["record"]["status"] == "approved"


@pytest.mark.slow
async def test_run_catalog_shows_tables_lineage_and_keys(client: AsyncClient, seeded_sources: Path):
    run_id = await _create_and_answer(client)
    catalog = (await client.get(f"{API}/runs/{run_id}/catalog")).json()
    tables = {t["id"]: t for t in catalog["tables"]}
    assert {"raw.shopee_orders", "main.stg_shopee_orders", "main.fct_daily_revenue"} <= set(tables)
    assert tables["main.fct_daily_revenue"]["layer"] == "mart" and tables["main.fct_daily_revenue"]["rows"] > 0
    assert any(c["name"] == "order_date" and c["is_key"] for c in tables["main.fct_daily_revenue"]["columns"])
    assert tables["raw.shopee_orders"]["duplicate_keys"] > 0  # dữ liệu giả lập có đơn trùng
    edges = {(e["source"], e["target"]) for e in catalog["lineage"]}
    assert ("raw.shopee_orders", "main.stg_shopee_orders") in edges
    assert ("main.stg_shopee_orders", "main.fct_daily_revenue") in edges
    # Hồ sơ dữ liệu của bảng do code AI sinh: chạy được trên sandbox và trên bộ dữ liệu bẩn
    mart = (await client.get(f"{API}/runs/{run_id}/profile", params={"table": "main.fct_daily_revenue"})).json()
    assert mart["layer"] == "mart" and mart["rows"] > 0 and mart["keys"] == ["order_date"]
    assert mart["duplicate_keys"] == 0 and len(mart["preview"]) == min(mart["rows"], 50)
    assert {"sandbox", "dirty"} <= set(mart["datasets"]) and "large" not in mart["datasets"]
    staging = await client.get(
        f"{API}/runs/{run_id}/profile", params={"table": "main.stg_shopee_orders", "dataset": "dirty"}
    )
    assert staging.status_code == 200 and staging.json()["rows_in"] is not None
    missing = await client.get(f"{API}/runs/{run_id}/profile", params={"table": "main.khong_co"})
    assert missing.status_code == 404


async def test_sources_catalog_suggests_join_keys(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from src.config import get_settings

    golden = Path(__file__).resolve().parents[2] / "eval" / "datasets" / "golden" / "g09_customer_dimension" / "sources"
    monkeypatch.setenv("SOURCES_DIR", str(golden))
    get_settings.cache_clear()
    try:
        catalog = (await client.get(f"{API}/catalog/sources")).json()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
    assert {t["name"] for t in catalog["tables"]} == {"customers", "orders"}
    assert catalog["joins"][0]["how"] == "gợi ý" and "customer_id" in catalog["joins"][0]["left"]


async def test_sources_profile_for_data_roles_only(login, monkeypatch: pytest.MonkeyPatch):
    """Hồ sơ dữ liệu có dòng xem trước → Engineer/Reviewer xem được, Admin bị 403 (quyền hẹp)."""
    from src.config import get_settings

    golden = Path(__file__).resolve().parents[2] / "eval" / "datasets" / "golden" / "g09_customer_dimension" / "sources"
    monkeypatch.setenv("SOURCES_DIR", str(golden))
    get_settings.cache_clear()
    try:
        path, params = f"{API}/catalog/sources/profile", {"table": "customers"}
        profile = (await (await login("reviewer")).get(path, params=params)).json()
        admin = await (await login("admin")).get(path, params=params)
        missing = await (await login("engineer")).get(path, params={"table": "khong_co"})
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
    assert profile["layer"] == "source" and profile["rows"] > 0 and profile["columns"]
    assert all(len(row) == len(profile["columns"]) for row in profile["preview"])
    assert admin.status_code == 403 and missing.status_code == 404


@pytest.mark.parametrize(
    ("role", "method", "path", "body", "code"),
    [
        ("engineer", "get", "/runs/khong-co", None, 404),
        ("engineer", "get", "/runs/khong-co/catalog", None, 404),
        ("engineer", "get", "/runs/khong-co/download", None, 404),
        ("engineer", "post", "/runs", {"request_text": "x"}, 422),
        ("reviewer", "post", "/runs/khong-co/review", {"decision": "approve"}, 404),
        ("engineer", "post", "/runs/khong-co/plan", {"decision": "approve"}, 404),
        ("reviewer", "post", "/errors/999999/approve", {"fix": "x"}, 404),
    ],
)
async def test_friendly_errors(login, role: str, method: str, path: str, body: dict | None, code: int):
    client = await login(role)
    response = await getattr(client, method)(f"{API}{path}", **({"json": body} if body is not None else {}))
    assert response.status_code == code
    assert isinstance(response.json()["detail"], str) and "Traceback" not in response.text


async def test_review_requires_note_and_waiting_state(client: AsyncClient, login):
    from src.services.store import get_store

    run_id = get_store().create_run("doanh thu", client.username).id
    reviewer = await login("reviewer")
    reject = await reviewer.post(f"{API}/runs/{run_id}/review", json={"decision": "reject"})
    assert reject.status_code == 422 and "ghi chú" in reject.json()["detail"]
    approve = await reviewer.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})
    assert approve.status_code == 409  # chưa ở bước chờ duyệt
    answer = await client.post(f"{API}/runs/{run_id}/answers", json={"answers": {"q": "a"}})
    assert answer.status_code == 409


async def test_status_reports_review_mode(client: AsyncClient):
    data = (await client.get(f"{API}/status")).json()
    assert data["simulated"] is True and data["models"] == "mock"


async def test_error_book_listing(client: AsyncClient):
    response = await client.get(f"{API}/errors")
    assert response.status_code == 200 and isinstance(response.json(), list)


@pytest.mark.slow
async def test_review_gate_blocks_direct_approve_api(
    client: AsyncClient, login, seeded_sources: Path, monkeypatch: pytest.MonkeyPatch
):
    """Cổng duyệt do backend tính: gọi thẳng API Duyệt khi kiểm tra bắt buộc không đạt / chưa kiểm chứng → 409, không ghi duyệt."""
    from src.agents import runner

    run_id = await _create_and_answer(client)
    detail = (await client.get(f"{API}/runs/{run_id}")).json()
    gate = detail["review_gate"]
    assert gate["passed"] and [c["id"] for c in gate["checks"]] == ["model_run", "dag", "dbt_tests", "expected"]
    assert {c["id"]: c["status"] for c in gate["extra"]}["airflow_run"] == "unverified"
    assert detail["sandbox"]["model_timings"] and detail["optimization"]["bottlenecks"]["measured"]
    assert detail["reviews"] == []
    tests = detail["dbt_tests"]  # từng dbt test của lần V2 cuối, người dùng xem được (không chỉ con số x/y)
    assert len(tests) == detail["sandbox"]["tests_total"] and {t["kind"] for t in tests} >= {"testgen"}
    assert all(t["status"] in ("pass", "warn") for t in tests)
    real = runner.get_values(run_id)
    reviewer = await login("reviewer")
    tampered = {
        "failed": {**real, "sandbox": {**real["sandbox"], "tests_ok": real["sandbox"]["tests_total"] - 1}},
        "legacy": {k: v for k, v in real.items() if k != "test_files"},  # checkpoint cũ thiếu bằng chứng
    }
    for case, values in tampered.items():
        monkeypatch.setattr(runner, "get_values", lambda _run_id, values=values: values)
        shown = (await client.get(f"{API}/runs/{run_id}")).json()["review_gate"]
        status = {c["id"]: c["status"] for c in shown["checks"]}
        assert not shown["passed"]
        assert status["dbt_tests" if case == "failed" else "expected"] == (
            "failed" if case == "failed" else "unverified"
        )
        blocked = await reviewer.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})
        assert blocked.status_code == 409 and "kiểm tra bắt buộc" in blocked.json()["detail"], case
    monkeypatch.undo()
    assert (await client.get(f"{API}/runs/{run_id}")).json()["record"]["status"] == "waiting_review"
    assert (await reviewer.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})).status_code == 202
    get_jobs().wait(run_id)
    reviews = (await client.get(f"{API}/runs/{run_id}")).json()["reviews"]
    assert (
        len(reviews) == 1
        and reviews[0]["decision"] == "approve"
        and reviews[0]["reviewer"]
        and reviews[0]["decided_at"]
    )

"""Test API: health, trạng thái agent, đọc danh sách/chi tiết lần chạy."""

from src.services.store import get_store


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["llm_provider"] == "mock"
    assert data["version"] and data["timestamp"]


async def test_agent_status_reports_simulated_mode(client):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["simulated"] is True


async def test_get_unknown_run_returns_friendly_404(client):
    response = await client.get("/api/v1/runs/khong-ton-tai")
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


async def test_list_and_get_run(client):
    record = get_store().create_run("tính doanh thu ngày", "alice")
    listed = await client.get("/api/v1/runs", params={"limit": 5})
    assert listed.status_code == 200
    assert record.id in [r["id"] for r in listed.json()]
    detail = await client.get(f"/api/v1/runs/{record.id}")
    assert detail.json()["record"]["requester"] == "alice"


async def test_list_runs_rejects_invalid_limit(client):
    response = await client.get("/api/v1/runs", params={"limit": 0})
    assert response.status_code == 422


def test_dev_cors_regex_accepts_local_origins_only():
    """Development: web mở bằng 127.0.0.1 / IP mạng nội bộ / cổng khác vẫn gọi được API; domain lạ bị chặn."""
    import re

    from src.main import DEV_ORIGIN_REGEX

    for origin in (
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://192.168.1.20:3000",
        "http://10.0.0.5:3000",
    ):
        assert re.fullmatch(DEV_ORIGIN_REGEX, origin), origin
    for origin in ("http://evil.example.com", "http://192.168.1.20.evil.com", "https://localhost.evil.com:3000"):
        assert not re.fullmatch(DEV_ORIGIN_REGEX, origin), origin


async def test_cors_outside_development_accepts_only_configured_origins(client):
    """APP_ENV=test (giống production): chỉ CORS_ORIGINS, không nhận 127.0.0.1."""
    ok = await client.get("/health", headers={"Origin": "http://localhost:3000"})
    other = await client.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert other.headers.get("access-control-allow-origin") is None

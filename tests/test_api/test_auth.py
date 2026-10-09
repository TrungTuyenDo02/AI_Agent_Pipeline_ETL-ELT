"""Đăng nhập, đăng xuất, phân quyền Engineer/Reviewer/Admin, nhật ký kiểm toán, migration từ đầu (CLAUDE.md mục 2–5)."""

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.orm import Session

from src.api.deps import SESSION_COOKIE
from src.services import auth
from src.services.store import get_store
from tests.conftest import TEST_DATABASE_URL, migrate

API = "/api/v1"


def _actions(target: str) -> list[tuple[str, str]]:
    with Session(auth.get_engine()) as db:
        rows = db.scalars(sa.select(auth.AuditEntry).where(auth.AuditEntry.target.contains(target)))
        return [(r.action, r.outcome) for r in rows]


# ---------- 401: chưa đăng nhập ----------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/status"),
        ("get", "/runs"),
        ("get", "/runs/abc"),
        ("post", "/runs"),
        ("post", "/runs/abc/review"),
        ("get", "/errors"),
        ("get", "/catalog/sources"),
        ("get", "/auth/me"),
        ("get", "/admin/users"),
    ],
)
async def test_every_api_requires_login(anon: AsyncClient, method: str, path: str):
    response = await getattr(anon, method)(f"{API}{path}", **({"json": {}} if method == "post" else {}))
    assert response.status_code == 401
    assert response.json()["detail"] == "Bạn cần đăng nhập."


async def test_health_stays_public_for_docker(anon: AsyncClient):
    assert (await anon.get("/health")).status_code == 200


async def test_no_signup_endpoint(anon: AsyncClient):
    for path in ("/auth/register", "/auth/signup", "/users"):
        assert (await anon.post(f"{API}{path}", json={"username": "x", "password": "y" * 12})).status_code in (404, 405)


# ---------- Đăng nhập / đăng xuất / cookie ----------


async def test_login_sets_safe_cookie_and_password_is_hashed(anon: AsyncClient, make_user):
    name, password = make_user("engineer")
    response = await anon.post(f"{API}/auth/login", json={"username": name.upper(), "password": password})
    assert response.status_code == 200 and response.json()["role"] == "engineer"
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie and "max-age=" in cookie
    me = (await anon.get(f"{API}/auth/me")).json()
    assert me["name"] == name and me["role"] == "engineer"
    stored = auth.find_user(name)
    assert stored.password_hash.startswith("$argon2id$") and password not in stored.password_hash


async def test_wrong_password_and_unknown_user_get_same_message(anon: AsyncClient, make_user):
    name, _ = make_user("engineer")
    wrong = await anon.post(f"{API}/auth/login", json={"username": name, "password": "sai-mat-khau-123"})
    unknown = await anon.post(f"{API}/auth/login", json={"username": "khong-ton-tai", "password": "x" * 12})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]
    assert ("login", "fail") in _actions(name)


async def test_too_many_failures_locks_login(anon: AsyncClient, make_user):
    name, password = make_user("engineer")
    for _ in range(auth.get_settings().login_max_failures):
        await anon.post(f"{API}/auth/login", json={"username": name, "password": "sai-mat-khau-123"})
    locked = await anon.post(f"{API}/auth/login", json={"username": name, "password": password})
    assert locked.status_code == 429  # đúng mật khẩu cũng phải chờ hết thời gian khóa


async def test_logout_invalidates_session_on_server(anon: AsyncClient, make_user):
    name, password = make_user("engineer")
    await anon.post(f"{API}/auth/login", json={"username": name, "password": password})
    token = anon.cookies[SESSION_COOKIE]
    assert (await anon.post(f"{API}/auth/logout")).status_code == 204
    anon.cookies.set(SESSION_COOKIE, token)  # kẻ gian giữ lại cookie cũ
    assert (await anon.get(f"{API}/auth/me")).status_code == 401
    assert ("logout", "ok") in _actions(name)


async def test_expired_session_is_rejected(login):
    client = await login("engineer")
    with Session(auth.get_engine()) as db, db.begin():
        user = db.scalar(sa.select(auth.User).where(auth.User.username == client.username))
        for session in db.scalars(sa.select(auth.AuthSession).where(auth.AuthSession.user_id == user.id)):
            session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def test_write_without_csrf_header_is_blocked(login):
    client = await login("engineer")
    response = await client.post(
        f"{API}/runs", json={"request_text": "tính doanh thu ngày"}, headers={"X-Requested-With": ""}
    )
    assert response.status_code == 403


# ---------- 403: phân quyền theo vai trò ----------


async def test_engineer_calling_review_api_gets_403_and_is_logged(login):
    engineer = await login("engineer")
    run_id = get_store().create_run("doanh thu", engineer.username).id
    response = await engineer.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Bạn không có quyền thực hiện thao tác này."  # không lộ luật chi tiết
    assert ("permission.denied", "denied") in _actions(f"/runs/{run_id}/review")


async def test_reviewer_passes_role_check_and_may_review_own_request(login):
    """Người dùng chọn: Reviewer được duyệt cả yêu cầu do mình tạo (chỉ chặn sai vai trò)."""
    reviewer = await login("reviewer")
    run_id = get_store().create_run("doanh thu", reviewer.username).id
    response = await reviewer.post(f"{API}/runs/{run_id}/review", json={"decision": "approve"})
    assert response.status_code == 409  # qua kiểm tra quyền, chỉ vì lần chạy chưa ở bước chờ duyệt


@pytest.mark.parametrize(
    ("role", "method", "path", "body"),
    [
        ("reviewer", "post", "/runs", {"request_text": "tính doanh thu ngày"}),
        ("reviewer", "post", "/runs/abc/plan", {"decision": "approve"}),
        ("reviewer", "post", "/runs/abc/answers", {"answers": {"q": "a"}}),
        ("admin", "post", "/runs", {"request_text": "tính doanh thu ngày"}),
        ("admin", "post", "/runs/abc/review", {"decision": "approve"}),
        ("engineer", "post", "/errors/1/approve", {"fix": "x"}),
        ("engineer", "post", "/errors/1/discard", {}),
        ("engineer", "get", "/admin/users", None),
        ("reviewer", "get", "/admin/users", None),
    ],
)
async def test_wrong_role_gets_403(login, role: str, method: str, path: str, body: dict | None):
    client = await login(role)
    response = await getattr(client, method)(f"{API}{path}", **({"json": body} if body is not None else {}))
    assert response.status_code == 403


# ---------- Admin ----------


async def test_admin_manages_users_and_lock_revokes_sessions(login, anon: AsyncClient):
    admin = await login("admin")
    target = await login("engineer")
    users = (await admin.get(f"{API}/admin/users")).json()
    assert target.username in [u["username"] for u in users] and all("password_hash" not in u for u in users)
    target_id = next(u["id"] for u in users if u["username"] == target.username)

    short = await admin.post(f"{API}/admin/users", json={"username": "moi1", "role": "reviewer", "password": "ngan"})
    assert short.status_code == 422
    created = await admin.post(
        f"{API}/admin/users", json={"username": "Moi-1", "role": "reviewer", "password": "mat-khau-tam-du-dai"}
    )
    assert created.status_code == 201 and created.json()["username"] == "moi-1"
    duplicate = await admin.post(
        f"{API}/admin/users", json={"username": "moi-1", "role": "reviewer", "password": "mat-khau-tam-du-dai"}
    )
    assert duplicate.status_code == 422

    locked = await admin.patch(f"{API}/admin/users/{target_id}", json={"is_active": False})
    assert locked.status_code == 200 and locked.json()["is_active"] is False
    assert (await target.get(f"{API}/auth/me")).status_code == 401  # khóa là mất quyền ngay

    me = (await admin.get(f"{API}/auth/me")).json()
    self_lock = await admin.patch(f"{API}/admin/users/{me['id']}", json={"is_active": False})
    assert self_lock.status_code == 422
    assert ("user.create", "ok") in _actions("moi-1")
    with Session(auth.get_engine()) as db:
        details = [r.detail for r in db.scalars(sa.select(auth.AuditEntry))]
    assert not any("mat-khau-tam-du-dai" in str(d) for d in details)  # không ghi mật khẩu vào nhật ký


# ---------- Migration ----------


def test_migrations_run_from_scratch_on_empty_database(tmp_path):
    """Dựng từ đầu trên CSDL trống → đủ bảng/chỉ mục → gỡ sạch → dựng lại (vòng tròn upgrade/downgrade)."""
    postgres = TEST_DATABASE_URL.startswith("postgresql")
    url = TEST_DATABASE_URL if postgres else f"sqlite+pysqlite:///{(tmp_path / 'empty.db').as_posix()}"
    if postgres:  # CSDL test riêng (conftest đã kiểm tên chứa "test"): gỡ hết để bắt đầu từ trống
        migrate(url, "base", down=True)
    engine = sa.create_engine(url)
    try:
        assert set(sa.inspect(engine).get_table_names()) <= {"alembic_version"}
        migrate(url)
        inspector = sa.inspect(engine)
        assert {"users", "sessions", "audit_log"} <= set(inspector.get_table_names())
        indexes = {i["name"] for i in inspector.get_indexes("audit_log")}
        assert {"ix_audit_log_at", "ix_audit_log_actor_id", "ix_audit_log_action"} <= indexes
        assert "ix_sessions_user_id" in {i["name"] for i in inspector.get_indexes("sessions")}
        migrate(url, "base", down=True)
        assert set(sa.inspect(engine).get_table_names()) <= {"alembic_version"}
        migrate(url)
    finally:
        engine.dispose()

"""Phân quyền theo phòng ban + sổ nguồn qua API (CLAUDE.md bản 2, giai đoạn 3): không lộ nguồn/bảng/bí mật ngoài quyền."""

import csv
import json
import logging
import secrets as pysecrets
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.agents import runner
from src.api.deps import CurrentUser, run_visible_to
from src.config import get_settings
from src.models.schemas import RunRecord, RunStatus
from src.services import auth, secrets
from src.services import source_registry as registry
from src.services.store import get_store
from tests.conftest import CSRF

API = "/api/v1"
SECRET_VALUE = "hunter2-GIA-TRI-BI-MAT-KHONG-DUOC-LO"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def client_for(role: str, department_id: int | None = None) -> AsyncClient:
    """Client đã đăng nhập bằng tài khoản mới thuộc phòng `department_id` (không có thì phòng mặc định)."""
    from src.main import app

    name, password = _unique(role[:3]), pysecrets.token_urlsafe(16)
    auth.create_user(name, name, role, password, department_id)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="https://test", headers=CSRF)
    response = await client.post(f"{API}/auth/login", json={"username": name, "password": password})
    assert response.status_code == 200, response.text
    client.username = name  # type: ignore[attr-defined]
    return client


@pytest.fixture
async def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Hai phòng ban, mỗi phòng một nguồn `file` (2 bảng) + một engineer + Admin; đóng client khi xong."""
    suffix = uuid.uuid4().hex[:6]
    clients: list[AsyncClient] = []
    out: dict = {"dept": {}, "source": {}, "tables": {}, "engineer": {}}
    for key in ("a", "b"):
        directory = tmp_path / key
        directory.mkdir()
        tables = (f"{key}_orders", f"{key}_items")
        for table in tables:
            with (directory / f"{table}.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows([["id", "amount"], ["1", "10"], ["2", "20"], ["3", "30"]])
        ref = f"perm_{key}_{suffix}"
        monkeypatch.setenv(secrets.env_name(ref), str(directory))
        dept = registry.create_department(_unique(f"phong-{key}"))
        from src.models.sources import CreateSourceBody

        source = registry.create_source(
            CreateSourceBody(
                name=_unique(f"nguon-{key}"),
                department_id=dept.id,
                kind="file",
                secret_ref=ref,
                allowed_tables=list(tables),
            ),
            "adm",
        )
        out["dept"][key], out["source"][key], out["tables"][key] = dept, source, tables
        out["engineer"][key] = await client_for("engineer", dept.id)
        clients.append(out["engineer"][key])
    out["admin"] = await client_for("admin")
    clients.append(out["admin"])
    out["suffix"] = suffix
    yield out
    for client in clients:
        await client.aclose()


# ---------- Danh sách nguồn ----------


async def test_user_sees_only_sources_of_own_department(world):
    seen = (await world["engineer"]["a"].get(f"{API}/sources")).json()
    assert [s["id"] for s in seen] == [world["source"]["a"].id]
    assert seen[0]["secret_ref"] == "" and seen[0]["access_text"] == "AI thấy thống kê, không thấy dòng thật"
    assert [s["id"] for s in (await world["engineer"]["b"].get(f"{API}/sources")).json()] == [world["source"]["b"].id]


async def test_admin_sees_all_sources_and_the_reference_name_only(world):
    admin_view = (await world["admin"].get(f"{API}/sources")).json()
    mine = {s["id"]: s for s in admin_view}
    assert {world["source"]["a"].id, world["source"]["b"].id} <= set(mine)
    assert mine[world["source"]["a"].id]["secret_ref"].startswith("perm_a_")  # tên tham chiếu, không phải giá trị
    assert mine[world["source"]["a"].id]["department_name"] == world["dept"]["a"].name


async def test_only_admin_manages_sources_departments_and_grants(world):
    body = {"name": _unique("x"), "department_id": world["dept"]["a"].id, "kind": "file", "allowed_tables": ["*"]}
    for role_client in (world["engineer"]["a"], await client_for("reviewer")):
        assert (await role_client.post(f"{API}/sources", json=body)).status_code == 403
        assert (
            await role_client.patch(f"{API}/sources/{world['source']['a'].id}", json={"enabled": False})
        ).status_code == 403
        assert (await role_client.get(f"{API}/departments")).status_code == 403
        assert (await role_client.post(f"{API}/departments", json={"name": _unique("p")})).status_code == 403
        assert (await role_client.post(f"{API}/sources/1/grants", json={"user_id": 1})).status_code == 403
        await role_client.aclose()
    created = await world["admin"].post(f"{API}/sources", json=body)
    assert created.status_code == 201 and created.json()["llm_access"] == "profile"  # mặc định LLM_ACCESS_DEFAULT
    assert (await world["admin"].post(f"{API}/departments", json={"name": _unique("p")})).status_code == 201


async def test_api_rejects_llm_access_above_sensitivity_cap(world):
    body = {"name": _unique("x"), "department_id": world["dept"]["a"].id, "kind": "file", "allowed_tables": ["*"]}
    too_high = await world["admin"].post(
        f"{API}/sources", json={**body, "sensitivity": "high", "llm_access": "profile"}
    )
    assert too_high.status_code == 422 and "schema_only" in too_high.json()["detail"]
    sample_on_medium = await world["admin"].post(
        f"{API}/sources", json={**body, "name": _unique("y"), "sensitivity": "medium", "llm_access": "masked_sample"}
    )
    assert sample_on_medium.status_code == 422
    bad_ref = await world["admin"].post(
        f"{API}/sources", json={**body, "kind": "postgres", "secret_ref": "postgres://u:p@h/db"}
    )
    assert bad_ref.status_code == 422
    no_ref = await world["admin"].post(f"{API}/sources", json={**body, "name": _unique("z"), "kind": "postgres"})
    assert no_ref.status_code == 422 and "secret_ref" in no_ref.json()["detail"]


async def test_admin_can_patch_and_grant_extra_access(world):
    admin, outsider = world["admin"], world["engineer"]["b"]
    source_id = world["source"]["a"].id
    patched = await admin.patch(f"{API}/sources/{source_id}", json={"sensitivity": "high"})
    assert patched.status_code == 200 and patched.json()["llm_access"] == "schema_only"  # tự hạ về trần
    assert (await admin.patch(f"{API}/sources/99999999", json={"enabled": False})).status_code == 404
    me = (await outsider.get(f"{API}/auth/me")).json()
    grant = await admin.post(f"{API}/sources/{source_id}/grants", json={"user_id": me["id"]})
    assert grant.status_code == 201
    assert source_id in {s["id"] for s in (await outsider.get(f"{API}/sources")).json()}
    assert (await admin.delete(f"{API}/sources/grants/{grant.json()['id']}")).status_code == 204
    assert source_id not in {s["id"] for s in (await outsider.get(f"{API}/sources")).json()}
    two = await admin.post(f"{API}/sources/{source_id}/grants", json={"user_id": 1, "department_id": 1})
    assert two.status_code == 422


# ---------- Bảng ngoài quyền ----------


async def test_catalog_lists_only_tables_the_user_may_see(world):
    seen_a = {t["name"] for t in (await world["engineer"]["a"].get(f"{API}/catalog/sources")).json()["tables"]}
    seen_b = {t["name"] for t in (await world["engineer"]["b"].get(f"{API}/catalog/sources")).json()["tables"]}
    assert set(world["tables"]["a"]) <= seen_a and not (set(world["tables"]["b"]) & seen_a)
    assert set(world["tables"]["b"]) <= seen_b and not (set(world["tables"]["a"]) & seen_b)


async def test_hidden_table_is_indistinguishable_from_missing_table(world):
    a = world["engineer"]["a"]
    hidden = await a.get(f"{API}/catalog/sources/profile", params={"table": world["tables"]["b"][0]})
    missing = await a.get(f"{API}/catalog/sources/profile", params={"table": "bang_khong_ton_tai"})
    assert hidden.status_code == missing.status_code == 404 and hidden.json() == missing.json()
    allowed = await a.get(f"{API}/catalog/sources/profile", params={"table": world["tables"]["a"][0]})
    assert allowed.status_code == 200


async def test_table_outside_allowed_tables_is_not_visible_even_in_own_source(world):
    source = world["source"]["a"]
    from src.models.sources import UpdateSourceBody

    registry.update_source(source.id, UpdateSourceBody(allowed_tables=[world["tables"]["a"][0]]), "adm")
    names = {t["name"] for t in (await world["engineer"]["a"].get(f"{API}/catalog/sources")).json()["tables"]}
    assert world["tables"]["a"][0] in names and world["tables"]["a"][1] not in names
    hidden = await world["engineer"]["a"].get(
        f"{API}/catalog/sources/profile", params={"table": world["tables"]["a"][1]}
    )
    assert hidden.status_code == 404


def test_spec_with_unlisted_table_gets_a_message_that_does_not_reveal_existence():
    from src.agents.nodes.spec_check import check_spec

    spec = {
        "request_text": "x", "target": "fct_x", "mode": "ELT", "grain": ["d"], "metrics": [], "unknowns": [],
        "output_columns": [{"name": "d", "type": "DATE", "description": "", "references": ""}],
        "sources": [{"name": "bang_cua_phong_khac", "kind": "csv", "path": ""}],
    }  # fmt: skip
    message = " ".join(check_spec(spec, [{"name": "bang_cua_minh", "kind": "csv"}]))
    assert "không tồn tại hoặc bạn chưa được cấp quyền" in message  # cùng một câu cho bảng không có và bảng ngoài quyền


# ---------- Lần chạy theo phòng ban ----------


def _record(requester: str, sources: list[str]) -> RunRecord:
    return RunRecord(
        id="r1", request_text="x", requester=requester, status=RunStatus.WAITING_REVIEW, provider="mock", model="mock",
        created_at="t", updated_at="t", summary={"sources": sources},
    )  # fmt: skip


def test_run_visibility_rules(monkeypatch: pytest.MonkeyPatch):
    def user(name: str, role: str) -> CurrentUser:
        return CurrentUser(id=1, name=name, display_name=name, role=role)  # type: ignore[arg-type]

    record = _record("an", ["a_orders"])
    assert run_visible_to(user("an", "engineer"), record)  # người tạo
    assert run_visible_to(user("rv", "reviewer"), record) and run_visible_to(user("ad", "admin"), record)
    assert run_visible_to(user("bo", "engineer"), record, visible={"a_orders", "x"})  # thấy mọi nguồn lần chạy dùng
    assert not run_visible_to(user("bo", "engineer"), record, visible={"b_orders"})
    assert not run_visible_to(
        user("bo", "engineer"), _record("an", []), visible={"a_orders"}
    )  # chưa chọn nguồn: chỉ người tạo


async def test_engineer_cannot_open_runs_of_other_department(world):
    store = get_store()
    run = store.create_run("x", world["engineer"]["a"].username)
    store.update_run(run.id, RunStatus.WAITING_REVIEW, {"sources": list(world["tables"]["a"])})
    assert (await world["engineer"]["a"].get(f"{API}/runs/{run.id}")).status_code == 200
    other = await world["engineer"]["b"].get(f"{API}/runs/{run.id}")
    missing = await world["engineer"]["b"].get(f"{API}/runs/khong-co-lan-chay-nay")
    assert other.status_code == missing.status_code == 404 and other.json() == missing.json()
    assert run.id not in {r["id"] for r in (await world["engineer"]["b"].get(f"{API}/runs")).json()}
    assert run.id in {r["id"] for r in (await world["engineer"]["a"].get(f"{API}/runs")).json()}
    reviewer = await client_for("reviewer")
    assert (await reviewer.get(f"{API}/runs/{run.id}")).status_code == 200  # Reviewer cần bằng chứng để duyệt
    await reviewer.aclose()
    for path in ("files", "catalog", "profile?table=x"):
        assert (await world["engineer"]["b"].get(f"{API}/runs/{run.id}/{path}")).status_code == 404


# ---------- Nhật ký truy cập ----------


async def test_every_access_and_change_is_audited(world):
    await world["engineer"]["a"].get(f"{API}/sources")
    await world["engineer"]["a"].get(f"{API}/catalog/sources/profile", params={"table": world["tables"]["a"][0]})
    created = await world["admin"].post(
        f"{API}/sources",
        json={
            "name": _unique("kiem-toan"),
            "department_id": world["dept"]["a"].id,
            "kind": "file",
            "allowed_tables": ["*"],
        },
    )
    entries = [(e.action, e.actor_name, e.target) for e in auth.recent_audit(200)]
    me_a = world["engineer"]["a"].username
    assert ("source.list", me_a, f"source:{world['source']['a'].id}") in entries
    assert any(e[0] == "catalog.profile" and e[1] == me_a for e in entries)
    assert (
        "source.create",
        "adm",
        f"source:{created.json()['id']}",
    ) not in entries  # ghi theo tên Admin thật, kiểm bên dưới
    admin_name = world["admin"].username
    assert ("source.create", admin_name, f"source:{created.json()['id']}") in entries
    audit = (await world["admin"].get(f"{API}/admin/audit", params={"limit": 200})).json()
    assert any(a["action"] == "source.create" for a in audit)


# ---------- Không lộ bí mật ----------


async def test_secret_value_never_reaches_responses_audit_logs_or_run_state(
    world, monkeypatch, caplog, seeded_sources: Path
):
    from src.models.sources import CreateSourceBody

    monkeypatch.setenv(secrets.env_name("conn_pg_secret_test"), SECRET_VALUE)
    pg = await world["admin"].post(
        f"{API}/sources",
        json={
            "name": _unique("pg"), "department_id": world["dept"]["a"].id, "kind": "postgres",
            "secret_ref": "conn_pg_secret_test", "allowed_tables": ["orders"], "sensitivity": "high",
        },
    )  # fmt: skip
    assert pg.status_code == 201 and pg.json()["secret_ref"] == "conn_pg_secret_test"
    assert registry.create_source  # (đã import) tránh cảnh báo import không dùng
    del CreateSourceBody
    caplog.set_level(logging.DEBUG)
    texts = [pg.text]
    for client in (world["admin"], world["engineer"]["a"], world["engineer"]["b"]):
        texts.append((await client.get(f"{API}/sources")).text)
        texts.append((await client.get(f"{API}/catalog/sources")).text)
    texts.append((await world["admin"].get(f"{API}/admin/audit", params={"limit": 200})).text)
    texts.append(json.dumps([(e.action, e.target, e.detail) for e in auth.recent_audit(200)], default=str))
    outcome = runner.start_run("Gộp đơn hàng 3 nguồn, tính doanh thu ngày", world["engineer"]["a"].username)
    texts.append(
        json.dumps(runner.get_values(outcome.run_id), default=str)
    )  # state LangGraph / checkpoint của lần chạy
    texts.append(caplog.text)
    assert all(SECRET_VALUE not in text for text in texts)


async def test_non_admin_never_sees_secret_reference_names(world):
    source_id = world["source"]["a"].id
    assert any(s["id"] == source_id and s["secret_ref"] for s in (await world["admin"].get(f"{API}/sources")).json())
    assert all(s["secret_ref"] == "" for s in (await world["engineer"]["a"].get(f"{API}/sources")).json())


# ---------- Tách người tạo và người duyệt ----------


def test_creator_cannot_review_own_request_when_separation_is_on(monkeypatch: pytest.MonkeyPatch):
    assert get_settings().require_separate_reviewer is True  # bật mặc định (ADR 0006)
    assert "tự duyệt" in runner.review_permission_error("reviewer", "binh", "binh")
    assert runner.review_permission_error("reviewer", "cuong", "binh") == ""
    assert "Reviewer" in runner.review_permission_error("engineer", "an", "binh")  # sai vai trò vẫn bị chặn
    monkeypatch.setenv("REQUIRE_SEPARATE_REVIEWER", "false")
    get_settings.cache_clear()
    try:
        assert runner.review_permission_error("reviewer", "binh", "binh") == ""  # tắt khi demo cá nhân
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


@pytest.mark.slow
def test_runner_blocks_self_review_of_a_real_run(seeded_sources: Path):
    from src.agents.runner import PermissionDeniedError, ResumeRequest
    from src.models.evidence import ReviewDecision

    outcome = runner.start_run("Gộp đơn hàng 3 nguồn, tính doanh thu ngày", "nguoi-tao")
    answers = {q["id"]: q["options"][0] for q in outcome.pending["questions"]}
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="clarify", value={"answers": answers}))
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="plan", value={"decision": "approve"}))
    assert outcome.status == RunStatus.WAITING_REVIEW, outcome.error
    own = ReviewDecision(run_id=outcome.run_id, reviewer="nguoi-tao", decision="approve")
    with pytest.raises(PermissionDeniedError, match="tự duyệt"):
        runner.submit_review(own, "reviewer")
    other = ReviewDecision(run_id=outcome.run_id, reviewer="nguoi-khac", decision="approve")
    assert runner.submit_review(other, "reviewer").status == RunStatus.APPROVED

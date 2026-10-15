"""Từ điển nghiệp vụ (CLAUDE.md bản 2, giai đoạn 6): chọn thuật ngữ, quyền, đường vào prompt, cửa kiểm tra tầng 1, API."""

import re
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.agents.nodes.planner import planner_variables, used_terms
from src.config import get_settings
from src.models.glossary import GlossaryBody, GlossaryTerm
from src.services import glossary
from src.services import input_gate as gate
from src.services import source_registry as registry
from src.services.llm_context import build_llm_context
from tests.conftest import CSRF

API = "/api/v1"
REPO = Path(__file__).resolve().parent.parent


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def term(name: str, synonyms: list[str] | None = None, maps_to: str = "") -> GlossaryTerm:
    return GlossaryTerm(id=1, term=name, synonyms=synonyms or [], definition="Định nghĩa thử.", maps_to=maps_to)


# ---------- Từ điển mẫu ----------


def test_seed_has_15_to_20_clear_terms():
    terms = glossary.seed_terms()
    assert 15 <= len(terms) <= 20
    assert all(5 <= len(t.definition) <= 400 for t in terms)
    assert len({t.term for t in terms}) == len(terms)
    assert "doanh thu" in {t.term for t in terms}
    assert all(t.department_id is None for t in terms)  # dùng chung


def test_seed_has_no_secrets_or_real_values():
    text = (REPO / "config" / "glossary_seed.yaml").read_text(encoding="utf-8")
    assert not re.search(r"[\w.]+@[\w.]+\.\w+|\b0\d{9}\b|password|passwd|secret|postgres://", text, re.I)


# ---------- Chọn thuật ngữ liên quan ----------


def test_matching_ignores_accents_case_and_uses_synonyms():
    terms = [term("doanh thu", ["revenue"]), term("hoàn tiền", ["trả hàng"]), term("kênh bán")]
    pick = lambda text: [t.term for t in glossary.relevant_terms(text, terms, 5)]  # noqa: E731
    assert pick("TINH DOANH THU theo ngay") == ["doanh thu"]
    assert pick("tong revenue moi thang") == ["doanh thu"]
    assert pick("dem don tra hang") == ["hoàn tiền"]
    assert pick("thời tiết hôm nay") == []
    assert pick("doanh thuận lợi") == []  # khớp nguyên cụm, không khớp một phần của từ


def test_matching_is_capped_and_prefers_longer_phrases():
    terms = [term("doanh thu"), term("doanh thu theo ngày"), term("đơn hủy")]
    chosen = glossary.relevant_terms("doanh thu theo ngày và đơn hủy", terms, 2)
    assert [t.term for t in chosen] == ["doanh thu theo ngày", "doanh thu"]  # cụm dài nhất trước, cắt theo trần
    assert glossary.relevant_terms("doanh thu", terms, 0) == []


def test_output_spec_boilerplate_does_not_pull_terms():
    request = (
        "Tính tổng tiền theo ngày từ website_orders. Bảng đích fct_daily_revenue, các cột: order_date (ngày đặt đơn), "
        "order_count (số đơn được tính)."
    )
    terms = [term("ngày đặt đơn"), term("số đơn"), term("tổng tiền")]
    assert [t.term for t in glossary.relevant_terms(request, terms, 5)] == ["tổng tiền"]


def test_mapping_hidden_when_it_names_a_table_the_user_cannot_see():
    terms = [
        term("doanh thu", maps_to="SUM(tiền); shopee_orders.total_amount, website_orders.amount_vnd"),
        term("khách", maps_to="customers.email"),
        term("kênh", maps_to="shopee_orders, website_orders"),
        term("đơn", maps_to="đếm đơn hợp lệ"),
    ]
    entries = {e["term"]: e for e in glossary.entries_for_prompt(terms, {"website_orders"})}
    assert (
        "maps_to" not in entries["doanh thu"] and "maps_to" not in entries["khách"] and "maps_to" not in entries["kênh"]
    )
    assert entries["đơn"]["maps_to"] == "đếm đơn hợp lệ"  # không nhắc bảng nào → giữ
    visible = glossary.entries_for_prompt(terms[:1], {"shopee_orders", "website_orders"})[0]
    assert "shopee_orders.total_amount" in visible["maps_to"]
    assert all(set(e) <= {"term", "definition", "maps_to"} for e in entries.values())


def test_definitions_are_trimmed_for_the_prompt():
    long = GlossaryTerm(term="x", definition="a" * 500)
    assert len(glossary.entries_for_prompt([long], set())[0]["definition"]) == glossary.MAX_DEFINITION_CHARS


# ---------- Đường vào prompt: chỉ qua build_llm_context ----------


def test_context_exposes_glossary_only_when_asked(seeded_sources: Path):
    plain = build_llm_context("alice")
    assert plain.glossary == [] and plain.glossary_for("tính doanh thu") == []
    ctx = build_llm_context("alice", glossary=True)
    entries = ctx.glossary_for("Tính doanh thu theo ngày")
    assert entries and entries[0]["term"].startswith("doanh thu")
    assert len(entries) <= get_settings().glossary_max_terms


def test_planner_prompt_gets_terms_and_spec_records_them(seeded_sources: Path):
    ctx = build_llm_context("alice", glossary=True)
    variables = planner_variables({"request_text": "Tính hoàn tiền và trùng đơn theo ngày"}, ctx, last_round=False)
    assert "hoàn tiền" in variables["glossary"] and "trùng đơn" in variables["glossary"]
    assert {u.term for u in used_terms(variables)} >= {"hoàn tiền", "trùng đơn"}
    none = planner_variables({"request_text": "thời tiết hôm nay"}, ctx, last_round=False)
    assert none["glossary"] == "(không có)" and used_terms(none) == []


def test_graph_plan_shows_which_terms_were_used(built_state: dict):
    used = {u["term"] for u in built_state["spec"]["glossary_used"]}
    assert "doanh thu" in used  # yêu cầu mẫu "tính doanh thu ngày"


def test_max_terms_zero_turns_the_feature_off(seeded_sources: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GLOSSARY_MAX_TERMS", "0")
    get_settings.cache_clear()
    try:
        ctx = build_llm_context("alice", glossary=True)
        assert ctx.glossary_for("Tính doanh thu hoàn tiền trùng đơn") == []
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_agents_never_write_the_glossary():
    """Agent chỉ đọc: không node/công cụ nào gọi hàm ghi của từ điển."""
    offenders = [
        str(path.relative_to(REPO))
        for folder in ("src/agents", "src/prompts")
        for path in (REPO / folder).rglob("*.py")
        if re.search(r"glossary\.(create_term|update_term|delete_term)", path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


# ---------- Cửa kiểm tra đầu vào, tầng 1 ----------

CATALOG = [{"name": "website_orders", "kind": "csv", "columns": {"order_id": "VARCHAR", "status": "VARCHAR"}}]


def test_gate_tier1_uses_terms_and_synonyms():
    text = "độ trễ giao nhận của tuần này ra sao nhỉ"  # không có động từ nghiệp vụ, không có tên bảng/cột
    assert gate.static_check(text, CATALOG).status == "unclear"
    extra = ["độ trễ giao nhận", "kênh"]
    assert gate.static_check(text, CATALOG, extra).status == "ok"
    weather = "kênh thời tiết hôm nay thế nào nhỉ"
    assert gate.static_check(weather, CATALOG, extra).status != "ok"  # từ đơn ngắn ("kênh") không đủ để cho qua


def test_gate_keywords_skip_short_or_generic_single_words():
    rules = gate.rules()
    kept = gate.glossary_keywords(["doanh thu", "kênh", "revenue", "đồng", "đơn hủy"], rules)
    assert "doanh thu" in kept and "don huy" in kept and "revenue" in kept
    assert "kenh" not in kept and "dong" not in kept


# ---------- API ----------


async def _client(role: str, department_id: int | None = None) -> AsyncClient:
    from src.main import app
    from src.services import auth

    name, password = _unique(role[:3]), uuid.uuid4().hex
    auth.create_user(name, name, role, password, department_id)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="https://test", headers=CSRF)
    response = await client.post(f"{API}/auth/login", json={"username": name, "password": password})
    assert response.status_code == 200, response.text
    return client


async def test_everyone_reads_but_only_admin_writes():
    engineer = await _client("engineer")
    listed = await engineer.get(f"{API}/glossary")
    assert listed.status_code == 200 and len(listed.json()) >= 15
    body = {"term": _unique("moi"), "definition": "Định nghĩa thử cho thuật ngữ mới."}
    assert (await engineer.post(f"{API}/glossary", json=body)).status_code == 403
    assert (await engineer.patch(f"{API}/glossary/1", json={"definition": "Sửa thử lén lút."})).status_code == 403
    reviewer = await _client("reviewer")
    assert (await reviewer.post(f"{API}/glossary", json=body)).status_code == 403
    await engineer.aclose()
    await reviewer.aclose()


async def test_admin_creates_edits_and_dept_terms_stay_in_their_department():
    dept_a = registry.create_department(_unique("phong-a"))
    dept_b = registry.create_department(_unique("phong-b"))
    admin = await _client("admin")
    name = _unique("tu")
    created = await admin.post(
        f"{API}/glossary",
        json={
            "term": name,
            "synonyms": [" dong nghia  ", "dong nghia"],
            "definition": "Chỉ phòng A dùng.",
            "department_id": dept_a.id,
        },
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["synonyms"] == ["dong nghia"] and item["department_id"] == dept_a.id  # chuẩn hóa, bỏ trùng
    dup = await admin.post(f"{API}/glossary", json={"term": name, "definition": "Trùng tên thuật ngữ."})
    assert dup.status_code == 422 and "Đã có" in dup.json()["detail"]
    bad_dept = await admin.post(
        f"{API}/glossary", json={"term": _unique("x"), "definition": "Phòng ban lạ.", "department_id": 999999}
    )
    assert bad_dept.status_code == 422
    patched = await admin.patch(f"{API}/glossary/{item['id']}", json={"definition": "Định nghĩa đã sửa lại."})
    assert patched.status_code == 200 and patched.json()["definition"] == "Định nghĩa đã sửa lại."
    assert (await admin.patch(f"{API}/glossary/999999999", json={"definition": "Không tồn tại."})).status_code == 404

    in_a, in_b = await _client("engineer", dept_a.id), await _client("engineer", dept_b.id)
    assert name in {t["term"] for t in (await in_a.get(f"{API}/glossary")).json()}
    assert name not in {t["term"] for t in (await in_b.get(f"{API}/glossary")).json()}
    assert name in {t["term"] for t in (await admin.get(f"{API}/glossary")).json()}  # Admin thấy tất cả
    shared = await admin.patch(f"{API}/glossary/{item['id']}", json={"department_id": 0})
    assert shared.json()["department_id"] is None  # chuyển thành dùng chung
    assert name in {t["term"] for t in (await in_b.get(f"{API}/glossary")).json()}
    for client in (admin, in_a, in_b):
        await client.aclose()


def test_body_validation_rejects_empty_and_oversized_input():
    with pytest.raises(ValueError):
        GlossaryBody(term="a", definition="Định nghĩa đủ dài.")
    with pytest.raises(ValueError):
        GlossaryBody(term="hai chữ", definition="Định nghĩa đủ dài.", synonyms=["x" * 81])
    assert GlossaryBody(term="  doanh   thu ", definition="Định  nghĩa  đủ dài.").term == "doanh thu"

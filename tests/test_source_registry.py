"""Sổ nguồn dữ liệu (CLAUDE.md bản 2, giai đoạn 3): đăng ký, kiểm tra cấu hình, phòng ban, bảng được phép, quyền xem thêm."""

import csv
import re
import secrets as pysecrets
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import get_settings
from src.models.sources import CreateSourceBody, UpdateSourceBody, UserContext
from src.services import auth, secrets
from src.services import source_registry as registry

REPO = Path(__file__).resolve().parent.parent


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _write_csv(directory: Path, table: str, rows: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"{table}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Hai phòng ban, mỗi phòng một nguồn `file` có 2 bảng, một người thường mỗi phòng, một Admin."""
    suffix = uuid.uuid4().hex[:6]
    env = {}
    for key, tables in (("hr", ("hr_staff", "hr_leave")), ("sales", ("sales_orders", "sales_items"))):
        directory = tmp_path / key
        for table in tables:
            _write_csv(directory, table, [{"id": "1", "note": f"{table}-giá-trị"}, {"id": "2", "note": "x"}])
        ref = f"dir_{key}_{suffix}"
        monkeypatch.setenv(secrets.env_name(ref), str(directory))
        env[key] = {"ref": ref, "tables": tables, "dir": directory}
    dept = {k: registry.create_department(_unique(f"phong-{k}")) for k in env}
    source = {}
    for key, info in env.items():
        source[key] = registry.create_source(
            CreateSourceBody(
                name=_unique(f"nguon-{key}"),
                department_id=dept[key].id,
                kind="file",
                secret_ref=info["ref"],
                allowed_tables=["*"],
                sensitivity="medium",
            ),
            "admin-test",
        )
    users = {}
    for key in env:
        name = _unique(f"u-{key}")
        auth.create_user(name, name, "engineer", pysecrets.token_urlsafe(16), dept[key].id)
        users[key] = registry.user_context(name)
    return {"env": env, "dept": dept, "source": source, "users": users, "admin": UserContext(name="adm", role="admin")}


# ---------- Kiểm tra cấu hình khi đăng ký ----------


def test_secret_ref_must_be_a_name_not_a_credential():
    for bad in ("postgres://u:p@host/db", "my password", "p@ss", "../etc/passwd", "1abc"):
        with pytest.raises(ValidationError, match="tên tham chiếu"):
            CreateSourceBody(name="x1", department_id=1, kind="postgres", secret_ref=bad, allowed_tables=["a"])
    assert CreateSourceBody(
        name="x1", department_id=1, kind="postgres", secret_ref="conn_orders_db", allowed_tables=["a"]
    )


def test_registry_rejects_inconsistent_configuration(world):
    dept = world["dept"]["hr"].id

    def make(**kw):
        return CreateSourceBody(
            **{"name": _unique("n"), "department_id": dept, "kind": "file", "allowed_tables": ["*"], **kw}
        )

    with pytest.raises(registry.RegistryError, match="secret_ref"):
        registry.create_source(make(kind="postgres"), "adm")  # DB cần tên tham chiếu
    with pytest.raises(registry.RegistryError, match="bảng được phép"):
        registry.create_source(make(allowed_tables=[]), "adm")
    with pytest.raises(registry.RegistryError, match="schema_only"):
        registry.create_source(make(sensitivity="high", llm_access="profile"), "adm")  # vượt trần theo độ nhạy cảm
    with pytest.raises(registry.RegistryError, match="profile"):
        registry.create_source(make(sensitivity="medium", llm_access="masked_sample"), "adm")
    with pytest.raises(registry.RegistryError, match="phòng ban"):
        registry.create_source(make(department_id=999_999), "adm")
    with pytest.raises(registry.RegistryError, match="đã tồn tại"):
        registry.create_source(make(name=world["source"]["hr"].name), "adm")


def test_default_access_comes_from_setting_and_is_capped_by_sensitivity(world):
    dept = world["dept"]["hr"].id
    base = {"department_id": dept, "kind": "file", "allowed_tables": ["*"]}
    levels = {}
    for sensitivity in ("high", "medium", "low"):
        source = registry.create_source(CreateSourceBody(name=_unique("s"), sensitivity=sensitivity, **base), "adm")
        levels[sensitivity] = source.llm_access
    assert levels == {"high": "schema_only", "medium": "profile", "low": "profile"}  # LLM_ACCESS_DEFAULT=profile
    low = registry.create_source(
        CreateSourceBody(name=_unique("s"), sensitivity="low", llm_access="masked_sample", **base), "adm"
    )
    assert low.llm_access == "masked_sample"  # chỉ khi admin bật rõ ràng và nguồn `low`


def test_raising_sensitivity_lowers_llm_access_but_explicit_excess_is_rejected(world):
    source = registry.create_source(
        CreateSourceBody(
            name=_unique("s"), department_id=world["dept"]["hr"].id, kind="file", allowed_tables=["*"],
            sensitivity="low", llm_access="masked_sample",
        ),
        "adm",
    )  # fmt: skip
    updated = registry.update_source(source.id, UpdateSourceBody(sensitivity="high"), "adm")
    assert (
        updated.sensitivity == "high"
        and updated.llm_access == "schema_only"
        and updated.effective_llm_access == "schema_only"
    )
    with pytest.raises(registry.RegistryError, match="schema_only"):
        registry.update_source(source.id, UpdateSourceBody(llm_access="profile"), "adm")
    assert registry.update_source(999_999, UpdateSourceBody(enabled=False), "adm") is None


def test_effective_access_is_capped_even_if_row_was_edited_directly():
    from src.models.sources import DataSource

    broken = DataSource(
        id=1,
        name="x",
        department_id=1,
        kind="file",
        allowed_tables=["*"],
        sensitivity="high",
        llm_access="masked_sample",
    )
    assert broken.effective_llm_access == "schema_only"  # phòng thủ lần hai


# ---------- Quyền xem theo phòng ban ----------


def test_user_sees_only_own_department_sources(world):
    a, b = world["users"]["hr"], world["users"]["sales"]
    assert [s.id for s in registry.get_visible_sources(a)] == [world["source"]["hr"].id]
    assert [s.id for s in registry.get_visible_sources(b)] == [world["source"]["sales"].id]


def test_admin_sees_every_source_including_disabled_but_users_do_not(world):
    registry.update_source(world["source"]["hr"].id, UpdateSourceBody(enabled=False), "adm")
    admin_ids = {s.id for s in registry.get_visible_sources(world["admin"])}
    assert {world["source"]["hr"].id, world["source"]["sales"].id} <= admin_ids
    assert registry.get_visible_sources(world["users"]["hr"]) == []  # nguồn tắt: người thường không dùng được
    assert registry.visible_catalog(world["users"]["hr"]) == []


def test_catalog_contains_only_tables_of_visible_sources(world):
    names_a = {i["name"] for i in registry.visible_catalog(world["users"]["hr"])}
    names_b = {i["name"] for i in registry.visible_catalog(world["users"]["sales"])}
    assert names_a == set(world["env"]["hr"]["tables"]) and names_b == set(world["env"]["sales"]["tables"])
    item = registry.visible_catalog(world["users"]["hr"])[0]
    assert (
        item["sample"] == [] and "llm_access" in item and item["sensitivity"] == "medium"
    )  # không có dòng mẫu trong danh mục


def test_allowed_tables_limits_the_catalog(world):
    registry.update_source(world["source"]["hr"].id, UpdateSourceBody(allowed_tables=["hr_staff"]), "adm")
    names = {i["name"] for i in registry.visible_catalog(world["users"]["hr"])}
    assert names == {"hr_staff"}  # bảng ngoài danh sách không có trong danh mục
    refreshed = next(s for s in registry.list_sources() if s.id == world["source"]["hr"].id)
    assert refreshed.allows_table("HR_STAFF") and not refreshed.allows_table("hr_leave")


def test_grant_to_user_or_department_adds_access_and_revoke_removes_it(world):
    outsider = world["users"]["sales"]
    hr_source = world["source"]["hr"]
    grant = registry.add_grant(hr_source.id, "adm", user_id=outsider.user_id)
    assert hr_source.id in {s.id for s in registry.get_visible_sources(outsider)}
    assert registry.remove_grant(grant.id, "adm") and hr_source.id not in {
        s.id for s in registry.get_visible_sources(outsider)
    }
    dept_grant = registry.add_grant(hr_source.id, "adm", department_id=world["dept"]["sales"].id)
    assert hr_source.id in {s.id for s in registry.get_visible_sources(outsider)}
    assert [g.id for g in registry.list_grants(hr_source.id)] == [dept_grant.id]
    with pytest.raises(registry.RegistryError, match="đúng một"):
        registry.add_grant(hr_source.id, "adm")
    assert registry.remove_grant(99_999_999, "adm") is False


def test_user_context_falls_back_to_default_department_for_trusted_cli_names():
    context = registry.user_context("ten-khong-co-tai-khoan", "engineer")
    assert context.user_id is None and context.role == "engineer" and context.department_id is not None


def test_creating_user_in_unknown_department_fails(world):
    with pytest.raises(ValueError, match="phòng ban"):
        auth.create_user(_unique("x"), "x", "engineer", pysecrets.token_urlsafe(16), 999_999)


def test_default_registry_has_demo_source_for_default_department():
    demo = next(s for s in registry.list_sources() if s.name == registry.DEFAULT_SOURCE_NAME)
    assert demo.kind == "file" and demo.allows_table("bat-ky-bang-nao") and demo.llm_access == "profile"
    context = registry.user_context("an-demo-khong-tai-khoan")
    assert demo.id in {s.id for s in registry.get_visible_sources(context)}


# ---------- Bí mật ----------


def test_secret_resolution_from_env_and_file_and_clear_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("P113_SECRET_CONN_TEST_ENV", "gia-tri-bi-mat-1")
    assert secrets.resolve("conn_test_env") == "gia-tri-bi-mat-1" and secrets.is_configured("conn_test_env")
    (tmp_path / "conn_test_file").write_text("gia-tri-bi-mat-2\n", encoding="utf-8")
    monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        assert secrets.resolve("conn_test_file") == "gia-tri-bi-mat-2"
    finally:
        monkeypatch.delenv("SECRETS_DIR")
        get_settings.cache_clear()
    with pytest.raises(secrets.SecretError) as missing:
        secrets.resolve("conn_chua_cau_hinh")
    assert "P113_SECRET_CONN_CHUA_CAU_HINH" in str(missing.value) and "Chưa cấu hình" in str(missing.value)
    with pytest.raises(secrets.SecretError, match="không hợp lệ"):
        secrets.resolve("../etc/passwd")
    assert not secrets.is_configured("conn_chua_cau_hinh")


def test_secret_env_vars_are_hidden_from_dbt_subprocess(monkeypatch: pytest.MonkeyPatch):
    from src.agents.tools.dbt_tools import _dbt_env

    monkeypatch.setenv("P113_SECRET_CONN_X", "khong-duoc-thay")
    assert "P113_SECRET_CONN_X" not in _dbt_env()


# ---------- Không có đường vòng ----------

# Chỉ những file này được đụng tới thư mục nguồn: định nghĩa, sổ nguồn, lệnh cấp dữ liệu demo, kiểm tra sức khỏe,
# và các hàm nhận đường dẫn thư mục do sổ nguồn đưa vào (không tự chọn thư mục).
DIRECT_ACCESS_ALLOWED = {
    "src/config.py",
    "src/services/source_registry.py",
    "src/agents/tools/duckdb_tools.py",
    "src/services/source_catalog.py",
    "src/services/schema_watch.py",
    "src/services/company/__init__.py",
    "src/services/doctor.py",
    "src/cli_commands.py",
    "src/main.py",
}
DIRECT_ACCESS = re.compile(r"\.sources_dir\b|\bdiscover_sources\(")


def test_no_module_reaches_source_files_except_through_the_registry():
    offenders = []
    for path in sorted((REPO / "src").rglob("*.py")):
        relative = path.relative_to(REPO).as_posix()
        if relative not in DIRECT_ACCESS_ALLOWED and DIRECT_ACCESS.search(path.read_text(encoding="utf-8")):
            offenders.append(relative)
    assert not offenders, f"Các file này đọc thư mục nguồn trực tiếp, phải đi qua source_registry: {offenders}"


def test_api_routes_use_visible_sources_for_catalog():
    text = (REPO / "src/api/catalog.py").read_text(encoding="utf-8")
    assert "visible_directories(" in text and "get_settings().sources_dir" not in text

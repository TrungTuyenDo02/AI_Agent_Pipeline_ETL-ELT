"""Hồi quy lỗi CI: git không lưu thư mục trống nên `pipelines/template/models/` có thể không tồn tại trên bản clone mới."""

import yaml

from src.agents.tools import dbt_tools
from src.config import get_settings


def test_write_sources_yml_creates_missing_models_dir(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    dbt_tools.write_sources_yml(workspace, ["orders", "customers"])
    doc = yaml.safe_load((workspace / "models" / "sources.yml").read_text(encoding="utf-8"))
    assert [t["name"] for t in doc["sources"][0]["tables"]] == ["orders", "customers"]


def test_workspace_from_template_without_models_dir(tmp_path, monkeypatch):
    template = tmp_path / "template"
    template.mkdir()
    (template / "dbt_project.yml").write_text("name: p113_sandbox\n", encoding="utf-8")  # không có models/ tests/
    settings = get_settings().model_copy(update={"template_dir": template, "workspaces_dir": tmp_path / "workspaces"})
    monkeypatch.setattr(dbt_tools, "get_settings", lambda: settings)

    workspace = dbt_tools.prepare_workspace("fixture-run")
    dbt_tools.write_sources_yml(workspace, ["orders"])
    assert (workspace / "models" / "sources.yml").is_file()


def test_dbt_env_drops_secrets(monkeypatch):
    """Tiến trình dbt không nhận khóa API, mật khẩu, chuỗi kết nối DB (lớp thứ hai sau V1 chặn env_var())."""
    secrets = {
        "OPENAI_API_KEY": "<k>",
        "DATABASE_URL": "<u>",
        "MIGRATION_DATABASE_URL": "<u>",
        "TEST_DATABASE_URL": "<u>",
        "POSTGRES_PASSWORD": "<p>",
        "P113_APP_PASSWORD": "<p>",
        "SESSION_SECRET": "<s>",
        "GITHUB_TOKEN": "<t>",
    }
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("P113_KEEP_ME", "1")
    env = {k.upper() for k in dbt_tools._dbt_env()}
    assert not env & set(secrets)
    assert "P113_KEEP_ME" in env and "PATH" in env

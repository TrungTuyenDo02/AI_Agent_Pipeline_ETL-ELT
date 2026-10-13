"""Kiểm tra môi trường (`python -m src.cli doctor`): cái gì thiếu, cái gì chưa bắt buộc ở giai đoạn hiện tại.

Không bao giờ in giá trị khóa.
"""

import importlib.metadata
import shutil
import sys
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel
from sqlalchemy.engine import make_url

from src.config import get_settings, is_real_secret


class CheckResult(BaseModel):
    """Một mục kiểm tra."""

    name: str
    level: Literal["ok", "warn", "fail", "info"]
    message: str


def _package(name: str) -> CheckResult:
    try:
        return CheckResult(name=name, level="ok", message=f"đã cài {importlib.metadata.version(name)}")
    except importlib.metadata.PackageNotFoundError:
        return CheckResult(name=name, level="fail", message="chưa cài — chạy: pip install -r requirements.txt")


def _python() -> CheckResult:
    ok = sys.version_info >= (3, 11)
    return CheckResult(
        name="Python",
        level="ok" if ok else "fail",
        message=f"{sys.version.split()[0]}" + ("" if ok else " — cần Python 3.11 trở lên"),
    )


def _llm() -> CheckResult:
    settings = get_settings()
    if settings.is_mock:
        return CheckResult(name="LLM", level="info", message="LLM_PROVIDER=mock: chế độ mô phỏng, không cần khóa.")
    if settings.llm_provider == "google":
        ok = settings.has_google_key
        message = f"google, model {settings.google_model_name}" + ("" if ok else " — thiếu GOOGLE_API_KEY trong .env")
        return CheckResult(name="LLM", level="ok" if ok else "fail", message=message)
    has_key = {
        "openai": settings.has_openai_key,
        "anthropic": settings.has_anthropic_key,
        "google": settings.has_google_key,
    }
    missing = sorted(f"{p.upper()}_API_KEY" for p in settings.providers_in_use if not has_key[p])
    if not missing:
        return CheckResult(name="LLM", level="ok", message=settings.models_summary)
    message = f"config/models.yaml cần {', '.join(missing)} nhưng .env chưa có ({settings.models_summary})"
    return CheckResult(name="LLM", level="fail", message=message)


def _fallback() -> CheckResult:
    settings = get_settings()
    if settings.is_mock or settings.llm_provider == "google" or settings.llm_fallback == "none":
        return CheckResult(name="LLM dự phòng", level="info", message="không dùng (không bắt buộc)")
    if settings.has_google_key:
        return CheckResult(
            name="LLM dự phòng", level="ok", message=f"Gemini {settings.google_model_name} khi model chính gọi lỗi"
        )
    return CheckResult(
        name="LLM dự phòng",
        level="warn",
        message="LLM_FALLBACK=google nhưng thiếu GOOGLE_API_KEY — sẽ không có dự phòng",
    )


def _env_file() -> CheckResult:
    if Path(".env").exists():
        return CheckResult(name=".env", level="ok", message="có file .env")
    return CheckResult(
        name=".env", level="info", message="chưa có .env — đang dùng giá trị mặc định (đủ cho giai đoạn A)"
    )


def _data() -> CheckResult:
    sources = get_settings().sources_dir
    if sources.exists() and any(sources.iterdir()):
        return CheckResult(name="Dữ liệu nguồn", level="ok", message=f"có dữ liệu trong {sources}")
    return CheckResult(name="Dữ liệu nguồn", level="warn", message="chưa có — chạy: python -m src.cli seed")


def _tool(name: str, command: str, when: str) -> CheckResult:
    found = shutil.which(command) is not None
    return CheckResult(
        name=name, level="ok" if found else "info", message=f"có {name}" if found else f"không có — chỉ cần {when}"
    )


def _langsmith() -> CheckResult:
    settings = get_settings()
    if not settings.langchain_tracing_v2:
        return CheckResult(name="LangSmith", level="info", message="đang tắt (tùy chọn)")
    if settings.has_langsmith_key:
        return CheckResult(name="LangSmith", level="ok", message="đang bật")
    return CheckResult(
        name="LangSmith",
        level="warn",
        message="bật nhưng khóa chưa thật — tự tắt khi chạy; đặt LANGCHAIN_TRACING_V2=false trong .env",
    )


def _ai_log_key() -> CheckResult:
    if is_real_secret(dotenv_values(".env").get("AI_LOG_API_KEY")):
        return CheckResult(name="AI_LOG_API_KEY", level="ok", message="đã đặt")
    return CheckResult(name="AI_LOG_API_KEY", level="warn", message="chưa đặt — chỉ cần cho hook ghi log AI khi push")


def _optional() -> list[CheckResult]:
    return [
        _tool("Docker", "docker", "ở giai đoạn B (docker compose)"),
        _tool("Node.js", "node", "cho frontend (giai đoạn B)"),
        _langsmith(),
        _ai_log_key(),
    ]


def _database() -> CheckResult:
    """Cơ sở dữ liệu đăng nhập: chỉ in loại máy chủ + tên database, KHÔNG in chuỗi kết nối hay mật khẩu."""
    settings = get_settings()
    if settings.missing_auth_settings:
        missing = ", ".join(settings.missing_auth_settings)
        return CheckResult(name="Cơ sở dữ liệu", level="info", message=f"đăng nhập đang tắt (thiếu {missing})")
    from src.services import auth

    try:
        url = make_url(settings.database_url)
        where = "Neon" if (url.host or "").endswith(".neon.tech") else (url.host or url.get_backend_name())
        target = f"{where}, database {url.database or '—'}"
    except Exception:  # noqa: BLE001 — chuỗi sai định dạng: không lộ nội dung
        return CheckResult(name="Cơ sở dữ liệu", level="fail", message="DATABASE_URL sai định dạng")
    if auth.ping():
        return CheckResult(name="Cơ sở dữ liệu", level="ok", message=f"kết nối được ({target})")
    hint = (
        "kiểm tra mật khẩu, sslmode; Neon: compute có thể đang dậy, thử lại" if where == "Neon" else "kiểm tra máy chủ"
    )
    return CheckResult(name="Cơ sở dữ liệu", level="fail", message=f"không kết nối được ({target}) — {hint}")


def run_checks() -> list[CheckResult]:
    """Chạy toàn bộ kiểm tra."""
    packages = [_package(p) for p in ("duckdb", "dbt-core", "dbt-duckdb", "sqlglot", "langgraph", "fastapi")]
    return [_python(), _env_file(), _llm(), _fallback(), _database(), *packages, _data(), *_optional()]

"""Công cụ dbt: dựng workspace từ mẫu, ghi file sinh ra, chạy `dbt build` trong tiến trình con có timeout."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import yaml
from pydantic import BaseModel, Field

from src.config import get_settings

GENERATED_DIRS = ("models/staging", "models/marts", "tests", "dags")
ALLOWED_PREFIXES = ("models/staging/", "models/marts/", "tests/", "dags/")
PROFILE_NAME = "p113_sandbox"


class DbtNodeResult(BaseModel):
    """Kết quả một model/test trong `run_results.json`."""

    unique_id: str
    status: str
    message: str = ""
    compile_ms: float | None = None
    execute_ms: float | None = None
    rows: int | None = None  # chỉ khi adapter báo `rows_affected`
    materialized: str = ""


class DbtResult(BaseModel):
    """Kết quả một lần chạy dbt."""

    ok: bool
    results: list[DbtNodeResult] = Field(default_factory=list)
    log_tail: str = ""
    timed_out: bool = False
    invocation_id: str = ""
    elapsed_ms: float | None = None  # thời gian thực của cả lệnh dbt (không phải tổng các model)


def workspace_path(run_id: str) -> Path:
    """Thư mục làm việc của một lần chạy (git-ignored)."""
    return get_settings().workspaces_dir.resolve() / run_id


def prepare_workspace(run_id: str) -> Path:
    """Chép dự án dbt mẫu vào workspace và tạo profiles.yml trỏ tới sandbox DuckDB."""
    settings = get_settings()
    workspace = workspace_path(run_id)
    shutil.copytree(settings.template_dir, workspace, dirs_exist_ok=True)
    profile = {
        PROFILE_NAME: {
            "target": "sandbox",
            "outputs": {
                "sandbox": {
                    "type": "duckdb",
                    "path": str((workspace / "sandbox.duckdb").as_posix()),
                    "threads": settings.sandbox_threads,
                    "settings": {"memory_limit": settings.sandbox_memory_limit, "enable_external_access": False},
                }
            },
        }
    }
    (workspace / "profiles.yml").write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    return workspace


TIME_TYPES = ("DATE", "TIMESTAMP")
TIME_NAME_RE = re.compile(r"date|time|day|_at$|_on$|_ts$", re.IGNORECASE)
MAX_ACCEPTED_VALUES = 6


def _column_declaration(name: str, info: dict, key: str, unique_key: bool) -> dict:
    """Một cột nguồn: tên, kiểu kỳ vọng và test. `not_null` cho khóa và cột ngày chưa từng rỗng lúc sinh (rỗng về sau = nguồn đã đổi),
    `unique` cho khóa chưa từng trùng, `accepted_values` (chỉ cảnh báo) cho cột phân loại ít giá trị."""
    entry: dict = {"name": name, "data_type": str(info.get("type", "")).lower()}
    tests: list = []
    never_null = info.get("null_pct", 100) == 0
    if never_null and (name == key or TIME_NAME_RE.search(name)):
        tests.append("not_null")
    if name == key and unique_key:
        tests.append("unique")
    categories = info.get("categories") or []
    if 0 < len(categories) <= MAX_ACCEPTED_VALUES:
        tests.append({"accepted_values": {"arguments": {"values": categories}, "config": {"severity": "warn"}}})
    if tests:
        entry["data_tests"] = tests
    return entry


def source_tables(profile: dict) -> list[dict]:
    """Khai báo bảng nguồn từ hồ sơ dữ liệu (code sinh): cột kỳ vọng + kiểu + test + freshness khi có cột thời gian kiểu ngày/giờ."""
    tables = []
    for table, info in profile.items():
        key = info.get("key_column", "")
        unique_key = bool(key) and info.get("duplicate_keys", 1) == 0
        columns = info.get("columns", {})
        entry: dict = {
            "name": table,
            "columns": [_column_declaration(n, c, key, unique_key) for n, c in columns.items()],
        }
        clock = next((n for n, c in columns.items() if str(c.get("type", "")).upper().startswith(TIME_TYPES)), "")
        if clock:
            entry["loaded_at_field"] = f'"{clock}"'
            entry["freshness"] = {"warn_after": {"count": 1, "period": "day"}}
        tables.append(entry)
    return tables


def write_sources_yml(workspace: Path, tables: list[str] | dict[str, dict]) -> None:
    """Khai báo nguồn raw cho dbt từ danh mục thật (code sinh, không phải LLM). Danh sách tên: chỉ bảng; hồ sơ dữ liệu: đủ cột,
    kiểu, test và freshness để macro `check_source_schema` so cấu trúc thật lúc chạy."""
    declared = source_tables(tables) if isinstance(tables, dict) else [{"name": t} for t in tables]
    doc = {"version": 2, "sources": [{"name": "raw", "schema": "raw", "tables": declared}]}
    target = workspace / "models" / "sources.yml"
    target.parent.mkdir(parents=True, exist_ok=True)  # git không lưu thư mục trống: bản clone mới có thể thiếu models/
    target.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def is_allowed_path(relative: str) -> bool:
    """File sinh ra chỉ được nằm trong các thư mục cho phép, không có `..` hay đường dẫn tuyệt đối."""
    normalized = relative.replace("\\", "/")
    return normalized.startswith(ALLOWED_PREFIXES) and ".." not in normalized.split("/") and ":" not in normalized


def write_generated_files(workspace: Path, files: dict[str, str]) -> None:
    """Xóa file sinh lần trước rồi ghi bộ file mới (đường dẫn đã được V1 kiểm tra)."""
    for folder in GENERATED_DIRS:
        shutil.rmtree(workspace / folder, ignore_errors=True)
        (workspace / folder).mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        if not is_allowed_path(relative):
            continue
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


# dbt đọc được biến môi trường (env_var()) → không chuyển khóa API, mật khẩu, chuỗi kết nối DB sang tiến trình dbt.
# V1 đã chặn Jinja env_var() trong model; đây là lớp thứ hai nếu V1 lọt.
SECRET_ENV_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_DATABASE_URL", "_DSN")
SECRET_ENV_NAMES = {"DATABASE_URL", "PGPASSWORD", "SESSION_SECRET"}
SECRET_ENV_PREFIXES = ("P113_SECRET_",)  # bí mật của sổ nguồn (src/services/secrets.py): dbt không được thấy


def is_secret_env(name: str) -> bool:
    """Tên biến môi trường có thể chứa bí mật (so không phân biệt hoa/thường, vì Windows)."""
    upper = name.upper()
    return upper in SECRET_ENV_NAMES or upper.endswith(SECRET_ENV_SUFFIXES) or upper.startswith(SECRET_ENV_PREFIXES)


def _dbt_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not is_secret_env(k)}
    env.update({"DBT_SEND_ANONYMOUS_USAGE_STATS": "false", "DBT_USE_COLORS": "false", "PYTHONIOENCODING": "utf-8"})
    return env


def _phase_ms(result: dict, phase: str) -> float | None:
    for item in result.get("timing") or []:
        if item.get("name") == phase and item.get("started_at") and item.get("completed_at"):
            start, end = (
                datetime.fromisoformat(item[k].replace("Z", "+00:00")) for k in ("started_at", "completed_at")
            )
            return round((end - start).total_seconds() * 1000, 3)
    return None


def source_sha(sql: str) -> str:
    """Dấu phiên bản của SQL gốc một model (bỏ khác biệt xuống dòng Windows/Linux và khoảng trắng đầu/cuối)."""
    return hashlib.sha256(sql.replace("\r\n", "\n").strip().encode("utf-8")).hexdigest()


def _manifest(workspace: Path) -> dict:
    try:
        return json.loads((workspace / "target" / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def read_run_results(workspace: Path) -> DbtResult:
    """Số đo từng model/test từ `run_results.json` + `manifest.json` (run lỗi một phần vẫn giữ số đo đã có).

    Lưu thêm bản riêng `target/runs/<invocation_id>.json` (kèm SQL đã biên dịch, phiên bản dbt/DuckDB) để lệnh dbt sau
    không ghi đè; SQL chỉ nằm trong workspace, không vào state.
    """
    path = workspace / "target" / "run_results.json"
    if not path.exists():
        return DbtResult(ok=False)
    data = json.loads(path.read_text(encoding="utf-8"))
    manifest, meta = _manifest(workspace), data.get("metadata") or {}
    nodes = manifest.get("nodes") or {}
    results, archived = [], []
    for r in data.get("results", []):
        rows = (r.get("adapter_response") or {}).get("rows_affected")
        node = DbtNodeResult(
            unique_id=r["unique_id"],
            status=r["status"],
            message=str(r.get("message") or ""),
            compile_ms=_phase_ms(r, "compile"),
            execute_ms=_phase_ms(r, "execute"),
            rows=rows if isinstance(rows, int) and rows >= 0 else None,
            materialized=str((nodes.get(r["unique_id"]) or {}).get("config", {}).get("materialized", "")),
        )
        results.append(node)
        raw = (nodes.get(r["unique_id"]) or {}).get("raw_code")
        archived.append(
            {
                **node.model_dump(),
                "sql": r.get("compiled_code") or "",
                "source_sha": source_sha(raw) if isinstance(raw, str) else "",  # phiên bản SQL gốc đã chạy
            }
        )
    elapsed = data.get("elapsed_time")
    run = DbtResult(
        ok=False,
        results=results,
        invocation_id=str(meta.get("invocation_id", "")),
        elapsed_ms=round(elapsed * 1000, 3) if isinstance(elapsed, int | float) else None,
    )
    if run.invocation_id:
        archive = {
            "invocation_id": run.invocation_id,
            "generated_at": meta.get("generated_at"),
            "dbt_version": meta.get("dbt_version"),
            "adapter": (manifest.get("metadata") or {}).get("adapter_type"),
            "duckdb_version": duckdb.__version__,
            "elapsed_ms": run.elapsed_ms,
            "results": archived,
        }
        (workspace / "target" / "runs").mkdir(parents=True, exist_ok=True)
        (workspace / "target" / "runs" / f"{run.invocation_id}.json").write_text(json.dumps(archive), encoding="utf-8")
    return run


def read_archived_run(workspace: Path, invocation_id: str) -> dict:
    """Bản đã lưu của một lần `dbt build`; không có thì {}."""
    try:
        return json.loads((workspace / "target" / "runs" / f"{invocation_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


OPT_ASSUMPTION_PREFIX = "assert_opt_assumption_"  # test giả định do optimizer thêm (compare.assumption_tests)


def archived_tests(workspace: Path, invocation_id: str, test_files: dict[str, str]) -> list[dict]:
    """Từng dbt test của một lần build để người dùng xem: tên, trạng thái, loại (`optimizer` = bảo vệ bản tối ưu, `testgen` = do
    Testgen viết độc lập từ đặc tả, `declared` = khai báo trong yml: not_null, unique, nguồn...). Không có artifact → []."""
    tests = []
    for r in read_archived_run(workspace, invocation_id).get("results", []):
        if not r["unique_id"].startswith("test."):
            continue
        name = r["unique_id"].split(".")[2]
        kind = (
            "optimizer"
            if name.startswith(OPT_ASSUMPTION_PREFIX)
            else "testgen"
            if f"tests/{name}.sql" in test_files
            else "declared"
        )
        tests.append({"name": name, "status": r["status"], "kind": kind, "message": str(r.get("message") or "")[:300]})
    return tests


OK_STATUSES = (
    "success",
    "pass",
    "warn",
)  # `warn`: test khai báo severity warn (accepted_values) — không làm hỏng lần chạy
PREFLIGHT_MARK = "P113_SOURCE_SCHEMA_CHANGED"
PREFLIGHT_FAILED = "Cấu trúc nguồn đã đổi so với lúc sinh pipeline (preflight check_source_schema):"


def run_preflight(workspace: Path) -> DbtResult | None:
    """Chạy macro `check_source_schema` TRƯỚC khi build (cũng là task đầu của DAG). Lệch cấu trúc → DbtResult lỗi có thông báo rõ;
    khớp → None. dbt không chạy được (macro thiếu) cũng báo lỗi, không im lặng bỏ qua."""
    command = [
        sys.executable, "-m", "dbt.cli.main", "run-operation", "check_source_schema",
        "--project-dir", str(workspace), "--profiles-dir", str(workspace), "--no-use-colors",
    ]  # fmt: skip
    try:
        proc = subprocess.run(  # noqa: S603 — lệnh cố định
            command, cwd=workspace, env=_dbt_env(), capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=get_settings().sandbox_timeout_sec, check=False,
        )  # fmt: skip
    except subprocess.TimeoutExpired:
        return DbtResult(ok=False, timed_out=True, log_tail="Kiểm tra cấu trúc nguồn vượt quá thời gian cho phép.")
    if proc.returncode == 0:
        return None
    text = f"{proc.stdout}\n{proc.stderr}"
    if PREFLIGHT_MARK in text:
        detail = text.split(PREFLIGHT_MARK, 1)[1].lstrip(": ").splitlines()
        lines = [detail[0].strip(), *[line.strip() for line in detail[1:] if line.strip().startswith("-")]]
        return DbtResult(ok=False, log_tail=f"{PREFLIGHT_FAILED}\n" + "\n".join(lines))
    return DbtResult(ok=False, log_tail=_log_tail(proc))


def run_dbt_build(workspace: Path) -> DbtResult:
    """V2: chạy preflight cấu trúc nguồn rồi `dbt build` trong tiến trình con (timeout, không có khóa API trong môi trường)."""
    if (failed := run_preflight(workspace)) is not None:
        return failed
    (workspace / "target" / "run_results.json").unlink(missing_ok=True)
    command = [
        sys.executable,
        "-m",
        "dbt.cli.main",
        "build",
        "--project-dir",
        str(workspace),
        "--profiles-dir",
        str(workspace),
        "--no-use-colors",
    ]
    try:
        proc = subprocess.run(  # noqa: S603 — lệnh cố định, không ghép chuỗi từ LLM
            command,
            cwd=workspace,
            env=_dbt_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=get_settings().sandbox_timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return DbtResult(ok=False, timed_out=True, log_tail="dbt build vượt quá thời gian cho phép.")
    run = read_run_results(workspace)
    ok = proc.returncode == 0 and all(r.status in OK_STATUSES for r in run.results)
    return run.model_copy(update={"ok": ok, "log_tail": _log_tail(proc)})


def _log_tail(proc: subprocess.CompletedProcess) -> str:
    """Cuối log dbt; dbt không in gì (bị ngắt, lỗi khởi động) thì ghi mã thoát + cuối stderr thay vì để trống."""
    stdout = "\n".join(proc.stdout.splitlines()[-25:])
    if stdout.strip():
        return stdout
    stderr = [line for line in proc.stderr.splitlines() if "RuntimeWarning" not in line][-15:]
    head = f"dbt dừng mà không in kết quả (mã thoát {proc.returncode}). Có thể tiến trình bị ngắt giữa chừng."
    return "\n".join([head, *stderr])

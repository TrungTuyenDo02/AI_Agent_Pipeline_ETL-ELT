"""Đo thời gian phản hồi API (0 token): p50 / p95 cho /health, danh sách lần chạy, đọc một lần chạy.

Gọi thẳng ứng dụng FastAPI trong cùng tiến trình (httpx ASGITransport, không qua mạng), LLM `mock`, dữ liệu và
cơ sở dữ liệu SQLite nằm trong thư mục tạm, nên số đo là thời gian XỬ LÝ của ứng dụng, chưa gồm độ trễ mạng và
chưa phản ánh PostgreSQL thật. Ghi kết quả vào eval/results/api_latency.md.

    python eval/api_latency.py            # hoặc: python scripts/tasks.py api-latency
    python eval/api_latency.py --n 200
"""

import argparse
import asyncio
import os
import platform
import secrets
import shutil
import statistics
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results" / "api_latency.md"
API = "/api/v1"
REQUEST = {"request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày"}


def _prepare_env(tmp: Path) -> str:
    """Trỏ mọi đường dẫn vào thư mục tạm và tạo bảng bằng chính migration Alembic. Trả về URL cơ sở dữ liệu."""
    url = f"sqlite+pysqlite:///{(tmp / 'auth.db').as_posix()}"
    os.environ.update(
        {
            "DATABASE_URL": url,
            "MIGRATION_DATABASE_URL": url,
            "SESSION_SECRET": secrets.token_urlsafe(48),
            "APP_ENV": "test",
            "LLM_PROVIDER": "mock",
            "LLM_FALLBACK": "none",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "LANGCHAIN_TRACING_V2": "false",
            "STORE_PATH": str(tmp / "app.db"),
            "CHECKPOINT_PATH": str(tmp / "checkpoints.db"),
            "SOURCES_DIR": str(tmp / "sources"),
            "WORKSPACES_DIR": str(tmp / "workspaces"),
            "TEMPLATE_DIR": str(ROOT / "pipelines" / "template"),
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
        }
    )
    sys.path.insert(0, str(ROOT))
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")
    return url


def _percentile(sorted_ms: list[float], p: float) -> float:
    index = min(len(sorted_ms) - 1, max(0, round(p / 100 * (len(sorted_ms) - 1))))
    return sorted_ms[index]


async def _time(client, path: str, n: int) -> list[float]:
    """n lần GET liên tiếp (sau 3 lần chạy nóng), trả về thời gian mỗi lần bằng mili giây."""
    for _ in range(3):
        assert (await client.get(path)).status_code == 200
    samples = []
    for _ in range(n):
        start = time.perf_counter()
        response = await client.get(path)
        samples.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 200, (path, response.status_code)
    return sorted(samples)


async def _create_finished_run(client) -> str:
    """Một lần chạy mô phỏng tới bước chờ duyệt (J1 → J1b → bản duyệt) để đọc chi tiết có dữ liệu thật."""
    from src.services.jobs import get_jobs

    created = await client.post(f"{API}/runs", json=REQUEST)
    run_id = created.json()["run_id"]
    get_jobs().wait(run_id)
    pending = (await client.get(f"{API}/runs/{run_id}")).json()["pending"]
    answers = {q["id"]: q["options"][0] for q in pending["questions"]}
    await client.post(f"{API}/runs/{run_id}/answers", json={"answers": answers})
    get_jobs().wait(run_id)
    await client.post(f"{API}/runs/{run_id}/plan", json={"decision": "approve"})
    get_jobs().wait(run_id)
    return run_id


async def measure(n: int) -> tuple[list[tuple[str, list[float]]], str]:
    from httpx import ASGITransport, AsyncClient

    from src.config import get_settings
    from src.main import app
    from src.services import auth
    from src.services.seed import SeedConfig, generate_sources

    get_settings.cache_clear()
    generate_sources(SeedConfig(out_dir=get_settings().sources_dir, seed=42, dirty=0.05, rows_per_source=120))
    password = secrets.token_urlsafe(16)
    auth.create_user("latency-bench", "Latency Bench", "engineer", password)
    headers = {"X-Requested-With": "latency"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test", headers=headers) as client:
        login = await client.post(f"{API}/auth/login", json={"username": "latency-bench", "password": password})
        assert login.status_code == 200, login.text
        run_id = await _create_finished_run(client)
        rows = [
            ("GET /health", await _time(client, "/health", n)),
            (f"GET {API}/runs?limit=20", await _time(client, f"{API}/runs?limit=20", n)),
            (f"GET {API}/runs/{{id}} (đã xong tới bản duyệt)", await _time(client, f"{API}/runs/{run_id}", n)),
        ]
    return rows, run_id


def render(rows: list[tuple[str, list[float]]], n: int) -> str:
    lines = [
        "# Thời gian phản hồi API",
        "",
        f"> Sinh bởi `eval/api_latency.py` ngày {date.today().isoformat()}. 0 token. Mỗi endpoint đo {n} lần liên tiếp sau 3 lần chạy nóng.",
        "",
        "**Điều kiện đo:** gọi thẳng ứng dụng FastAPI trong cùng tiến trình (không qua mạng), một client đã đăng nhập,",
        f"LLM `mock`, SQLite trong thư mục tạm (không phải PostgreSQL), {platform.system()} {platform.version()}, "
        f"Python {platform.python_version()}. Đây là thời gian xử lý của ứng dụng, **chưa gồm độ trễ mạng**; chỉ chạy 1 lượt đo.",
        "",
        "| Endpoint | p50 (ms) | p95 (ms) | Lớn nhất (ms) |",
        "|---|---:|---:|---:|",
    ]
    for name, samples in rows:
        lines.append(
            f"| `{name}` | {statistics.median(samples):.1f} | {_percentile(samples, 95):.1f} | {samples[-1]:.1f} |"
        )
    lines += ["", "Tái hiện: `python scripts/tasks.py api-latency`.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=100, help="Số lần đo mỗi endpoint")
    args = parser.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="p113-latency-"))
    try:
        _prepare_env(tmp)
        rows, _ = asyncio.run(measure(args.n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    text = render(rows, args.n)
    RESULTS.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    print(f"Đã ghi {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

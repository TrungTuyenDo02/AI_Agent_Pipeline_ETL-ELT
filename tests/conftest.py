"""Fixture dùng chung. Mọi test chạy không cần khóa: LLM_PROVIDER=mock, dữ liệu/ổ lưu trong thư mục tạm.

Cơ sở dữ liệu đăng nhập: TEST_DATABASE_URL (PostgreSQL riêng cho test, tên phải chứa "test") nếu có; không có thì
SQLite tạm. KHÔNG BAO GIỜ dùng DATABASE_URL của dev/prod. Bảng được tạo bằng chính migration Alembic (từ đầu).
"""

import atexit
import copy
import os
import secrets
import shutil
import tempfile
import uuid
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
_TMP = Path(tempfile.mkdtemp(prefix="p113-tests-"))
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)  # dọn dữ liệu test khi kết thúc


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(REPO_ROOT / ".env").get("TEST_DATABASE_URL") or ""
    if not url:
        return f"sqlite+pysqlite:///{(_TMP / 'auth.db').as_posix()}"
    if "test" not in url.rsplit("/", 1)[-1]:
        raise RuntimeError("TEST_DATABASE_URL phải trỏ tới cơ sở dữ liệu riêng cho test (tên chứa 'test').")
    return url


TEST_DATABASE_URL = _test_database_url()
CSRF = {"X-Requested-With": "pytest"}
os.environ.update(
    {
        "DATABASE_URL": TEST_DATABASE_URL,
        "MIGRATION_DATABASE_URL": TEST_DATABASE_URL,
        "SESSION_SECRET": secrets.token_urlsafe(48),  # sinh lúc chạy test, không phải bí mật trong Git
        "APP_ENV": "test",
        "LLM_PROVIDER": "mock",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "GOOGLE_API_KEY": "",  # .env có thể có khóa thật: test không bao giờ gọi Gemini thật
        "LLM_FALLBACK": "none",
        "LANGCHAIN_TRACING_V2": "false",
        "LANGSMITH_TRACING": "false",
        "STORE_PATH": str(_TMP / "app.db"),
        "CHECKPOINT_PATH": str(_TMP / "checkpoints.db"),
        "SOURCES_DIR": str(_TMP / "sources"),
        "WORKSPACES_DIR": str(_TMP / "workspaces"),
        "TEMPLATE_DIR": str(REPO_ROOT / "pipelines" / "template"),
        "DRIFT_GATE_ENABLED": "false",  # test của giai đoạn 5 bật lại bằng fixture `drift_on`
        "MOCK_LARGE_ROWS": "20000",
        "OPT_BENCH_RUNS": "3",
    }
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.services.seed import SeedConfig, generate_sources  # noqa: E402

get_settings.cache_clear()


def migrate(url: str, target: str = "head", down: bool = False) -> None:
    """Chạy migration Alembic (giống `alembic upgrade head`) trên `url`."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    (command.downgrade if down else command.upgrade)(cfg, target)


migrate(TEST_DATABASE_URL)


@pytest.fixture
def make_user():
    """Tạo tài khoản với mật khẩu ngẫu nhiên: `make_user("reviewer")` → (tên, mật khẩu)."""
    from src.services import auth

    def _make(role: str = "engineer", username: str | None = None) -> tuple[str, str]:
        name = username or f"{role[:3]}-{uuid.uuid4().hex[:8]}"
        password = secrets.token_urlsafe(16)
        auth.create_user(name, name, role, password)
        return name, password

    return _make


@pytest_asyncio.fixture
async def login(make_user):
    """Client đã đăng nhập theo vai trò: `reviewer = await login("reviewer")` (mỗi client một phiên riêng)."""
    from src.main import app

    clients: list[AsyncClient] = []

    async def _login(role: str = "engineer", username: str | None = None) -> AsyncClient:
        name, password = make_user(role, username)
        ac = AsyncClient(transport=ASGITransport(app=app), base_url="https://test", headers=CSRF)
        response = await ac.post("/api/v1/auth/login", json={"username": name, "password": password})
        assert response.status_code == 200, response.text
        ac.username = name  # type: ignore[attr-defined]
        clients.append(ac)
        return ac

    yield _login
    for ac in clients:
        await ac.aclose()


@pytest_asyncio.fixture
async def anon():
    """Client CHƯA đăng nhập (https để cookie Secure hoạt động như trình duyệt thật)."""
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test", headers=CSRF) as ac:
        yield ac


@pytest.fixture(scope="session")
def seeded_sources() -> Path:
    """Dữ liệu giả lập 3 nguồn (seed cố định) trong thư mục tạm."""
    out = get_settings().sources_dir
    generate_sources(SeedConfig(out_dir=out, seed=42, dirty=0.05, rows_per_source=120))
    return out


@pytest_asyncio.fixture
async def client(login):
    """HTTP client gọi thẳng ứng dụng FastAPI (không mở cổng), đã đăng nhập vai trò Engineer."""
    return await login("engineer")


@pytest.fixture(autouse=True)
def _fresh_breakers():
    """Bộ ngắt mạch LLM nằm trong bộ nhớ tiến trình: mỗi test bắt đầu với bộ ngắt trống."""
    from src.services.circuit_breaker import reset_breakers

    reset_breakers()
    yield
    reset_breakers()


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch):
    """Thay câu trả lời LLM của một tác vụ bằng dict cố định: `mock_llm("codegen", {...})`."""
    from src.services import llm_mock

    def _set(task: str, payload: dict) -> None:
        monkeypatch.setitem(llm_mock.HANDLERS, task, lambda variables: payload)

    return _set


@pytest.fixture(scope="session")
def built_state(seeded_sources: Path) -> dict:
    """State sau E1 → E0 → P → E2 → E3 → E3b (mock), chưa chạy V1/V2. Dùng chung, không sửa trực tiếp."""
    from src.agents.nodes.codegen import codegen_node
    from src.agents.nodes.ingest import ingest_node
    from src.agents.nodes.mock_data import mock_data_node
    from src.agents.nodes.planner import planner_node
    from src.agents.nodes.profiler import profiler_node
    from src.agents.nodes.testgen import testgen_node
    from src.services.llm_mock import DUPLICATE_OPTIONS, Q_DUPLICATES, Q_STATUS, STATUS_OPTIONS

    state: dict = {
        "run_id": "fixture-run",
        "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày",
        "requester": "alice",
        "answers": {Q_STATUS: STATUS_OPTIONS[0], Q_DUPLICATES: DUPLICATE_OPTIONS[0]},
    }
    for node in (planner_node, ingest_node, profiler_node, mock_data_node, codegen_node, testgen_node):
        state.update(node(state))
    return state


@pytest.fixture
def pipeline_state(built_state: dict) -> dict:
    """Bản sao độc lập của `built_state` cho từng test."""
    return copy.deepcopy(built_state)

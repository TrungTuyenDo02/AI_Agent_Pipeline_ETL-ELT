"""Health check cho Docker HEALTHCHECK, Render và UptimeRobot."""

from datetime import UTC, datetime

from fastapi import APIRouter

from src.config import APP_VERSION, get_settings
from src.models.schemas import HealthResponse
from src.services import auth
from src.services.store import get_store

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Trạng thái dịch vụ; `status` luôn là "ok" khi tiến trình còn sống, `database` báo riêng.

    `database` = kho lần chạy + (khi đã cấu hình) PostgreSQL của đăng nhập.
    Hàm thường (không async): ping DB là gọi chặn, FastAPI chạy nó trong threadpool để không chặn request khác.
    """
    settings = get_settings()
    db_ok = get_store().ping() and (not settings.database_url or auth.ping())
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        version=APP_VERSION,
        env=settings.app_env,
        database="ok" if db_ok else "error",
        llm_provider=settings.llm_provider,
    )

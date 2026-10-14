"""Router gốc `/api/v1`. Mọi API đều cần đăng nhập, trừ `/auth/login` và `/auth/logout`."""

from fastapi import APIRouter, Depends

from src.api import auth, catalog, drift, error_book, memory, reviews, runs, sources
from src.api.deps import current_user
from src.config import APP_VERSION, get_settings
from src.services.circuit_breaker import breaker_snapshots

router = APIRouter()
router.include_router(auth.router)  # login/logout tự kiểm tra; /auth/me có phụ thuộc đăng nhập riêng
router.include_router(auth.admin_router)  # từng endpoint đòi vai trò admin
router.include_router(
    drift.cron_router
)  # kiểm tra định kỳ: không có phiên đăng nhập, bảo vệ bằng khóa DRIFT_CHECK_TOKEN
protected = APIRouter(dependencies=[Depends(current_user)])
protected.include_router(runs.router)
protected.include_router(reviews.router)
protected.include_router(error_book.router)
protected.include_router(memory.router)
protected.include_router(catalog.router)
protected.include_router(sources.router)
protected.include_router(drift.router)


@protected.get("/status")
async def agent_status() -> dict[str, str | bool | list[dict]]:
    """Trạng thái agent: LLM đang dùng, có phải mô phỏng không (web hiển thị nhãn tương ứng)."""
    settings = get_settings()
    return {
        "status": "ready",
        "agent": f"P-113 Pipeline Agent v{APP_VERSION}",
        "llm_provider": settings.llm_provider,
        "models": settings.models_summary,
        "simulated": settings.is_mock,
        "breakers": breaker_snapshots(),  # trạng thái ngắt mạch từng nhà cung cấp × model (closed/open/half_open)
    }


router.include_router(protected)

"""Kết nối cơ sở dữ liệu cho lần chạy, sổ lỗi, bộ nhớ agent (CLAUDE.md mục 7).

`STATE_BACKEND=sqlite` (mặc định, demo và test): mỗi nơi lưu một file SQLite trong data/.
`STATE_BACKEND=postgres`: dùng chung DATABASE_URL (Neon, tài khoản p113_app). Bảng do Alembic tạo (migration 0003, 0004),
ứng dụng không tự tạo bảng trên Postgres vì p113_app không có quyền đổi cấu trúc.
"""

from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine

from src.config import get_settings


def use_postgres() -> bool:
    """True khi cấu hình lưu trạng thái trên PostgreSQL."""
    return get_settings().state_backend == "postgres"


@lru_cache(maxsize=8)
def _sqlite_engine(path: str) -> Engine:
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False, "timeout": 30})


def state_engine(sqlite_path: Path) -> Engine:
    """Engine cho bảng trạng thái: PostgreSQL (DATABASE_URL) hoặc file SQLite `sqlite_path`."""
    if use_postgres():
        from src.services.auth import get_engine  # nạp muộn: auth kéo theo cấu hình đăng nhập

        return get_engine()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return _sqlite_engine(str(sqlite_path.resolve()))


def is_postgres(engine: Engine) -> bool:
    return engine.dialect.name == "postgresql"

"""Bảng checkpoint của LangGraph trên PostgreSQL (chỉ chạy trên Postgres; SQLite bỏ qua).

Revision ID: 0004_langgraph_checkpoints
Revises: 0003_state_tables
Create Date: 2026-10-14

Bảng do chính thư viện `langgraph-checkpoint-postgres` tạo (hàm `setup()`), nên tên/cột theo thư viện. Chạy bằng tài khoản
migration; sau đó cấp quyền đọc/ghi cho tài khoản ứng dụng (không cấp quyền đổi cấu trúc).
"""

from collections.abc import Sequence

from alembic import op

from src.config import get_settings

revision: str = "0004_langgraph_checkpoints"
down_revision: str | None = "0003_state_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECKPOINT_TABLES = ("checkpoint_migrations", "checkpoints", "checkpoint_blobs", "checkpoint_writes")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg import Connection

    # setup() cần kết nối riêng ở chế độ autocommit; dùng cùng địa chỉ với migration (bỏ phần "+psycopg" của SQLAlchemy)
    url = bind.engine.url.render_as_string(hide_password=False).replace("postgresql+psycopg", "postgresql", 1)
    with Connection.connect(url, autocommit=True, prepare_threshold=None) as conn:
        PostgresSaver(conn).setup()
    role = get_settings().db_app_role
    tables = ", ".join(CHECKPOINT_TABLES)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON {tables} TO {role};
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in reversed(CHECKPOINT_TABLES):
            op.execute(f"DROP TABLE IF EXISTS {table}")

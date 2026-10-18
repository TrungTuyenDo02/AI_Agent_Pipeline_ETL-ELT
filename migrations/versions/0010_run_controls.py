"""Yêu cầu tạm dừng lần chạy (ADR 0016): bảng `run_controls`, mỗi lần chạy tối đa một dòng.

Revision ID: 0010_run_controls
Revises: 0009_glossary_grants
Create Date: 2026-10-18

Có dòng = người tạo yêu cầu đã bấm "Tạm dừng" khi lần chạy đang chạy; runner xóa dòng khi dừng ở ranh giới giữa hai node,
hoặc khi lần chạy tự sang trạng thái khác (chờ người, xong, lỗi). Bảng riêng để lần chạy cũ không cần đổi gì.
Chỉ tạo trên PostgreSQL; SQLite: Store tự tạo bảng trong file của nó.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.config import get_settings

revision: str = "0010_run_controls"
down_revision: str | None = "0009_glossary_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.create_table(
        "run_controls",
        sa.Column("run_id", sa.String(40), primary_key=True),
        sa.Column("pause_requested_by", sa.String(64), nullable=False),
        sa.Column("pause_requested_at", sa.String(40), nullable=False),
    )
    role = get_settings().db_app_role  # đã kiểm bằng regex trong Settings
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON run_controls TO {role};
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_table("run_controls")

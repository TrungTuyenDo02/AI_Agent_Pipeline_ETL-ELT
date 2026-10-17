"""Sổ chi phí LLM và bảng đếm giữ trước ngân sách (ADR 0014): llm_calls, budget_counters.

Revision ID: 0008_llm_cost_ledger
Revises: 0007_glossary
Create Date: 2026-10-17

Tiền lưu micro-USD (BigInteger). Thời gian dạng chuỗi ISO UTC như bảng `runs`; `day` là ngày giờ Việt Nam (YYYY-MM-DD).
Chỉ tạo trên PostgreSQL; SQLite: CostLedger tự tạo bảng trong file của nó (giống Store).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.config import get_settings

revision: str = "0008_llm_cost_ledger"
down_revision: str | None = "0007_glossary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("owner", sa.String(64), nullable=False),
        sa.Column("run_id", sa.String(40), nullable=False, server_default=""),
        sa.Column("task", sa.String(40), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reserved_micros", sa.BigInteger(), nullable=False),
        sa.Column("cost_micros", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.CheckConstraint("status IN ('reserved', 'settled', 'released', 'unknown')", name="ck_llm_calls_status"),
    )
    op.create_index("ix_llm_calls_status", "llm_calls", ["status", "expires_at"])
    op.create_table(
        "budget_counters",
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(64), nullable=False),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column("reserved_micros", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("spent_micros", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("scope", "subject", "day"),
    )
    role = get_settings().db_app_role  # đã kiểm bằng regex trong Settings
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                GRANT SELECT, INSERT, UPDATE ON llm_calls TO {role};
                GRANT SELECT, INSERT, UPDATE ON budget_counters TO {role};
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_index("ix_llm_calls_status", table_name="llm_calls")
    op.drop_table("budget_counters")
    op.drop_table("llm_calls")

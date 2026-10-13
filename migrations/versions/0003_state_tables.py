"""Bảng trạng thái chuyển từ SQLite sang PostgreSQL: runs, reviews, error_entries, memory_items.

Revision ID: 0003_state_tables
Revises: 0002_schema_snapshots
Create Date: 2026-10-14

Cột thời gian của `runs`/`reviews` giữ dạng chuỗi ISO UTC như bản SQLite (so sánh theo chữ vẫn đúng thứ tự thời gian).
`memory_items.embedding` để trống: sau này đổi sang kiểu `vector` của pgvector mà không phải làm lại bảng.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.config import get_settings

revision: str = "0003_state_tables"
down_revision: str | None = "0002_schema_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
DOC = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return  # SQLite: Store/ErrorMemory/MemoryStore tự tạo bảng trong file của chúng
    op.create_table(
        "runs",
        sa.Column("seq", ID, sa.Identity(), nullable=False, unique=True),  # thứ tự tạo (cùng giây vẫn phân biệt được)
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("requester", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_runs_created_at", "runs", ["created_at"])
    op.create_index("ix_runs_requester", "runs", ["requester"])
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_table(
        "reviews",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(40), nullable=False),
        sa.Column("reviewer", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("decided_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_reviews_run_id", "reviews", ["run_id"])
    op.create_table(
        "error_entries",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("signature", sa.String(40), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cause", sa.Text(), nullable=False, server_default=""),
        sa.Column("fix", sa.Text(), nullable=False, server_default=""),
        sa.Column("sql_before", sa.Text(), nullable=False, server_default=""),
        sa.Column("sql_after", sa.Text(), nullable=False, server_default=""),
        sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approved", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_error_entries_code", "error_entries", ["code"])
    # Bộ nhớ dài hạn của agent (CLAUDE.md mục 13): tách theo tài khoản, mục do agent ghi luôn "pending" cho tới khi duyệt
    op.create_table(
        "memory_items",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("account", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("content_hash", sa.String(40), nullable=False),
        sa.Column("source_run_id", sa.String(40), nullable=False, server_default=""),
        sa.Column("warnings", DOC, nullable=False),
        sa.Column("embedding", DOC, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account", "content_hash", name="uq_memory_account_hash"),
        sa.CheckConstraint("status IN ('pending', 'approved')", name="ck_memory_status"),
    )
    op.create_index("ix_memory_lookup", "memory_items", ["account", "status", "kind"])
    role = get_settings().db_app_role  # đã kiểm bằng regex trong Settings
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                GRANT SELECT, INSERT, UPDATE ON runs TO {role};
                GRANT SELECT, INSERT ON reviews TO {role};
                GRANT SELECT, INSERT, UPDATE, DELETE ON error_entries TO {role};
                GRANT SELECT, INSERT, UPDATE, DELETE ON memory_items TO {role};
                GRANT USAGE, SELECT ON SEQUENCE runs_seq_seq TO {role};
                GRANT USAGE, SELECT ON SEQUENCE reviews_id_seq TO {role};
                GRANT USAGE, SELECT ON SEQUENCE error_entries_id_seq TO {role};
                GRANT USAGE, SELECT ON SEQUENCE memory_items_id_seq TO {role};
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ("memory_items", "error_entries", "reviews", "runs"):
        op.drop_table(table)

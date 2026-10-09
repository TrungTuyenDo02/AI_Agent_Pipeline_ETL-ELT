"""Bản chuẩn cấu trúc bảng nguồn (CLAUDE.md mục 8): schema_snapshots, chỉ ghi thêm.

Revision ID: 0002_schema_snapshots
Revises: 0001_auth_tables
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.config import get_settings

revision: str = "0002_schema_snapshots"
down_revision: str | None = "0001_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
DOC = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "schema_snapshots",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("origin", sa.String(400), nullable=False, server_default=""),
        sa.Column("columns", DOC, nullable=False),
        sa.Column("categories", DOC, nullable=False),
        sa.Column("run_id", sa.String(40), nullable=False, server_default=""),
        sa.Column("approved_by", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schema_snapshots_source_name", "schema_snapshots", ["source_name"])
    op.create_index("ix_schema_snapshots_created_at", "schema_snapshots", ["created_at"])
    if op.get_bind().dialect.name == "postgresql":
        role = get_settings().db_app_role  # đã kiểm bằng regex trong Settings
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    GRANT SELECT, INSERT ON schema_snapshots TO {role};
                    GRANT USAGE, SELECT ON SEQUENCE schema_snapshots_id_seq TO {role};
                END IF;
            END $$;
            """
        )
        op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON schema_snapshots FROM PUBLIC")


def downgrade() -> None:
    op.drop_table("schema_snapshots")

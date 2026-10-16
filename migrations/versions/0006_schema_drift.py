"""Giám sát thay đổi cấu trúc nguồn (CLAUDE.md bản 2, giai đoạn 5): ảnh chụp cấu trúc có phiên bản, thay đổi, bản chuẩn thống kê,
phụ thuộc của pipeline. Bảng `schema_snapshots` cũ (bản chuẩn theo lần chạy được duyệt, node Vs) giữ nguyên.

Revision ID: 0006_schema_drift
Revises: 0005_source_registry
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.config import get_settings

revision: str = "0006_schema_drift"
down_revision: str | None = "0005_source_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
TS = sa.DateTime(timezone=True)
DOC = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "source_schema_snapshots",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("source_id", ID, sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("table_name", sa.String(160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("columns", DOC, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("captured_at", TS, nullable=False),
        sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("source_id", "table_name", "version", name="uq_snapshot_version"),
    )
    op.create_index("ix_snapshot_source_table", "source_schema_snapshots", ["source_id", "table_name"])

    op.create_table(
        "schema_changes",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("source_id", ID, sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("table_name", sa.String(160), nullable=False),
        sa.Column("from_version", sa.Integer(), nullable=False),
        sa.Column("to_version", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("hint", sa.String(200), nullable=False, server_default=""),
        sa.Column("detected_at", TS, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("acknowledged_by", sa.String(64), nullable=False, server_default=""),
        sa.Column("acknowledged_at", TS, nullable=True),
        sa.CheckConstraint("severity IN ('info', 'warning', 'breaking')", name="ck_schema_changes_severity"),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="ck_schema_changes_status"),
    )
    op.create_index("ix_schema_changes_source", "schema_changes", ["source_id", "status"])

    op.create_table(
        "profile_baselines",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("source_id", ID, sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("table_name", sa.String(160), nullable=False),
        sa.Column("profile", DOC, nullable=False),
        sa.Column("captured_at", TS, nullable=False),
    )
    op.create_index("ix_profile_baseline_source_table", "profile_baselines", ["source_id", "table_name"])

    op.create_table(
        "pipeline_dependencies",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(40), nullable=False),
        sa.Column("source_id", ID, sa.ForeignKey("data_sources.id"), nullable=True),
        sa.Column("source_name", sa.String(160), nullable=False),
        sa.Column("table_name", sa.String(160), nullable=False),
        sa.Column("column_name", sa.String(160), nullable=False),
    )
    op.create_index("ix_pipeline_dependencies_run", "pipeline_dependencies", ["run_id"])
    op.create_index(
        "ix_pipeline_dependencies_column", "pipeline_dependencies", ["source_name", "table_name", "column_name"]
    )

    if op.get_bind().dialect.name == "postgresql":
        _grant_app_role(get_settings().db_app_role)


def _grant_app_role(role: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                GRANT SELECT, INSERT, UPDATE ON source_schema_snapshots, schema_changes, profile_baselines TO {role};
                GRANT SELECT, INSERT, DELETE ON pipeline_dependencies TO {role};
                GRANT USAGE, SELECT ON SEQUENCE source_schema_snapshots_id_seq, schema_changes_id_seq,
                    profile_baselines_id_seq, pipeline_dependencies_id_seq TO {role};
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_table("pipeline_dependencies")
    op.drop_table("profile_baselines")
    op.drop_table("schema_changes")
    op.drop_table("source_schema_snapshots")

"""Sổ nguồn dữ liệu (CLAUDE.md bản 2, giai đoạn 3): phòng ban, nguồn đã đăng ký, quyền xem thêm, phòng ban của người dùng.

Seed: phòng "Mặc định" (người dùng cũ vào phòng này) và nguồn "P113 Retail" (file, mọi bảng) để luồng demo cũ vẫn chạy.
`secret_ref` chỉ lưu TÊN tham chiếu; giá trị thật không bao giờ nằm trong cơ sở dữ liệu.

Revision ID: 0005_source_registry
Revises: 0004_langgraph_checkpoints
Create Date: 2026-10-15
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.config import get_settings

revision: str = "0005_source_registry"
down_revision: str | None = "0004_langgraph_checkpoints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
TS = sa.DateTime(timezone=True)
LIST = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
DEFAULT_DEPARTMENT = "Mặc định"
DEFAULT_SOURCE = "P113 Retail"


def upgrade() -> None:
    now = datetime.now(UTC)
    departments = op.create_table(
        "departments",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("created_at", TS, nullable=False),
    )
    op.bulk_insert(departments, [{"id": 1, "name": DEFAULT_DEPARTMENT, "created_at": now}])

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("department_id", ID, nullable=True))
        batch.create_foreign_key("fk_users_department_id", "departments", ["department_id"], ["id"])
        batch.create_index("ix_users_department_id", ["department_id"])
    op.execute("UPDATE users SET department_id = 1")  # người dùng cũ thuộc phòng mặc định

    sources = op.create_table(
        "data_sources",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("department_id", ID, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("secret_ref", sa.String(64), nullable=False, server_default=""),
        sa.Column("allowed_tables", LIST, nullable=False),
        sa.Column("sensitivity", sa.String(8), nullable=False, server_default="medium"),
        sa.Column("llm_access", sa.String(16), nullable=False, server_default="profile"),
        sa.Column("restricted_columns", LIST, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.CheckConstraint("kind IN ('file', 'duckdb', 'postgres')", name="ck_data_sources_kind"),
        sa.CheckConstraint("sensitivity IN ('low', 'medium', 'high')", name="ck_data_sources_sensitivity"),
        sa.CheckConstraint(
            "llm_access IN ('schema_only', 'profile', 'masked_sample')", name="ck_data_sources_llm_access"
        ),
    )
    op.create_index("ix_data_sources_department_id", "data_sources", ["department_id"])
    op.bulk_insert(
        sources,
        [
            {
                "id": 1,
                "name": DEFAULT_SOURCE,
                "department_id": 1,
                "kind": "file",
                "secret_ref": "",
                "allowed_tables": ["*"],
                "sensitivity": "medium",
                "llm_access": "schema_only"
                if get_settings().llm_access_default == "schema_only"
                else "profile",  # nguồn `medium`: tối đa profile
                "restricted_columns": [],
                "enabled": True,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    op.create_table(
        "source_grants",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("source_id", ID, sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("user_id", ID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("department_id", ID, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", TS, nullable=False),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND department_id IS NULL) OR (user_id IS NULL AND department_id IS NOT NULL)",
            name="ck_source_grants_one_target",
        ),
    )
    op.create_index("ix_source_grants_source_id", "source_grants", ["source_id"])

    if op.get_bind().dialect.name == "postgresql":
        _advance_sequences()  # đã chèn id = 1 tường minh: đẩy bộ đếm tự tăng qua đó, nếu không lần chèn kế tiếp trùng khóa
        _grant_app_role(get_settings().db_app_role)


def _advance_sequences() -> None:
    for table in ("departments", "data_sources"):
        op.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT max(id) FROM {table}))")


def _grant_app_role(role: str) -> None:
    """Tài khoản ứng dụng: đọc/ghi sổ nguồn; không có quyền đổi cấu trúc bảng (chỉ tài khoản migration có)."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                GRANT SELECT, INSERT, UPDATE ON departments, data_sources TO {role};
                GRANT SELECT, INSERT, DELETE ON source_grants TO {role};
                GRANT USAGE, SELECT ON SEQUENCE departments_id_seq, data_sources_id_seq, source_grants_id_seq TO {role};
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_table("source_grants")
    op.drop_table("data_sources")
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_department_id")
        batch.drop_constraint("fk_users_department_id", type_="foreignkey")
        batch.drop_column("department_id")
    op.drop_table("departments")

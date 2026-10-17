"""Cấp quyền bảng `glossary_terms` cho tài khoản ứng dụng (0007 tạo bảng nhưng quên GRANT → p113_app bị "permission denied").

Revision ID: 0009_glossary_grants
Revises: 0008_llm_cost_ledger
Create Date: 2026-10-17
"""

from collections.abc import Sequence

from alembic import op

from src.config import get_settings

revision: str = "0009_glossary_grants"
down_revision: str | None = "0008_llm_cost_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _run(statements: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    role = get_settings().db_app_role  # đã kiểm bằng regex trong Settings
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                {statements.format(role=role)}
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    _run(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON glossary_terms TO {role}; "
        "GRANT USAGE, SELECT ON SEQUENCE glossary_terms_id_seq TO {role};"
    )


def downgrade() -> None:
    _run(
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON glossary_terms FROM {role}; "
        "REVOKE USAGE, SELECT ON SEQUENCE glossary_terms_id_seq FROM {role};"
    )

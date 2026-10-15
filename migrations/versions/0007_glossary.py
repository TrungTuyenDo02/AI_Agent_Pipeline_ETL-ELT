"""Từ điển nghiệp vụ (CLAUDE.md bản 2, giai đoạn 6): thuật ngữ + từ đồng nghĩa + định nghĩa + ánh xạ. Seed từ config/glossary_seed.yaml
(dùng chung mọi phòng ban: department_id trống).

Revision ID: 0007_glossary
Revises: 0006_schema_drift
Create Date: 2026-10-16
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
import yaml
from alembic import op
from sqlalchemy.dialects import postgresql

from src.config import GLOSSARY_SEED_FILE

revision: str = "0007_glossary"
down_revision: str | None = "0006_schema_drift"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
TS = sa.DateTime(timezone=True)
DOC = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    table = op.create_table(
        "glossary_terms",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("term", sa.String(80), nullable=False, unique=True),
        sa.Column("synonyms", DOC, nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("maps_to", sa.String(300), nullable=False, server_default=""),
        sa.Column("department_id", ID, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("updated_by", sa.String(64), nullable=False, server_default=""),
        sa.Column("updated_at", TS, nullable=False),
    )
    op.create_index("ix_glossary_department", "glossary_terms", ["department_id"])
    seed = (yaml.safe_load(GLOSSARY_SEED_FILE.read_text(encoding="utf-8")) or {}).get("terms", [])
    now = datetime.now(UTC)
    op.bulk_insert(
        table,
        [
            {
                "term": item["term"], "synonyms": list(item.get("synonyms") or []), "definition": item["definition"],
                "maps_to": item.get("maps_to", ""), "department_id": None, "updated_by": "seed", "updated_at": now,
            }
            for item in seed
        ],
    )  # fmt: skip


def downgrade() -> None:
    op.drop_index("ix_glossary_department", table_name="glossary_terms")
    op.drop_table("glossary_terms")

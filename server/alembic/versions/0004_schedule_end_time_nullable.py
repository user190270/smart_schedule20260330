"""make schedule end_time nullable

Revision ID: 0004_schedule_end_time_nullable
Revises: 0003_schedule_allow_rag_indexing
Create Date: 2026-03-25 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_schedule_end_time_nullable"
down_revision = "0003_schedule_allow_rag_indexing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "schedules",
        "end_time",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "schedules",
        "end_time",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )

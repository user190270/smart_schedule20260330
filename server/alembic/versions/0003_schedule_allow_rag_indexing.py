"""schedule knowledge-base eligibility

Revision ID: 0003_schedule_allow_rag_indexing
Revises: 0002_knowledge_base_state
Create Date: 2026-03-24 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_schedule_allow_rag_indexing"
down_revision = "0002_knowledge_base_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column(
            "allow_rag_indexing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_schedules_user_id_allow_rag_indexing",
        "schedules",
        ["user_id", "allow_rag_indexing"],
        unique=False,
    )
    op.alter_column("schedules", "allow_rag_indexing", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_schedules_user_id_allow_rag_indexing", table_name="schedules")
    op.drop_column("schedules", "allow_rag_indexing")

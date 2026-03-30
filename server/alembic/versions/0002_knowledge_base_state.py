"""knowledge base state

Revision ID: 0002_knowledge_base_state
Revises: 0001_baseline
Create Date: 2026-03-24 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_knowledge_base_state"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("last_rebuild_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_rebuild_status", sa.String(length=32), nullable=True),
        sa.Column("last_rebuild_message", sa.Text(), nullable=True),
        sa.Column("last_rebuild_schedules_considered", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_rebuild_schedules_indexed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_rebuild_chunks_created", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_knowledge_base_states_user_id"),
    )
    op.create_index("ix_knowledge_base_states_user_id", "knowledge_base_states", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_knowledge_base_states_user_id", table_name="knowledge_base_states")
    op.drop_table("knowledge_base_states")

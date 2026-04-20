"""add ai usage ledger events

Revision ID: 0007_ai_usage_ledger
Revises: 0006_demo_quota_tiers
Create Date: 2026-04-19 22:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_ai_usage_ledger"
down_revision = "0006_demo_quota_tiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_usage_events_operation", "ai_usage_events", ["operation"], unique=False)
    op.create_index("ix_ai_usage_events_user_id", "ai_usage_events", ["user_id"], unique=False)
    op.create_index(
        "ix_ai_usage_events_user_id_created_at",
        "ai_usage_events",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_events_user_id_created_at", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_events_user_id", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_events_operation", table_name="ai_usage_events")
    op.drop_table("ai_usage_events")

"""add demo subscription tiers for ai quota limits

Revision ID: 0006_demo_quota_tiers
Revises: 0005_optional_email_reminders
Create Date: 2026-04-19 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_demo_quota_tiers"
down_revision = "0005_optional_email_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "subscription_tier",
            sa.Enum("free", "plus", "pro", name="subscription_tier", native_enum=False),
            nullable=False,
            server_default="free",
        ),
    )
    op.alter_column("users", "subscription_tier", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "subscription_tier")

"""normalize subscription tier enum values

Revision ID: 0008_norm_tier_values
Revises: 0007_ai_usage_ledger
Create Date: 2026-04-20 14:30:00
"""

from __future__ import annotations

from alembic import op


revision = "0008_norm_tier_values"
down_revision = "0007_ai_usage_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET subscription_tier = CASE subscription_tier
            WHEN 'FREE' THEN 'free'
            WHEN 'PLUS' THEN 'plus'
            WHEN 'PRO' THEN 'pro'
            ELSE subscription_tier
        END
        WHERE subscription_tier IN ('FREE', 'PLUS', 'PRO')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET subscription_tier = CASE subscription_tier
            WHEN 'free' THEN 'FREE'
            WHEN 'plus' THEN 'PLUS'
            WHEN 'pro' THEN 'PRO'
            ELSE subscription_tier
        END
        WHERE subscription_tier IN ('free', 'plus', 'pro')
        """
    )

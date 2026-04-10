"""add optional email reminder support

Revision ID: 0005_optional_email_reminders
Revises: 0004_schedule_end_time_nullable
Create Date: 2026-04-09 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_optional_email_reminders"
down_revision = "0004_schedule_end_time_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("notification_email", sa.String(length=320), nullable=True))

    op.add_column(
        "schedules",
        sa.Column("email_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("schedules", sa.Column("email_remind_before_minutes", sa.Integer(), nullable=True))

    op.create_table(
        "email_reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("target_email", sa.String(length=320), nullable=False),
        sa.Column("trigger_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lead_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("delivery_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("send_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_id"),
    )
    op.create_index("ix_email_reminders_user_id", "email_reminders", ["user_id"])
    op.create_index("ix_email_reminders_schedule_id", "email_reminders", ["schedule_id"], unique=True)
    op.create_index(
        "ix_email_reminders_trigger_at_status",
        "email_reminders",
        ["trigger_at", "delivery_status"],
        unique=False,
    )
    op.create_index("ix_email_reminders_user_id_active", "email_reminders", ["user_id", "active"], unique=False)

    op.alter_column("schedules", "email_reminder_enabled", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_email_reminders_user_id_active", table_name="email_reminders")
    op.drop_index("ix_email_reminders_trigger_at_status", table_name="email_reminders")
    op.drop_index("ix_email_reminders_schedule_id", table_name="email_reminders")
    op.drop_index("ix_email_reminders_user_id", table_name="email_reminders")
    op.drop_table("email_reminders")

    op.drop_column("schedules", "email_remind_before_minutes")
    op.drop_column("schedules", "email_reminder_enabled")
    op.drop_column("users", "notification_email")

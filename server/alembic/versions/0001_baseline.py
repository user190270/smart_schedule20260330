"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-03-23 00:00:00
"""

from __future__ import annotations

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("user", "admin", name="user_role", native_enum=False)
    schedule_source = sa.Enum("manual", "ai_parsed", name="schedule_source", native_enum=False)
    chat_role = sa.Enum("user", "assistant", name="chat_role", native_enum=False)

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("daily_token_usage", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_reset_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("source", schedule_source, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_schedules_user_id", "schedules", ["user_id"], unique=False)
    op.create_index("ix_schedules_user_id_updated_at", "schedules", ["user_id", "updated_at"], unique=False)

    op.create_table(
        "share_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("share_uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_share_links_share_uuid", "share_links", ["share_uuid"], unique=True)
    op.create_index("ix_share_links_user_id", "share_links", ["user_id"], unique=False)
    op.create_index("ix_share_links_user_id_schedule_id", "share_links", ["user_id", "schedule_id"], unique=True)

    op.create_table(
        "vector_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=False),
    )
    op.create_index("ix_vector_chunks_schedule_id", "vector_chunks", ["schedule_id"], unique=False)
    op.create_index("ix_vector_chunks_user_id", "vector_chunks", ["user_id"], unique=False)
    op.execute(
        "CREATE INDEX ix_vector_chunks_embedding_hnsw "
        "ON vector_chunks USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops)"
    )

    op.create_table(
        "chat_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", chat_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_history_user_id", "chat_history", ["user_id"], unique=False)
    op.create_index("ix_chat_history_user_id_created_at", "chat_history", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_vector_chunks_embedding_hnsw")
    op.drop_index("ix_chat_history_user_id_created_at", table_name="chat_history")
    op.drop_index("ix_chat_history_user_id", table_name="chat_history")
    op.drop_table("chat_history")

    op.drop_index("ix_vector_chunks_user_id", table_name="vector_chunks")
    op.drop_index("ix_vector_chunks_schedule_id", table_name="vector_chunks")
    op.drop_table("vector_chunks")

    op.drop_index("ix_share_links_user_id_schedule_id", table_name="share_links")
    op.drop_index("ix_share_links_user_id", table_name="share_links")
    op.drop_index("ix_share_links_share_uuid", table_name="share_links")
    op.drop_table("share_links")

    op.drop_index("ix_schedules_user_id_updated_at", table_name="schedules")
    op.drop_index("ix_schedules_user_id", table_name="schedules")
    op.drop_table("schedules")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

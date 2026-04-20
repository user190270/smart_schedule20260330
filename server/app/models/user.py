from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SubscriptionTier, UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.USER,
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, name="subscription_tier", native_enum=False),
        nullable=False,
        default=SubscriptionTier.FREE,
    )
    daily_token_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notification_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    last_reset_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    schedules: Mapped[list["Schedule"]] = relationship(back_populates="user")
    vector_chunks: Mapped[list["VectorChunk"]] = relationship(back_populates="user")
    chat_history: Mapped[list["ChatHistory"]] = relationship(back_populates="user")
    knowledge_base_state: Mapped["KnowledgeBaseState | None"] = relationship(back_populates="user")
    email_reminders: Mapped[list["EmailReminder"]] = relationship(back_populates="user")
    ai_usage_events: Mapped[list["AiUsageEvent"]] = relationship(back_populates="user")


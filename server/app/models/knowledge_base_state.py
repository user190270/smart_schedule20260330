from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KnowledgeBaseState(Base):
    __tablename__ = "knowledge_base_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    last_rebuild_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_rebuild_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_rebuild_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_rebuild_schedules_considered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_rebuild_schedules_indexed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_rebuild_chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="knowledge_base_state")

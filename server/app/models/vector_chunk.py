from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VectorChunk(Base):
    __tablename__ = "vector_chunks"
    __table_args__ = (
        Index("ix_vector_chunks_user_id", "user_id"),
        Index("ix_vector_chunks_schedule_id", "schedule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(3072), nullable=False)

    schedule: Mapped["Schedule"] = relationship(back_populates="vector_chunks")
    user: Mapped["User"] = relationship(back_populates="vector_chunks")


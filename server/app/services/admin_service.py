from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserAdminUpdateRequest


class AdminService:
    @staticmethod
    def list_users(db: Session) -> list[User]:
        return list(db.scalars(select(User).order_by(User.id)).all())

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        payload: UserAdminUpdateRequest,
    ) -> User | None:
        if payload.is_active is None and not payload.reset_quota:
            raise ValueError("At least one admin update field is required.")

        user = db.scalar(select(User).where(User.id == user_id))
        if user is None:
            return None

        if payload.is_active is not None:
            user.is_active = payload.is_active

        if payload.reset_quota:
            user.daily_token_usage = 0
            user.last_reset_time = datetime.now(timezone.utc)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

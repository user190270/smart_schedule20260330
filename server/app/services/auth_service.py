from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.models.enums import UserRole
from app.schemas import AuthLoginRequest, AuthRegisterRequest, AuthTokenResponse, UserProfileUpdateRequest, UserPublic
from app.services.email_reminder_service import EmailReminderService


class AuthService:
    @staticmethod
    def register_user(db: Session, payload: AuthRegisterRequest) -> User:
        existing = db.scalar(select(User).where(User.username == payload.username))
        if existing is not None:
            raise ValueError("Username already exists.")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, payload: AuthLoginRequest) -> User | None:
        user = db.scalar(select(User).where(User.username == payload.username))
        if user is None or not user.is_active:
            return None
        if not verify_password(payload.password, user.password_hash):
            return None
        return user

    @staticmethod
    def get_active_user_by_id(db: Session, user_id: int) -> User | None:
        return db.scalar(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )

    @staticmethod
    def build_auth_response(user: User) -> AuthTokenResponse:
        settings = get_settings()
        expires_minutes = settings.jwt_access_token_expire_minutes
        token = create_access_token(
            user_id=user.id,
            secret_key=settings.jwt_secret_key,
            expires_minutes=expires_minutes,
        )
        return AuthTokenResponse(
            user=UserPublic.model_validate(user),
            access_token=token,
            expires_in=expires_minutes * 60,
        )

    @staticmethod
    def update_profile(db: Session, user_id: int, payload: UserProfileUpdateRequest) -> User | None:
        user = AuthService.get_active_user_by_id(db=db, user_id=user_id)
        if user is None:
            return None

        user.notification_email = payload.notification_email
        db.commit()
        EmailReminderService.sync_user_reminders(db, user.id)
        db.commit()
        db.refresh(user)
        return user

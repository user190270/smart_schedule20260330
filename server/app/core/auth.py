from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import UserRole


def _raise_unauthorized(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if authorization is None:
        _raise_unauthorized("Authorization header is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        _raise_unauthorized("Authorization header must use Bearer token.")

    settings = get_settings()
    try:
        payload = decode_access_token(token, secret_key=settings.jwt_secret_key)
    except ValueError as exc:
        _raise_unauthorized(str(exc))

    user = db.scalar(
        select(User).where(
            User.id == payload.user_id,
            User.is_active.is_(True),
        )
    )
    if user is None:
        _raise_unauthorized("User not found or inactive.")
    return user


def get_current_user_id(user: User = Depends(get_current_user)) -> int:
    return int(user.id)


def get_current_user_id_ai_safe(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> int:
    if authorization is None:
        _raise_unauthorized("Authorization header is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        _raise_unauthorized("Authorization header must use Bearer token.")

    settings = get_settings()
    try:
        payload = decode_access_token(token, secret_key=settings.jwt_secret_key)
    except ValueError as exc:
        _raise_unauthorized(str(exc))

    with SessionLocal() as db:
        user_id = db.scalar(
            select(User.id).where(
                User.id == payload.user_id,
                User.is_active.is_(True),
            )
        )
    if user_id is None:
        _raise_unauthorized("User not found or inactive.")
    return int(user_id)


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas import AuthLoginRequest, AuthRegisterRequest, AuthTokenResponse, UserProfileUpdateRequest, UserPublic
from app.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: AuthRegisterRequest,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    try:
        user = AuthService.register_user(db=db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AuthService.build_auth_response(user)


@router.post("/login", response_model=AuthTokenResponse, status_code=status.HTTP_200_OK)
def login(
    payload: AuthLoginRequest,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    user = AuthService.authenticate_user(db=db, payload=payload)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    return AuthService.build_auth_response(user)


@router.get("/me", response_model=UserPublic, status_code=status.HTTP_200_OK)
def me(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> UserPublic:
    user = AuthService.get_active_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserPublic, status_code=status.HTTP_200_OK)
def update_me(
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> UserPublic:
    user = AuthService.update_profile(db=db, user_id=user_id, payload=payload)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return UserPublic.model_validate(user)

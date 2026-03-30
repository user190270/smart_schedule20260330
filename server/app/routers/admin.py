from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.schemas import UserAdminUpdateRequest, UserAdminView
from app.services import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserAdminView], status_code=status.HTTP_200_OK)
def list_users(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> list[UserAdminView]:
    users = AdminService.list_users(db=db)
    return [UserAdminView.model_validate(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserAdminView, status_code=status.HTTP_200_OK)
def update_user(
    user_id: int,
    payload: UserAdminUpdateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> UserAdminView:
    try:
        updated = AdminService.update_user(db=db, user_id=user_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserAdminView.model_validate(updated)

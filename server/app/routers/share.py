from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas import ShareCreateResponse, ShareScheduleDTO
from app.services import ShareService

router = APIRouter(prefix="/share", tags=["share"])


@router.post("/schedules/{schedule_id}", response_model=ShareCreateResponse, status_code=status.HTTP_201_CREATED)
def create_share_link(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ShareCreateResponse:
    created = ShareService.create_share_link(db=db, user_id=user_id, schedule_id=schedule_id)
    if created is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    return created


@router.get("/{share_uuid}", response_model=ShareScheduleDTO, status_code=status.HTTP_200_OK)
def get_shared_schedule(
    share_uuid: str,
    db: Session = Depends(get_db),
) -> ShareScheduleDTO:
    shared = ShareService.get_shared_schedule(db=db, share_uuid=share_uuid)
    if shared is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found.")
    return shared


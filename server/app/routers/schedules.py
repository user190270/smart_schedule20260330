from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.services import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ScheduleRead:
    try:
        created = ScheduleService.create_schedule(db=db, user_id=user_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ScheduleRead.model_validate(created)


@router.get("", response_model=list[ScheduleRead], status_code=status.HTTP_200_OK)
def list_schedules(
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[ScheduleRead]:
    schedules = ScheduleService.list_schedules(db=db, user_id=user_id, include_deleted=include_deleted)
    return [ScheduleRead.model_validate(item) for item in schedules]


@router.patch("/{schedule_id}", response_model=ScheduleRead, status_code=status.HTTP_200_OK)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ScheduleRead:
    try:
        updated = ScheduleService.update_schedule(
            db=db,
            user_id=user_id,
            schedule_id=schedule_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    return ScheduleRead.model_validate(updated)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> Response:
    deleted = ScheduleService.soft_delete_schedule(db=db, user_id=user_id, schedule_id=schedule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

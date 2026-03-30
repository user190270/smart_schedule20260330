from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas import ScheduleRead, SyncPullResponse, SyncPushRequest, SyncPushResponse, SyncStatusResponse
from app.services import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/push", response_model=SyncPushResponse, status_code=status.HTTP_200_OK)
def push_sync_records(
    payload: SyncPushRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> SyncPushResponse:
    results = SyncService.push_schedules(db=db, user_id=user_id, payload=payload)
    return SyncPushResponse(results=results)


@router.get("/pull", response_model=SyncPullResponse, status_code=status.HTTP_200_OK)
def pull_sync_records(
    since: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> SyncPullResponse:
    records = SyncService.pull_schedules(db=db, user_id=user_id, since=since)
    return SyncPullResponse(records=[ScheduleRead.model_validate(item) for item in records])


@router.get("/status", response_model=SyncStatusResponse, status_code=status.HTTP_200_OK)
def get_sync_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> SyncStatusResponse:
    return SyncService.get_status(db=db, user_id=user_id)


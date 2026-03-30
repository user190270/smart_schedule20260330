from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Schedule, ShareLink
from app.schemas import ShareCreateResponse, ShareScheduleDTO


def _to_share_schedule_dto(schedule: Schedule) -> ShareScheduleDTO:
    return ShareScheduleDTO(
        id=schedule.id,
        title=schedule.title,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        location=schedule.location,
        remark=schedule.remark,
        source=schedule.source,
        updated_at=schedule.updated_at,
        is_deleted=schedule.is_deleted,
    )


class ShareService:
    @staticmethod
    def create_share_link(db: Session, user_id: int, schedule_id: int) -> ShareCreateResponse | None:
        schedule = db.scalar(
            select(Schedule).where(
                Schedule.id == schedule_id,
                Schedule.user_id == user_id,
            )
        )
        if schedule is None:
            return None

        share_link = db.scalar(
            select(ShareLink).where(
                ShareLink.user_id == user_id,
                ShareLink.schedule_id == schedule_id,
            )
        )
        if share_link is None:
            share_link = ShareLink(
                schedule_id=schedule_id,
                user_id=user_id,
                share_uuid=str(uuid4()),
            )
            db.add(share_link)
            db.commit()
            db.refresh(share_link)

        return ShareCreateResponse(
            share_uuid=share_link.share_uuid,
            share_path=f"/api/share/{share_link.share_uuid}",
            schedule=_to_share_schedule_dto(schedule),
        )

    @staticmethod
    def get_shared_schedule(db: Session, share_uuid: str) -> ShareScheduleDTO | None:
        share_link = db.scalar(select(ShareLink).where(ShareLink.share_uuid == share_uuid))
        if share_link is None:
            return None

        schedule = db.scalar(
            select(Schedule).where(
                Schedule.id == share_link.schedule_id,
                Schedule.user_id == share_link.user_id,
            )
        )
        if schedule is None:
            return None

        return _to_share_schedule_dto(schedule)


from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Schedule
from app.models.enums import ScheduleSource
from app.schemas import ScheduleCreate, ScheduleUpdate
from app.services.email_reminder_service import EmailReminderService


class ScheduleService:
    @staticmethod
    def create_schedule(db: Session, user_id: int, payload: ScheduleCreate) -> Schedule:
        if payload.source == ScheduleSource.AI_PARSED and not payload.confirmed_by_user:
            raise ValueError("AI parsed schedules require explicit user confirmation before persistence.")

        schedule = Schedule(
            user_id=user_id,
            title=payload.title,
            start_time=payload.start_time,
            end_time=payload.end_time,
            location=payload.location,
            remark=payload.remark,
            source=payload.source,
            allow_rag_indexing=payload.allow_rag_indexing,
            email_reminder_enabled=payload.email_reminder_enabled,
            email_remind_before_minutes=payload.email_remind_before_minutes,
        )
        db.add(schedule)
        db.commit()
        EmailReminderService.sync_schedule_reminder(db, schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def list_schedules(db: Session, user_id: int, include_deleted: bool = False) -> list[Schedule]:
        statement = select(Schedule).where(Schedule.user_id == user_id)
        if not include_deleted:
            statement = statement.where(Schedule.is_deleted.is_(False))
        statement = statement.order_by(Schedule.start_time.asc())
        return list(db.scalars(statement).all())

    @staticmethod
    def get_schedule_by_id(db: Session, user_id: int, schedule_id: int) -> Schedule | None:
        statement = select(Schedule).where(
            Schedule.id == schedule_id,
            Schedule.user_id == user_id,
        )
        return db.scalar(statement)

    @staticmethod
    def update_schedule(
        db: Session,
        user_id: int,
        schedule_id: int,
        payload: ScheduleUpdate,
    ) -> Schedule | None:
        schedule = ScheduleService.get_schedule_by_id(db, user_id, schedule_id)
        if schedule is None:
            return None

        updates = payload.model_dump(exclude_unset=True)
        for field_name, field_value in updates.items():
            setattr(schedule, field_name, field_value)

        if schedule.end_time is not None and schedule.end_time < schedule.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")

        schedule.updated_at = datetime.now(timezone.utc)
        db.commit()
        EmailReminderService.sync_schedule_reminder(db, schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def soft_delete_schedule(db: Session, user_id: int, schedule_id: int) -> bool:
        schedule = ScheduleService.get_schedule_by_id(db, user_id, schedule_id)
        if schedule is None:
            return False

        schedule.is_deleted = True
        schedule.updated_at = datetime.now(timezone.utc)
        db.commit()
        EmailReminderService.sync_schedule_reminder(db, schedule)
        db.commit()
        return True

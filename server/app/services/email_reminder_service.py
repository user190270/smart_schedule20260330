from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import EmailReminder, Schedule, User
from app.services.mail_service import MailConfigurationError, MailDeliveryError, MailService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class EmailReminderService:
    @staticmethod
    def should_run_background_loop() -> bool:
        if "pytest" in sys.modules:
            return False
        settings = get_settings()
        return bool(settings.mail_scan_enabled and MailService.is_configured())

    @staticmethod
    def _normalize_email(email: str | None) -> str | None:
        if email is None:
            return None
        normalized = email.strip()
        return normalized or None

    @staticmethod
    def _get_existing_reminder(db: Session, schedule_id: int) -> EmailReminder | None:
        return db.scalar(select(EmailReminder).where(EmailReminder.schedule_id == schedule_id))

    @classmethod
    def _deactivate_reminder(cls, reminder: EmailReminder | None, *, status: str, error: str | None = None) -> None:
        if reminder is None:
            return
        reminder.active = False
        reminder.delivery_status = status
        reminder.last_error = error

    @classmethod
    def sync_schedule_reminder(cls, db: Session, schedule: Schedule) -> EmailReminder | None:
        reminder = cls._get_existing_reminder(db, schedule.id)
        user = db.scalar(select(User).where(User.id == schedule.user_id))
        target_email = cls._normalize_email(user.notification_email if user else None)

        if (
            schedule.is_deleted
            or not schedule.email_reminder_enabled
            or schedule.email_remind_before_minutes is None
            or not target_email
        ):
            cls._deactivate_reminder(reminder, status="cancelled")
            return reminder

        now = _utcnow()
        start_time = _as_utc(schedule.start_time)
        if start_time <= now:
            cls._deactivate_reminder(reminder, status="skipped")
            return reminder

        trigger_at = start_time - timedelta(minutes=schedule.email_remind_before_minutes)
        if trigger_at <= now:
            trigger_at = now

        if reminder is None:
            reminder = EmailReminder(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
            )
            db.add(reminder)

        reminder.target_email = target_email
        reminder.trigger_at = trigger_at
        reminder.lead_minutes = schedule.email_remind_before_minutes
        reminder.active = True
        reminder.delivery_status = "pending"
        reminder.send_attempts = 0
        reminder.sent_at = None
        reminder.last_error = None
        reminder.provider_message_id = None
        return reminder

    @classmethod
    def sync_schedule_by_id(cls, db: Session, schedule_id: int) -> EmailReminder | None:
        schedule = db.scalar(select(Schedule).where(Schedule.id == schedule_id))
        if schedule is None:
            return None
        return cls.sync_schedule_reminder(db, schedule)

    @classmethod
    def sync_user_reminders(cls, db: Session, user_id: int) -> None:
        schedules = list(db.scalars(select(Schedule).where(Schedule.user_id == user_id)).all())
        for schedule in schedules:
            cls.sync_schedule_reminder(db, schedule)

    @classmethod
    async def scan_due_reminders_once(cls) -> int:
        with SessionLocal() as db:
            due_reminders = list(
                db.scalars(
                    select(EmailReminder)
                    .options(
                        selectinload(EmailReminder.schedule),
                        selectinload(EmailReminder.user),
                    )
                    .where(
                        EmailReminder.active.is_(True),
                        EmailReminder.delivery_status == "pending",
                        EmailReminder.trigger_at <= _utcnow(),
                    )
                    .order_by(EmailReminder.trigger_at.asc(), EmailReminder.id.asc())
                ).all()
            )

            processed = 0
            for reminder in due_reminders:
                processed += 1
                schedule = reminder.schedule
                user = reminder.user
                target_email = cls._normalize_email(reminder.target_email)

                if (
                    schedule is None
                    or user is None
                    or schedule.is_deleted
                    or not schedule.email_reminder_enabled
                    or schedule.email_remind_before_minutes is None
                    or not target_email
                ):
                    cls._deactivate_reminder(reminder, status="cancelled")
                    db.commit()
                    continue

                try:
                    provider_message_id = await MailService.send_schedule_reminder(
                        to_email=target_email,
                        schedule=schedule,
                        lead_minutes=reminder.lead_minutes,
                    )
                except (MailConfigurationError, MailDeliveryError) as exc:
                    reminder.send_attempts += 1
                    reminder.active = False
                    reminder.delivery_status = "failed"
                    reminder.last_error = str(exc)[:500]
                    db.commit()
                    continue

                reminder.send_attempts += 1
                reminder.active = False
                reminder.delivery_status = "sent"
                reminder.sent_at = _utcnow()
                reminder.last_error = None
                reminder.provider_message_id = provider_message_id
                db.commit()

            return processed

    @classmethod
    async def run_background_loop(cls, stop_event: asyncio.Event) -> None:
        settings = get_settings()
        while not stop_event.is_set():
            try:
                await cls.scan_due_reminders_once()
            except Exception:
                logger.exception("Email reminder scan loop failed unexpectedly.")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.mail_scan_interval_seconds)
            except asyncio.TimeoutError:
                continue

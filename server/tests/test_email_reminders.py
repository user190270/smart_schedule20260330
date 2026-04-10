from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import EmailReminder
from app.services.email_reminder_service import EmailReminderService
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


def iso_after(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class EmailReminderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)
        self.user_id, self.headers = register_user(self.client, "mail_user")

    def _update_notification_email(self, email: str | None) -> None:
        response = self.client.patch(
            "/api/auth/me",
            json={"notification_email": email},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)

    def _create_schedule(
        self,
        *,
        start_time: str,
        email_reminder_enabled: bool = True,
        email_remind_before_minutes: int | None = 10,
    ) -> int:
        response = self.client.post(
            "/api/schedules",
            json={
                "title": "Reminder Event",
                "start_time": start_time,
                "end_time": None,
                "location": "Room A",
                "remark": "Bring laptop",
                "email_reminder_enabled": email_reminder_enabled,
                "email_remind_before_minutes": email_remind_before_minutes,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201)
        return int(response.json()["id"])

    def _fetch_reminder(self, schedule_id: int) -> EmailReminder | None:
        with SessionLocal() as db:
            return db.scalar(select(EmailReminder).where(EmailReminder.schedule_id == schedule_id))

    def test_notification_email_profile_update(self) -> None:
        response = self.client.patch(
            "/api/auth/me",
            json={"notification_email": "notify@example.com"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["notification_email"], "notify@example.com")

        me = self.client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["notification_email"], "notify@example.com")

    def test_future_schedule_with_email_reminder_creates_pending_reminder(self) -> None:
        self._update_notification_email("notify@example.com")
        schedule_id = self._create_schedule(start_time=iso_after(120), email_remind_before_minutes=30)

        reminder = self._fetch_reminder(schedule_id)
        self.assertIsNotNone(reminder)
        assert reminder is not None
        self.assertTrue(reminder.active)
        self.assertEqual(reminder.delivery_status, "pending")
        self.assertEqual(reminder.target_email, "notify@example.com")
        self.assertEqual(reminder.lead_minutes, 30)

    def test_updating_schedule_time_recomputes_existing_reminder(self) -> None:
        self._update_notification_email("notify@example.com")
        schedule_id = self._create_schedule(start_time=iso_after(120), email_remind_before_minutes=10)

        original = self._fetch_reminder(schedule_id)
        self.assertIsNotNone(original)
        assert original is not None
        original_reminder_id = original.id
        original_trigger_at = original.trigger_at

        response = self.client.patch(
            f"/api/schedules/{schedule_id}",
            json={
                "start_time": iso_after(240),
                "email_reminder_enabled": True,
                "email_remind_before_minutes": 5,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)

        updated = self._fetch_reminder(schedule_id)
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated.id, original_reminder_id)
        self.assertNotEqual(updated.trigger_at, original_trigger_at)
        self.assertEqual(updated.lead_minutes, 5)
        self.assertTrue(updated.active)

    def test_disabling_or_deleting_schedule_stops_reminder(self) -> None:
        self._update_notification_email("notify@example.com")
        schedule_id = self._create_schedule(start_time=iso_after(90), email_remind_before_minutes=10)

        disable_response = self.client.patch(
            f"/api/schedules/{schedule_id}",
            json={"email_reminder_enabled": False},
            headers=self.headers,
        )
        self.assertEqual(disable_response.status_code, 200)

        disabled = self._fetch_reminder(schedule_id)
        self.assertIsNotNone(disabled)
        assert disabled is not None
        self.assertFalse(disabled.active)
        self.assertEqual(disabled.delivery_status, "cancelled")

        reenable_response = self.client.patch(
            f"/api/schedules/{schedule_id}",
            json={"email_reminder_enabled": True, "email_remind_before_minutes": 10},
            headers=self.headers,
        )
        self.assertEqual(reenable_response.status_code, 200)

        delete_response = self.client.delete(f"/api/schedules/{schedule_id}", headers=self.headers)
        self.assertEqual(delete_response.status_code, 204)

        deleted = self._fetch_reminder(schedule_id)
        self.assertIsNotNone(deleted)
        assert deleted is not None
        self.assertFalse(deleted.active)
        self.assertEqual(deleted.delivery_status, "cancelled")

    def test_past_schedule_does_not_register_active_reminder(self) -> None:
        self._update_notification_email("notify@example.com")
        schedule_id = self._create_schedule(start_time=iso_after(-30), email_remind_before_minutes=10)

        reminder = self._fetch_reminder(schedule_id)
        self.assertIsNotNone(reminder)
        assert reminder is not None
        self.assertFalse(reminder.active)
        self.assertEqual(reminder.delivery_status, "skipped")

    def test_due_scan_sends_once_without_duplicate_delivery(self) -> None:
        self._update_notification_email("notify@example.com")
        schedule_id = self._create_schedule(start_time=iso_after(5), email_remind_before_minutes=10)

        with patch(
            "app.services.email_reminder_service.MailService.send_schedule_reminder",
            new=AsyncMock(return_value="brevo-message-1"),
        ) as send_mock:
            asyncio.run(EmailReminderService.scan_due_reminders_once())
            asyncio.run(EmailReminderService.scan_due_reminders_once())

        self.assertEqual(send_mock.await_count, 1)

        reminder = self._fetch_reminder(schedule_id)
        self.assertIsNotNone(reminder)
        assert reminder is not None
        self.assertFalse(reminder.active)
        self.assertEqual(reminder.delivery_status, "sent")
        self.assertEqual(reminder.send_attempts, 1)
        self.assertEqual(reminder.provider_message_id, "brevo-message-1")


if __name__ == "__main__":
    unittest.main()

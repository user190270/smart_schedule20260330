from __future__ import annotations

from datetime import datetime
import unittest

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models import Schedule
from app.models.enums import ScheduleSource
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


class ShareApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)
        self.user_a_id, self.headers_a = register_user(self.client, "share_user_a")
        self.user_b_id, self.headers_b = register_user(self.client, "share_user_b")

        with SessionLocal() as db:

            schedule = Schedule(
                user_id=self.user_a_id,
                title="Shareable event",
                start_time=datetime.fromisoformat("2026-04-01T09:00:00+00:00"),
                end_time=datetime.fromisoformat("2026-04-01T10:00:00+00:00"),
                location="Room E",
                remark="Read-only shared schedule.",
                source=ScheduleSource.MANUAL,
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            self.schedule_id = schedule.id

    def test_create_and_read_share_link(self) -> None:
        create_response = self.client.post(f"/api/share/schedules/{self.schedule_id}", headers=self.headers_a)
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        self.assertIn("share_uuid", created)
        self.assertIn("share_path", created)

        share_uuid = created["share_uuid"]
        read_response = self.client.get(f"/api/share/{share_uuid}")
        self.assertEqual(read_response.status_code, 200)
        shared = read_response.json()
        self.assertEqual(shared["title"], "Shareable event")
        self.assertNotIn("user_id", shared)

    def test_share_creation_respects_user_isolation(self) -> None:
        response = self.client.post(f"/api/share/schedules/{self.schedule_id}", headers=self.headers_b)
        self.assertEqual(response.status_code, 404)

    def test_share_creation_requires_user_header(self) -> None:
        response = self.client.post(f"/api/share/schedules/{self.schedule_id}")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

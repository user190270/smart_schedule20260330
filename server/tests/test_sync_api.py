from __future__ import annotations

from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import Schedule
from app.models.enums import ScheduleSource
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


def parse_iso(iso_text: str) -> datetime:
    return datetime.fromisoformat(iso_text).astimezone(timezone.utc)


class SyncApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)
        self.user_a_id, self.headers_a = register_user(self.client, "sync_user_a")
        self.user_b_id, self.headers_b = register_user(self.client, "sync_user_b")

    def _insert_schedule(
        self,
        user_id: int,
        title: str,
        updated_at: str,
        *,
        allow_rag_indexing: bool = False,
    ) -> int:
        with SessionLocal() as db:
            schedule = Schedule(
                user_id=user_id,
                title=title,
                start_time=parse_iso("2026-03-26T09:00:00+00:00"),
                end_time=parse_iso("2026-03-26T10:00:00+00:00"),
                source=ScheduleSource.MANUAL,
                updated_at=parse_iso(updated_at),
                allow_rag_indexing=allow_rag_indexing,
                is_deleted=False,
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            return schedule.id

    def test_push_lww_ignores_older_and_applies_newer(self) -> None:
        schedule_id = self._insert_schedule(
            user_id=self.user_a_id,
            title="Server Version",
            updated_at="2026-03-26T12:00:00+00:00",
        )
        older_payload = {
            "records": [
                {
                    "id": schedule_id,
                    "title": "Older Client Version",
                    "start_time": "2026-03-26T09:00:00+00:00",
                    "end_time": "2026-03-26T10:00:00+00:00",
                    "source": "manual",
                    "updated_at": "2026-03-26T11:00:00+00:00",
                    "allow_rag_indexing": False,
                    "is_deleted": False,
                }
            ]
        }
        older_response = self.client.post("/api/sync/push", json=older_payload, headers=self.headers_a)
        self.assertEqual(older_response.status_code, 200)
        self.assertEqual(older_response.json()["results"][0]["status"], "ignored")

        newer_payload = {
            "records": [
                {
                    "id": schedule_id,
                    "title": "Newer Client Version",
                    "start_time": "2026-03-26T09:00:00+00:00",
                    "end_time": "2026-03-26T10:30:00+00:00",
                    "source": "manual",
                    "updated_at": "2026-03-26T13:00:00+00:00",
                    "allow_rag_indexing": True,
                    "is_deleted": False,
                }
            ]
        }
        newer_response = self.client.post("/api/sync/push", json=newer_payload, headers=self.headers_a)
        self.assertEqual(newer_response.status_code, 200)
        self.assertEqual(newer_response.json()["results"][0]["status"], "updated")

        with SessionLocal() as db:
            updated = db.scalar(select(Schedule).where(Schedule.id == schedule_id))
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.title, "Newer Client Version")
            self.assertTrue(updated.allow_rag_indexing)
            updated_end_time = updated.end_time
            if updated_end_time.tzinfo is None:
                updated_end_time = updated_end_time.replace(tzinfo=timezone.utc)
            else:
                updated_end_time = updated_end_time.astimezone(timezone.utc)
            self.assertEqual(updated_end_time, parse_iso("2026-03-26T10:30:00+00:00"))

    def test_pull_since_filters_records_and_isolates_user(self) -> None:
        self._insert_schedule(
            user_id=self.user_a_id,
            title="A1",
            updated_at="2026-03-26T12:00:00+00:00",
        )
        self._insert_schedule(
            user_id=self.user_a_id,
            title="A2",
            updated_at="2026-03-26T13:00:00+00:00",
        )
        self._insert_schedule(
            user_id=self.user_b_id,
            title="B1",
            updated_at="2026-03-26T14:00:00+00:00",
        )

        response = self.client.get(
            "/api/sync/pull",
            params={"since": "2026-03-26T12:30:00+00:00"},
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)
        records = response.json()["records"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "A2")
        self.assertEqual(records[0]["user_id"], self.user_a_id)
        self.assertFalse(records[0]["allow_rag_indexing"])

    def test_push_without_id_creates_new_record(self) -> None:
        payload = {
            "records": [
                {
                    "title": "Created by push",
                    "start_time": "2026-03-26T15:00:00+00:00",
                    "end_time": "2026-03-26T16:00:00+00:00",
                    "source": "manual",
                    "updated_at": "2026-03-26T15:00:00+00:00",
                    "allow_rag_indexing": True,
                    "is_deleted": False,
                }
            ]
        }
        response = self.client.post("/api/sync/push", json=payload, headers=self.headers_a)
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["status"], "created")
        self.assertTrue(result["schedule_id"] > 0)

        with SessionLocal() as db:
            created = db.scalar(select(Schedule).where(Schedule.id == result["schedule_id"]))
            self.assertIsNotNone(created)
            assert created is not None
            self.assertTrue(created.allow_rag_indexing)

    def test_status_reports_cloud_counts_and_idle_rebuild_state(self) -> None:
        self._insert_schedule(
            user_id=self.user_a_id,
            title="Status Check Event",
            updated_at="2026-03-26T19:00:00+00:00",
            allow_rag_indexing=True,
        )
        self._insert_schedule(
            user_id=self.user_a_id,
            title="Cloud Only Event",
            updated_at="2026-03-26T20:00:00+00:00",
        )

        response = self.client.get("/api/sync/status", headers=self.headers_a)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["cloud_schedule_count"], 2)
        self.assertEqual(body["knowledge_base_eligible_schedule_count"], 1)
        self.assertEqual(body["indexed_schedule_count"], 0)
        self.assertEqual(body["indexed_chunk_count"], 0)
        self.assertEqual(body["last_knowledge_rebuild_status"], "idle")
        self.assertEqual(body["embedding_dimensions"], 3072)
        self.assertEqual(body["cloud_connection_status"], "connected")

    def test_push_rejects_record_id_owned_by_other_user(self) -> None:
        foreign_schedule_id = self._insert_schedule(
            user_id=self.user_b_id,
            title="User B Event",
            updated_at="2026-03-26T17:00:00+00:00",
        )
        payload = {
            "records": [
                {
                    "id": foreign_schedule_id,
                    "title": "User A overwrite attempt",
                    "start_time": "2026-03-26T17:00:00+00:00",
                    "end_time": "2026-03-26T18:00:00+00:00",
                    "source": "manual",
                    "updated_at": "2026-03-26T18:00:00+00:00",
                    "allow_rag_indexing": False,
                    "is_deleted": False,
                }
            ]
        }
        response = self.client.post("/api/sync/push", json=payload, headers=self.headers_a)
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["status"], "ignored")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app
from tests.db_helpers import reset_database
from tests.auth_helpers import register_user


class ScheduleCrudTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)
        self.user_a_id, self.headers_a = register_user(self.client, "user_a")
        self.user_b_id, self.headers_b = register_user(self.client, "user_b")

    def test_create_update_list_and_soft_delete(self) -> None:
        create_payload = {
            "title": "Morning Standup",
            "start_time": "2026-03-23T09:00:00+08:00",
            "end_time": "2026-03-23T09:30:00+08:00",
            "location": "Room A",
            "remark": "Daily sync",
            "source": "manual",
        }
        create_response = self.client.post("/api/schedules", json=create_payload, headers=self.headers_a)
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        self.assertEqual(created["title"], create_payload["title"])
        self.assertEqual(created["user_id"], self.user_a_id)
        self.assertFalse(created["allow_rag_indexing"])
        schedule_id = created["id"]

        list_response = self.client.get("/api/schedules", headers=self.headers_a)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        patch_response = self.client.patch(
            f"/api/schedules/{schedule_id}",
            json={"title": "Updated Standup", "allow_rag_indexing": True},
            headers=self.headers_a,
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["title"], "Updated Standup")
        self.assertTrue(patch_response.json()["allow_rag_indexing"])

        delete_response = self.client.delete(f"/api/schedules/{schedule_id}", headers=self.headers_a)
        self.assertEqual(delete_response.status_code, 204)

        list_after_delete = self.client.get("/api/schedules", headers=self.headers_a)
        self.assertEqual(list_after_delete.status_code, 200)
        self.assertEqual(list_after_delete.json(), [])

        list_with_deleted = self.client.get("/api/schedules?include_deleted=true", headers=self.headers_a)
        self.assertEqual(list_with_deleted.status_code, 200)
        self.assertEqual(len(list_with_deleted.json()), 1)
        self.assertTrue(list_with_deleted.json()[0]["is_deleted"])

    def test_user_isolation_for_update_and_delete(self) -> None:
        create_payload = {
            "title": "Private Event",
            "start_time": "2026-03-24T10:00:00+08:00",
            "end_time": "2026-03-24T11:00:00+08:00",
            "source": "manual",
        }

        create_response = self.client.post("/api/schedules", json=create_payload, headers=self.headers_a)
        schedule_id = create_response.json()["id"]

        list_response_b = self.client.get("/api/schedules", headers=self.headers_b)
        self.assertEqual(list_response_b.status_code, 200)
        self.assertEqual(list_response_b.json(), [])

        patch_response_b = self.client.patch(
            f"/api/schedules/{schedule_id}",
            json={"title": "Should not pass"},
            headers=self.headers_b,
        )
        self.assertEqual(patch_response_b.status_code, 404)

        delete_response_b = self.client.delete(f"/api/schedules/{schedule_id}", headers=self.headers_b)
        self.assertEqual(delete_response_b.status_code, 404)

    def test_missing_user_header_returns_401(self) -> None:
        response = self.client.get("/api/schedules")
        self.assertEqual(response.status_code, 401)

    def test_ai_parsed_schedule_requires_confirmation(self) -> None:
        payload = {
            "title": "AI Draft Event",
            "start_time": "2026-03-24T10:00:00+08:00",
            "end_time": "2026-03-24T11:00:00+08:00",
            "source": "ai_parsed",
            "confirmed_by_user": False,
        }
        response = self.client.post("/api/schedules", json=payload, headers=self.headers_a)
        self.assertEqual(response.status_code, 422)

    def test_ai_parsed_schedule_persists_after_confirmation(self) -> None:
        payload = {
            "title": "AI Draft Confirmed",
            "start_time": "2026-03-24T12:00:00+08:00",
            "end_time": "2026-03-24T13:00:00+08:00",
            "source": "ai_parsed",
            "confirmed_by_user": True,
            "allow_rag_indexing": True,
        }
        response = self.client.post("/api/schedules", json=payload, headers=self.headers_a)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["source"], "ai_parsed")
        self.assertTrue(response.json()["allow_rag_indexing"])

    def test_schedule_can_persist_without_end_time(self) -> None:
        payload = {
            "title": "No End Time Event",
            "start_time": "2026-03-24T12:00:00+08:00",
            "end_time": None,
            "source": "manual",
        }
        response = self.client.post("/api/schedules", json=payload, headers=self.headers_a)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["end_time"])


if __name__ == "__main__":
    unittest.main()

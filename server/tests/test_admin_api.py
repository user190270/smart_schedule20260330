from __future__ import annotations

from datetime import datetime
import unittest

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models import User
from app.models.enums import UserRole
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


class AdminApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)

        self.admin_id, self.admin_headers = register_user(self.client, "admin_user")
        self.member_id, self.member_headers = register_user(self.client, "member_user")

        with SessionLocal() as db:
            admin = db.get(User, self.admin_id)
            member = db.get(User, self.member_id)
            if admin is None or member is None:
                raise AssertionError("Seed users were not created.")

            admin.role = UserRole.ADMIN
            member.daily_token_usage = 18
            member.last_reset_time = datetime.fromisoformat("2026-03-22T08:00:00+00:00")
            db.commit()

    def test_admin_can_list_users_and_update_user_state(self) -> None:
        list_response = self.client.get("/api/admin/users", headers=self.admin_headers)
        self.assertEqual(list_response.status_code, 200)
        users = list_response.json()
        self.assertEqual(len(users), 2)
        self.assertTrue(any(item["role"] == "admin" for item in users))

        update_response = self.client.patch(
            f"/api/admin/users/{self.member_id}",
            json={"is_active": False, "reset_quota": True},
            headers=self.admin_headers,
        )
        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()
        self.assertEqual(updated["id"], self.member_id)
        self.assertFalse(updated["is_active"])
        self.assertEqual(updated["daily_token_usage"], 0)
        self.assertNotEqual(updated["last_reset_time"], "2026-03-22T08:00:00+00:00")

    def test_non_admin_is_forbidden(self) -> None:
        response = self.client.get("/api/admin/users", headers=self.member_headers)
        self.assertEqual(response.status_code, 403)

    def test_admin_update_rejects_empty_payload(self) -> None:
        response = self.client.patch(
            f"/api/admin/users/{self.member_id}",
            json={},
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_admin_update_returns_404_for_missing_user(self) -> None:
        response = self.client.patch(
            "/api/admin/users/999999",
            json={"reset_quota": True},
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

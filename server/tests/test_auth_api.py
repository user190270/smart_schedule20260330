from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app
from tests.db_helpers import reset_database


class AuthApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)

    def test_register_login_me_flow(self) -> None:
        register = self.client.post(
            "/api/auth/register",
            json={"username": "auth_user_1", "password": "demo_pass_123"},
        )
        self.assertEqual(register.status_code, 201)
        register_body = register.json()
        self.assertEqual(register_body["user"]["username"], "auth_user_1")
        self.assertTrue(register_body["access_token"])

        login = self.client.post(
            "/api/auth/login",
            json={"username": "auth_user_1", "password": "demo_pass_123"},
        )
        self.assertEqual(login.status_code, 200)
        login_body = login.json()

        me = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["username"], "auth_user_1")

    def test_login_rejects_wrong_password(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "auth_user_2", "password": "demo_pass_123"},
        )
        login = self.client.post(
            "/api/auth/login",
            json={"username": "auth_user_2", "password": "wrong_pass_123"},
        )
        self.assertEqual(login.status_code, 401)

    def test_me_requires_bearer_token(self) -> None:
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

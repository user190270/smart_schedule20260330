from __future__ import annotations

from fastapi.testclient import TestClient


def register_user(client: TestClient, username: str, password: str = "demo_pass_123") -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )
    if response.status_code != 201:
        raise AssertionError(f"register_user failed for {username}: {response.status_code} {response.text}")

    body = response.json()
    token = body["access_token"]
    user_id = int(body["user"]["id"])
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, headers

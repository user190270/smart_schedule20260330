from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.database import engine, init_db
from app.main import app


class SmokeTestCase(unittest.TestCase):
    def test_app_title(self) -> None:
        self.assertEqual(app.title, "Smart Schedule MVP")

    def test_health_endpoint(self) -> None:
        client = TestClient(app)
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_core_tables_exist_after_init(self) -> None:
        init_db()
        table_names = set(inspect(engine).get_table_names())
        self.assertTrue(
            {"users", "schedules", "share_links", "vector_chunks", "chat_history", "knowledge_base_states"}.issubset(table_names),
            msg=f"expected core tables missing, got: {sorted(table_names)}",
        )


if __name__ == "__main__":
    unittest.main()

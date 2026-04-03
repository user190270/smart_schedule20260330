from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


class ParseContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        runtime_patcher = patch("app.services.parse_service.ParseService._get_runtime", return_value=None)
        runtime_patcher.start()
        self.addCleanup(runtime_patcher.stop)
        self.client = TestClient(app)
        self.user_id, self.headers = register_user(self.client, "parse_user_a")

    def test_parse_returns_draft_and_human_review_flags(self) -> None:
        payload = {
            "text": "Project sync from 2026-03-28T09:00:00+00:00 to 2026-03-28T09:30:00+00:00 in Room B.",
            "reference_time": "2026-03-27T10:00:00+08:00",
        }
        response = self.client.post("/api/parse/schedule-draft", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertTrue(body["requires_human_review"])
        self.assertFalse(body["can_persist_directly"])
        self.assertEqual(body["missing_fields"], [])
        self.assertEqual(body["follow_up_questions"], [])
        self.assertEqual(body["draft"]["source"], "ai_parsed")
        self.assertIsNotNone(body["draft"]["start_time"])
        self.assertIsNotNone(body["draft"]["end_time"])

    def test_parse_reports_missing_start_time_when_time_not_found(self) -> None:
        payload = {
            "text": "Need to discuss roadmap next week.",
            "reference_time": "2026-03-27T10:00:00+08:00",
        }
        response = self.client.post("/api/parse/schedule-draft", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertIn("start_time", body["missing_fields"])
        self.assertNotIn("end_time", body["missing_fields"])
        self.assertGreaterEqual(len(body["follow_up_questions"]), 1)
        self.assertTrue(body["requires_human_review"])
        self.assertFalse(body["can_persist_directly"])

    def test_parse_understands_common_chinese_relative_time(self) -> None:
        payload = {
            "text": "明早8点到9点在三饭吃饭",
            "reference_time": "2026-03-27T10:00:00+08:00",
        }
        response = self.client.post("/api/parse/schedule-draft", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["draft"]["title"], "吃饭")
        self.assertEqual(body["draft"]["location"], "三饭")
        self.assertEqual(body["draft"]["start_time"], "2026-03-28T08:00:00+08:00")
        self.assertEqual(body["draft"]["end_time"], "2026-03-28T09:00:00+08:00")
        self.assertEqual(body["missing_fields"], [])

    def test_parse_allows_missing_end_time(self) -> None:
        payload = {
            "text": "明天到A-201开会",
            "reference_time": "2026-03-27T10:00:00+08:00",
        }
        response = self.client.post("/api/parse/schedule-draft", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["draft"]["title"], "开会")
        self.assertEqual(body["draft"]["location"], "A-201")
        self.assertIn("start_time", body["missing_fields"])
        self.assertIsNone(body["draft"]["end_time"])

    def test_parse_sse_emits_follow_up_events_for_missing_fields(self) -> None:
        payload = {
            "text": "Roadmap discussion next week.",
            "reference_time": "2026-03-27T10:00:00+08:00",
        }
        response = self.client.post("/api/parse/schedule-draft/stream", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-type"), "text/event-stream; charset=utf-8")

        body_text = response.text
        self.assertIn("event: draft", body_text)
        self.assertIn("event: follow_up", body_text)
        self.assertIn("event: done", body_text)
        self.assertIn("start_time", body_text)
        self.assertNotIn('"field": "end_time"', body_text)

    def test_parse_sse_skips_follow_up_when_required_fields_exist(self) -> None:
        payload = {
            "text": "Sync 2026-03-30T09:00:00+00:00 2026-03-30T10:00:00+00:00",
            "reference_time": "2026-03-27T10:00:00+08:00",
        }
        response = self.client.post("/api/parse/schedule-draft/stream", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        events = [
            line.removeprefix("event: ").strip()
            for line in response.text.splitlines()
            if line.startswith("event: ")
        ]
        self.assertEqual(events.count("follow_up"), 0)
        self.assertEqual(events.count("draft"), 1)
        self.assertEqual(events.count("done"), 1)

    def test_parse_requires_auth_header(self) -> None:
        response = self.client.post("/api/parse/schedule-draft", json={"text": "hello"})
        self.assertEqual(response.status_code, 401)

    def test_parse_session_create_returns_session_state(self) -> None:
        payload = {
            "message": "明早8点到9点在三饭吃饭",
            "reference_time": "2026-03-27T10:00:00+08:00",
        }
        response = self.client.post("/api/parse/sessions", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertTrue(body["parse_session_id"])
        self.assertTrue(body["draft_visible"])
        self.assertEqual(body["draft"]["title"], "吃饭")
        self.assertEqual(body["draft"]["location"], "三饭")
        self.assertTrue(body["ready_for_confirm"])
        self.assertEqual(body["next_action"], "finalize_draft")
        self.assertGreaterEqual(len(body["tool_calls"]), 2)

    def test_parse_session_multi_turn_updates_same_draft(self) -> None:
        create_response = self.client.post(
            "/api/parse/sessions",
            json={
                "message": "明天到 A-201 开会",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["parse_session_id"]

        continue_response = self.client.post(
            f"/api/parse/sessions/{session_id}/messages",
            json={
                "message": "上午10点开始，到11点结束",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(continue_response.status_code, 200)

        body = continue_response.json()
        self.assertEqual(body["draft"]["title"], "开会")
        self.assertEqual(body["draft"]["location"], "A-201")
        self.assertEqual(body["draft"]["start_time"], "2026-03-28T10:00:00+08:00")
        self.assertEqual(body["draft"]["end_time"], "2026-03-28T11:00:00+08:00")
        self.assertEqual(body["missing_fields"], [])
        self.assertTrue(body["ready_for_confirm"])

    def test_parse_session_follow_up_short_answer_fills_missing_start_time(self) -> None:
        create_response = self.client.post(
            "/api/parse/sessions",
            json={
                "message": "明天到A-201开会",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["parse_session_id"]

        first_body = create_response.json()
        self.assertEqual(first_body["draft"]["title"], "开会")
        self.assertEqual(first_body["draft"]["location"], "A-201")
        self.assertIsNone(first_body["draft"]["start_time"])
        self.assertIn("start_time", first_body["missing_fields"])

        continue_response = self.client.post(
            f"/api/parse/sessions/{session_id}/messages",
            json={
                "message": "早上九点开始",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(continue_response.status_code, 200)

        body = continue_response.json()
        self.assertEqual(body["draft"]["title"], "开会")
        self.assertEqual(body["draft"]["location"], "A-201")
        self.assertEqual(body["draft"]["start_time"], "2026-03-28T09:00:00+08:00")
        self.assertIsNone(body["draft"]["end_time"])
        self.assertEqual(body["missing_fields"], [])
        self.assertTrue(body["ready_for_confirm"])

    def test_parse_session_draft_patch_preserves_manual_override(self) -> None:
        create_response = self.client.post(
            "/api/parse/sessions",
            json={
                "message": "明早8点到9点在三饭吃饭",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["parse_session_id"]

        patch_response = self.client.patch(
            f"/api/parse/sessions/{session_id}/draft",
            json={
                "draft": {
                    "title": "早餐会",
                    "end_time": None,
                    "storage_strategy": "sync_to_cloud_and_knowledge",
                }
            },
            headers=self.headers,
        )
        self.assertEqual(patch_response.status_code, 200)

        body = patch_response.json()
        self.assertEqual(body["draft"]["title"], "早餐会")
        self.assertIsNone(body["draft"]["end_time"])
        self.assertEqual(body["draft"]["storage_strategy"], "sync_to_cloud_and_knowledge")
        self.assertEqual(body["next_action"], "finalize_draft")

    def test_parse_session_keeps_prior_time_when_only_location_changes(self) -> None:
        create_response = self.client.post(
            "/api/parse/sessions",
            json={
                "message": "明天上午10点到11点在A-201开会",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["parse_session_id"]

        continue_response = self.client.post(
            f"/api/parse/sessions/{session_id}/messages",
            json={
                "message": "把第一次说的时间保留，只改地点到B-301",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(continue_response.status_code, 200)

        body = continue_response.json()
        self.assertEqual(body["draft"]["title"], "开会")
        self.assertEqual(body["draft"]["location"], "B-301")
        self.assertEqual(body["draft"]["start_time"], "2026-03-28T10:00:00+08:00")
        self.assertEqual(body["draft"]["end_time"], "2026-03-28T11:00:00+08:00")

    def test_parse_session_clear_end_time_only_preserves_other_fields(self) -> None:
        create_response = self.client.post(
            "/api/parse/sessions",
            json={
                "message": "明天下午3点到4点在A-201开会",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["parse_session_id"]

        continue_response = self.client.post(
            f"/api/parse/sessions/{session_id}/messages",
            json={
                "message": "前面那个安排不要结束时间了",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(continue_response.status_code, 200)

        body = continue_response.json()
        self.assertEqual(body["draft"]["title"], "开会")
        self.assertEqual(body["draft"]["location"], "A-201")
        self.assertEqual(body["draft"]["start_time"], "2026-03-28T15:00:00+08:00")
        self.assertIsNone(body["draft"]["end_time"])
        self.assertTrue(body["ready_for_confirm"])

    def test_parse_session_replaces_time_and_keeps_existing_title_and_location(self) -> None:
        create_response = self.client.post(
            "/api/parse/sessions",
            json={
                "message": "明天上午10点到11点在A-201开会",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        session_id = create_response.json()["parse_session_id"]

        continue_response = self.client.post(
            f"/api/parse/sessions/{session_id}/messages",
            json={
                "message": "还是上次那个会议，只改成明天下午3点到4点",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(continue_response.status_code, 200)

        body = continue_response.json()
        self.assertEqual(body["draft"]["title"], "开会")
        self.assertEqual(body["draft"]["location"], "A-201")
        self.assertEqual(body["draft"]["start_time"], "2026-03-28T15:00:00+08:00")
        self.assertEqual(body["draft"]["end_time"], "2026-03-28T16:00:00+08:00")

    def test_parse_session_can_keep_referenced_location_while_overriding_title(self) -> None:
        first_response = self.client.post(
            "/api/parse/sessions",
            json={
                "message": "明天下午3点到4点在A楼开会",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(first_response.status_code, 200)
        session_id = first_response.json()["parse_session_id"]

        second_response = self.client.post(
            f"/api/parse/sessions/{session_id}/messages",
            json={
                "message": "地点改到B楼",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(second_response.status_code, 200)

        third_response = self.client.post(
            f"/api/parse/sessions/{session_id}/messages",
            json={
                "message": "第二条说的地点保留，标题改成组会",
                "reference_time": "2026-03-27T10:00:00+08:00",
            },
            headers=self.headers,
        )
        self.assertEqual(third_response.status_code, 200)

        body = third_response.json()
        self.assertEqual(body["draft"]["title"], "组会")
        self.assertEqual(body["draft"]["location"], "B楼")
        self.assertEqual(body["draft"]["start_time"], "2026-03-28T15:00:00+08:00")
        self.assertEqual(body["draft"]["end_time"], "2026-03-28T16:00:00+08:00")


if __name__ == "__main__":
    unittest.main()

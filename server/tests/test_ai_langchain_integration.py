from __future__ import annotations

import asyncio
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import Schedule, VectorChunk
from app.models.enums import ScheduleSource
from app.services.ai_runtime import LangChainAiRuntime
from app.services.parse_service import ParseFieldUpdate, ParseLLMOutput
from app.services.rag_service import RagService
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


class RuntimeStructuredOutputModel(BaseModel):
    title: str | None = None


class LangChainRuntimeTestCase(unittest.TestCase):
    def test_structured_output_chain_executes_with_langchain_runnable(self) -> None:
        runtime = LangChainAiRuntime(
            base_url="https://example.com/v1",
            api_key="demo-key",
            chat_model="demo-chat",
            embedding_model="demo-embedding",
            embedding_dimensions=3,
        )
        fake_model = RunnableLambda(lambda _: AIMessage(content='{"title": "Architecture Review"}'))

        with patch.object(runtime, "_build_chat_model", return_value=fake_model):
            result = asyncio.run(
                runtime.ainvoke_structured_output(
                    system_prompt="Return a title only.",
                    human_payload={"message": "Need an architecture review meeting."},
                    output_model=RuntimeStructuredOutputModel,
                    temperature=0,
                )
            )

        self.assertEqual(result.title, "Architecture Review")

    def test_text_chain_executes_with_langchain_runnable(self) -> None:
        runtime = LangChainAiRuntime(
            base_url="https://example.com/v1",
            api_key="demo-key",
            chat_model="demo-chat",
            embedding_model="demo-embedding",
            embedding_dimensions=3,
        )
        fake_model = RunnableLambda(lambda _: AIMessage(content="Use the schedule context"))

        with patch.object(runtime, "_build_chat_model", return_value=fake_model):
            result = asyncio.run(
                runtime.ainvoke_text(
                    system_prompt="Answer from context only.",
                    human_payload={"query": "What matters today?"},
                    temperature=0.2,
                )
            )

        self.assertEqual(result, "Use the schedule context")


class AiServiceLangChainPathTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        RagService._sessions.clear()
        self.client = TestClient(app)
        self.user_id, self.headers = register_user(self.client, "ai_langchain_user")

        with SessionLocal() as db:
            schedule = Schedule(
                user_id=self.user_id,
                title="Prepare design review",
                start_time=datetime.fromisoformat("2026-04-01T09:00:00+00:00"),
                end_time=datetime.fromisoformat("2026-04-01T10:00:00+00:00"),
                location="Room A",
                remark="Discuss async AI path isolation.",
                source=ScheduleSource.MANUAL,
                allow_rag_indexing=True,
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            self.schedule_id = schedule.id

    def test_parse_session_uses_langchain_runtime_when_available(self) -> None:
        captured_payloads: list[dict] = []

        async def fake_invoke_structured_output(**kwargs):
            captured_payloads.append(kwargs["human_payload"])
            if len(captured_payloads) == 1:
                return ParseLLMOutput(
                    title=ParseFieldUpdate(action="set", value="Design Review"),
                    start_time=ParseFieldUpdate(action="set", value="2026-04-02T09:00:00+08:00"),
                    end_time=ParseFieldUpdate(action="set", value="2026-04-02T10:00:00+08:00"),
                    location=ParseFieldUpdate(action="set", value="Room A"),
                    remark=ParseFieldUpdate(action="set", value="Need async service review"),
                    storage_strategy=ParseFieldUpdate(action="set", value="sync_to_cloud"),
                )
            return ParseLLMOutput(
                title=ParseFieldUpdate(action="keep"),
                start_time=ParseFieldUpdate(action="keep"),
                end_time=ParseFieldUpdate(action="keep"),
                location=ParseFieldUpdate(action="set", value="Room B"),
                remark=ParseFieldUpdate(action="keep"),
                storage_strategy=ParseFieldUpdate(action="keep"),
            )

        runtime = type("FakeParseRuntime", (), {})()
        runtime.ainvoke_structured_output = AsyncMock(side_effect=fake_invoke_structured_output)

        with patch("app.services.parse_service.ParseService._get_runtime", return_value=runtime):
            create_response = self.client.post(
                "/api/parse/sessions",
                json={
                    "message": "Tomorrow 9 to 10 design review in Room A.",
                    "reference_time": "2026-04-01T10:00:00+08:00",
                },
                headers=self.headers,
            )
            self.assertEqual(create_response.status_code, 200)
            session_id = create_response.json()["parse_session_id"]

            response = self.client.post(
                f"/api/parse/sessions/{session_id}/messages",
                json={
                    "message": "Keep the previous time and only change the location to Room B.",
                    "reference_time": "2026-04-01T10:00:00+08:00",
                },
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["draft"]["title"], "Design Review")
        self.assertEqual(body["draft"]["location"], "Room B")
        self.assertEqual(body["draft"]["start_time"], "2026-04-02T09:00:00+08:00")
        self.assertIsNotNone(captured_payloads[1]["session_context"])
        self.assertEqual(
            captured_payloads[1]["session_context"]["prior_user_turns"][0]["message"],
            "Tomorrow 9 to 10 design review in Room A.",
        )
        self.assertEqual(
            captured_payloads[1]["session_context"]["recent_dialogue"][-2]["role"],
            "assistant",
        )
        self.assertNotIn("pending_follow_up_fields", captured_payloads[1]["session_context"])
        runtime.ainvoke_structured_output.assert_awaited()

    def test_parse_follow_up_context_guides_pending_slot_completion(self) -> None:
        captured_payloads: list[dict] = []

        async def fake_invoke_structured_output(**kwargs):
            captured_payloads.append(kwargs["human_payload"])
            if len(captured_payloads) == 1:
                return ParseLLMOutput(
                    title=ParseFieldUpdate(action="set", value="开会"),
                    start_time=ParseFieldUpdate(action="keep"),
                    end_time=ParseFieldUpdate(action="keep"),
                    location=ParseFieldUpdate(action="set", value="A-201"),
                    remark=ParseFieldUpdate(action="keep"),
                    storage_strategy=ParseFieldUpdate(action="keep"),
                )
            return ParseLLMOutput(
                title=ParseFieldUpdate(action="keep"),
                start_time=ParseFieldUpdate(action="keep"),
                end_time=ParseFieldUpdate(action="keep"),
                location=ParseFieldUpdate(action="keep"),
                remark=ParseFieldUpdate(action="keep"),
                storage_strategy=ParseFieldUpdate(action="keep"),
            )

        runtime = type("FakeParseRuntime", (), {})()
        runtime.ainvoke_structured_output = AsyncMock(side_effect=fake_invoke_structured_output)

        with patch("app.services.parse_service.ParseService._get_runtime", return_value=runtime):
            create_response = self.client.post(
                "/api/parse/sessions",
                json={
                    "message": "明天到A-201开会",
                    "reference_time": "2026-04-01T10:00:00+08:00",
                },
                headers=self.headers,
            )
            self.assertEqual(create_response.status_code, 200)
            session_id = create_response.json()["parse_session_id"]

            response = self.client.post(
                f"/api/parse/sessions/{session_id}/messages",
                json={
                    "message": "早上九点开始",
                    "reference_time": "2026-04-01T10:00:00+08:00",
                },
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["draft"]["title"], "开会")
        self.assertEqual(body["draft"]["location"], "A-201")
        self.assertEqual(body["draft"]["start_time"], "2026-04-02T09:00:00+08:00")
        self.assertEqual(body["missing_fields"], [])
        self.assertTrue(body["ready_for_confirm"])

        follow_up_context = captured_payloads[1]["session_context"]
        self.assertEqual(follow_up_context["current_missing_fields"], ["start_time"])
        self.assertEqual(follow_up_context["pending_follow_up_fields"], ["start_time"])
        self.assertEqual(follow_up_context["active_follow_up_field"], "start_time")
        self.assertEqual(follow_up_context["current_follow_up_questions"][0]["field"], "start_time")
        self.assertTrue(follow_up_context["follow_up_reply_expected"])
        self.assertIn("开始", follow_up_context["last_assistant_message"])
        self.assertEqual(follow_up_context["recent_dialogue"][-1]["content"], "早上九点开始")
        runtime.ainvoke_structured_output.assert_awaited()

    def test_parse_runtime_cannot_fabricate_precise_start_time_without_signal(self) -> None:
        async def fake_invoke_structured_output(**kwargs):
            return ParseLLMOutput(
                title=ParseFieldUpdate(action="set", value="体育馆游泳"),
                start_time=ParseFieldUpdate(action="set", value="2026-04-02T09:00:00+08:00"),
                end_time=ParseFieldUpdate(action="set", value="2026-04-02T10:00:00+08:00"),
                location=ParseFieldUpdate(action="set", value="体育馆"),
                remark=ParseFieldUpdate(action="set", value="明天去体育馆游泳"),
                storage_strategy=ParseFieldUpdate(action="keep"),
            )

        runtime = type("FakeParseRuntime", (), {})()
        runtime.ainvoke_structured_output = AsyncMock(side_effect=fake_invoke_structured_output)

        with patch("app.services.parse_service.ParseService._get_runtime", return_value=runtime):
            response = self.client.post(
                "/api/parse/sessions",
                json={
                    "message": "明天去体育馆游泳",
                    "reference_time": "2026-04-01T21:00:00+08:00",
                },
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["draft"]["title"], "体育馆游泳")
        self.assertEqual(body["draft"]["location"], "体育馆")
        self.assertIsNone(body["draft"]["start_time"])
        self.assertIsNone(body["draft"]["end_time"])
        self.assertIn("start_time", body["missing_fields"])
        self.assertFalse(body["ready_for_confirm"])
        runtime.ainvoke_structured_output.assert_awaited()

    def test_rag_paths_use_langchain_runtime_when_available(self) -> None:
        async def fake_embed_documents(texts: list[str], **kwargs) -> list[list[float]]:
            return [[round(0.01 * (index + 1), 2)] * 3072 for index, _ in enumerate(texts)]

        streamed_payloads: list[dict] = []

        def fake_astream_text(**kwargs):
            streamed_payloads.append(kwargs["human_payload"])

            async def iterator():
                for chunk in ("Focus ", "on async AI ", "path isolation."):
                    yield chunk

            return iterator()

        runtime = type("FakeRagRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)
        runtime.aembed_query = AsyncMock(return_value=[0.04] * 3072)
        runtime.astream_text = MagicMock(side_effect=fake_astream_text)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            rebuild_response = self.client.post(
                f"/api/rag/chunks/rebuild/{self.schedule_id}",
                json={"chunk_size": 500},
                headers=self.headers,
            )
            self.assertEqual(rebuild_response.status_code, 200)

            retrieve_response = self.client.post(
                "/api/rag/retrieve",
                json={"query": "What should I focus on?", "top_k": 5},
                headers=self.headers,
            )
            self.assertEqual(retrieve_response.status_code, 200)

            stream_response = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "What should I focus on?", "top_k": 5},
                headers=self.headers,
            )
            self.assertEqual(stream_response.status_code, 200)
            self.assertIn("event: token", stream_response.text)

        runtime.aembed_documents.assert_awaited()
        runtime.aembed_query.assert_awaited()
        runtime.astream_text.assert_called_once()
        self.assertEqual(streamed_payloads[0]["query"], "What should I focus on?")
        candidates = streamed_payloads[0]["schedule_candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["date"], "2026-04-01")
        self.assertEqual(candidates[0]["start_time"], "17:00")
        self.assertEqual(candidates[0]["end_time"], "18:00")
        self.assertEqual(candidates[0]["time_range"], "2026-04-01 17:00 -> 2026-04-01 18:00")
        self.assertEqual(candidates[0]["location"], "Room A")
        self.assertIn("Discuss async AI path isolation.", candidates[0]["remark"])

        with SessionLocal() as db:
            chunk_count = len(
                list(
                    db.scalars(
                        select(VectorChunk).where(
                            VectorChunk.user_id == self.user_id,
                            VectorChunk.schedule_id == self.schedule_id,
                        )
                    ).all()
                )
            )
            self.assertGreater(chunk_count, 0)

    def test_rag_follow_up_session_history_reaches_runtime(self) -> None:
        async def fake_embed_documents(texts: list[str], **kwargs) -> list[list[float]]:
            return [[round(0.015 * (index + 1), 2)] * 3072 for index, _ in enumerate(texts)]

        streamed_payloads: list[dict] = []

        def fake_astream_text(**kwargs):
            streamed_payloads.append(kwargs["human_payload"])
            reply = (
                "Your advisor meeting is tomorrow morning."
                if len(streamed_payloads) == 1
                else "It is at 09:00."
            )

            async def iterator():
                yield reply

            return iterator()

        runtime = type("FakeMultiTurnRagRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)
        runtime.aembed_query = AsyncMock(return_value=[0.045] * 3072)
        runtime.astream_text = MagicMock(side_effect=fake_astream_text)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            rebuild_response = self.client.post(
                f"/api/rag/chunks/rebuild/{self.schedule_id}",
                json={"chunk_size": 20},
                headers=self.headers,
            )
            self.assertEqual(rebuild_response.status_code, 200)

            first_response = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "Which advisor meetings do I have?", "top_k": 3, "session_id": "rag-langchain"},
                headers=self.headers,
            )
            self.assertEqual(first_response.status_code, 200)

            second_response = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "What time is it?", "top_k": 3, "session_id": "rag-langchain"},
                headers=self.headers,
            )
            self.assertEqual(second_response.status_code, 200)

        runtime.aembed_documents.assert_awaited()
        runtime.aembed_query.assert_awaited()
        self.assertEqual(runtime.astream_text.call_count, 2)
        self.assertNotIn("session_history", streamed_payloads[0])
        self.assertIn("schedule_candidates", streamed_payloads[0])
        self.assertGreaterEqual(len(streamed_payloads[0]["schedule_candidates"]), 1)
        self.assertEqual(
            streamed_payloads[1]["session_history"],
            [
                {
                    "user_query": "Which advisor meetings do I have?",
                    "assistant_answer": "Your advisor meeting is tomorrow morning.",
                }
            ],
        )
        self.assertEqual(streamed_payloads[1]["query"], "What time is it?")
        self.assertIn("schedule_candidates", streamed_payloads[1])
        self.assertGreaterEqual(len(streamed_payloads[1]["schedule_candidates"]), 1)
        second_embed_query = runtime.aembed_query.await_args_list[-1].args[0]
        self.assertIn("What time is it?", second_embed_query)
        self.assertIn("Which advisor meetings do I have?", second_embed_query)

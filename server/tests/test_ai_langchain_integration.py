from __future__ import annotations

import asyncio
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

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
        runtime.ainvoke_structured_output.assert_awaited()

    def test_rag_paths_use_langchain_runtime_when_available(self) -> None:
        async def fake_embed_documents(texts: list[str]) -> list[list[float]]:
            return [[round(0.01 * (index + 1), 2)] * 3072 for index, _ in enumerate(texts)]

        runtime = type("FakeRagRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)
        runtime.aembed_query = AsyncMock(return_value=[0.04] * 3072)
        runtime.ainvoke_text = AsyncMock(return_value="Focus on async AI path isolation.")

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            rebuild_response = self.client.post(
                f"/api/rag/chunks/rebuild/{self.schedule_id}",
                json={"chunk_size": 20},
                headers=self.headers,
            )
            self.assertEqual(rebuild_response.status_code, 200)

            retrieve_response = self.client.post(
                "/api/rag/retrieve",
                json={"query": "What should I focus on?", "top_k": 3},
                headers=self.headers,
            )
            self.assertEqual(retrieve_response.status_code, 200)

            stream_response = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "What should I focus on?", "top_k": 3},
                headers=self.headers,
            )
            self.assertEqual(stream_response.status_code, 200)
            self.assertIn("event: token", stream_response.text)

        runtime.aembed_documents.assert_awaited()
        runtime.aembed_query.assert_awaited()
        runtime.ainvoke_text.assert_awaited()

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

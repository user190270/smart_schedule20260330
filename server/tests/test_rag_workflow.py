from __future__ import annotations

from datetime import datetime
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import ChatHistory, KnowledgeBaseState, Schedule, VectorChunk
from app.models.enums import ScheduleSource
from app.services.ai_runtime import AiRuntimeError
from app.services.rag_service import RagService
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


def parse_sse_events(body_text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for chunk in body_text.split("\n\n"):
        if not chunk.strip():
            continue
        event_line = next((line for line in chunk.splitlines() if line.startswith("event: ")), None)
        data_line = next((line for line in chunk.splitlines() if line.startswith("data: ")), None)
        if event_line is None or data_line is None:
            continue
        events.append(
            {
                "event": event_line.removeprefix("event: ").strip(),
                "data": json.loads(data_line.removeprefix("data: ").strip()),
            }
        )
    return events


class RagWorkflowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        RagService._sessions.clear()
        runtime_patcher = patch("app.services.rag_service.RagService._get_runtime", return_value=None)
        runtime_patcher.start()
        self.addCleanup(runtime_patcher.stop)
        self.client = TestClient(app)
        self.user_a_id, self.headers_a = register_user(self.client, "rag_user_a")
        self.user_b_id, self.headers_b = register_user(self.client, "rag_user_b")

        with SessionLocal() as db:

            schedule_a = Schedule(
                user_id=self.user_a_id,
                title="Prepare architecture review notes",
                start_time=datetime.fromisoformat("2026-03-31T09:00:00+00:00"),
                end_time=datetime.fromisoformat("2026-03-31T10:00:00+00:00"),
                location="Room C",
                remark="Focus on sync and parse workflow robustness.",
                source=ScheduleSource.MANUAL,
                allow_rag_indexing=True,
            )
            schedule_b = Schedule(
                user_id=self.user_b_id,
                title="Private beta strategy meeting",
                start_time=datetime.fromisoformat("2026-03-31T11:00:00+00:00"),
                end_time=datetime.fromisoformat("2026-03-31T12:00:00+00:00"),
                location="Room D",
                remark="Confidential beta roadmap and launch plan.",
                source=ScheduleSource.MANUAL,
                allow_rag_indexing=True,
            )
            db.add_all([schedule_a, schedule_b])
            db.commit()
            db.refresh(schedule_a)
            db.refresh(schedule_b)
            self.schedule_a_id = schedule_a.id
            self.schedule_b_id = schedule_b.id

    def test_rebuild_chunks_creates_vector_records(self) -> None:
        response = self.client.post(
            f"/api/rag/chunks/rebuild/{self.schedule_a_id}",
            json={"chunk_size": 30},
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["chunks_created"], 0)
        self.assertEqual(body["embedding_dimensions"], 3072)
        self.assertEqual(body["status"], "success")
        self.assertIsNotNone(body["rebuilt_at"])

        with SessionLocal() as db:
            chunks = list(
                db.scalars(
                    select(VectorChunk).where(
                        VectorChunk.user_id == self.user_a_id,
                        VectorChunk.schedule_id == self.schedule_a_id,
                    )
                ).all()
            )
            self.assertGreater(len(chunks), 0)
            self.assertTrue(all(len(chunk.embedding) == body["embedding_dimensions"] for chunk in chunks))

            kb_state = db.scalar(select(KnowledgeBaseState).where(KnowledgeBaseState.user_id == self.user_a_id))
            self.assertIsNotNone(kb_state)
            assert kb_state is not None
            self.assertEqual(kb_state.last_rebuild_status, "success")
            self.assertEqual(kb_state.last_rebuild_schedules_considered, 1)
            self.assertEqual(kb_state.last_rebuild_schedules_indexed, 1)

    def test_rebuild_chunks_include_structured_temporal_fields(self) -> None:
        response = self.client.post(
            f"/api/rag/chunks/rebuild/{self.schedule_a_id}",
            json={"chunk_size": 500},
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)

        with SessionLocal() as db:
            chunks = list(
                db.scalars(
                    select(VectorChunk).where(
                        VectorChunk.user_id == self.user_a_id,
                        VectorChunk.schedule_id == self.schedule_a_id,
                    )
                ).all()
            )
            indexed_text = " ".join(chunk.content for chunk in chunks)

        self.assertIn("title Prepare architecture review notes", indexed_text)
        self.assertIn("date 2026-03-31", indexed_text)
        self.assertIn("start 17:00", indexed_text)
        self.assertIn("end 18:00", indexed_text)
        self.assertIn("time_range 2026-03-31 17:00 -> 2026-03-31 18:00", indexed_text)
        self.assertIn("location Room C", indexed_text)
        self.assertIn("remark Focus on sync and parse workflow robustness.", indexed_text)
        self.assertNotIn("+00:00", indexed_text)

    def test_rebuild_default_chunk_size_keeps_single_schedule_coherent(self) -> None:
        response = self.client.post(
            f"/api/rag/chunks/rebuild/{self.schedule_a_id}",
            json={},
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["chunks_created"], 1)

        with SessionLocal() as db:
            chunks = list(
                db.scalars(
                    select(VectorChunk).where(
                        VectorChunk.user_id == self.user_a_id,
                        VectorChunk.schedule_id == self.schedule_a_id,
                    )
                ).all()
            )

        self.assertEqual(len(chunks), 1)

    def test_rebuild_chunks_respects_user_isolation(self) -> None:
        response = self.client.post(
            f"/api/rag/chunks/rebuild/{self.schedule_a_id}",
            json={"chunk_size": 40},
            headers=self.headers_b,
        )
        self.assertEqual(response.status_code, 404)

    def test_retrieve_results_are_filtered_by_user_id(self) -> None:
        self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_a_id}", json={"chunk_size": 30}, headers=self.headers_a)
        self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_b_id}", json={"chunk_size": 30}, headers=self.headers_b)

        retrieve_a = self.client.post("/api/rag/retrieve", json={"query": "beta", "top_k": 5}, headers=self.headers_a)
        self.assertEqual(retrieve_a.status_code, 200)
        result_a = retrieve_a.json()["results"]
        self.assertGreater(len(result_a), 0)
        self.assertTrue(all(item["schedule_id"] == self.schedule_a_id for item in result_a))

        retrieve_b = self.client.post("/api/rag/retrieve", json={"query": "architecture", "top_k": 5}, headers=self.headers_b)
        self.assertEqual(retrieve_b.status_code, 200)
        result_b = retrieve_b.json()["results"]
        self.assertGreater(len(result_b), 0)
        self.assertTrue(all(item["schedule_id"] == self.schedule_b_id for item in result_b))

    def test_rebuild_all_chunks_updates_status_summary(self) -> None:
        response = self.client.post(
            "/api/rag/chunks/rebuild-all",
            json={"chunk_size": 30},
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["user_id"], self.user_a_id)
        self.assertEqual(body["schedules_considered"], 1)
        self.assertEqual(body["schedules_indexed"], 1)
        self.assertGreater(body["chunks_created"], 0)
        self.assertEqual(body["embedding_dimensions"], 3072)
        self.assertEqual(body["status"], "success")

        status_response = self.client.get("/api/sync/status", headers=self.headers_a)
        self.assertEqual(status_response.status_code, 200)
        status_body = status_response.json()
        self.assertEqual(status_body["cloud_schedule_count"], 1)
        self.assertEqual(status_body["knowledge_base_eligible_schedule_count"], 1)
        self.assertEqual(status_body["indexed_schedule_count"], 1)
        self.assertGreater(status_body["indexed_chunk_count"], 0)
        self.assertEqual(status_body["last_knowledge_rebuild_status"], "success")
        self.assertEqual(status_body["last_knowledge_rebuild_schedules_considered"], 1)
        self.assertEqual(status_body["last_knowledge_rebuild_schedules_indexed"], 1)
        self.assertGreater(status_body["last_knowledge_rebuild_chunks_created"], 0)

    def test_failed_rebuild_updates_status(self) -> None:
        with patch("app.services.rag_service.RagService._build_embeddings", side_effect=RuntimeError("embedding unavailable")):
            response = self.client.post(
                "/api/rag/chunks/rebuild-all",
                json={"chunk_size": 30},
                headers=self.headers_a,
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "embedding unavailable")

        status_response = self.client.get("/api/sync/status", headers=self.headers_a)
        self.assertEqual(status_response.status_code, 200)
        status_body = status_response.json()
        self.assertEqual(status_body["last_knowledge_rebuild_status"], "failed")
        self.assertEqual(status_body["last_knowledge_rebuild_message"], "embedding unavailable")
        self.assertEqual(status_body["indexed_chunk_count"], 0)

    def test_rebuild_all_only_indexes_eligible_schedules(self) -> None:
        with SessionLocal() as db:
            db.add(
                Schedule(
                    user_id=self.user_a_id,
                    title="Cloud but not in knowledge base",
                    start_time=datetime.fromisoformat("2026-03-31T13:00:00+00:00"),
                    end_time=datetime.fromisoformat("2026-03-31T14:00:00+00:00"),
                    location="Room E",
                    remark="Should stay out of rebuild-all context.",
                    source=ScheduleSource.MANUAL,
                    allow_rag_indexing=False,
                )
            )
            db.commit()

        response = self.client.post(
            "/api/rag/chunks/rebuild-all",
            json={"chunk_size": 30},
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["schedules_considered"], 1)
        self.assertEqual(body["schedules_indexed"], 1)

        retrieve_response = self.client.post(
            "/api/rag/retrieve",
            json={"query": "knowledge base", "top_k": 10},
            headers=self.headers_a,
        )
        self.assertEqual(retrieve_response.status_code, 200)
        schedule_ids = {item["schedule_id"] for item in retrieve_response.json()["results"]}
        self.assertEqual(schedule_ids, {self.schedule_a_id})

    def test_stream_answer_writes_chat_history(self) -> None:
        self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_a_id}", json={"chunk_size": 30}, headers=self.headers_a)

        response = self.client.post(
            "/api/rag/answer/stream",
            json={"query": "What should I focus on today?", "top_k": 3},
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-type"), "text/event-stream; charset=utf-8")
        self.assertIn("event: token", response.text)
        self.assertIn("event: done", response.text)

        with SessionLocal() as db:
            history = list(db.scalars(select(ChatHistory).where(ChatHistory.user_id == self.user_a_id)).all())
            self.assertGreaterEqual(len(history), 2)
            last_two_contents = [item.content for item in history[-2:]]
            self.assertIn("What should I focus on today?", last_two_contents[0])
            self.assertTrue(len(last_two_contents[1]) > 0)
            history_user_b = list(db.scalars(select(ChatHistory).where(ChatHistory.user_id == self.user_b_id)).all())
            self.assertEqual(history_user_b, [])

    def test_stream_answer_forwards_runtime_chunks_in_order(self) -> None:
        async def fake_embed_documents(texts: list[str]) -> list[list[float]]:
            return [[round(0.02 * (index + 1), 2)] * 3072 for index, _ in enumerate(texts)]

        def fake_astream_text(**kwargs):
            self.assertEqual(kwargs["human_payload"]["query"], "Stream the answer please.")

            async def iterator():
                for chunk in ("Alpha ", "Beta", " + Gamma"):
                    yield chunk

            return iterator()

        runtime = type("FakeStreamingRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)
        runtime.aembed_query = AsyncMock(return_value=[0.08] * 3072)
        runtime.astream_text = MagicMock(side_effect=fake_astream_text)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_a_id}", json={"chunk_size": 30}, headers=self.headers_a)
            response = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "Stream the answer please.", "top_k": 3},
                headers=self.headers_a,
            )

        self.assertEqual(response.status_code, 200)
        events = parse_sse_events(response.text)
        self.assertEqual([item["event"] for item in events], ["meta", "token", "token", "token", "done"])
        self.assertEqual(
            [item["data"]["text"] for item in events if item["event"] == "token"],
            ["Alpha ", "Beta", " + Gamma"],
        )
        self.assertEqual(events[-1]["data"]["message"], "stream_completed")

        with SessionLocal() as db:
            history = list(
                db.scalars(
                    select(ChatHistory)
                    .where(ChatHistory.user_id == self.user_a_id)
                    .order_by(ChatHistory.id.asc())
                ).all()
            )
            self.assertGreaterEqual(len(history), 2)
            self.assertEqual(history[-1].content, "Alpha Beta + Gamma")

    def test_stream_answer_emits_done_on_runtime_failure_without_persisting_partial_history(self) -> None:
        async def fake_embed_documents(texts: list[str]) -> list[list[float]]:
            return [[round(0.03 * (index + 1), 2)] * 3072 for index, _ in enumerate(texts)]

        def fake_astream_text(**kwargs):
            self.assertEqual(kwargs["human_payload"]["query"], "Fail mid stream")

            async def iterator():
                yield "Partial answer"
                raise AiRuntimeError("stream interrupted")

            return iterator()

        runtime = type("FakeBrokenStreamingRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)
        runtime.aembed_query = AsyncMock(return_value=[0.09] * 3072)
        runtime.astream_text = MagicMock(side_effect=fake_astream_text)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_a_id}", json={"chunk_size": 30}, headers=self.headers_a)
            response = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "Fail mid stream", "top_k": 3},
                headers=self.headers_a,
            )

        self.assertEqual(response.status_code, 200)
        events = parse_sse_events(response.text)
        self.assertEqual([item["event"] for item in events], ["meta", "token", "done"])
        self.assertEqual(events[1]["data"]["text"], "Partial answer")
        self.assertEqual(events[-1]["data"]["message"], "stream_failed")

        with SessionLocal() as db:
            history = list(db.scalars(select(ChatHistory).where(ChatHistory.user_id == self.user_a_id)).all())
            self.assertEqual(history, [])

    def test_stream_answer_reuses_recent_session_history_for_follow_up(self) -> None:
        async def fake_embed_documents(texts: list[str]) -> list[list[float]]:
            return [[round(0.04 * (index + 1), 2)] * 3072 for index, _ in enumerate(texts)]

        async def fake_embed_query(_query: str) -> list[float]:
            return [0.06] * 3072

        streamed_payloads: list[dict[str, object]] = []

        def fake_astream_text(**kwargs):
            streamed_payloads.append(kwargs["human_payload"])
            reply = (
                "Your first event tomorrow is meeting with your advisor."
                if len(streamed_payloads) == 1
                else "It takes place in Room C."
            )

            async def iterator():
                yield reply

            return iterator()

        runtime = type("FakeMultiTurnRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)
        runtime.aembed_query = AsyncMock(side_effect=fake_embed_query)
        runtime.astream_text = MagicMock(side_effect=fake_astream_text)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_a_id}", json={"chunk_size": 30}, headers=self.headers_a)

            first_response = self.client.post(
                "/api/rag/answer/stream",
                json={
                    "query": "What is my first event tomorrow?",
                    "top_k": 3,
                    "session_id": "rag-session-a",
                },
                headers=self.headers_a,
            )
            self.assertEqual(first_response.status_code, 200)

            second_response = self.client.post(
                "/api/rag/answer/stream",
                json={
                    "query": "Where is it?",
                    "top_k": 3,
                    "session_id": "rag-session-a",
                },
                headers=self.headers_a,
            )

        self.assertEqual(second_response.status_code, 200)
        second_events = parse_sse_events(second_response.text)
        self.assertEqual([item["event"] for item in second_events], ["meta", "token", "done"])
        self.assertEqual(second_events[1]["data"]["text"], "It takes place in Room C.")
        self.assertEqual(second_events[-1]["data"]["message"], "stream_completed")

        self.assertNotIn("session_history", streamed_payloads[0])
        self.assertIn("session_history", streamed_payloads[1])
        self.assertEqual(
            streamed_payloads[1]["session_history"],
            [
                {
                    "user_query": "What is my first event tomorrow?",
                    "assistant_answer": "Your first event tomorrow is meeting with your advisor.",
                }
            ],
        )
        self.assertEqual(streamed_payloads[1]["query"], "Where is it?")
        second_embed_query = runtime.aembed_query.await_args_list[-1].args[0]
        self.assertIn("Where is it?", second_embed_query)
        self.assertIn("What is my first event tomorrow?", second_embed_query)
        self.assertIn("Your first event tomorrow is meeting with your advisor.", second_embed_query)
        self.assertEqual(
            RagService._sessions[(self.user_a_id, "rag-session-a")].turns[-1].assistant_answer,
            "It takes place in Room C.",
        )

    def test_stream_answer_same_session_id_does_not_cross_users(self) -> None:
        async def fake_embed_documents(texts: list[str]) -> list[list[float]]:
            return [[round(0.05 * (index + 1), 2)] * 3072 for index, _ in enumerate(texts)]

        streamed_payloads: list[dict[str, object]] = []

        def fake_astream_text(**kwargs):
            streamed_payloads.append(kwargs["human_payload"])

            async def iterator():
                yield "Scoped reply."

            return iterator()

        runtime = type("FakeScopedRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)
        runtime.aembed_query = AsyncMock(return_value=[0.07] * 3072)
        runtime.astream_text = MagicMock(side_effect=fake_astream_text)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_a_id}", json={"chunk_size": 30}, headers=self.headers_a)
            self.client.post(f"/api/rag/chunks/rebuild/{self.schedule_b_id}", json={"chunk_size": 30}, headers=self.headers_b)

            response_a = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "What is scheduled?", "top_k": 3, "session_id": "shared-session"},
                headers=self.headers_a,
            )
            response_b = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "Where is it?", "top_k": 3, "session_id": "shared-session"},
                headers=self.headers_b,
            )

        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        self.assertNotIn("session_history", streamed_payloads[0])
        self.assertNotIn("session_history", streamed_payloads[1])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models import AiUsageEvent, Schedule, User, VectorChunk
from app.models.enums import ScheduleSource, SubscriptionTier
from app.services.ai_runtime import TokenUsage
from app.services.parse_service import ParseFieldUpdate, ParseLLMOutput
from app.services.quota_service import QuotaService
from tests.auth_helpers import register_user
from tests.db_helpers import reset_database


class AiQuotaDemoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)
        self.user_id, self.headers = register_user(self.client, "quota_user")

    def _set_user_quota_state(
        self,
        *,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        usage: int,
        last_reset_time: datetime,
    ) -> None:
        with SessionLocal() as db:
            user = db.get(User, self.user_id)
            if user is None:
                raise AssertionError("Expected seeded user to exist.")
            user.subscription_tier = tier
            user.daily_token_usage = usage
            user.last_reset_time = last_reset_time
            db.commit()

    def _seed_rag_schedule_with_chunk(self) -> None:
        with SessionLocal() as db:
            schedule = Schedule(
                user_id=self.user_id,
                title="Design Review",
                start_time=datetime.fromisoformat("2026-04-19T09:00:00+08:00"),
                end_time=datetime.fromisoformat("2026-04-19T10:00:00+08:00"),
                location="A-201",
                remark="Token quota review.",
                source=ScheduleSource.MANUAL,
                allow_rag_indexing=True,
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            db.add(
                VectorChunk(
                    schedule_id=schedule.id,
                    user_id=self.user_id,
                    content="title Design Review | date 2026-04-19 | start 09:00 | end 10:00",
                    embedding=[0.03] * 3072,
                )
            )
            db.commit()

    def test_auth_me_reports_default_token_quota_status_and_demo_upgrade_changes_limit(self) -> None:
        me_response = self.client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["subscription_tier"], "free")
        self.assertEqual(me_response.json()["daily_token_usage"], 0)
        self.assertEqual(me_response.json()["daily_token_limit"], 5_000)

        upgrade_response = self.client.post("/api/auth/me/demo-upgrade", json={}, headers=self.headers)
        self.assertEqual(upgrade_response.status_code, 200)
        self.assertEqual(upgrade_response.json()["subscription_tier"], "plus")
        self.assertEqual(upgrade_response.json()["daily_token_limit"], 20_000)
        self.assertEqual(upgrade_response.json()["daily_token_usage"], 0)

        second_upgrade = self.client.post("/api/auth/me/demo-upgrade", json={}, headers=self.headers)
        self.assertEqual(second_upgrade.status_code, 200)
        self.assertEqual(second_upgrade.json()["subscription_tier"], "pro")
        self.assertEqual(second_upgrade.json()["daily_token_limit"], 50_000)

    def test_parse_rejects_when_token_quota_is_already_exhausted_on_cloud_path(self) -> None:
        limit = QuotaService.get_daily_limit(SubscriptionTier.FREE)
        self._set_user_quota_state(
            usage=limit,
            last_reset_time=datetime.now(timezone.utc),
        )

        async def fake_invoke_structured_output(**kwargs):
            raise AssertionError("Runtime should not be called when quota is already exhausted.")

        runtime = type("FakeParseRuntime", (), {})()
        runtime.ainvoke_structured_output = AsyncMock(side_effect=fake_invoke_structured_output)

        with patch("app.services.parse_service.ParseService._get_runtime", return_value=runtime):
            response = self.client.post(
                "/api/parse/schedule-draft",
                json={"text": "明早8点到9点在三饭吃饭", "reference_time": "2026-03-27T10:00:00+08:00"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 429)
        body = response.json()
        self.assertEqual(body["detail"]["error_code"], "daily_token_quota_exceeded")
        self.assertEqual(body["detail"]["subscription_tier"], "free")
        self.assertEqual(body["detail"]["daily_token_usage"], limit)
        self.assertEqual(body["detail"]["daily_token_limit"], limit)

    def test_parse_uses_soft_limit_and_records_real_token_usage(self) -> None:
        limit = QuotaService.get_daily_limit(SubscriptionTier.FREE)
        self._set_user_quota_state(
            usage=limit - 120,
            last_reset_time=datetime.now(timezone.utc),
        )

        async def fake_invoke_structured_output(**kwargs):
            usage_callback = kwargs.get("usage_callback")
            if usage_callback is not None:
                usage_callback(TokenUsage(input_tokens=90, output_tokens=110, total_tokens=200))
            return ParseLLMOutput(
                title=ParseFieldUpdate(action="set", value="吃饭"),
                start_time=ParseFieldUpdate(action="set", value="2026-03-28T08:00:00+08:00"),
                end_time=ParseFieldUpdate(action="set", value="2026-03-28T09:00:00+08:00"),
                location=ParseFieldUpdate(action="set", value="三饭"),
                remark=ParseFieldUpdate(action="keep"),
                storage_strategy=ParseFieldUpdate(action="keep"),
            )

        runtime = type("FakeParseRuntime", (), {})()
        runtime.ainvoke_structured_output = AsyncMock(side_effect=fake_invoke_structured_output)

        with patch("app.services.parse_service.ParseService._get_runtime", return_value=runtime):
            response = self.client.post(
                "/api/parse/schedule-draft",
                json={"text": "明早8点到9点在三饭吃饭", "reference_time": "2026-03-27T10:00:00+08:00"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)

        with SessionLocal() as db:
            user = db.get(User, self.user_id)
            self.assertIsNotNone(user)
            assert user is not None
            self.assertEqual(user.daily_token_usage, limit + 80)
            events = list(db.query(AiUsageEvent).filter(AiUsageEvent.user_id == self.user_id).all())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].operation, "parse_llm")
            self.assertEqual(events[0].total_tokens, 200)

    def test_parse_local_fallback_is_not_blocked_by_cloud_quota(self) -> None:
        limit = QuotaService.get_daily_limit(SubscriptionTier.FREE)
        self._set_user_quota_state(
            usage=limit,
            last_reset_time=datetime.now(timezone.utc),
        )

        with patch("app.services.parse_service.ParseService._get_runtime", return_value=None):
            response = self.client.post(
                "/api/parse/schedule-draft",
                json={"text": "明早8点到9点在三饭吃饭", "reference_time": "2026-03-27T10:00:00+08:00"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)

        with SessionLocal() as db:
            user = db.get(User, self.user_id)
            self.assertIsNotNone(user)
            assert user is not None
            self.assertEqual(user.daily_token_usage, limit)
            event_count = db.query(AiUsageEvent).filter(AiUsageEvent.user_id == self.user_id).count()
            self.assertEqual(event_count, 0)

    def test_shanghai_day_window_reset_uses_local_day_even_with_utc_storage(self) -> None:
        with SessionLocal() as db:
            user = db.get(User, self.user_id)
            if user is None:
                raise AssertionError("Expected seeded user to exist.")
            user.daily_token_usage = 321
            user.last_reset_time = datetime.fromisoformat("2026-04-18T15:55:00+00:00")
            db.commit()
            db.refresh(user)

            snapshot = QuotaService.get_quota_snapshot(
                db,
                self.user_id,
                now=datetime.fromisoformat("2026-04-18T16:10:00+00:00"),
            )
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.daily_token_usage, 0)

            db.refresh(user)
            self.assertEqual(user.last_reset_time, datetime.fromisoformat("2026-04-18T16:10:00+00:00"))

    def test_rag_retrieve_records_query_embedding_tokens(self) -> None:
        async def fake_embed_query(text: str, **kwargs):
            usage_callback = kwargs.get("usage_callback")
            if usage_callback is not None:
                usage_callback(TokenUsage(input_tokens=64, total_tokens=64))
            return [0.04] * 3072

        runtime = type("FakeRagRuntime", (), {})()
        runtime.aembed_query = AsyncMock(side_effect=fake_embed_query)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            response = self.client.post(
                "/api/rag/retrieve",
                json={"query": "今天有什么安排？", "top_k": 3},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)

        with SessionLocal() as db:
            user = db.get(User, self.user_id)
            self.assertIsNotNone(user)
            assert user is not None
            self.assertEqual(user.daily_token_usage, 64)
            events = list(db.query(AiUsageEvent).filter(AiUsageEvent.user_id == self.user_id).all())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].operation, "rag_query_embedding")
            self.assertEqual(events[0].total_tokens, 64)

    def test_rag_rebuild_records_embedding_tokens(self) -> None:
        self._seed_rag_schedule_with_chunk()

        async def fake_embed_documents(texts: list[str], **kwargs):
            usage_callback = kwargs.get("usage_callback")
            if usage_callback is not None:
                usage_callback(TokenUsage(input_tokens=180, total_tokens=180))
            return [[0.05] * 3072 for _ in texts]

        runtime = type("FakeRagRuntime", (), {})()
        runtime.aembed_documents = AsyncMock(side_effect=fake_embed_documents)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            response = self.client.post(
                "/api/rag/chunks/rebuild-all",
                json={"chunk_size": 160},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)

        with SessionLocal() as db:
            user = db.get(User, self.user_id)
            self.assertIsNotNone(user)
            assert user is not None
            self.assertEqual(user.daily_token_usage, 180)
            events = list(db.query(AiUsageEvent).filter(AiUsageEvent.user_id == self.user_id).all())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].operation, "rag_rebuild_embedding")
            self.assertEqual(events[0].total_tokens, 180)

    def test_rag_answer_blocks_second_cloud_call_after_query_embedding_pushes_usage_over_limit(self) -> None:
        self._seed_rag_schedule_with_chunk()
        limit = QuotaService.get_daily_limit(SubscriptionTier.FREE)
        self._set_user_quota_state(
            usage=limit - 50,
            last_reset_time=datetime.now(timezone.utc),
        )

        async def fake_embed_query(text: str, **kwargs):
            usage_callback = kwargs.get("usage_callback")
            if usage_callback is not None:
                usage_callback(TokenUsage(input_tokens=80, total_tokens=80))
            return [0.06] * 3072

        def fake_astream_text(**kwargs):
            async def iterator():
                yield "不应该开始流式回答"

            return iterator()

        runtime = type("FakeRagRuntime", (), {})()
        runtime.aembed_query = AsyncMock(side_effect=fake_embed_query)
        runtime.astream_text = MagicMock(side_effect=fake_astream_text)

        with patch("app.services.rag_service.RagService._get_runtime", return_value=runtime):
            response = self.client.post(
                "/api/rag/answer/stream",
                json={"query": "今天有什么安排？", "top_k": 3},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 429)
        body = response.json()
        self.assertEqual(body["detail"]["error_code"], "daily_token_quota_exceeded")
        self.assertEqual(body["detail"]["daily_token_usage"], limit + 30)
        self.assertEqual(body["detail"]["daily_token_limit"], limit)

        with SessionLocal() as db:
            events = list(db.query(AiUsageEvent).filter(AiUsageEvent.user_id == self.user_id).all())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].operation, "rag_query_embedding")
            self.assertEqual(events[0].total_tokens, 80)


if __name__ == "__main__":
    unittest.main()

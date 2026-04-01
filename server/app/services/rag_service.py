from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import delete, select, text

from app.core.config import get_settings
from app.core.database import session_scope
from app.models import ChatHistory, KnowledgeBaseState, Schedule, VectorChunk
from app.models.enums import ChatRole
from app.schemas import (
    RagChunkBuildAllResponse,
    RagChunkBuildResponse,
    RagRetrievedChunk,
    RagRetrieveResponse,
)
from app.services.ai_runtime import AiRuntimeError, AiRuntimeUnavailable, LangChainAiRuntime


def _to_chunks(raw_text: str, chunk_size: int) -> list[str]:
    cleaned = " ".join(raw_text.split())
    if not cleaned:
        return []
    return [cleaned[index : index + chunk_size] for index in range(0, len(cleaned), chunk_size)]


def _mock_embedding(text: str, dimensions: int) -> list[float]:
    vector: list[float] = []
    salt = 0
    while len(vector) < dimensions:
        digest = hashlib.sha256(f"{text}:{salt}".encode("utf-8")).digest()
        salt += 1
        for index in range(0, len(digest), 4):
            if len(vector) >= dimensions:
                break
            segment = digest[index : index + 4]
            value = int.from_bytes(segment, byteorder="big", signed=False) / 4294967295
            vector.append(round(value, 6))
    return vector


@dataclass(frozen=True)
class RagScheduleSnapshot:
    id: int
    title: str
    location: str | None
    remark: str | None
    allow_rag_indexing: bool


@dataclass(frozen=True)
class ChunkWritePlan:
    schedule_id: int
    chunks: list[str]
    embeddings: list[list[float]]


@dataclass(frozen=True)
class PreparedRagAnswer:
    retrieved: RagRetrieveResponse
    answer_text: str


class RagService:
    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _get_runtime() -> LangChainAiRuntime | None:
        try:
            return LangChainAiRuntime.from_settings()
        except AiRuntimeUnavailable:
            return None

    @staticmethod
    def _snapshot_from_schedule(schedule: Schedule) -> RagScheduleSnapshot:
        return RagScheduleSnapshot(
            id=int(schedule.id),
            title=schedule.title,
            location=schedule.location,
            remark=schedule.remark,
            allow_rag_indexing=bool(schedule.allow_rag_indexing),
        )

    @staticmethod
    def _build_schedule_source_text(schedule: RagScheduleSnapshot) -> str:
        source_parts = [schedule.title]
        if schedule.location:
            source_parts.append(schedule.location)
        if schedule.remark:
            source_parts.append(schedule.remark)
        return " ".join(source_parts)

    @staticmethod
    async def _build_embedding(text_value: str, runtime: LangChainAiRuntime | None) -> list[float]:
        settings = get_settings()
        if runtime is None:
            return _mock_embedding(text_value, dimensions=settings.embedding_dimensions)
        try:
            return await runtime.aembed_query(text_value)
        except AiRuntimeError:
            return _mock_embedding(text_value, dimensions=settings.embedding_dimensions)

    @staticmethod
    async def _build_embeddings(
        texts: Iterable[str],
        runtime: LangChainAiRuntime | None,
    ) -> list[list[float]]:
        values = list(texts)
        settings = get_settings()
        if not values:
            return []
        if runtime is None:
            return [_mock_embedding(text_value, dimensions=settings.embedding_dimensions) for text_value in values]
        try:
            return await runtime.aembed_documents(values)
        except AiRuntimeError:
            return [_mock_embedding(text_value, dimensions=settings.embedding_dimensions) for text_value in values]

    @staticmethod
    def _record_rebuild_state(
        db,
        user_id: int,
        *,
        rebuilt_at: datetime,
        status: str,
        message: str,
        schedules_considered: int,
        schedules_indexed: int,
        chunks_created: int,
        embedding_dimensions: int,
    ) -> None:
        kb_state = db.scalar(select(KnowledgeBaseState).where(KnowledgeBaseState.user_id == user_id))
        if kb_state is None:
            kb_state = KnowledgeBaseState(user_id=user_id)
            db.add(kb_state)

        kb_state.last_rebuild_at = rebuilt_at
        kb_state.last_rebuild_status = status
        kb_state.last_rebuild_message = message
        kb_state.last_rebuild_schedules_considered = schedules_considered
        kb_state.last_rebuild_schedules_indexed = schedules_indexed
        kb_state.last_rebuild_chunks_created = chunks_created
        kb_state.embedding_dimensions = embedding_dimensions

    @staticmethod
    def _load_schedule_snapshot(user_id: int, schedule_id: int) -> RagScheduleSnapshot | None:
        with session_scope() as db:
            schedule = db.scalar(
                select(Schedule).where(
                    Schedule.id == schedule_id,
                    Schedule.user_id == user_id,
                    Schedule.is_deleted.is_(False),
                )
            )
            if schedule is None:
                return None
            return RagService._snapshot_from_schedule(schedule)

    @staticmethod
    def _load_rebuildable_schedule_snapshots(user_id: int) -> list[RagScheduleSnapshot]:
        with session_scope() as db:
            schedules = list(
                db.scalars(
                    select(Schedule)
                    .where(
                        Schedule.user_id == user_id,
                        Schedule.is_deleted.is_(False),
                        Schedule.allow_rag_indexing.is_(True),
                    )
                    .order_by(Schedule.updated_at.asc(), Schedule.id.asc())
                ).all()
            )
        return [RagService._snapshot_from_schedule(schedule) for schedule in schedules]

    @staticmethod
    def _write_rebuild(
        *,
        user_id: int,
        delete_all: bool,
        schedule_ids: list[int],
        plans: list[ChunkWritePlan],
        rebuilt_at: datetime,
        status: str,
        message: str,
        schedules_considered: int,
        schedules_indexed: int,
        chunks_created: int,
        embedding_dimensions: int,
    ) -> None:
        with session_scope() as db:
            if delete_all:
                db.execute(delete(VectorChunk).where(VectorChunk.user_id == user_id))
            elif schedule_ids:
                db.execute(
                    delete(VectorChunk).where(
                        VectorChunk.user_id == user_id,
                        VectorChunk.schedule_id.in_(schedule_ids),
                    )
                )

            for plan in plans:
                for chunk, embedding in zip(plan.chunks, plan.embeddings, strict=True):
                    db.add(
                        VectorChunk(
                            schedule_id=plan.schedule_id,
                            user_id=user_id,
                            content=chunk,
                            embedding=embedding,
                        )
                    )

            RagService._record_rebuild_state(
                db=db,
                user_id=user_id,
                rebuilt_at=rebuilt_at,
                status=status,
                message=message,
                schedules_considered=schedules_considered,
                schedules_indexed=schedules_indexed,
                chunks_created=chunks_created,
                embedding_dimensions=embedding_dimensions,
            )
            db.commit()

    @staticmethod
    def _query_retrieved_rows(user_id: int, query_vector: str, top_k: int):
        with session_scope() as db:
            return db.execute(
                text(
                    """
                    SELECT
                        vc.id,
                        vc.schedule_id,
                        vc.content,
                        GREATEST(
                            0.0,
                            1 - ((vc.embedding::halfvec(3072)) <=> CAST(:query_vector AS halfvec(3072)))
                        ) AS score
                    FROM vector_chunks AS vc
                    JOIN schedules AS s
                        ON s.id = vc.schedule_id
                    WHERE vc.user_id = :user_id
                      AND s.user_id = :user_id
                      AND s.is_deleted = FALSE
                      AND s.allow_rag_indexing = TRUE
                    ORDER BY (vc.embedding::halfvec(3072)) <=> CAST(:query_vector AS halfvec(3072))
                    LIMIT :top_k
                    """
                ),
                {
                    "query_vector": query_vector,
                    "user_id": user_id,
                    "top_k": top_k,
                },
            ).mappings().all()

    @staticmethod
    def _save_chat_turn(user_id: int, user_query: str, assistant_answer: str) -> None:
        with session_scope() as db:
            db.add(
                ChatHistory(
                    user_id=user_id,
                    role=ChatRole.USER,
                    content=user_query,
                )
            )
            db.add(
                ChatHistory(
                    user_id=user_id,
                    role=ChatRole.ASSISTANT,
                    content=assistant_answer,
                )
            )
            db.commit()

    @staticmethod
    async def rebuild_chunks_for_schedule(
        user_id: int,
        schedule_id: int,
        chunk_size: int,
    ) -> RagChunkBuildResponse | None:
        schedule = RagService._load_schedule_snapshot(user_id, schedule_id)
        if schedule is None:
            return None

        embedding_dimensions = get_settings().embedding_dimensions
        rebuilt_at = RagService._utcnow()

        if not schedule.allow_rag_indexing:
            message = "Schedule is not allowed to enter the knowledge base, so related chunks were removed."
            RagService._write_rebuild(
                user_id=user_id,
                delete_all=False,
                schedule_ids=[schedule.id],
                plans=[],
                rebuilt_at=rebuilt_at,
                status="success",
                message=message,
                schedules_considered=1,
                schedules_indexed=0,
                chunks_created=0,
                embedding_dimensions=embedding_dimensions,
            )
            return RagChunkBuildResponse(
                schedule_id=schedule_id,
                user_id=user_id,
                chunks_created=0,
                embedding_dimensions=embedding_dimensions,
                rebuilt_at=rebuilt_at,
                status="success",
                message=message,
            )

        chunks = _to_chunks(RagService._build_schedule_source_text(schedule), chunk_size=chunk_size)
        runtime = RagService._get_runtime()

        try:
            embeddings = await RagService._build_embeddings(chunks, runtime)
        except RuntimeError as exc:
            RagService._write_rebuild(
                user_id=user_id,
                delete_all=False,
                schedule_ids=[],
                plans=[],
                rebuilt_at=rebuilt_at,
                status="failed",
                message=str(exc),
                schedules_considered=1,
                schedules_indexed=0,
                chunks_created=0,
                embedding_dimensions=embedding_dimensions,
            )
            raise

        plans = [ChunkWritePlan(schedule_id=schedule.id, chunks=chunks, embeddings=embeddings)]
        schedules_indexed = 1 if chunks else 0
        chunks_created = len(chunks)
        message = f"Rebuilt 1 schedule, generated {chunks_created} chunks, embedding dimensions {embedding_dimensions}."
        RagService._write_rebuild(
            user_id=user_id,
            delete_all=False,
            schedule_ids=[schedule.id],
            plans=plans,
            rebuilt_at=rebuilt_at,
            status="success",
            message=message,
            schedules_considered=1,
            schedules_indexed=schedules_indexed,
            chunks_created=chunks_created,
            embedding_dimensions=embedding_dimensions,
        )
        return RagChunkBuildResponse(
            schedule_id=schedule_id,
            user_id=user_id,
            chunks_created=chunks_created,
            embedding_dimensions=embedding_dimensions,
            rebuilt_at=rebuilt_at,
            status="success",
            message=message,
        )

    @staticmethod
    async def rebuild_chunks_for_user(
        user_id: int,
        chunk_size: int,
    ) -> RagChunkBuildAllResponse:
        schedules = RagService._load_rebuildable_schedule_snapshots(user_id)
        embedding_dimensions = get_settings().embedding_dimensions
        rebuilt_at = RagService._utcnow()
        schedules_considered = len(schedules)
        runtime = RagService._get_runtime()

        try:
            plans: list[ChunkWritePlan] = []
            for schedule in schedules:
                chunks = _to_chunks(RagService._build_schedule_source_text(schedule), chunk_size=chunk_size)
                embeddings = await RagService._build_embeddings(chunks, runtime)
                plans.append(ChunkWritePlan(schedule_id=schedule.id, chunks=chunks, embeddings=embeddings))
        except RuntimeError as exc:
            RagService._write_rebuild(
                user_id=user_id,
                delete_all=False,
                schedule_ids=[],
                plans=[],
                rebuilt_at=rebuilt_at,
                status="failed",
                message=str(exc),
                schedules_considered=schedules_considered,
                schedules_indexed=0,
                chunks_created=0,
                embedding_dimensions=embedding_dimensions,
            )
            raise

        schedules_indexed = sum(1 for plan in plans if plan.chunks)
        chunks_created = sum(len(plan.chunks) for plan in plans)
        if schedules_considered == 0:
            message = "No eligible schedules were found for a knowledge-base rebuild."
        else:
            message = (
                f"Rebuilt {schedules_indexed} / {schedules_considered} schedules, "
                f"generated {chunks_created} chunks, embedding dimensions {embedding_dimensions}."
            )

        RagService._write_rebuild(
            user_id=user_id,
            delete_all=True,
            schedule_ids=[],
            plans=plans,
            rebuilt_at=rebuilt_at,
            status="success",
            message=message,
            schedules_considered=schedules_considered,
            schedules_indexed=schedules_indexed,
            chunks_created=chunks_created,
            embedding_dimensions=embedding_dimensions,
        )
        return RagChunkBuildAllResponse(
            user_id=user_id,
            schedules_considered=schedules_considered,
            schedules_indexed=schedules_indexed,
            chunks_created=chunks_created,
            embedding_dimensions=embedding_dimensions,
            rebuilt_at=rebuilt_at,
            status="success",
            message=message,
        )

    @staticmethod
    async def retrieve_chunks(
        user_id: int,
        query: str,
        top_k: int,
    ) -> RagRetrieveResponse:
        runtime = RagService._get_runtime()
        query_embedding = await RagService._build_embedding(query, runtime)
        query_vector = "[" + ",".join(f"{value:.6f}" for value in query_embedding) + "]"
        rows = RagService._query_retrieved_rows(user_id, query_vector, top_k)
        results = [
            RagRetrievedChunk(
                chunk_id=row["id"],
                schedule_id=row["schedule_id"],
                content=row["content"],
                score=round(float(row["score"]), 6),
            )
            for row in rows
        ]
        return RagRetrieveResponse(query=query, results=results)

    @staticmethod
    async def build_answer_text(query: str, retrieved: RagRetrieveResponse) -> str:
        if not retrieved.results:
            return (
                "No relevant schedule context was retrieved yet. "
                "Try rebuilding the knowledge base or ask a more specific question."
            )

        runtime = RagService._get_runtime()
        snippets = [
            {
                "schedule_id": item.schedule_id,
                "content": item.content,
                "score": item.score,
            }
            for item in retrieved.results[:5]
        ]
        if runtime is None:
            preview = "\n".join(f"- {item['content']}" for item in snippets)
            return f"Based on the currently retrieved schedule context, here are the most relevant notes:\n{preview}"

        try:
            return await runtime.ainvoke_text(
                system_prompt=(
                    "You are the knowledge-base answering service for a schedule app. "
                    "Answer only from the supplied schedule context. "
                    "If the context is insufficient, say what is missing."
                ),
                human_payload={
                    "query": query,
                    "schedule_context": snippets,
                },
                temperature=0.2,
            )
        except AiRuntimeError as exc:
            raise RuntimeError(str(exc)) from exc

    @staticmethod
    async def prepare_stream_answer(
        user_id: int,
        query: str,
        top_k: int,
    ) -> PreparedRagAnswer:
        retrieved = await RagService.retrieve_chunks(user_id=user_id, query=query, top_k=top_k)
        answer_text = await RagService.build_answer_text(query, retrieved)
        RagService._save_chat_turn(user_id, query, answer_text)
        return PreparedRagAnswer(retrieved=retrieved, answer_text=answer_text)

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ChatHistory, KnowledgeBaseState, Schedule, VectorChunk
from app.models.enums import ChatRole
from app.schemas import (
    RagChunkBuildAllResponse,
    RagChunkBuildResponse,
    RagRetrievedChunk,
    RagRetrieveResponse,
)
from app.services.llm_provider import LlmProviderError, OpenAICompatibleProvider


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


class RagService:
    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _resolve_provider() -> OpenAICompatibleProvider | None:
        try:
            return OpenAICompatibleProvider.from_settings()
        except LlmProviderError:
            return None

    @staticmethod
    def _build_embedding(text: str, provider: OpenAICompatibleProvider | None) -> list[float]:
        settings = get_settings()
        if provider is None:
            return _mock_embedding(text, dimensions=settings.embedding_dimensions)
        try:
            return provider.create_embedding(text)
        except LlmProviderError:
            return _mock_embedding(text, dimensions=settings.embedding_dimensions)

    @staticmethod
    def _build_embeddings(
        texts: Iterable[str],
        provider: OpenAICompatibleProvider | None,
    ) -> list[list[float]]:
        return [RagService._build_embedding(text, provider) for text in texts]

    @staticmethod
    def _build_schedule_source_text(schedule: Schedule) -> str:
        source_parts = [schedule.title]
        if schedule.location:
            source_parts.append(schedule.location)
        if schedule.remark:
            source_parts.append(schedule.remark)
        return " ".join(source_parts)

    @staticmethod
    def _replace_chunks_for_schedules(
        db: Session,
        user_id: int,
        schedules: list[Schedule],
        chunk_size: int,
    ) -> tuple[int, int]:
        schedule_ids = [schedule.id for schedule in schedules]
        if schedule_ids:
            db.execute(
                delete(VectorChunk).where(
                    VectorChunk.user_id == user_id,
                    VectorChunk.schedule_id.in_(schedule_ids),
                )
            )

        provider = RagService._resolve_provider()
        schedules_indexed = 0
        chunks_created = 0

        for schedule in schedules:
            chunks = _to_chunks(RagService._build_schedule_source_text(schedule), chunk_size=chunk_size)
            embeddings = RagService._build_embeddings(chunks, provider)
            if chunks:
                schedules_indexed += 1
            chunks_created += len(chunks)

            for chunk, embedding in zip(chunks, embeddings, strict=True):
                db.add(
                    VectorChunk(
                        schedule_id=schedule.id,
                        user_id=user_id,
                        content=chunk,
                        embedding=embedding,
                    )
                )

        return schedules_indexed, chunks_created

    @staticmethod
    def _replace_chunks_for_user(
        db: Session,
        user_id: int,
        schedules: list[Schedule],
        chunk_size: int,
    ) -> tuple[int, int]:
        db.execute(delete(VectorChunk).where(VectorChunk.user_id == user_id))
        return RagService._replace_chunks_for_schedules(
            db=db,
            user_id=user_id,
            schedules=schedules,
            chunk_size=chunk_size,
        )

    @staticmethod
    def _record_rebuild_state(
        db: Session,
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
        db.commit()

    @staticmethod
    def rebuild_chunks_for_schedule(
        db: Session,
        user_id: int,
        schedule_id: int,
        chunk_size: int,
    ) -> RagChunkBuildResponse | None:
        schedule = db.scalar(
            select(Schedule).where(
                Schedule.id == schedule_id,
                Schedule.user_id == user_id,
                Schedule.is_deleted.is_(False),
            )
        )
        if schedule is None:
            return None

        embedding_dimensions = get_settings().embedding_dimensions
        rebuilt_at = RagService._utcnow()

        if not schedule.allow_rag_indexing:
            db.execute(
                delete(VectorChunk).where(
                    VectorChunk.user_id == user_id,
                    VectorChunk.schedule_id == schedule.id,
                )
            )
            db.commit()
            message = "当前日程未允许纳入知识库索引。"
            RagService._record_rebuild_state(
                db=db,
                user_id=user_id,
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

        try:
            schedules_indexed, chunks_created = RagService._replace_chunks_for_schedules(
                db=db,
                user_id=user_id,
                schedules=[schedule],
                chunk_size=chunk_size,
            )
            db.commit()
        except RuntimeError as exc:
            db.rollback()
            RagService._record_rebuild_state(
                db=db,
                user_id=user_id,
                rebuilt_at=rebuilt_at,
                status="failed",
                message=str(exc),
                schedules_considered=1,
                schedules_indexed=0,
                chunks_created=0,
                embedding_dimensions=embedding_dimensions,
            )
            raise

        message = f"已重建 1 条日程，生成 {chunks_created} 个 chunks，向量维度 {embedding_dimensions}。"
        RagService._record_rebuild_state(
            db=db,
            user_id=user_id,
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
    def rebuild_chunks_for_user(
        db: Session,
        user_id: int,
        chunk_size: int,
    ) -> RagChunkBuildAllResponse:
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

        embedding_dimensions = get_settings().embedding_dimensions
        rebuilt_at = RagService._utcnow()
        schedules_considered = len(schedules)

        try:
            schedules_indexed, chunks_created = RagService._replace_chunks_for_user(
                db=db,
                user_id=user_id,
                schedules=schedules,
                chunk_size=chunk_size,
            )
            db.commit()
        except RuntimeError as exc:
            db.rollback()
            RagService._record_rebuild_state(
                db=db,
                user_id=user_id,
                rebuilt_at=rebuilt_at,
                status="failed",
                message=str(exc),
                schedules_considered=schedules_considered,
                schedules_indexed=0,
                chunks_created=0,
                embedding_dimensions=embedding_dimensions,
            )
            raise

        if schedules_considered == 0:
            message = "当前没有允许纳入知识库的云端日程。"
        else:
            message = (
                f"已重建 {schedules_indexed} / {schedules_considered} 条云端日程，"
                f"生成 {chunks_created} 个 chunks，向量维度 {embedding_dimensions}。"
            )

        RagService._record_rebuild_state(
            db=db,
            user_id=user_id,
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
    def retrieve_chunks(
        db: Session,
        user_id: int,
        query: str,
        top_k: int,
    ) -> RagRetrieveResponse:
        provider = RagService._resolve_provider()
        query_embedding = RagService._build_embedding(query, provider)
        query_vector = "[" + ",".join(f"{value:.6f}" for value in query_embedding) + "]"
        rows = db.execute(
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

        results = [
            RagRetrievedChunk(
                chunk_id=row.id,
                schedule_id=row.schedule_id,
                content=row.content,
                score=round(float(row.score), 6),
            )
            for row in rows
        ]
        return RagRetrieveResponse(query=query, results=results)

    @staticmethod
    def build_answer_text(query: str, retrieved: RagRetrieveResponse) -> str:
        if not retrieved.results:
            return "当前没有命中的知识库上下文。请先确认相关日程已 Push 到云端、允许纳入知识库，并已完成重建。"

        provider = RagService._resolve_provider()
        snippets = "\n".join(f"- {item.content}" for item in retrieved.results[:5])
        if provider is None:
            return f"已根据当前命中的日程上下文生成回答草案：\n{snippets}"

        prompt = (
            "Answer the user based only on the provided schedule context. "
            "If context is insufficient, say what is missing.\n\n"
            f"User query:\n{query}\n\n"
            f"Schedule context:\n{snippets}"
        )
        try:
            return provider.create_chat_completion(
                [
                    {"role": "system", "content": "You are a schedule assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        except LlmProviderError as exc:
            raise RuntimeError(str(exc)) from exc

    @staticmethod
    def save_chat_turn(db: Session, user_id: int, user_query: str, assistant_answer: str) -> None:
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

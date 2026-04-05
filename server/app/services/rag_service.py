from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def _normalize_chunk_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _split_long_segment(segment: str, chunk_size: int) -> list[str]:
    cleaned = _normalize_chunk_text(segment)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    words = cleaned.split(" ")
    if len(words) == 1:
        return [cleaned[index : index + chunk_size] for index in range(0, len(cleaned), chunk_size)]

    parts: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and len(candidate) > chunk_size:
            parts.append(current)
            current = word
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def _pack_segments(segments: list[str], chunk_size: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for segment in segments:
        for part in _split_long_segment(segment, chunk_size):
            candidate = part if not current else f"{current} | {part}"
            if current and len(candidate) > chunk_size:
                chunks.append(current)
                current = part
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


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
    start_time: datetime | None
    end_time: datetime | None
    location: str | None
    remark: str | None
    allow_rag_indexing: bool


@dataclass(frozen=True)
class ChunkWritePlan:
    schedule_id: int
    chunks: list[str]
    embeddings: list[list[float]]


@dataclass(frozen=True)
class RagSessionTurn:
    user_query: str
    assistant_answer: str
    created_at: datetime


@dataclass
class RagSessionState:
    session_id: str
    user_id: int
    turns: list[RagSessionTurn] = field(default_factory=list)
    updated_at: datetime | None = None


@dataclass(frozen=True)
class PreparedRagStream:
    retrieved: RagRetrieveResponse
    answer_candidates: list[dict[str, object]]
    session_id: str | None
    recent_turns: list[RagSessionTurn]
    retrieval_query: str


RAG_SESSION_TURN_WINDOW = 4
RAG_RETRIEVAL_CONTEXT_WINDOW = 2
SHORT_FOLLOW_UP_QUERY_LENGTH = 24
RAG_ANSWER_FETCH_MULTIPLIER = 3


class RagService:
    _sessions: dict[tuple[int, str], RagSessionState] = {}

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
    def _local_timezone() -> ZoneInfo:
        timezone_name = getattr(get_settings(), "app_timezone", "Asia/Shanghai")
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("Asia/Shanghai")

    @staticmethod
    def _to_local_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(RagService._local_timezone())

    @staticmethod
    def _local_date_text(value: datetime | None) -> str | None:
        local_dt = RagService._to_local_datetime(value)
        return None if local_dt is None else local_dt.strftime("%Y-%m-%d")

    @staticmethod
    def _local_time_text(value: datetime | None) -> str | None:
        local_dt = RagService._to_local_datetime(value)
        return None if local_dt is None else local_dt.strftime("%H:%M")

    @staticmethod
    def _local_range_text(start_time: datetime | None, end_time: datetime | None) -> str | None:
        local_start = RagService._to_local_datetime(start_time)
        local_end = RagService._to_local_datetime(end_time)
        if local_start is None:
            return None
        if local_end is None:
            return local_start.strftime("%Y-%m-%d %H:%M")
        return f"{local_start.strftime('%Y-%m-%d %H:%M')} -> {local_end.strftime('%Y-%m-%d %H:%M')}"

    @staticmethod
    def _snapshot_from_schedule(schedule: Schedule) -> RagScheduleSnapshot:
        return RagScheduleSnapshot(
            id=int(schedule.id),
            title=schedule.title,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            location=schedule.location,
            remark=schedule.remark,
            allow_rag_indexing=bool(schedule.allow_rag_indexing),
        )

    @staticmethod
    def _build_schedule_source_segments(schedule: RagScheduleSnapshot) -> list[str]:
        segments = [f"title {schedule.title}"]

        local_start_date = RagService._local_date_text(schedule.start_time)
        local_end_date = RagService._local_date_text(schedule.end_time)
        local_start_time = RagService._local_time_text(schedule.start_time)
        local_end_time = RagService._local_time_text(schedule.end_time)
        local_range = RagService._local_range_text(schedule.start_time, schedule.end_time)

        if local_start_date is not None:
            segments.append(f"date {local_start_date}")
        if local_start_time is not None:
            segments.append(f"start {local_start_time}")
        if local_end_date is not None and local_end_date != local_start_date:
            segments.append(f"end_date {local_end_date}")
        if local_end_time is not None:
            segments.append(f"end {local_end_time}")
        if local_range is not None:
            segments.append(f"time_range {local_range}")
        if schedule.location:
            segments.append(f"location {schedule.location}")
        if schedule.remark:
            segments.append(f"remark {_normalize_chunk_text(schedule.remark)}")

        return [segment for segment in segments if _normalize_chunk_text(segment)]

    @staticmethod
    def _build_schedule_source_text(schedule: RagScheduleSnapshot) -> str:
        return " | ".join(RagService._build_schedule_source_segments(schedule))

    @staticmethod
    def _build_schedule_chunks(schedule: RagScheduleSnapshot, chunk_size: int) -> list[str]:
        return _pack_segments(RagService._build_schedule_source_segments(schedule), chunk_size=chunk_size)

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
    def _load_schedule_snapshots_by_ids(user_id: int, schedule_ids: list[int]) -> dict[int, RagScheduleSnapshot]:
        if not schedule_ids:
            return {}
        with session_scope() as db:
            schedules = list(
                db.scalars(
                    select(Schedule).where(
                        Schedule.user_id == user_id,
                        Schedule.is_deleted.is_(False),
                        Schedule.id.in_(schedule_ids),
                    )
                ).all()
            )
        return {int(schedule.id): RagService._snapshot_from_schedule(schedule) for schedule in schedules}

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
    def _normalize_session_id(session_id: str | None) -> str | None:
        if session_id is None:
            return None
        normalized = session_id.strip()
        return normalized or None

    @staticmethod
    def _get_or_create_session(user_id: int, session_id: str) -> RagSessionState:
        key = (user_id, session_id)
        state = RagService._sessions.get(key)
        if state is None:
            state = RagSessionState(session_id=session_id, user_id=user_id, updated_at=RagService._utcnow())
            RagService._sessions[key] = state
        return state

    @staticmethod
    def _recent_session_turns(user_id: int, session_id: str | None) -> list[RagSessionTurn]:
        normalized = RagService._normalize_session_id(session_id)
        if normalized is None:
            return []
        state = RagService._sessions.get((user_id, normalized))
        if state is None:
            return []
        return list(state.turns[-RAG_SESSION_TURN_WINDOW:])

    @staticmethod
    def _append_session_turn(user_id: int, session_id: str | None, user_query: str, assistant_answer: str) -> None:
        normalized = RagService._normalize_session_id(session_id)
        if normalized is None:
            return
        state = RagService._get_or_create_session(user_id, normalized)
        state.turns.append(
            RagSessionTurn(
                user_query=user_query,
                assistant_answer=assistant_answer,
                created_at=RagService._utcnow(),
            )
        )
        state.turns = state.turns[-RAG_SESSION_TURN_WINDOW:]
        state.updated_at = RagService._utcnow()

    @staticmethod
    def _should_expand_retrieval_query(query: str, recent_turns: list[RagSessionTurn]) -> bool:
        compact_query = " ".join(query.split())
        return bool(recent_turns) and len(compact_query) <= SHORT_FOLLOW_UP_QUERY_LENGTH

    @staticmethod
    def _build_effective_retrieval_query(query: str, recent_turns: list[RagSessionTurn]) -> str:
        if not RagService._should_expand_retrieval_query(query, recent_turns):
            return query

        recent_context_parts = [query]
        for turn in recent_turns[-RAG_RETRIEVAL_CONTEXT_WINDOW:]:
            recent_context_parts.append(turn.user_query)
            if turn.assistant_answer:
                recent_context_parts.append(turn.assistant_answer[:240])
        return "\n".join(recent_context_parts)

    @staticmethod
    def _build_session_history_payload(recent_turns: list[RagSessionTurn]) -> list[dict[str, str]]:
        return [
            {
                "user_query": turn.user_query,
                "assistant_answer": turn.assistant_answer,
            }
            for turn in recent_turns
        ]

    @staticmethod
    def _build_answer_candidates(user_id: int, retrieved: RagRetrieveResponse) -> list[dict[str, object]]:
        grouped: dict[int, dict[str, object]] = {}
        for item in retrieved.results:
            existing = grouped.get(item.schedule_id)
            if existing is None:
                grouped[item.schedule_id] = {
                    "score": item.score,
                    "matched_snippets": [item.content],
                }
                continue
            existing["score"] = max(float(existing["score"]), item.score)
            snippets = existing["matched_snippets"]
            assert isinstance(snippets, list)
            if item.content not in snippets:
                snippets.append(item.content)

        schedule_ids = list(grouped.keys())
        snapshots = RagService._load_schedule_snapshots_by_ids(user_id, schedule_ids)

        candidates: list[dict[str, object]] = []
        for schedule_id in schedule_ids:
            snapshot = snapshots.get(schedule_id)
            if snapshot is None:
                continue
            group = grouped[schedule_id]
            local_start = RagService._to_local_datetime(snapshot.start_time)
            local_end = RagService._to_local_datetime(snapshot.end_time)
            candidate = {
                "schedule_id": schedule_id,
                "score": round(float(group["score"]), 6),
                "title": snapshot.title,
                "start_local_iso": None if local_start is None else local_start.isoformat(timespec="minutes"),
                "end_local_iso": None if local_end is None else local_end.isoformat(timespec="minutes"),
                "date": RagService._local_date_text(snapshot.start_time),
                "start_time": RagService._local_time_text(snapshot.start_time),
                "end_time": RagService._local_time_text(snapshot.end_time),
                "time_range": RagService._local_range_text(snapshot.start_time, snapshot.end_time),
                "location": snapshot.location,
                "remark": _normalize_chunk_text(snapshot.remark or "") or None,
                "matched_snippets": list(group["matched_snippets"])[:2],
            }
            candidates.append(candidate)
        return candidates

    @staticmethod
    def _build_schedule_preview(candidate: dict[str, object]) -> str:
        preview_parts = [f"title={candidate['title']}"]
        if candidate.get("date"):
            preview_parts.append(f"date={candidate['date']}")
        if candidate.get("time_range"):
            preview_parts.append(f"time_range={candidate['time_range']}")
        if candidate.get("location"):
            preview_parts.append(f"location={candidate['location']}")
        if candidate.get("remark"):
            preview_parts.append(f"remark={candidate['remark']}")
        return ", ".join(preview_parts)

    @staticmethod
    def _fallback_answer_text(answer_candidates: list[dict[str, object]]) -> str:
        if not answer_candidates:
            return (
                "No relevant schedule context was retrieved yet. "
                "Try rebuilding the knowledge base or ask a more specific question."
            )

        preview = "\n".join(f"- {RagService._build_schedule_preview(candidate)}" for candidate in answer_candidates)
        return f"Based on the current schedule candidates, here are the strongest matches:\n{preview}"

    @staticmethod
    def finalize_stream_answer(
        user_id: int,
        user_query: str,
        chunks: list[str],
        *,
        session_id: str | None = None,
    ) -> str:
        answer_text = "".join(chunks).strip()
        if answer_text:
            RagService._save_chat_turn(user_id, user_query, answer_text)
            RagService._append_session_turn(user_id, session_id, user_query, answer_text)
        return answer_text

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

        chunks = RagService._build_schedule_chunks(schedule, chunk_size=chunk_size)
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
                chunks = RagService._build_schedule_chunks(schedule, chunk_size=chunk_size)
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
    async def build_answer_text(
        user_id: int,
        query: str,
        retrieved: RagRetrieveResponse,
        *,
        recent_turns: list[RagSessionTurn] | None = None,
    ) -> str:
        answer_candidates = RagService._build_answer_candidates(user_id, retrieved)
        if not answer_candidates:
            return RagService._fallback_answer_text(answer_candidates)

        runtime = RagService._get_runtime()
        if runtime is None:
            return RagService._fallback_answer_text(answer_candidates)

        human_payload: dict[str, object] = {
            "query": query,
            "schedule_candidates": answer_candidates,
        }
        if recent_turns:
            human_payload["session_history"] = RagService._build_session_history_payload(recent_turns)

        try:
            return await runtime.ainvoke_text(
                system_prompt=(
                    "You are the knowledge-base answering service for a schedule app. "
                    "Answer only from the supplied schedule_candidates. "
                    "Each candidate is already normalized to the user's local time. "
                    "For earliest/latest/date/time questions, compare the candidates before answering. "
                    "If the context is insufficient, say exactly which fact is missing. "
                    "If session_history is provided, use it only to resolve references in the current query."
                ),
                human_payload=human_payload,
                temperature=0.2,
            )
        except AiRuntimeError as exc:
            raise RuntimeError(str(exc)) from exc

    @staticmethod
    async def stream_answer_text(
        query: str,
        answer_candidates: list[dict[str, object]],
        *,
        recent_turns: list[RagSessionTurn] | None = None,
    ) -> AsyncIterator[str]:
        runtime = RagService._get_runtime()
        if runtime is None or not answer_candidates:
            yield RagService._fallback_answer_text(answer_candidates)
            return

        human_payload: dict[str, object] = {
            "query": query,
            "schedule_candidates": answer_candidates,
        }
        if recent_turns:
            human_payload["session_history"] = RagService._build_session_history_payload(recent_turns)
        try:
            async for chunk in runtime.astream_text(
                system_prompt=(
                    "You are the knowledge-base answering service for a schedule app. "
                    "Answer only from the supplied schedule_candidates. "
                    "The candidates are already deduplicated by schedule and normalized to the user's local time. "
                    "For earliest/latest/date/time questions, identify the relevant candidates first, compare their local time fields, and then answer. "
                    "If multiple candidates satisfy the query, say so clearly. "
                    "If the context is insufficient, say exactly which fact is missing. "
                    "If session_history is provided, use it only to resolve references in the current query. "
                    "Do not answer from session_history alone."
                ),
                human_payload=human_payload,
                temperature=0.2,
            ):
                if chunk:
                    yield chunk
        except AiRuntimeError as exc:
            raise RuntimeError(str(exc)) from exc

    @staticmethod
    async def prepare_stream_answer(
        user_id: int,
        query: str,
        top_k: int,
        *,
        session_id: str | None = None,
    ) -> PreparedRagStream:
        normalized_session_id = RagService._normalize_session_id(session_id)
        recent_turns = RagService._recent_session_turns(user_id, normalized_session_id)
        retrieval_query = RagService._build_effective_retrieval_query(query, recent_turns)
        retrieved = await RagService.retrieve_chunks(
            user_id=user_id,
            query=retrieval_query,
            top_k=max(top_k, top_k * RAG_ANSWER_FETCH_MULTIPLIER),
        )
        answer_candidates = RagService._build_answer_candidates(user_id, retrieved)
        return PreparedRagStream(
            retrieved=retrieved,
            answer_candidates=answer_candidates,
            session_id=normalized_session_id,
            recent_turns=recent_turns,
            retrieval_query=retrieval_query,
        )

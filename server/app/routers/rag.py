from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id_ai_safe
from app.core.database import get_db
from app.schemas import (
    RagChunkBuildAllResponse,
    RagChunkBuildRequest,
    RagChunkBuildResponse,
    RagRetrieveRequest,
    RagRetrieveResponse,
    RagStreamAnswerRequest,
)
from app.services import QuotaService, RagService
from app.services.quota_service import QuotaExceededError

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/chunks/rebuild/{schedule_id}", response_model=RagChunkBuildResponse, status_code=status.HTTP_200_OK)
async def rebuild_schedule_chunks(
    schedule_id: int,
    payload: RagChunkBuildRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> RagChunkBuildResponse:
    def ensure_quota() -> None:
        QuotaService.ensure_token_quota_available(db, user_id)

    def record_usage(usage) -> None:
        QuotaService.record_token_usage(db, user_id, operation="rag_rebuild_embedding", usage=usage)

    try:
        result = await RagService.rebuild_chunks_for_schedule(
            user_id=user_id,
            schedule_id=schedule_id,
            chunk_size=payload.chunk_size,
            before_ai_call=ensure_quota,
            usage_callback=record_usage,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    return result


@router.post("/chunks/rebuild-all", response_model=RagChunkBuildAllResponse, status_code=status.HTTP_200_OK)
async def rebuild_all_chunks(
    payload: RagChunkBuildRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> RagChunkBuildAllResponse:
    def ensure_quota() -> None:
        QuotaService.ensure_token_quota_available(db, user_id)

    def record_usage(usage) -> None:
        QuotaService.record_token_usage(db, user_id, operation="rag_rebuild_embedding", usage=usage)

    try:
        return await RagService.rebuild_chunks_for_user(
            user_id=user_id,
            chunk_size=payload.chunk_size,
            before_ai_call=ensure_quota,
            usage_callback=record_usage,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/retrieve", response_model=RagRetrieveResponse, status_code=status.HTTP_200_OK)
async def retrieve_chunks(
    payload: RagRetrieveRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> RagRetrieveResponse:
    def ensure_quota() -> None:
        QuotaService.ensure_token_quota_available(db, user_id)

    def record_usage(usage) -> None:
        QuotaService.record_token_usage(db, user_id, operation="rag_query_embedding", usage=usage)

    try:
        return await RagService.retrieve_chunks(
            user_id=user_id,
            query=payload.query,
            top_k=payload.top_k,
            before_ai_call=ensure_quota,
            usage_callback=record_usage,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _raise_quota_http_error(exc: QuotaExceededError) -> None:
    raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.to_http_detail()) from exc


@router.post("/answer/stream", status_code=status.HTTP_200_OK)
async def stream_answer(
    payload: RagStreamAnswerRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> StreamingResponse:
    def ensure_retrieval_quota() -> None:
        QuotaService.ensure_token_quota_available(db, user_id)

    def record_retrieval_usage(usage) -> None:
        QuotaService.record_token_usage(db, user_id, operation="rag_query_embedding", usage=usage)

    def record_answer_usage(usage) -> None:
        QuotaService.record_token_usage(db, user_id, operation="rag_answer_llm", usage=usage)

    try:
        prepared = await RagService.prepare_stream_answer(
            user_id=user_id,
            query=payload.query,
            top_k=payload.top_k,
            session_id=payload.session_id,
            before_retrieval_call=ensure_retrieval_quota,
            retrieval_usage_callback=record_retrieval_usage,
        )
        if prepared.answer_candidates and RagService._get_runtime() is not None:
            QuotaService.ensure_token_quota_available(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except QuotaExceededError as exc:
        _raise_quota_http_error(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    async def event_iterator():
        yield _sse_event("meta", {"retrieved_chunks": len(prepared.retrieved.results)})
        collected_chunks: list[str] = []
        completion_message = "stream_completed"

        try:
            async for chunk in RagService.stream_answer_text(
                payload.query,
                prepared.answer_candidates,
                recent_turns=prepared.recent_turns,
                usage_callback=record_answer_usage,
            ):
                collected_chunks.append(chunk)
                yield _sse_event("token", {"text": chunk})
            RagService.finalize_stream_answer(
                user_id,
                payload.query,
                collected_chunks,
                session_id=prepared.session_id,
            )
        except RuntimeError:
            completion_message = "stream_failed"
        except LookupError:
            completion_message = "stream_failed"

        yield _sse_event("done", {"message": completion_message})

    return StreamingResponse(event_iterator(), media_type="text/event-stream")

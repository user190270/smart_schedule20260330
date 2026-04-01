from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.auth import get_current_user_id_ai_safe
from app.schemas import (
    RagChunkBuildAllResponse,
    RagChunkBuildRequest,
    RagChunkBuildResponse,
    RagRetrieveRequest,
    RagRetrieveResponse,
    RagStreamAnswerRequest,
)
from app.services import RagService

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/chunks/rebuild/{schedule_id}", response_model=RagChunkBuildResponse, status_code=status.HTTP_200_OK)
async def rebuild_schedule_chunks(
    schedule_id: int,
    payload: RagChunkBuildRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> RagChunkBuildResponse:
    try:
        result = await RagService.rebuild_chunks_for_schedule(
            user_id=user_id,
            schedule_id=schedule_id,
            chunk_size=payload.chunk_size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    return result


@router.post("/chunks/rebuild-all", response_model=RagChunkBuildAllResponse, status_code=status.HTTP_200_OK)
async def rebuild_all_chunks(
    payload: RagChunkBuildRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> RagChunkBuildAllResponse:
    try:
        return await RagService.rebuild_chunks_for_user(
            user_id=user_id,
            chunk_size=payload.chunk_size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/retrieve", response_model=RagRetrieveResponse, status_code=status.HTTP_200_OK)
async def retrieve_chunks(
    payload: RagRetrieveRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> RagRetrieveResponse:
    try:
        return await RagService.retrieve_chunks(
            user_id=user_id,
            query=payload.query,
            top_k=payload.top_k,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/answer/stream", status_code=status.HTTP_200_OK)
async def stream_answer(
    payload: RagStreamAnswerRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> StreamingResponse:
    try:
        prepared = await RagService.prepare_stream_answer(
            user_id=user_id,
            query=payload.query,
            top_k=payload.top_k,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    def event_iterator():
        yield _sse_event("meta", {"retrieved_chunks": len(prepared.retrieved.results)})
        for token in prepared.answer_text.split():
            yield _sse_event("token", {"text": token})
        yield _sse_event("done", {"message": "stream_completed"})

    return StreamingResponse(event_iterator(), media_type="text/event-stream")

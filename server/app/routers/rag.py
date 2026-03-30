from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
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
def rebuild_schedule_chunks(
    schedule_id: int,
    payload: RagChunkBuildRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> RagChunkBuildResponse:
    try:
        result = RagService.rebuild_chunks_for_schedule(
            db=db,
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
def rebuild_all_chunks(
    payload: RagChunkBuildRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> RagChunkBuildAllResponse:
    try:
        return RagService.rebuild_chunks_for_user(
            db=db,
            user_id=user_id,
            chunk_size=payload.chunk_size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/retrieve", response_model=RagRetrieveResponse, status_code=status.HTTP_200_OK)
def retrieve_chunks(
    payload: RagRetrieveRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> RagRetrieveResponse:
    try:
        return RagService.retrieve_chunks(
            db=db,
            user_id=user_id,
            query=payload.query,
            top_k=payload.top_k,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/answer/stream", status_code=status.HTTP_200_OK)
def stream_answer(
    payload: RagStreamAnswerRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> StreamingResponse:
    try:
        retrieved = RagService.retrieve_chunks(
            db=db,
            user_id=user_id,
            query=payload.query,
            top_k=payload.top_k,
        )
        answer_text = RagService.build_answer_text(payload.query, retrieved)
        RagService.save_chat_turn(
            db=db,
            user_id=user_id,
            user_query=payload.query,
            assistant_answer=answer_text,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    def event_iterator():
        yield _sse_event("meta", {"retrieved_chunks": len(retrieved.results)})
        for token in answer_text.split(" "):
            yield _sse_event("token", {"text": token})
        yield _sse_event("done", {"message": "stream_completed"})

    return StreamingResponse(event_iterator(), media_type="text/event-stream")

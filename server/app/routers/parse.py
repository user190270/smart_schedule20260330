from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.auth import get_current_user_id_ai_safe
from app.schemas import (
    ParseDraftRequest,
    ParseDraftResponse,
    ParseSessionCreateRequest,
    ParseSessionDraftPatchRequest,
    ParseSessionMessageRequest,
    ParseSessionResponse,
)
from app.services import ParseService

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("/schedule-draft", response_model=ParseDraftResponse, status_code=status.HTTP_200_OK)
async def parse_schedule_draft(
    payload: ParseDraftRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> ParseDraftResponse:
    try:
        return await ParseService.build_schedule_draft(payload, user_id=user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/schedule-draft/stream", status_code=status.HTTP_200_OK)
async def parse_schedule_draft_stream(
    payload: ParseDraftRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> StreamingResponse:
    try:
        draft_response = await ParseService.build_schedule_draft(payload, user_id=user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    def event_iterator():
        draft_payload = draft_response.model_dump(mode="json")
        yield _sse_event("draft", draft_payload)

        follow_ups = ParseService.build_follow_up_questions(draft_response.missing_fields)
        for follow_up in follow_ups:
            yield _sse_event("follow_up", follow_up)

        yield _sse_event(
            "done",
            {
                "missing_fields": draft_response.missing_fields,
                "follow_up_questions": [item.model_dump(mode="json") for item in draft_response.follow_up_questions],
                "requires_human_review": draft_response.requires_human_review,
            },
        )

    return StreamingResponse(event_iterator(), media_type="text/event-stream")


@router.post("/sessions", response_model=ParseSessionResponse, status_code=status.HTTP_200_OK)
async def create_parse_session(
    payload: ParseSessionCreateRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> ParseSessionResponse:
    try:
        return await ParseService.create_session(payload, user_id=user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/messages", response_model=ParseSessionResponse, status_code=status.HTTP_200_OK)
async def append_parse_session_message(
    session_id: str,
    payload: ParseSessionMessageRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> ParseSessionResponse:
    try:
        return await ParseService.append_session_message(session_id, payload, user_id=user_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parse session not found.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.patch("/sessions/{session_id}/draft", response_model=ParseSessionResponse, status_code=status.HTTP_200_OK)
async def patch_parse_session_draft(
    session_id: str,
    payload: ParseSessionDraftPatchRequest,
    user_id: int = Depends(get_current_user_id_ai_safe),
) -> ParseSessionResponse:
    try:
        return await ParseService.patch_session_draft(session_id, payload, user_id=user_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parse session not found.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

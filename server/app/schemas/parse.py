from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ScheduleSource


ScheduleStorageStrategy = Literal[
    "local_only",
    "sync_to_cloud",
    "sync_to_cloud_and_knowledge",
]
ParseAgentAction = Literal["ask_follow_up", "finalize_draft"]
ParseAgentToolName = Literal["update_draft", "ask_follow_up", "finalize_draft", "save_schedule_to_local"]
ParseAgentMessageRole = Literal["user", "assistant"]


class ParseDraftRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    reference_time: datetime | None = None


class ScheduleDraft(BaseModel):
    title: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = None
    remark: str | None = None
    source: ScheduleSource = ScheduleSource.AI_PARSED
    storage_strategy: ScheduleStorageStrategy | None = None


class ScheduleDraftPatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    remark: str | None = None
    storage_strategy: ScheduleStorageStrategy | None = None


class ParseFollowUpQuestion(BaseModel):
    field: str
    question: str


class ParseDraftResponse(BaseModel):
    draft: ScheduleDraft
    missing_fields: list[str]
    follow_up_questions: list[ParseFollowUpQuestion] = Field(default_factory=list)
    requires_human_review: bool = True
    can_persist_directly: bool = False


class ParseSessionCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    reference_time: datetime | None = None


class ParseSessionMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    reference_time: datetime | None = None


class ParseSessionDraftPatchRequest(BaseModel):
    draft: ScheduleDraftPatch


class ParseAgentMessage(BaseModel):
    id: str
    role: ParseAgentMessageRole
    content: str


class ParseAgentToolCall(BaseModel):
    name: ParseAgentToolName
    summary: str


class ParseSessionResponse(BaseModel):
    parse_session_id: str
    messages: list[ParseAgentMessage]
    draft: ScheduleDraft
    missing_fields: list[str]
    follow_up_questions: list[ParseFollowUpQuestion] = Field(default_factory=list)
    ready_for_confirm: bool
    next_action: ParseAgentAction
    tool_calls: list[ParseAgentToolCall] = Field(default_factory=list)
    latest_assistant_message: str | None = None
    draft_visible: bool = False

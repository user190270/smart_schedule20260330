from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ScheduleSource
from app.schemas.schedule import ALLOWED_EMAIL_REMINDER_MINUTES, ScheduleRead


class SyncScheduleRecord(BaseModel):
    id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    start_time: datetime
    end_time: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    remark: str | None = None
    source: ScheduleSource = ScheduleSource.MANUAL
    updated_at: datetime
    allow_rag_indexing: bool = False
    email_reminder_enabled: bool = False
    email_remind_before_minutes: int | None = None
    is_deleted: bool = False

    @model_validator(mode="after")
    def validate_time_range(self) -> "SyncScheduleRecord":
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        if self.email_reminder_enabled:
            if self.email_remind_before_minutes not in ALLOWED_EMAIL_REMINDER_MINUTES:
                raise ValueError("email_remind_before_minutes must be one of 0, 1, 5, 10, 30")
        elif self.email_remind_before_minutes is not None:
            raise ValueError("email_remind_before_minutes requires email_reminder_enabled=true")
        return self


class SyncPushRequest(BaseModel):
    records: list[SyncScheduleRecord] = Field(default_factory=list)


class SyncPushResultItem(BaseModel):
    schedule_id: int
    status: Literal["created", "updated", "ignored"]
    reason: str | None = None


class SyncPushResponse(BaseModel):
    results: list[SyncPushResultItem]


class SyncPullResponse(BaseModel):
    records: list[ScheduleRead]


class SyncStatusResponse(BaseModel):
    cloud_schedule_count: int
    knowledge_base_eligible_schedule_count: int
    indexed_schedule_count: int
    indexed_chunk_count: int
    last_knowledge_rebuild_at: datetime | None = None
    last_knowledge_rebuild_status: Literal["idle", "success", "failed"] = "idle"
    last_knowledge_rebuild_message: str | None = None
    last_knowledge_rebuild_schedules_considered: int = 0
    last_knowledge_rebuild_schedules_indexed: int = 0
    last_knowledge_rebuild_chunks_created: int = 0
    embedding_dimensions: int
    cloud_connection_status: Literal["connected"] = "connected"


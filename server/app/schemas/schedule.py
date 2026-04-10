from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ScheduleSource

ALLOWED_EMAIL_REMINDER_MINUTES = {0, 1, 5, 10, 30}


class ScheduleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_time: datetime
    end_time: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    remark: str | None = None
    source: ScheduleSource = ScheduleSource.MANUAL
    confirmed_by_user: bool = False
    allow_rag_indexing: bool = False
    email_reminder_enabled: bool = False
    email_remind_before_minutes: int | None = Field(default=None)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleCreate":
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        if self.email_reminder_enabled:
            if self.email_remind_before_minutes not in ALLOWED_EMAIL_REMINDER_MINUTES:
                raise ValueError("email_remind_before_minutes must be one of 0, 1, 5, 10, 30")
        elif self.email_remind_before_minutes is not None:
            raise ValueError("email_remind_before_minutes requires email_reminder_enabled=true")
        return self


class ScheduleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    remark: str | None = None
    source: ScheduleSource | None = None
    allow_rag_indexing: bool | None = None
    email_reminder_enabled: bool | None = None
    email_remind_before_minutes: int | None = None
    is_deleted: bool | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleUpdate":
        if self.start_time is not None and self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        if self.email_reminder_enabled is True:
            if self.email_remind_before_minutes not in ALLOWED_EMAIL_REMINDER_MINUTES:
                raise ValueError("email_remind_before_minutes must be one of 0, 1, 5, 10, 30")
        elif self.email_reminder_enabled is False and self.email_remind_before_minutes is not None:
            raise ValueError("email_remind_before_minutes requires email_reminder_enabled=true")
        return self


class ScheduleRead(BaseModel):
    id: int
    user_id: int
    title: str
    start_time: datetime
    end_time: datetime | None
    location: str | None
    remark: str | None
    source: ScheduleSource
    updated_at: datetime
    allow_rag_indexing: bool
    email_reminder_enabled: bool
    email_remind_before_minutes: int | None
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)

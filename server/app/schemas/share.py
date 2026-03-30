from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ScheduleSource


class ShareScheduleDTO(BaseModel):
    id: int
    title: str
    start_time: datetime
    end_time: datetime | None
    location: str | None
    remark: str | None
    source: ScheduleSource
    updated_at: datetime
    is_deleted: bool


class ShareCreateResponse(BaseModel):
    share_uuid: str
    share_path: str
    schedule: ShareScheduleDTO


from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class UserAdminView(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    daily_token_usage: int
    last_reset_time: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAdminUpdateRequest(BaseModel):
    is_active: bool | None = None
    reset_quota: bool = False

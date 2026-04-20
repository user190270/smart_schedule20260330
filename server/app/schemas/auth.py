from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SubscriptionTier, UserRole


class UserPublic(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    notification_email: str | None = None
    subscription_tier: SubscriptionTier
    daily_token_usage: int
    daily_token_limit: int

    model_config = ConfigDict(from_attributes=True)


class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class AuthTokenResponse(BaseModel):
    user: UserPublic
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserProfileUpdateRequest(BaseModel):
    notification_email: str | None = Field(default=None, max_length=320)

    @field_validator("notification_email")
    @classmethod
    def normalize_notification_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if "@" not in normalized:
            raise ValueError("notification_email must be a valid email address")
        return normalized


class DemoUpgradeRequest(BaseModel):
    target_tier: SubscriptionTier | None = None

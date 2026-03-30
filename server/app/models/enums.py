from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class ScheduleSource(str, Enum):
    MANUAL = "manual"
    AI_PARSED = "ai_parsed"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

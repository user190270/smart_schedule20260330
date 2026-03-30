from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RagChunkBuildRequest(BaseModel):
    chunk_size: int = Field(default=120, ge=20, le=2000)


class RagChunkBuildResponse(BaseModel):
    schedule_id: int
    user_id: int
    chunks_created: int
    embedding_dimensions: int
    rebuilt_at: datetime
    status: Literal["success"] = "success"
    message: str | None = None


class RagChunkBuildAllResponse(BaseModel):
    user_id: int
    schedules_considered: int
    schedules_indexed: int
    chunks_created: int
    embedding_dimensions: int
    rebuilt_at: datetime
    status: Literal["success"] = "success"
    message: str | None = None


class RagRetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=20)


class RagRetrievedChunk(BaseModel):
    chunk_id: int
    schedule_id: int
    content: str
    score: float


class RagRetrieveResponse(BaseModel):
    query: str
    results: list[RagRetrievedChunk]


class RagStreamAnswerRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=20)

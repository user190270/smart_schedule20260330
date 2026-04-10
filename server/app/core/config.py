from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def _default_database_url() -> str:
    return "postgresql+psycopg://smart_schedule:smart_schedule@localhost:5432/smart_schedule"


class Settings(BaseSettings):
    app_name: str = "Smart Schedule MVP"
    environment: str = "dev"
    debug: bool = True
    api_prefix: str = "/api"
    postgres_db: str = "smart_schedule"
    postgres_user: str = "smart_schedule"
    postgres_password: str = "smart_schedule"
    database_url: str = _default_database_url()
    embedding_dimensions: int = 3072
    app_timezone: str = "Asia/Shanghai"
    sqlalchemy_echo: bool = False
    jwt_secret_key: str = token_urlsafe(48)
    jwt_access_token_expire_minutes: int = 120
    cors_allow_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.1.101:5173",
        "http://localhost",
        "https://localhost",
        "capacitor://localhost",
    ]
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_chat_model: str | None = "gemini-2.5-flash"
    llm_embedding_model: str | None = "gemini-embedding-001"
    mail_provider: str | None = None
    mail_api_key: str | None = None
    mail_from_address: str | None = None
    mail_from_name: str = "Smart Schedule"
    mail_scan_enabled: bool = True
    mail_scan_interval_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production", "false", "0", "off"}:
                return False
            if lowered in {"debug", "dev", "development", "true", "1", "on"}:
                return True
        return value

    @field_validator("jwt_access_token_expire_minutes")
    @classmethod
    def validate_expire_minutes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("jwt_access_token_expire_minutes must be greater than 0")
        return value

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("embedding_dimensions must be greater than 0")
        return value

    @field_validator("mail_scan_interval_seconds")
    @classmethod
    def validate_mail_scan_interval_seconds(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("mail_scan_interval_seconds must be greater than 0")
        return value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def normalize_cors_allow_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

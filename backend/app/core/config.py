from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./quiz_pass.db"
    jwt_secret_key: str = "change-me"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 14
    frontend_base_url: str = "http://localhost:5173"
    email_verify_token_expire_hours: int = 24
    password_reset_token_expire_minutes: int = 30
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    ai_config_encryption_key: str = ""
    upload_max_mb: int = 10
    ai_max_text_chars: int = 30000
    cors_origins: Annotated[list[str], NoDecode] = ["*"]
    redis_url: str = "redis://localhost:6379/0"
    ai_workflow_queue_name: str = "ai-generation"
    ai_workflow_execution_mode: str = "background_tasks"
    ai_workflow_worker_count: int = 1

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

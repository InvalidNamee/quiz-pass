from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AIProviderConfigCreate(BaseModel):
    name: str = Field(default="", max_length=128)
    api_base_url: str = Field(min_length=1, max_length=512)
    api_key: str = Field(min_length=1, max_length=2048)
    model: str = Field(min_length=1, max_length=128)
    is_default: bool = False


class AIProviderConfigUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    api_base_url: str | None = Field(default=None, min_length=1, max_length=512)
    api_key: str | None = Field(default=None, min_length=1, max_length=2048)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    is_default: bool | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class AIProviderConfigOut(BaseModel):
    id: int
    name: str
    api_base_url: str
    model: str
    is_default: bool
    is_active: bool
    has_api_key: bool = True
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIGenerationBankJobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    desired_visibility: str = Field(default="private", pattern="^(private|public)$")
    ai_provider_config_id: int | None = None
    prompt_template_id: int | None = None
    question_count_mode: str = Field(default="fixed", pattern="^(fixed|adaptive)$")
    question_count: int | None = Field(default=10, ge=1, le=100)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")


class ImportJobOut(BaseModel):
    id: int
    user_id: int
    bank_id: int | None
    type: str
    status: str
    desired_visibility: str
    file_name: str | None
    ai_model_snapshot: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIGenerationBankJobOut(BaseModel):
    bank_id: int
    job_id: int

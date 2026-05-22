from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AIProviderConfigCreate(BaseModel):
    name: str = Field(default="", max_length=128)
    api_base_url: str = Field(min_length=1, max_length=512)
    api_key: str = Field(min_length=1, max_length=2048)
    model: str = Field(min_length=1, max_length=128)
    response_format_type: str = Field(default="json_object", pattern="^(json_object|json_schema)$")
    is_default: bool = False


class AIProviderConfigUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    api_base_url: str | None = Field(default=None, min_length=1, max_length=512)
    api_key: str | None = Field(default=None, min_length=1, max_length=2048)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    response_format_type: str | None = Field(default=None, pattern="^(json_object|json_schema)$")
    is_default: bool | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class AIProviderConfigOut(BaseModel):
    id: int
    name: str
    api_base_url: str
    model: str
    response_format_type: str
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
    workflow_id: int | None = None
    type: str
    status: str
    desired_visibility: str
    file_name: str | None
    ai_model_snapshot: str | None
    error_message: str | None
    workflow_status: str | None = None
    draft_question_count: int = 0
    repair_attempts: int = 0
    can_confirm: bool = False
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIGenerationBankJobOut(BaseModel):
    bank_id: int
    job_id: int


class AIGenerationWorkflowOut(BaseModel):
    id: int
    workflow_id: int | None = None
    bank_id: int
    user_id: int
    job_id: int | None = None
    type: str | None = None
    purpose: str
    generation_mode: str
    status: str
    workflow_status: str | None = None
    source_file_name: str | None
    requested_count: int | None
    generate_description: str
    extra_instruction: str | None
    ai_model_snapshot: str | None
    ai_base_url_snapshot: str | None
    repair_attempts: int
    error_message: str | None
    draft_question_count: int = 0
    can_confirm: bool = False
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIGenerationWorkflowStepOut(BaseModel):
    id: int
    workflow_id: int
    step_name: str
    status: str
    input_json: str | None
    output_json: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AIGenerationDraftQuestionOut(BaseModel):
    id: int
    type: str
    stem: str
    explanation: str | None
    difficulty: str | None
    options: list[dict]
    validation_status: str
    validation_message: str | None


class AIGenerationDraftOut(BaseModel):
    id: int
    workflow_id: int
    job_id: int | None = None
    bank_id: int
    bank_description: str | None
    validation_summary: str | None
    status: str
    questions: list[AIGenerationDraftQuestionOut]

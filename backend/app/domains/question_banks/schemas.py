from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.question_bank import QuestionBankTagOut


class QuestionBankOwnerOut(BaseModel):
    id: int
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class QuestionBankStatsOut(BaseModel):
    question_count: int = 0
    favorite_count: int = 0


class QuestionBankPermissionsOut(BaseModel):
    can_read: bool = False
    can_manage: bool = False
    can_export: bool = False
    can_practice: bool = False
    can_view_mistakes: bool = False
    can_extend_ai: bool = False


class ActiveWorkflowOut(BaseModel):
    id: int
    status: str
    purpose: str
    draft_question_count: int = 0


class QuestionBankV2Out(BaseModel):
    id: int
    title: str
    description: str | None = None
    visibility: str
    desired_visibility: str
    generation_status: str
    owner: QuestionBankOwnerOut
    tags: list[QuestionBankTagOut] = Field(default_factory=list)
    stats: QuestionBankStatsOut
    permissions: QuestionBankPermissionsOut
    active_workflow: ActiveWorkflowOut | None = None
    ai_model_name: str | None = None
    is_favorited: bool = False
    created_at: datetime
    updated_at: datetime


class QuestionBankV2Create(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    visibility: str = Field(default="private", pattern="^(private|public)$")
    tag_names: list[str] | None = None


class QuestionBankV2Update(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|public)$")
    tag_names: list[str] | None = None

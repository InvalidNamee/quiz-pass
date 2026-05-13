from datetime import datetime

from pydantic import BaseModel, Field


class QuestionBankCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    visibility: str = Field(default="private", pattern="^(private|public)$")


class QuestionBankUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|public)$")


class QuestionBankOut(BaseModel):
    id: int
    owner_id: int
    owner_username: str | None = None
    owner_display_name: str | None = None
    owner_avatar_url: str | None = None
    title: str
    description: str | None
    visibility: str
    desired_visibility: str
    generation_status: str
    question_count: int
    favorite_count: int
    ai_model_name: str | None
    created_at: datetime
    updated_at: datetime
    is_favorited: bool = False

    model_config = {"from_attributes": True}

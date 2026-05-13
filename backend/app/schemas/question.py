from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class QuestionOptionIn(BaseModel):
    label: str = Field(min_length=1, max_length=8)
    content: str = Field(min_length=1)
    is_correct: bool = False


class QuestionOptionOut(QuestionOptionIn):
    id: int
    sort_order: int

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    type: str = Field(pattern="^(single|multiple)$")
    stem: str = Field(min_length=1)
    explanation: str | None = None
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    options: list[QuestionOptionIn] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_correct_options(self):
        correct_count = sum(1 for option in self.options if option.is_correct)
        if self.type == "single" and correct_count != 1:
            raise ValueError("single choice questions must have exactly one correct option")
        if self.type == "multiple" and correct_count < 2:
            raise ValueError("multiple choice questions must have at least two correct options")
        return self


class QuestionUpdate(QuestionCreate):
    pass


class QuestionOut(BaseModel):
    id: int
    bank_id: int
    type: str
    stem: str
    explanation: str | None
    difficulty: str | None
    source: str
    generated_model: str | None
    options: list[QuestionOptionOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

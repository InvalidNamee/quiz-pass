import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


QUESTION_TYPES = ("single", "multiple", "blank", "short_answer")
QuestionType = Literal["single", "multiple", "blank", "short_answer"]


class QuestionOptionIn(BaseModel):
    label: str = Field(min_length=1, max_length=8)
    content: str = Field(min_length=1)
    is_correct: bool = False


class QuestionOptionOut(QuestionOptionIn):
    id: int
    sort_order: int

    model_config = {"from_attributes": True}


class QuestionBlankIn(BaseModel):
    label: str = Field(min_length=1, max_length=16)
    answers: list[str] = Field(min_length=1, max_length=20)


class QuestionBlankOut(QuestionBlankIn):
    id: int
    sort_order: int

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    type: QuestionType
    stem: str = Field(min_length=1)
    explanation: str | None = None
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    options: list[QuestionOptionIn] = Field(default_factory=list, max_length=26)
    blanks: list[QuestionBlankIn] = Field(default_factory=list, max_length=26)

    @model_validator(mode="after")
    def validate_correct_options(self):
        if self.type in {"single", "multiple"} and len(self.options) < 2:
            raise ValueError("choice questions must have at least two options")
        if self.type in {"blank", "short_answer"} and self.options:
            raise ValueError("blank and short answer questions cannot have options")
        if self.type != "blank" and self.blanks:
            raise ValueError("only blank questions can have blanks")
        correct_count = sum(1 for option in self.options if option.is_correct)
        if self.type == "single" and correct_count != 1:
            raise ValueError("single choice questions must have exactly one correct option")
        if self.type == "multiple" and correct_count < 2:
            raise ValueError("multiple choice questions must have at least two correct options")
        if self.type == "blank":
            labels = [blank.label.strip() for blank in self.blanks]
            if not labels:
                raise ValueError("blank questions must have at least one blank")
            if len(set(labels)) != len(labels):
                raise ValueError("blank labels must be unique")
            for label in labels:
                if f"{{{{{label}}}}}" not in self.stem:
                    raise ValueError(f"blank placeholder {{{{{label}}}}} is missing from stem")
            for blank in self.blanks:
                answers = [answer.strip() for answer in blank.answers if answer.strip()]
                if not answers:
                    raise ValueError("each blank must have at least one answer")
            placeholders = set(re.findall(r"\{\{([^{}]+)\}\}", self.stem))
            if placeholders != set(labels):
                raise ValueError("blank placeholders must match blanks")
        if self.type == "short_answer" and not (self.explanation or "").strip():
            raise ValueError("short answer questions must include grading points in explanation")
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
    blanks: list[QuestionBlankOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

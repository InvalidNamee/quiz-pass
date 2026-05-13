from datetime import datetime

from pydantic import BaseModel, Field


class PracticeSessionCreate(BaseModel):
    bank_id: int
    mode: str = Field(default="practice", pattern="^(practice|exam|mistake_review)$")
    question_limit: int | None = Field(default=None, ge=1, le=200)
    shuffle_questions: bool = True
    shuffle_options: bool = True


class PracticeSessionOut(BaseModel):
    id: int
    user_id: int
    bank_id: int
    mode: str
    status: str
    total_questions: int
    answered_count: int = 0
    correct_count: int
    score: float
    started_at: datetime
    submitted_at: datetime | None

    model_config = {"from_attributes": True}


class PracticeAnswerCreate(BaseModel):
    question_id: int
    selected_option_ids: list[int]


class PracticeAnswerOut(BaseModel):
    is_submitted: bool = True
    reveal: bool
    is_correct: bool | None = None
    correct_option_ids: list[int] = Field(default_factory=list)
    correct_labels: list[str] = Field(default_factory=list)
    explanation: str | None


class PracticeQuestionAnswerStateOut(BaseModel):
    is_answered: bool = False
    selected_option_ids: list[int] = Field(default_factory=list)
    reveal: bool = False
    is_correct: bool | None = None
    correct_labels: list[str] = Field(default_factory=list)
    explanation: str | None = None


class PracticeQuestionOptionOut(BaseModel):
    id: int
    label: str
    content: str
    sort_order: int

    model_config = {"from_attributes": True}


class PracticeQuestionOut(BaseModel):
    id: int
    type: str
    stem: str
    options: list[PracticeQuestionOptionOut]
    answer_state: PracticeQuestionAnswerStateOut = Field(default_factory=PracticeQuestionAnswerStateOut)

    model_config = {"from_attributes": True}


class PracticeResultOptionOut(BaseModel):
    id: int
    label: str
    content: str


class PracticeResultAnswerOut(BaseModel):
    question_id: int
    type: str
    stem: str
    options: list[PracticeResultOptionOut]
    selected_option_ids: list[int]
    selected_labels: list[str]
    correct_option_ids: list[int]
    correct_labels: list[str]
    is_correct: bool
    is_unanswered: bool
    explanation: str | None


class MistakeRecordOut(BaseModel):
    id: int
    user_id: int
    bank_id: int
    question_id: int
    wrong_count: int
    last_wrong_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}

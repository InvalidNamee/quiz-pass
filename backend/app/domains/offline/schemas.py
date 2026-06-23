from datetime import datetime

from pydantic import BaseModel, Field


class DownloadOwnerOut(BaseModel):
    id: int
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class DownloadBankOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    ai_context: str | None = None
    visibility: str
    generation_status: str
    source_bank_id: int | None = None
    is_shared_copy: bool = False
    owner: DownloadOwnerOut
    question_count: int = 0
    favorite_count: int = 0
    created_at: datetime
    updated_at: datetime


class DownloadTagOut(BaseModel):
    id: int
    name: str


class DownloadOptionOut(BaseModel):
    id: int
    label: str
    content: str
    is_correct: bool
    sort_order: int


class DownloadBlankOut(BaseModel):
    id: int
    label: str
    answers: list[str]
    sort_order: int


class DownloadQuestionOut(BaseModel):
    id: int
    bank_id: int
    type: str
    stem: str
    explanation: str | None = None
    difficulty: str | None = None
    source: str
    generated_model: str | None = None
    options: list[DownloadOptionOut] = Field(default_factory=list)
    blanks: list[DownloadBlankOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BankDownloadPackage(BaseModel):
    version: int = 1
    bank: DownloadBankOut
    tags: list[DownloadTagOut] = Field(default_factory=list)
    questions: list[DownloadQuestionOut] = Field(default_factory=list)
    content_hash: str
    exported_at: datetime


class OfflinePracticeAnswerIn(BaseModel):
    question_id: int
    selected_option_ids: list[int] = Field(default_factory=list)
    text_answers: list[str] = Field(default_factory=list)
    is_submitted: bool = True
    answered_at: datetime | None = None


class OfflinePracticeSessionIn(BaseModel):
    client_session_id: str = Field(min_length=1, max_length=128)
    remote_bank_id: int
    mode: str = Field(pattern="^(practice|exam|mistake_review)$")
    status: str = Field(pattern="^(in_progress|submitted)$")
    question_order: list[int] = Field(min_length=1, max_length=500)
    answers: list[OfflinePracticeAnswerIn] = Field(default_factory=list)
    started_at: datetime
    submitted_at: datetime | None = None


class OfflinePracticeSyncRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    sessions: list[OfflinePracticeSessionIn] = Field(default_factory=list, max_length=100)


class OfflinePracticeSyncItem(BaseModel):
    client_session_id: str
    remote_session_id: int


class OfflinePracticeSyncFailure(BaseModel):
    client_session_id: str
    code: str
    message: str


class OfflinePracticeSyncResult(BaseModel):
    synced: list[OfflinePracticeSyncItem] = Field(default_factory=list)
    failed: list[OfflinePracticeSyncFailure] = Field(default_factory=list)

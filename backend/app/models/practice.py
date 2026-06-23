from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (UniqueConstraint("user_id", "offline_device_id", "offline_client_session_id", name="uq_practice_session_offline_client"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="practice")
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0)
    mistake_source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mistake_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offline_device_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    offline_client_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    offline_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PracticeSessionQuestion(Base):
    __tablename__ = "practice_session_questions"
    __table_args__ = (UniqueConstraint("session_id", "question_id", name="uq_practice_session_question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class PracticeAnswer(Base):
    __tablename__ = "practice_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    selected_option_ids: Mapped[list[int]] = mapped_column(JSON)
    text_answers: Mapped[list[str] | None] = mapped_column(JSON, default=list, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MistakeRecord(Base):
    __tablename__ = "mistake_records"
    __table_args__ = (UniqueConstraint("user_id", "bank_id", "question_id", name="uq_mistake_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MistakeAttempt(Base):
    __tablename__ = "mistake_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    practice_session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id", ondelete="CASCADE"), index=True)
    practice_answer_id: Mapped[int | None] = mapped_column(ForeignKey("practice_answers.id", ondelete="SET NULL"), nullable=True, index=True)
    question_snapshot_json: Mapped[dict] = mapped_column(JSON)
    user_answer_json: Mapped[dict] = mapped_column(JSON)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    wrong_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIGenerationWorkflow(Base):
    __tablename__ = "ai_generation_workflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int | None] = mapped_column(ForeignKey("question_banks.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), default="create_bank", index=True)
    generation_mode: Mapped[str] = mapped_column(String(32), default="knowledge_generate")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_text_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_title_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generate_description: Mapped[str] = mapped_column(String(8), default="false")
    extra_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    inherit_context: Mapped[bool] = mapped_column(default=False)
    include_existing_questions: Mapped[bool] = mapped_column(default=False)
    question_type_settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_of_workflow_id: Mapped[int | None] = mapped_column(ForeignKey("ai_generation_workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    ai_provider_config_id: Mapped[int | None] = mapped_column(ForeignKey("user_ai_provider_configs.id", ondelete="SET NULL"), nullable=True)
    ai_model_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_base_url_snapshot: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repair_attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    steps = relationship("AIGenerationWorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    drafts = relationship("AIGenerationDraft", back_populates="workflow", cascade="all, delete-orphan")


class AIGenerationWorkflowStep(Base):
    __tablename__ = "ai_generation_workflow_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("ai_generation_workflows.id", ondelete="CASCADE"), index=True)
    step_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    workflow = relationship("AIGenerationWorkflow", back_populates="steps")


class AIGenerationDraft(Base):
    __tablename__ = "ai_generation_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("ai_generation_workflows.id", ondelete="CASCADE"), index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bank_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    repaired_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ready", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    workflow = relationship("AIGenerationWorkflow", back_populates="drafts")
    questions = relationship("AIGenerationDraftQuestion", back_populates="draft", cascade="all, delete-orphan")


class AIGenerationDraftQuestion(Base):
    __tablename__ = "ai_generation_draft_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("ai_generation_drafts.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(32))
    stem: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    options_json: Mapped[str] = mapped_column(Text)
    blanks_json: Mapped[str | None] = mapped_column(Text, default="[]", nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="valid")
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    draft = relationship("AIGenerationDraft", back_populates="questions")

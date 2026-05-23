from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bank_id: Mapped[int | None] = mapped_column(ForeignKey("question_banks.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id: Mapped[int | None] = mapped_column(ForeignKey("ai_generation_workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), default="document_ai")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    desired_visibility: Mapped[str] = mapped_column(String(32), default="private")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_provider_config_id: Mapped[int | None] = mapped_column(ForeignKey("user_ai_provider_configs.id", ondelete="SET NULL"), nullable=True)
    ai_base_url_snapshot: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_model_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queue_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enqueued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

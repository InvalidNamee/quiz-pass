from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


question_bank_tag_links = Table(
    "question_bank_tag_links",
    Base.metadata,
    Column("bank_id", ForeignKey("question_banks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("question_bank_tags.id", ondelete="CASCADE"), primary_key=True),
    UniqueConstraint("bank_id", "tag_id", name="uq_question_bank_tag_link"),
)


class QuestionBank(Base):
    __tablename__ = "question_banks"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_bank_id: Mapped[int | None] = mapped_column(ForeignKey("question_banks.id", ondelete="SET NULL"), nullable=True, index=True)
    is_shared_copy: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="private", index=True)
    desired_visibility: Mapped[str] = mapped_column(String(32), default="private")
    generation_status: Mapped[str] = mapped_column(String(32), default="none", index=True)
    ai_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_provider_config_id: Mapped[int | None] = mapped_column(ForeignKey("user_ai_provider_configs.id", ondelete="SET NULL"), nullable=True)
    ai_model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_base_url_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="question_banks")
    questions = relationship("Question", back_populates="bank", cascade="all, delete-orphan")
    tags = relationship("QuestionBankTag", secondary=question_bank_tag_links, back_populates="banks")


class QuestionBankTag(Base):
    __tablename__ = "question_bank_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    banks = relationship("QuestionBank", secondary=question_bank_tag_links, back_populates="tags")


class QuestionBankFavorite(Base):
    __tablename__ = "question_bank_favorites"
    __table_args__ = (UniqueConstraint("user_id", "bank_id", name="uq_question_bank_favorite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

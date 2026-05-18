from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.question import Question
from app.models.question_bank import QuestionBank, QuestionBankFavorite


class QuestionBankStatsService:
    """Single maintenance point for denormalized bank counters."""

    @staticmethod
    def rebuild_bank_stats(db: Session, bank_id: int) -> QuestionBank | None:
        bank = db.get(QuestionBank, bank_id)
        if not bank:
            return None
        question_count = db.scalar(select(func.count()).select_from(Question).where(Question.bank_id == bank_id)) or 0
        favorite_count = db.scalar(select(func.count()).select_from(QuestionBankFavorite).where(QuestionBankFavorite.bank_id == bank_id)) or 0
        bank.question_count = question_count
        bank.favorite_count = favorite_count
        db.flush()
        return bank

    @classmethod
    def increment_questions(cls, db: Session, bank: QuestionBank, count: int = 1) -> None:
        bank.question_count = max(0, bank.question_count + count)
        db.flush()

    @classmethod
    def decrement_questions(cls, db: Session, bank: QuestionBank, count: int = 1) -> None:
        bank.question_count = max(0, bank.question_count - count)
        db.flush()

    @classmethod
    def increment_favorites(cls, db: Session, bank: QuestionBank, count: int = 1) -> None:
        bank.favorite_count = max(0, bank.favorite_count + count)
        db.flush()

    @classmethod
    def decrement_favorites(cls, db: Session, bank: QuestionBank, count: int = 1) -> None:
        bank.favorite_count = max(0, bank.favorite_count - count)
        db.flush()

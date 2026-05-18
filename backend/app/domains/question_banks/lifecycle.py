from sqlalchemy.orm import Session

from app.models.question_bank import QuestionBank


class QuestionBankLifecycleService:
    """Owns cross-table lifecycle actions for a question bank aggregate."""

    def __init__(self, db: Session):
        self.db = db

    def delete_bank(self, bank: QuestionBank) -> None:
        self.db.delete(bank)
        self.db.flush()

    def cleanup_dependencies(self, bank_id: int) -> None:
        bank = self.db.get(QuestionBank, bank_id)
        if bank:
            self.delete_bank(bank)

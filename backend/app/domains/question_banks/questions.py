from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.stats import QuestionBankStatsService
from app.models.question import Question, QuestionOption
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.common import page_response
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.utils.pagination import paginate


class QuestionService:
    def __init__(self, db: Session):
        self.db = db

    def list_questions(self, bank_id: int, user: User, page: int = 1, page_size: int = 20, keyword: str | None = None, all: bool = False):
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_read(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        if all and not QuestionBankPermissionService.can_manage(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        stmt = select(Question).options(selectinload(Question.options)).where(Question.bank_id == bank_id)
        if keyword:
            stmt = stmt.where(or_(Question.stem.contains(keyword), Question.explanation.contains(keyword)))
        stmt = stmt.order_by(Question.created_at.desc())
        if all:
            items = self.db.scalars(stmt).all()
            total = len(items)
            return page_response(items, total, 1, total or 1)
        items, total, page, page_size = paginate(self.db, stmt, page, page_size)
        return page_response(items, total, page, page_size)

    def create_question(self, bank_id: int, payload: QuestionCreate, user: User) -> Question:
        bank = self.get_manageable_bank(bank_id, user)
        question = Question(
            bank_id=bank.id,
            type=payload.type,
            stem=payload.stem,
            explanation=payload.explanation,
            difficulty=payload.difficulty,
            source="manual",
        )
        self.db.add(question)
        self.db.flush()
        self.replace_options(question, payload.options)
        QuestionBankStatsService.increment_questions(self.db, bank)
        self.db.commit()
        return self.get_question_for_output(question.id)

    def get_question(self, question_id: int, user: User) -> Question:
        question = self.get_question_for_output(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        bank = self.db.get(QuestionBank, question.bank_id)
        if not QuestionBankPermissionService.can_read(bank, user):
            raise HTTPException(status_code=404, detail="Question not found")
        return question

    def update_question(self, question_id: int, payload: QuestionUpdate, user: User) -> Question:
        question = self.get_question_for_output(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        self.get_manageable_bank(question.bank_id, user)
        question.type = payload.type
        question.stem = payload.stem
        question.explanation = payload.explanation
        question.difficulty = payload.difficulty
        for option in list(question.options):
            self.db.delete(option)
        self.db.flush()
        self.replace_options(question, payload.options)
        self.db.commit()
        return self.get_question_for_output(question_id)

    def delete_question(self, question_id: int, user: User) -> None:
        question = self.db.get(Question, question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        bank = self.get_manageable_bank(question.bank_id, user)
        self.db.delete(question)
        QuestionBankStatsService.decrement_questions(self.db, bank)
        self.db.commit()

    def get_manageable_bank(self, bank_id: int, user: User) -> QuestionBank:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_manage(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        return bank

    def get_question_for_output(self, question_id: int) -> Question | None:
        return self.db.scalar(select(Question).options(selectinload(Question.options)).where(Question.id == question_id))

    def replace_options(self, question: Question, options) -> None:
        for index, option in enumerate(options):
            self.db.add(
                QuestionOption(
                    question_id=question.id,
                    label=option.label,
                    content=option.content,
                    is_correct=option.is_correct,
                    sort_order=index,
                )
            )

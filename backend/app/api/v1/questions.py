from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.question import Question, QuestionOption
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.common import Page, page_response
from app.schemas.question import QuestionCreate, QuestionOut, QuestionUpdate
from app.utils.pagination import paginate

router = APIRouter()


def require_owner_bank(db: Session, bank_id: int, user: User) -> QuestionBank:
    bank = db.get(QuestionBank, bank_id)
    if not bank or bank.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return bank


@router.get("/question-banks/{bank_id}/questions", response_model=Page[QuestionOut])
def list_questions(bank_id: int, page: int = 1, page_size: int = 20, keyword: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not bank or not (bank.owner_id == current_user.id or bank.visibility == "public"):
        raise HTTPException(status_code=404, detail="Question bank not found")
    stmt = select(Question).options(selectinload(Question.options)).where(Question.bank_id == bank_id)
    if keyword:
        stmt = stmt.where(or_(Question.stem.contains(keyword), Question.explanation.contains(keyword)))
    stmt = stmt.order_by(Question.created_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response(items, total, page, page_size)


@router.post("/question-banks/{bank_id}/questions", response_model=QuestionOut)
def create_question(bank_id: int, payload: QuestionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = require_owner_bank(db, bank_id, current_user)
    question = Question(bank_id=bank_id, type=payload.type, stem=payload.stem, explanation=payload.explanation, difficulty=payload.difficulty, source="manual")
    db.add(question)
    db.flush()
    for index, option in enumerate(payload.options):
        db.add(QuestionOption(question_id=question.id, label=option.label, content=option.content, is_correct=option.is_correct, sort_order=index))
    bank.question_count += 1
    db.commit()
    return db.scalar(select(Question).options(selectinload(Question.options)).where(Question.id == question.id))


@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    question = db.scalar(select(Question).options(selectinload(Question.options)).where(Question.id == question_id))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    bank = db.get(QuestionBank, question.bank_id)
    if not bank or not (bank.owner_id == current_user.id or bank.visibility == "public"):
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.patch("/questions/{question_id}", response_model=QuestionOut)
def update_question(question_id: int, payload: QuestionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    question = db.scalar(select(Question).options(selectinload(Question.options)).where(Question.id == question_id))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    require_owner_bank(db, question.bank_id, current_user)
    question.type = payload.type
    question.stem = payload.stem
    question.explanation = payload.explanation
    question.difficulty = payload.difficulty
    for option in list(question.options):
        db.delete(option)
    db.flush()
    for index, option in enumerate(payload.options):
        db.add(QuestionOption(question_id=question.id, label=option.label, content=option.content, is_correct=option.is_correct, sort_order=index))
    db.commit()
    return db.scalar(select(Question).options(selectinload(Question.options)).where(Question.id == question_id))


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    bank = require_owner_bank(db, question.bank_id, current_user)
    db.delete(question)
    bank.question_count = max(0, bank.question_count - 1)
    db.commit()
    return {"ok": True}

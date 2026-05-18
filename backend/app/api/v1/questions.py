from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.question_banks.questions import QuestionService
from app.models.user import User
from app.schemas.common import Page
from app.schemas.question import QuestionCreate, QuestionOut, QuestionUpdate

router = APIRouter()


@router.get("/question-banks/{bank_id}/questions", response_model=Page[QuestionOut])
def list_questions(bank_id: int, page: int = 1, page_size: int = 20, keyword: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).list_questions(bank_id, current_user, page, page_size, keyword)


@router.post("/question-banks/{bank_id}/questions", response_model=QuestionOut)
def create_question(bank_id: int, payload: QuestionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).create_question(bank_id, payload, current_user)


@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).get_question(question_id, current_user)


@router.patch("/questions/{question_id}", response_model=QuestionOut)
def update_question(question_id: int, payload: QuestionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).update_question(question_id, payload, current_user)


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    QuestionService(db).delete_question(question_id, current_user)
    return {"ok": True}

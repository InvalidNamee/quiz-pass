from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.practice.services import MistakeService, PracticeSessionService
from app.models.practice import PracticeSession
from app.models.question import Question
from app.models.user import User
from app.schemas.common import Page, page_response
from app.schemas.practice import (
    MistakeRecordOut,
    PracticeAnswerCreate,
    PracticeAnswerOut,
    PracticeQuestionOut,
    PracticeResultAnswerOut,
    PracticeSessionCreate,
    PracticeSessionOut,
)
from app.utils.pagination import paginate

router = APIRouter()


@router.post("/practice/sessions", response_model=PracticeSessionOut)
def create_session(payload: PracticeSessionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).create_session(payload, current_user)


@router.get("/practice/sessions/{session_id}", response_model=PracticeSessionOut)
def get_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = PracticeSessionService(db)
    return service.to_out(service.get_owned_session(session_id, current_user))


@router.get("/banks/{bank_id}/practice/resumable-session", response_model=PracticeSessionOut | None)
def get_resumable_session(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).latest_resumable_session(bank_id, current_user)


@router.get("/practice/sessions/{session_id}/questions", response_model=list[PracticeQuestionOut])
def get_session_questions(session_id: int, shuffle_options: bool = False, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).list_questions(session_id, current_user, shuffle_options)


@router.post("/practice/sessions/{session_id}/answers", response_model=PracticeAnswerOut)
def answer_question(session_id: int, payload: PracticeAnswerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).answer_question(session_id, payload, current_user)


@router.put("/practice/sessions/{session_id}/answers/{question_id}/draft")
def save_answer_draft(session_id: int, question_id: int, payload: PracticeAnswerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).save_answer_draft(
        session_id,
        PracticeAnswerCreate(question_id=question_id, selected_option_ids=payload.selected_option_ids, text_answers=payload.text_answers),
        current_user,
    )


@router.post("/practice/sessions/{session_id}/submit", response_model=PracticeSessionOut)
def submit_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).submit_session(session_id, current_user)


@router.get("/practice/sessions/{session_id}/result", response_model=list[PracticeResultAnswerOut])
def get_result(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).result(session_id, current_user)


@router.get("/banks/{bank_id}/mistakes", response_model=Page[MistakeRecordOut])
def list_mistakes(bank_id: int, page: int = 1, page_size: int = 20, resolved: bool | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = MistakeService(db)
    stmt = service.list_stmt(bank_id, current_user, resolved)
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    question_ids = [item.question_id for item in items]
    questions = db.scalars(select(Question).options(selectinload(Question.options), selectinload(Question.blanks)).where(Question.id.in_(question_ids))).all() if question_ids else []
    questions_by_id = {question.id: question for question in questions}
    return page_response([service.to_out(item, questions_by_id[item.question_id]) for item in items if item.question_id in questions_by_id], total, page, page_size)


@router.post("/banks/{bank_id}/mistakes/practice-sessions", response_model=PracticeSessionOut)
def create_mistake_session(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).create_session(PracticeSessionCreate(bank_id=bank_id, mode="mistake_review"), current_user)


@router.post("/banks/{bank_id}/mistakes/{question_id}/resolve")
def resolve_mistake(bank_id: int, question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    MistakeService(db).resolve(bank_id, question_id, current_user)
    return {"ok": True}


@router.get("/history/sessions", response_model=Page[PracticeSessionOut])
def list_history(
    page: int = 1,
    page_size: int = 20,
    bank_id: int | None = None,
    mode: str | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(PracticeSession).where(PracticeSession.user_id == current_user.id)
    if bank_id:
        stmt = stmt.where(PracticeSession.bank_id == bank_id)
    if mode:
        stmt = stmt.where(PracticeSession.mode == mode)
    if status:
        stmt = stmt.where(PracticeSession.status == status)
    stmt = stmt.order_by(PracticeSession.started_at.desc())
    service = PracticeSessionService(db)
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([service.to_out(item) for item in items], total, page, page_size)

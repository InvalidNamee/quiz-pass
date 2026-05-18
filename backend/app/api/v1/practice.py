import random
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.practice.services import MistakeService, PracticeSessionService
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.models.practice import MistakeRecord, PracticeAnswer, PracticeSession, PracticeSessionQuestion
from app.models.question import Question, QuestionOption
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.common import Page, page_response
from app.schemas.practice import (
    MistakeRecordOut,
    PracticeAnswerCreate,
    PracticeAnswerOut,
    PracticeQuestionAnswerStateOut,
    PracticeQuestionOut,
    PracticeResultOptionOut,
    PracticeResultAnswerOut,
    PracticeSessionCreate,
    PracticeSessionOut,
)
from app.utils.pagination import paginate

router = APIRouter()


def _can_read_bank(bank: QuestionBank | None, user: User) -> bool:
    return QuestionBankPermissionService.can_practice(bank, user)


def _record_wrong_answer(db: Session, user_id: int, bank_id: int, question_id: int) -> None:
    mistake = db.scalar(
        select(MistakeRecord).where(
            MistakeRecord.user_id == user_id,
            MistakeRecord.bank_id == bank_id,
            MistakeRecord.question_id == question_id,
        )
    )
    if mistake:
        mistake.wrong_count += 1
        mistake.last_wrong_at = datetime.now(UTC)
        mistake.resolved_at = None
    else:
        db.add(MistakeRecord(user_id=user_id, bank_id=bank_id, question_id=question_id))


def _mistake_out(mistake: MistakeRecord, question: Question) -> MistakeRecordOut:
    options = sorted(question.options, key=lambda item: item.sort_order)
    correct_options = [option for option in options if option.is_correct]
    return MistakeRecordOut(
        id=mistake.id,
        user_id=mistake.user_id,
        bank_id=mistake.bank_id,
        question_id=mistake.question_id,
        type=question.type,
        stem=question.stem,
        options=[PracticeResultOptionOut(id=option.id, label=option.label, content=option.content) for option in options],
        correct_option_ids=[option.id for option in correct_options],
        correct_labels=[option.label for option in correct_options],
        explanation=question.explanation,
        wrong_count=mistake.wrong_count,
        last_wrong_at=mistake.last_wrong_at,
        resolved_at=mistake.resolved_at,
    )


def _session_out(db: Session, session: PracticeSession) -> PracticeSessionOut:
    answered_count = db.query(PracticeAnswer).filter(PracticeAnswer.session_id == session.id).count()
    bank = db.get(QuestionBank, session.bank_id)
    last_answered_at = db.scalar(select(func.max(PracticeAnswer.answered_at)).where(PracticeAnswer.session_id == session.id))
    return PracticeSessionOut.model_validate(session, from_attributes=True).model_copy(
        update={
            "answered_count": answered_count,
            "bank_title": bank.title if bank else None,
            "bank_visibility": bank.visibility if bank else None,
            "bank_generation_status": bank.generation_status if bank else None,
            "last_answered_at": last_answered_at,
        }
    )


def _should_reveal(session: PracticeSession) -> bool:
    return session.mode != "exam" or session.status == "submitted"


@router.post("/practice/sessions", response_model=PracticeSessionOut)
def create_session(payload: PracticeSessionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).create_session(payload, current_user)


@router.get("/practice/sessions/{session_id}", response_model=PracticeSessionOut)
def get_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = PracticeSessionService(db)
    return service.to_out(service.get_owned_session(session_id, current_user))


@router.get("/practice/sessions/{session_id}/questions", response_model=list[PracticeQuestionOut])
def get_session_questions(session_id: int, shuffle_options: bool = False, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).list_questions(session_id, current_user, shuffle_options)


@router.post("/practice/sessions/{session_id}/answers", response_model=PracticeAnswerOut)
def answer_question(session_id: int, payload: PracticeAnswerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).answer_question(session_id, payload, current_user)


@router.post("/practice/sessions/{session_id}/submit", response_model=PracticeSessionOut)
def submit_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).submit_session(session_id, current_user)


@router.get("/practice/sessions/{session_id}/result", response_model=list[PracticeResultAnswerOut])
def get_result(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).result(session_id, current_user)


@router.get("/question-banks/{bank_id}/mistakes", response_model=Page[MistakeRecordOut])
def list_mistakes(bank_id: int, page: int = 1, page_size: int = 20, resolved: bool | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = MistakeService(db)
    stmt = service.list_stmt(bank_id, current_user, resolved)
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    question_ids = [item.question_id for item in items]
    questions = db.scalars(select(Question).options(selectinload(Question.options)).where(Question.id.in_(question_ids))).all() if question_ids else []
    questions_by_id = {question.id: question for question in questions}
    return page_response([service.to_out(item, questions_by_id[item.question_id]) for item in items if item.question_id in questions_by_id], total, page, page_size)


@router.post("/question-banks/{bank_id}/mistakes/practice-sessions", response_model=PracticeSessionOut)
def create_mistake_session(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PracticeSessionService(db).create_session(PracticeSessionCreate(bank_id=bank_id, mode="mistake_review"), current_user)


@router.post("/question-banks/{bank_id}/mistakes/{question_id}/resolve")
def resolve_mistake(bank_id: int, question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    MistakeService(db).resolve(bank_id, question_id, current_user)
    return {"ok": True}


@router.get("/history/sessions", response_model=Page[PracticeSessionOut])
def list_history(page: int = 1, page_size: int = 20, bank_id: int | None = None, mode: str | None = None, status: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(PracticeSession).where(PracticeSession.user_id == current_user.id)
    if bank_id:
        stmt = stmt.where(PracticeSession.bank_id == bank_id)
    if mode:
        stmt = stmt.where(PracticeSession.mode == mode)
    if status:
        stmt = stmt.where(PracticeSession.status == status)
    stmt = stmt.order_by(PracticeSession.started_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([_session_out(db, item) for item in items], total, page, page_size)

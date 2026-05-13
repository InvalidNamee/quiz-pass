import random
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
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
    return bool(bank and (bank.owner_id == user.id or bank.visibility == "public" or user.role == "admin"))


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
    bank = db.get(QuestionBank, payload.bank_id)
    if not _can_read_bank(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")

    if payload.mode == "mistake_review":
        question_ids = db.scalars(
            select(MistakeRecord.question_id).where(
                MistakeRecord.user_id == current_user.id,
                MistakeRecord.bank_id == bank.id,
                MistakeRecord.resolved_at.is_(None),
            )
        ).all()
        questions = db.scalars(select(Question).where(Question.id.in_(question_ids))).all() if question_ids else []
    else:
        questions = db.scalars(select(Question).where(Question.bank_id == bank.id)).all()
    if payload.shuffle_questions:
        random.shuffle(questions)
    if payload.question_limit:
        questions = questions[: payload.question_limit]
    if not questions:
        raise HTTPException(status_code=400, detail="没有可练习的题目")

    session = PracticeSession(user_id=current_user.id, bank_id=bank.id, mode=payload.mode, total_questions=len(questions))
    db.add(session)
    db.flush()
    for index, question in enumerate(questions):
        db.add(PracticeSessionQuestion(session_id=session.id, question_id=question.id, sort_order=index))
    db.commit()
    db.refresh(session)
    return _session_out(db, session)


@router.get("/practice/sessions/{session_id}", response_model=PracticeSessionOut)
def get_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_out(db, session)


@router.get("/practice/sessions/{session_id}/questions", response_model=list[PracticeQuestionOut])
def get_session_questions(session_id: int, shuffle_options: bool = False, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = db.scalars(select(PracticeSessionQuestion).where(PracticeSessionQuestion.session_id == session.id).order_by(PracticeSessionQuestion.sort_order)).all()
    questions = db.scalars(select(Question).options(selectinload(Question.options)).where(Question.id.in_([row.question_id for row in rows]))).all()
    by_id = {question.id: question for question in questions}
    ordered = [by_id[row.question_id] for row in rows if row.question_id in by_id]
    if shuffle_options:
        for question in ordered:
            random.shuffle(question.options)
    answers = db.scalars(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id)).all()
    answers_by_question = {answer.question_id: answer for answer in answers}
    reveal = _should_reveal(session)
    result = []
    for question in ordered:
        options = sorted(question.options, key=lambda item: item.sort_order)
        answer = answers_by_question.get(question.id)
        state = PracticeQuestionAnswerStateOut()
        if answer:
            state = PracticeQuestionAnswerStateOut(
                is_answered=True,
                selected_option_ids=answer.selected_option_ids,
                reveal=reveal,
                is_correct=answer.is_correct if reveal else None,
                correct_labels=[option.label for option in options if option.is_correct] if reveal else [],
                explanation=question.explanation if reveal else None,
            )
        result.append(PracticeQuestionOut.model_validate(question, from_attributes=True).model_copy(update={"answer_state": state}))
    return result


@router.post("/practice/sessions/{session_id}/answers", response_model=PracticeAnswerOut)
def answer_question(session_id: int, payload: PracticeAnswerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    in_session = db.scalar(
        select(PracticeSessionQuestion).where(
            PracticeSessionQuestion.session_id == session.id,
            PracticeSessionQuestion.question_id == payload.question_id,
        )
    )
    question = db.get(Question, payload.question_id)
    if not in_session or not question or question.bank_id != session.bank_id:
        raise HTTPException(status_code=400, detail="题目不属于当前练习")

    existing = db.scalar(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id, PracticeAnswer.question_id == payload.question_id))
    if existing:
        raise HTTPException(status_code=400, detail="这道题已经作答，不能重复修改")

    options = db.scalars(select(QuestionOption).where(QuestionOption.question_id == payload.question_id).order_by(QuestionOption.sort_order)).all()
    option_ids = {option.id for option in options}
    if any(option_id not in option_ids for option_id in payload.selected_option_ids):
        raise HTTPException(status_code=400, detail="选项不属于当前题目")
    correct_ids = [option.id for option in options if option.is_correct]
    is_correct = set(payload.selected_option_ids) == set(correct_ids)
    db.add(PracticeAnswer(session_id=session.id, question_id=payload.question_id, selected_option_ids=payload.selected_option_ids, is_correct=is_correct))
    if not is_correct and session.mode != "exam":
        _record_wrong_answer(db, current_user.id, session.bank_id, payload.question_id)
    db.commit()
    reveal = _should_reveal(session)
    return PracticeAnswerOut(
        reveal=reveal,
        is_correct=is_correct if reveal else None,
        correct_option_ids=correct_ids if reveal else [],
        correct_labels=[option.label for option in options if option.is_correct] if reveal else [],
        explanation=question.explanation if reveal else None,
    )


@router.post("/practice/sessions/{session_id}/submit", response_model=PracticeSessionOut)
def submit_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    answers = db.scalars(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id)).all()
    session.correct_count = sum(1 for answer in answers if answer.is_correct)
    session.score = round(session.correct_count / session.total_questions * 100, 2) if session.total_questions else 0
    if session.mode == "exam":
        for answer in answers:
            if not answer.is_correct:
                _record_wrong_answer(db, current_user.id, session.bank_id, answer.question_id)
    session.status = "submitted"
    session.submitted_at = datetime.now(UTC)
    db.commit()
    db.refresh(session)
    return _session_out(db, session)


@router.get("/practice/sessions/{session_id}/result", response_model=list[PracticeResultAnswerOut])
def get_result(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    answers = db.scalars(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id)).all()
    answers_by_question = {answer.question_id: answer for answer in answers}
    rows = db.scalars(select(PracticeSessionQuestion).where(PracticeSessionQuestion.session_id == session.id).order_by(PracticeSessionQuestion.sort_order)).all()
    results = []
    for row in rows:
        question = db.scalar(select(Question).options(selectinload(Question.options)).where(Question.id == row.question_id))
        if not question:
            continue
        answer = answers_by_question.get(question.id)
        options = sorted(question.options, key=lambda item: item.sort_order)
        selected_ids = answer.selected_option_ids if answer else []
        correct_ids = [option.id for option in options if option.is_correct]
        option_by_id = {option.id: option for option in options}
        results.append(
            PracticeResultAnswerOut(
                question_id=question.id,
                type=question.type,
                stem=question.stem,
                options=[PracticeResultOptionOut(id=option.id, label=option.label, content=option.content) for option in options],
                selected_option_ids=selected_ids,
                selected_labels=[option_by_id[id].label for id in selected_ids if id in option_by_id],
                correct_option_ids=correct_ids,
                correct_labels=[option.label for option in options if option.is_correct],
                is_correct=bool(answer and answer.is_correct),
                is_unanswered=answer is None,
                explanation=question.explanation,
            )
        )
    return results


@router.get("/question-banks/{bank_id}/mistakes", response_model=Page[MistakeRecordOut])
def list_mistakes(bank_id: int, page: int = 1, page_size: int = 20, resolved: bool | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not _can_read_bank(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    stmt = select(MistakeRecord).where(MistakeRecord.user_id == current_user.id, MistakeRecord.bank_id == bank_id)
    if resolved is True:
        stmt = stmt.where(MistakeRecord.resolved_at.is_not(None))
    elif resolved is False:
        stmt = stmt.where(MistakeRecord.resolved_at.is_(None))
    stmt = stmt.order_by(MistakeRecord.last_wrong_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response(items, total, page, page_size)


@router.post("/question-banks/{bank_id}/mistakes/practice-sessions", response_model=PracticeSessionOut)
def create_mistake_session(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_session(PracticeSessionCreate(bank_id=bank_id, mode="mistake_review"), current_user, db)


@router.post("/question-banks/{bank_id}/mistakes/{question_id}/resolve")
def resolve_mistake(bank_id: int, question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not _can_read_bank(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    mistake = db.scalar(select(MistakeRecord).where(MistakeRecord.user_id == current_user.id, MistakeRecord.bank_id == bank_id, MistakeRecord.question_id == question_id))
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")
    mistake.resolved_at = datetime.now(UTC)
    db.commit()
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

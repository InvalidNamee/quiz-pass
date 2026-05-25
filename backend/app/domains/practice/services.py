import json
import random
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.queries import QuestionBankQueryService
from app.models.practice import MistakeRecord, PracticeAnswer, PracticeSession, PracticeSessionQuestion
from app.models.question import Question, QuestionBlank, QuestionOption
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.practice import (
    MistakeRecordOut,
    PracticeAnswerCreate,
    PracticeAnswerOut,
    PracticeQuestionAnswerStateOut,
    PracticeQuestionBlankOut,
    PracticeQuestionOut,
    PracticeResultOptionOut,
    PracticeResultAnswerOut,
    PracticeSessionCreate,
    PracticeSessionOut,
)


class MistakeService:
    def __init__(self, db: Session):
        self.db = db

    def record_wrong_answer(self, user_id: int, bank_id: int, question_id: int) -> None:
        mistake = self.db.scalar(
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
            self.db.add(MistakeRecord(user_id=user_id, bank_id=bank_id, question_id=question_id))

    @staticmethod
    def to_out(mistake: MistakeRecord, question: Question) -> MistakeRecordOut:
        options = sorted(question.options, key=lambda item: item.sort_order)
        blanks = sorted(question.blanks, key=lambda item: item.sort_order)
        correct_options = [option for option in options if option.is_correct]
        return MistakeRecordOut(
            id=mistake.id,
            user_id=mistake.user_id,
            bank_id=mistake.bank_id,
            question_id=mistake.question_id,
            type=question.type,
            stem=question.stem,
            options=[PracticeResultOptionOut(id=option.id, label=option.label, content=option.content) for option in options],
            blanks=[PracticeQuestionBlankOut.model_validate(blank, from_attributes=True) for blank in blanks],
            correct_option_ids=[option.id for option in correct_options],
            correct_labels=[option.label for option in correct_options],
            correct_text_answers=[json.loads(blank.answers_json) for blank in blanks],
            explanation=question.explanation,
            wrong_count=mistake.wrong_count,
            last_wrong_at=mistake.last_wrong_at,
            resolved_at=mistake.resolved_at,
        )

    def list_stmt(self, bank_id: int, user: User, resolved: bool | None = None):
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_view_own_mistakes(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        stmt = select(MistakeRecord).join(Question, MistakeRecord.question_id == Question.id).where(MistakeRecord.user_id == user.id, MistakeRecord.bank_id == bank_id)
        if resolved is True:
            stmt = stmt.where(MistakeRecord.resolved_at.is_not(None))
        elif resolved is False:
            stmt = stmt.where(MistakeRecord.resolved_at.is_(None))
        return stmt.order_by(MistakeRecord.last_wrong_at.desc())

    def resolve(self, bank_id: int, question_id: int, user: User) -> None:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_view_own_mistakes(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        mistake = self.db.scalar(select(MistakeRecord).where(MistakeRecord.user_id == user.id, MistakeRecord.bank_id == bank_id, MistakeRecord.question_id == question_id))
        if not mistake:
            raise HTTPException(status_code=404, detail="Mistake not found")
        mistake.resolved_at = datetime.now(UTC)
        self.db.commit()


class PracticeSessionService:
    def __init__(self, db: Session):
        self.db = db
        self.mistakes = MistakeService(db)

    def to_out(self, session: PracticeSession) -> PracticeSessionOut:
        answered_query = self.db.query(PracticeAnswer).filter(PracticeAnswer.session_id == session.id)
        if session.mode != "exam":
            answered_query = answered_query.filter(PracticeAnswer.is_submitted.is_(True))
        answered_count = answered_query.count()
        bank = self.db.get(QuestionBank, session.bank_id)
        last_answered_at = self.db.scalar(select(func.max(PracticeAnswer.answered_at)).where(PracticeAnswer.session_id == session.id))
        return PracticeSessionOut.model_validate(session, from_attributes=True).model_copy(
            update={
                "answered_count": answered_count,
                "bank_title": bank.title if bank else None,
                "bank_visibility": bank.visibility if bank else None,
                "bank_generation_status": bank.generation_status if bank else None,
                "last_answered_at": last_answered_at,
            }
        )

    @staticmethod
    def should_reveal(session: PracticeSession) -> bool:
        return session.mode != "exam" or session.status == "submitted"

    @staticmethod
    def _apply_type_settings(questions: list[Question], settings: dict[str, dict[str, bool | int | None]] | None, shuffle: bool) -> list[Question]:
        if not settings:
            return questions
        allowed_types = ("single", "multiple", "blank", "short_answer")
        selected: list[Question] = []
        enabled_any = False
        for question_type in allowed_types:
            raw = settings.get(question_type) or {}
            if raw.get("enabled") is not True:
                continue
            enabled_any = True
            typed_questions = [question for question in questions if question.type == question_type]
            if shuffle:
                random.shuffle(typed_questions)
            count = raw.get("count")
            if count is not None:
                if not isinstance(count, int) or isinstance(count, bool) or count < 1 or count > 200:
                    raise HTTPException(status_code=422, detail="题型数量必须是 1-200 的整数或 null")
                typed_questions = typed_questions[:count]
            selected.extend(typed_questions)
        if not enabled_any:
            raise HTTPException(status_code=422, detail="至少启用一种题型")
        return selected

    def create_session(self, payload: PracticeSessionCreate, user: User) -> PracticeSessionOut:
        bank = self.db.get(QuestionBank, payload.bank_id)
        if not QuestionBankPermissionService.can_practice(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")

        if payload.mode == "mistake_review":
            question_ids = self.db.scalars(
                select(MistakeRecord.question_id).where(
                    MistakeRecord.user_id == user.id,
                    MistakeRecord.bank_id == bank.id,
                    MistakeRecord.resolved_at.is_(None),
                )
            ).all()
            questions = self.db.scalars(select(Question).where(Question.id.in_(question_ids))).all() if question_ids else []
        else:
            questions = self.db.scalars(select(Question).where(Question.bank_id == bank.id)).all()
        questions = self._apply_type_settings(questions, payload.question_type_settings, payload.shuffle_questions)
        if payload.shuffle_questions:
            random.shuffle(questions)
        if payload.question_limit:
            questions = questions[: payload.question_limit]
        if not questions:
            raise HTTPException(status_code=400, detail="没有可练习的题目")

        session = PracticeSession(user_id=user.id, bank_id=bank.id, mode=payload.mode, total_questions=len(questions))
        self.db.add(session)
        self.db.flush()
        for index, question in enumerate(questions):
            self.db.add(PracticeSessionQuestion(session_id=session.id, question_id=question.id, sort_order=index))
        self.db.commit()
        self.db.refresh(session)
        return self.to_out(session)

    def latest_resumable_session(self, bank_id: int, user: User) -> PracticeSessionOut | None:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_practice(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        resumable = QuestionBankQueryService(self.db).resumable_session_for_bank(bank_id, user)
        if not resumable:
            return None
        session = self.db.get(PracticeSession, resumable.id)
        return self.to_out(session) if session else None

    def get_owned_session(self, session_id: int, user: User) -> PracticeSession:
        session = self.db.get(PracticeSession, session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def list_questions(self, session_id: int, user: User, shuffle_options: bool = False) -> list[PracticeQuestionOut]:
        session = self.get_owned_session(session_id, user)
        rows = self.db.scalars(select(PracticeSessionQuestion).where(PracticeSessionQuestion.session_id == session.id).order_by(PracticeSessionQuestion.sort_order)).all()
        questions = self.db.scalars(select(Question).options(selectinload(Question.options), selectinload(Question.blanks)).where(Question.id.in_([row.question_id for row in rows]))).all()
        by_id = {question.id: question for question in questions}
        ordered = [by_id[row.question_id] for row in rows if row.question_id in by_id]
        if shuffle_options:
            for question in ordered:
                random.shuffle(question.options)
        answers = self.db.scalars(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id)).all()
        answers_by_question = {answer.question_id: answer for answer in answers}
        reveal = self.should_reveal(session)
        result = []
        for question in ordered:
            options = sorted(question.options, key=lambda item: item.sort_order)
            blanks = sorted(question.blanks, key=lambda item: item.sort_order)
            answer = answers_by_question.get(question.id)
            state = PracticeQuestionAnswerStateOut()
            if answer:
                is_answered = answer.is_submitted or session.mode == "exam"
                can_reveal_answer = reveal and answer.is_submitted
                state = PracticeQuestionAnswerStateOut(
                    is_answered=is_answered,
                    selected_option_ids=answer.selected_option_ids,
                    text_answers=answer.text_answers or [],
                    reveal=can_reveal_answer,
                    is_correct=answer.is_correct if can_reveal_answer else None,
                    correct_labels=[option.label for option in options if option.is_correct] if can_reveal_answer else [],
                    correct_text_answers=[json.loads(blank.answers_json) for blank in blanks] if can_reveal_answer else [],
                    explanation=question.explanation if can_reveal_answer else None,
                )
            result.append(PracticeQuestionOut.model_validate(question, from_attributes=True).model_copy(update={"answer_state": state}))
        return result

    def _get_session_question_parts(self, session: PracticeSession, question_id: int) -> tuple[Question, list[QuestionOption], list[QuestionBlank]]:
        in_session = self.db.scalar(
            select(PracticeSessionQuestion).where(
                PracticeSessionQuestion.session_id == session.id,
                PracticeSessionQuestion.question_id == question_id,
            )
        )
        question = self.db.get(Question, question_id)
        if not in_session or not question or question.bank_id != session.bank_id:
            raise HTTPException(status_code=400, detail="题目不属于当前练习")
        options = self.db.scalars(select(QuestionOption).where(QuestionOption.question_id == question_id).order_by(QuestionOption.sort_order)).all()
        blanks = self.db.scalars(select(QuestionBlank).where(QuestionBlank.question_id == question_id).order_by(QuestionBlank.sort_order)).all()
        return question, options, blanks

    @staticmethod
    def _validate_option_ids(options: list[QuestionOption], selected_option_ids: list[int]) -> None:
        option_ids = {option.id for option in options}
        if any(option_id not in option_ids for option_id in selected_option_ids):
            raise HTTPException(status_code=400, detail="选项不属于当前题目")

    @staticmethod
    def _is_correct(options: list[QuestionOption], selected_option_ids: list[int]) -> bool:
        correct_ids = [option.id for option in options if option.is_correct]
        return set(selected_option_ids) == set(correct_ids)

    @staticmethod
    def _normalize_text_answers(text_answers: list[str] | None) -> list[str]:
        return [str(answer) for answer in (text_answers or [])]

    @staticmethod
    def _correct_text_answers(blanks: list[QuestionBlank]) -> list[list[str]]:
        return [json.loads(blank.answers_json) for blank in blanks]

    @classmethod
    def _is_text_correct(cls, question: Question, blanks: list[QuestionBlank], text_answers: list[str]) -> bool:
        if question.type == "short_answer":
            return bool((text_answers[0] if text_answers else "").strip())
        if question.type != "blank":
            return False
        if len(text_answers) != len(blanks):
            return False
        for submitted, blank in zip(text_answers, blanks, strict=True):
            normalized = str(submitted).strip()
            accepted = [str(answer).strip() for answer in json.loads(blank.answers_json)]
            if normalized not in accepted:
                return False
        return True

    @staticmethod
    def _validate_text_answers(question: Question, blanks: list[QuestionBlank], text_answers: list[str]) -> None:
        if question.type == "blank" and len(text_answers) != len(blanks):
            raise HTTPException(status_code=400, detail="填空答案数量与空位数量不一致")
        if question.type == "short_answer" and not (text_answers and text_answers[0].strip()):
            raise HTTPException(status_code=400, detail="简答题答案不能为空")

    def save_answer_draft(self, session_id: int, payload: PracticeAnswerCreate, user: User) -> dict:
        session = self.get_owned_session(session_id, user)
        if session.status == "submitted":
            raise HTTPException(status_code=400, detail="会话已提交，不能保存答案")
        question, options, blanks = self._get_session_question_parts(session, payload.question_id)
        text_answers = self._normalize_text_answers(payload.text_answers)
        if question.type in {"single", "multiple"}:
            self._validate_option_ids(options, payload.selected_option_ids)
        else:
            payload.selected_option_ids = []
        existing = self.db.scalar(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id, PracticeAnswer.question_id == payload.question_id))
        if existing and existing.is_submitted and session.mode != "exam":
            return {"ok": True, "changed": False}
        if question.type in {"blank", "short_answer"} and not any(answer.strip() for answer in text_answers):
            if existing:
                self.db.delete(existing)
                self.db.commit()
                return {"ok": True, "changed": True}
            return {"ok": True, "changed": False}
        if question.type in {"single", "multiple"} and not payload.selected_option_ids:
            if existing:
                self.db.delete(existing)
                self.db.commit()
                return {"ok": True, "changed": True}
            return {"ok": True, "changed": False}
        if question.type in {"blank", "short_answer"}:
            is_correct = self._is_text_correct(question, blanks, text_answers) if question.type == "short_answer" or len(text_answers) == len(blanks) else False
        else:
            is_correct = self._is_correct(options, payload.selected_option_ids)
        if existing:
            if existing.selected_option_ids == payload.selected_option_ids and (existing.text_answers or []) == text_answers and existing.is_submitted == (session.mode == "exam"):
                return {"ok": True, "changed": False}
            existing.selected_option_ids = payload.selected_option_ids
            existing.text_answers = text_answers
            existing.is_correct = is_correct
            existing.is_submitted = session.mode == "exam"
            existing.answered_at = datetime.now(UTC)
        else:
            self.db.add(
                PracticeAnswer(
                    session_id=session.id,
                    question_id=question.id,
                    selected_option_ids=payload.selected_option_ids,
                    text_answers=text_answers,
                    is_correct=is_correct,
                    is_submitted=session.mode == "exam",
                )
            )
        self.db.commit()
        return {"ok": True, "changed": True}

    def answer_question(self, session_id: int, payload: PracticeAnswerCreate, user: User) -> PracticeAnswerOut:
        session = self.get_owned_session(session_id, user)
        question, options, blanks = self._get_session_question_parts(session, payload.question_id)

        existing = self.db.scalar(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id, PracticeAnswer.question_id == payload.question_id))
        if existing:
            if (session.mode != "exam" and existing.is_submitted) or session.status == "submitted":
                raise HTTPException(status_code=400, detail="这道题已经作答，不能重复修改")

        text_answers = self._normalize_text_answers(payload.text_answers)
        if question.type in {"single", "multiple"}:
            self._validate_option_ids(options, payload.selected_option_ids)
            correct_ids = [option.id for option in options if option.is_correct]
            is_correct = self._is_correct(options, payload.selected_option_ids)
        else:
            payload.selected_option_ids = []
            self._validate_text_answers(question, blanks, text_answers)
            correct_ids = []
            is_correct = self._is_text_correct(question, blanks, text_answers)
        if existing:
            existing.selected_option_ids = payload.selected_option_ids
            existing.text_answers = text_answers
            existing.is_correct = is_correct
            existing.is_submitted = True
            existing.answered_at = datetime.now(UTC)
        else:
            self.db.add(PracticeAnswer(session_id=session.id, question_id=payload.question_id, selected_option_ids=payload.selected_option_ids, text_answers=text_answers, is_correct=is_correct, is_submitted=True))
        if not is_correct and session.mode != "exam":
            self.mistakes.record_wrong_answer(user.id, session.bank_id, payload.question_id)
        self.db.commit()
        reveal = self.should_reveal(session)
        return PracticeAnswerOut(
            reveal=reveal,
            is_correct=is_correct if reveal else None,
            correct_option_ids=correct_ids if reveal else [],
            correct_labels=[option.label for option in options if option.is_correct] if reveal else [],
            correct_text_answers=self._correct_text_answers(blanks) if reveal else [],
            explanation=question.explanation if reveal else None,
        )

    def submit_session(self, session_id: int, user: User) -> PracticeSessionOut:
        session = self.get_owned_session(session_id, user)
        answers = self.db.scalars(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id)).all()
        if session.mode == "exam":
            for answer in answers:
                answer.is_submitted = True
        session.correct_count = sum(1 for answer in answers if answer.is_correct)
        session.score = round(session.correct_count / session.total_questions * 100, 2) if session.total_questions else 0
        if session.mode == "exam":
            for answer in answers:
                if not answer.is_correct:
                    self.mistakes.record_wrong_answer(user.id, session.bank_id, answer.question_id)
        session.status = "submitted"
        session.submitted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(session)
        return self.to_out(session)

    def result(self, session_id: int, user: User) -> list[PracticeResultAnswerOut]:
        session = self.get_owned_session(session_id, user)
        answers = self.db.scalars(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id)).all()
        answers_by_question = {answer.question_id: answer for answer in answers}
        rows = self.db.scalars(select(PracticeSessionQuestion).where(PracticeSessionQuestion.session_id == session.id).order_by(PracticeSessionQuestion.sort_order)).all()
        results = []
        for row in rows:
            question = self.db.scalar(select(Question).options(selectinload(Question.options), selectinload(Question.blanks)).where(Question.id == row.question_id))
            if not question:
                continue
            answer = answers_by_question.get(question.id)
            options = sorted(question.options, key=lambda item: item.sort_order)
            blanks = sorted(question.blanks, key=lambda item: item.sort_order)
            selected_ids = answer.selected_option_ids if answer and answer.is_submitted else []
            text_answers = answer.text_answers if answer and answer.is_submitted else []
            correct_ids = [option.id for option in options if option.is_correct]
            option_by_id = {option.id: option for option in options}
            results.append(
                PracticeResultAnswerOut(
                    question_id=question.id,
                    type=question.type,
                    stem=question.stem,
                    options=[PracticeResultOptionOut(id=option.id, label=option.label, content=option.content) for option in options],
                    blanks=[PracticeQuestionBlankOut.model_validate(blank, from_attributes=True) for blank in blanks],
                    selected_option_ids=selected_ids,
                    selected_labels=[option_by_id[id].label for id in selected_ids if id in option_by_id],
                    text_answers=text_answers,
                    correct_option_ids=correct_ids,
                    correct_labels=[option.label for option in options if option.is_correct],
                    correct_text_answers=self._correct_text_answers(blanks),
                    is_correct=bool(answer and answer.is_submitted and answer.is_correct),
                    is_unanswered=answer is None or not answer.is_submitted,
                    explanation=question.explanation,
                )
            )
        return results

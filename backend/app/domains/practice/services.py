import json
import random
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.queries import QuestionBankQueryService
from app.models.practice import MistakeAttempt, MistakeRecord, PracticeAnswer, PracticeSession, PracticeSessionQuestion
from app.models.question import Question, QuestionBlank, QuestionOption
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.practice import (
    MistakeAttemptOut,
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

    @staticmethod
    def _question_snapshot(question: Question, options: list[QuestionOption], blanks: list[QuestionBlank]) -> dict:
        correct_options = [option for option in options if option.is_correct]
        return {
            "type": question.type,
            "stem": question.stem,
            "options": [{"id": option.id, "label": option.label, "content": option.content} for option in options],
            "blanks": [{"id": blank.id, "label": blank.label, "sort_order": blank.sort_order} for blank in blanks],
            "correct_option_ids": [option.id for option in correct_options],
            "correct_labels": [option.label for option in correct_options],
            "correct_text_answers": [json.loads(blank.answers_json) for blank in blanks],
            "explanation": question.explanation,
        }

    @staticmethod
    def _user_answer_snapshot(answer: PracticeAnswer, options: list[QuestionOption]) -> dict:
        option_by_id = {option.id: option for option in options}
        selected_option_ids = answer.selected_option_ids or []
        return {
            "selected_option_ids": selected_option_ids,
            "selected_labels": [option_by_id[option_id].label for option_id in selected_option_ids if option_id in option_by_id],
            "text_answers": answer.text_answers or [],
        }

    def record_wrong_answer(self, user_id: int, session: PracticeSession, question: Question, options: list[QuestionOption], blanks: list[QuestionBlank], answer: PracticeAnswer) -> None:
        if answer.id:
            existing_attempt = self.db.scalar(select(MistakeAttempt).where(MistakeAttempt.practice_answer_id == answer.id))
            if existing_attempt:
                return
        bank_id = session.bank_id
        question_id = question.id
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
        self.db.add(
            MistakeAttempt(
                user_id=user_id,
                bank_id=bank_id,
                question_id=question_id,
                practice_session_id=session.id,
                practice_answer_id=answer.id,
                question_snapshot_json=self._question_snapshot(question, options, blanks),
                user_answer_json=self._user_answer_snapshot(answer, options),
            )
        )

    def rebuild_mistake_summary(self, user_id: int, bank_id: int, question_id: int) -> None:
        attempts = self.db.scalars(
            select(MistakeAttempt).where(
                MistakeAttempt.user_id == user_id,
                MistakeAttempt.bank_id == bank_id,
                MistakeAttempt.question_id == question_id,
            )
        ).all()
        mistake = self.db.scalar(
            select(MistakeRecord).where(
                MistakeRecord.user_id == user_id,
                MistakeRecord.bank_id == bank_id,
                MistakeRecord.question_id == question_id,
            )
        )
        if not attempts:
            if mistake:
                self.db.delete(mistake)
            return
        if not mistake:
            mistake = MistakeRecord(user_id=user_id, bank_id=bank_id, question_id=question_id)
            self.db.add(mistake)
        mistake.wrong_count = len(attempts)
        mistake.last_wrong_at = max(attempt.wrong_at for attempt in attempts)
        mistake.resolved_at = datetime.now(UTC) if all(attempt.is_resolved for attempt in attempts) else None

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

    @staticmethod
    def attempt_to_out(attempt: MistakeAttempt) -> MistakeAttemptOut:
        question_snapshot = attempt.question_snapshot_json or {}
        user_answer = attempt.user_answer_json or {}
        return MistakeAttemptOut(
            id=attempt.id,
            user_id=attempt.user_id,
            bank_id=attempt.bank_id,
            question_id=attempt.question_id,
            practice_session_id=attempt.practice_session_id,
            practice_answer_id=attempt.practice_answer_id,
            type=question_snapshot.get("type", "single"),
            stem=question_snapshot.get("stem", ""),
            options=[PracticeResultOptionOut(**option) for option in question_snapshot.get("options", [])],
            blanks=[PracticeQuestionBlankOut(**blank) for blank in question_snapshot.get("blanks", [])],
            selected_option_ids=user_answer.get("selected_option_ids", []),
            selected_labels=user_answer.get("selected_labels", []),
            text_answers=user_answer.get("text_answers", []),
            correct_option_ids=question_snapshot.get("correct_option_ids", []),
            correct_labels=question_snapshot.get("correct_labels", []),
            correct_text_answers=question_snapshot.get("correct_text_answers", []),
            explanation=question_snapshot.get("explanation"),
            is_resolved=attempt.is_resolved,
            wrong_at=attempt.wrong_at,
            resolved_at=attempt.resolved_at,
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

    def attempt_list_stmt(self, bank_id: int, user: User, resolved: bool | None = False):
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_view_own_mistakes(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        stmt = select(MistakeAttempt).where(MistakeAttempt.user_id == user.id, MistakeAttempt.bank_id == bank_id)
        if resolved is not None:
            stmt = stmt.where(MistakeAttempt.is_resolved.is_(resolved))
        return stmt.order_by(MistakeAttempt.wrong_at.desc(), MistakeAttempt.id.desc())

    def resolve_attempt(self, bank_id: int, attempt_id: int, user: User) -> None:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_view_own_mistakes(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        attempt = self.db.scalar(
            select(MistakeAttempt).where(
                MistakeAttempt.id == attempt_id,
                MistakeAttempt.user_id == user.id,
                MistakeAttempt.bank_id == bank_id,
            )
        )
        if not attempt:
            raise HTTPException(status_code=404, detail="Mistake attempt not found")
        attempt.is_resolved = True
        attempt.resolved_at = datetime.now(UTC)
        self.rebuild_mistake_summary(user.id, attempt.bank_id, attempt.question_id)
        self.db.commit()

    def unresolved_question_ids_for_bank(self, bank_id: int, user: User) -> list[int]:
        return self._dedup_question_ids(
            self.db.scalars(
                select(MistakeAttempt.question_id)
                .where(
                    MistakeAttempt.user_id == user.id,
                    MistakeAttempt.bank_id == bank_id,
                    MistakeAttempt.is_resolved.is_(False),
                )
                .order_by(MistakeAttempt.wrong_at.desc(), MistakeAttempt.id.desc())
            ).all()
        )

    def unresolved_question_ids_for_session(self, session_id: int, user: User) -> list[int]:
        return self._dedup_question_ids(
            self.db.scalars(
                select(MistakeAttempt.question_id)
                .where(
                    MistakeAttempt.user_id == user.id,
                    MistakeAttempt.practice_session_id == session_id,
                    MistakeAttempt.is_resolved.is_(False),
                )
                .order_by(MistakeAttempt.wrong_at.desc(), MistakeAttempt.id.desc())
            ).all()
        )

    @staticmethod
    def _dedup_question_ids(question_ids: list[int]) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for question_id in question_ids:
            if question_id in seen:
                continue
            seen.add(question_id)
            result.append(question_id)
        return result


class PracticeSessionService:
    def __init__(self, db: Session):
        self.db = db
        self.mistakes = MistakeService(db)

    def to_out(self, session: PracticeSession) -> PracticeSessionOut:
        answered_query = self.db.query(PracticeAnswer).filter(PracticeAnswer.session_id == session.id)
        if session.mode != "exam" or session.status == "submitted":
            answered_query = answered_query.filter(PracticeAnswer.is_submitted.is_(True))
        answered_count = answered_query.count()
        bank = self.db.get(QuestionBank, session.bank_id)
        last_answered_at = self.db.scalar(select(func.max(PracticeAnswer.answered_at)).where(PracticeAnswer.session_id == session.id))
        unresolved_mistakes = self.db.scalar(
            select(func.count())
            .select_from(MistakeAttempt)
            .where(
                MistakeAttempt.user_id == session.user_id,
                MistakeAttempt.practice_session_id == session.id,
                MistakeAttempt.is_resolved.is_(False),
            )
        )
        return PracticeSessionOut.model_validate(session, from_attributes=True).model_copy(
            update={
                "answered_count": answered_count,
                "bank_title": bank.title if bank else None,
                "bank_visibility": bank.visibility if bank else None,
                "bank_generation_status": bank.generation_status if bank else None,
                "last_answered_at": last_answered_at,
                "unresolved_mistake_attempt_count": unresolved_mistakes or 0,
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
            return self.create_mistake_review_session(bank.id, user, "bank", bank.id)
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

    def _existing_mistake_review_session(self, user: User, bank_id: int, source_type: str, source_id: int) -> PracticeSession | None:
        return self.db.scalar(
            select(PracticeSession).where(
                PracticeSession.user_id == user.id,
                PracticeSession.bank_id == bank_id,
                PracticeSession.mode == "mistake_review",
                PracticeSession.status == "in_progress",
                PracticeSession.mistake_source_type == source_type,
                PracticeSession.mistake_source_id == source_id,
            ).order_by(PracticeSession.started_at.desc(), PracticeSession.id.desc())
        )

    def create_mistake_review_session(self, bank_id: int, user: User, source_type: str = "bank", source_id: int | None = None, question_ids: list[int] | None = None) -> PracticeSessionOut:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_practice(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        actual_source_id = source_id if source_id is not None else bank_id
        existing = self._existing_mistake_review_session(user, bank.id, source_type, actual_source_id)
        if existing:
            return self.to_out(existing)
        if question_ids is None:
            question_ids = self.mistakes.unresolved_question_ids_for_bank(bank.id, user)
        questions = self.db.scalars(select(Question).where(Question.bank_id == bank.id, Question.id.in_(question_ids))).all() if question_ids else []
        by_id = {question.id: question for question in questions}
        ordered_questions = [by_id[question_id] for question_id in question_ids if question_id in by_id]
        if not ordered_questions:
            raise HTTPException(status_code=400, detail="没有可练习的错题")
        session = PracticeSession(
            user_id=user.id,
            bank_id=bank.id,
            mode="mistake_review",
            total_questions=len(ordered_questions),
            mistake_source_type=source_type,
            mistake_source_id=actual_source_id,
        )
        self.db.add(session)
        self.db.flush()
        for index, question in enumerate(ordered_questions):
            self.db.add(PracticeSessionQuestion(session_id=session.id, question_id=question.id, sort_order=index))
        self.db.commit()
        self.db.refresh(session)
        return self.to_out(session)

    def create_mistake_review_session_from_practice_session(self, session_id: int, user: User) -> PracticeSessionOut:
        source_session = self.get_owned_session(session_id, user)
        source_type = "mistake_session" if source_session.mode == "mistake_review" else "practice_session"
        question_ids = self.mistakes.unresolved_question_ids_for_session(source_session.id, user)
        return self.create_mistake_review_session(source_session.bank_id, user, source_type, source_session.id, question_ids)

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
                is_answered = answer.is_submitted or (session.mode == "exam" and session.status == "in_progress")
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

    @classmethod
    def _normalize_text_answers_for_question(cls, question: Question, blanks: list[QuestionBlank], text_answers: list[str] | None) -> list[str]:
        answers = cls._normalize_text_answers(text_answers)
        if question.type == "blank":
            blank_count = len(blanks)
            return (answers + [""] * blank_count)[:blank_count]
        if question.type == "short_answer":
            return [answers[0] if answers else ""]
        return answers

    @staticmethod
    def _correct_text_answers(blanks: list[QuestionBlank]) -> list[list[str]]:
        return [json.loads(blank.answers_json) for blank in blanks]

    @classmethod
    def _is_text_correct(cls, question: Question, blanks: list[QuestionBlank], text_answers: list[str]) -> bool:
        if question.type == "short_answer":
            return False
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

    def save_answer_draft(self, session_id: int, payload: PracticeAnswerCreate, user: User) -> dict:
        session = self.get_owned_session(session_id, user)
        if session.status == "submitted":
            raise HTTPException(status_code=400, detail="会话已提交，不能保存答案")
        question, options, blanks = self._get_session_question_parts(session, payload.question_id)
        text_answers = self._normalize_text_answers_for_question(question, blanks, payload.text_answers)
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
        is_correct = self._is_text_correct(question, blanks, text_answers) if question.type in {"blank", "short_answer"} else self._is_correct(options, payload.selected_option_ids)
        if existing:
            if existing.selected_option_ids == payload.selected_option_ids and (existing.text_answers or []) == text_answers and existing.is_submitted is False:
                return {"ok": True, "changed": False}
            existing.selected_option_ids = payload.selected_option_ids
            existing.text_answers = text_answers
            existing.is_correct = is_correct
            existing.is_submitted = False
            existing.answered_at = datetime.now(UTC)
        else:
            self.db.add(
                PracticeAnswer(
                    session_id=session.id,
                    question_id=question.id,
                    selected_option_ids=payload.selected_option_ids,
                    text_answers=text_answers,
                    is_correct=is_correct,
                    is_submitted=False,
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

        text_answers = self._normalize_text_answers_for_question(question, blanks, payload.text_answers)
        if question.type in {"single", "multiple"}:
            self._validate_option_ids(options, payload.selected_option_ids)
            correct_ids = [option.id for option in options if option.is_correct]
            is_correct = self._is_correct(options, payload.selected_option_ids)
        else:
            payload.selected_option_ids = []
            correct_ids = []
            is_correct = self._is_text_correct(question, blanks, text_answers)
        is_submitted = session.mode != "exam"
        if existing:
            existing.selected_option_ids = payload.selected_option_ids
            existing.text_answers = text_answers
            existing.is_correct = is_correct
            existing.is_submitted = is_submitted
            existing.answered_at = datetime.now(UTC)
            answer = existing
        else:
            answer = PracticeAnswer(session_id=session.id, question_id=payload.question_id, selected_option_ids=payload.selected_option_ids, text_answers=text_answers, is_correct=is_correct, is_submitted=is_submitted)
            self.db.add(answer)
        self.db.flush()
        if not is_correct and session.mode != "exam":
            self.mistakes.record_wrong_answer(user.id, session, question, options, blanks, answer)
        self.db.commit()
        reveal = self.should_reveal(session)
        return PracticeAnswerOut(
            is_submitted=is_submitted,
            reveal=reveal,
            is_correct=is_correct if reveal else None,
            correct_option_ids=correct_ids if reveal else [],
            correct_labels=[option.label for option in options if option.is_correct] if reveal else [],
            correct_text_answers=self._correct_text_answers(blanks) if reveal else [],
            explanation=question.explanation if reveal else None,
        )

    def submit_session(self, session_id: int, user: User, commit_drafts: bool = True) -> PracticeSessionOut:
        session = self.get_owned_session(session_id, user)
        if session.status == "submitted":
            return self.to_out(session)
        answers = self.db.scalars(select(PracticeAnswer).where(PracticeAnswer.session_id == session.id)).all()
        if session.mode == "exam" and commit_drafts:
            for answer in answers:
                answer.is_submitted = True
            self.db.flush()
        submitted_answers = [answer for answer in answers if answer.is_submitted]
        session.correct_count = sum(1 for answer in submitted_answers if answer.is_correct)
        session.score = round(session.correct_count / session.total_questions * 100, 2) if session.total_questions else 0
        if session.mode == "exam":
            for answer in submitted_answers:
                if not answer.is_correct:
                    question, options, blanks = self._get_session_question_parts(session, answer.question_id)
                    self.mistakes.record_wrong_answer(user.id, session, question, options, blanks, answer)
        session.status = "submitted"
        session.submitted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(session)
        return self.to_out(session)

    def delete_session(self, session_id: int, user: User) -> None:
        session = self.get_owned_session(session_id, user)
        affected = self.db.scalars(
            select(MistakeAttempt).where(
                MistakeAttempt.user_id == user.id,
                MistakeAttempt.practice_session_id == session.id,
            )
        ).all()
        affected_keys = {(attempt.user_id, attempt.bank_id, attempt.question_id) for attempt in affected}
        self.db.delete(session)
        self.db.flush()
        for attempt_user_id, bank_id, question_id in affected_keys:
            self.mistakes.rebuild_mistake_summary(attempt_user_id, bank_id, question_id)
        self.db.commit()

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

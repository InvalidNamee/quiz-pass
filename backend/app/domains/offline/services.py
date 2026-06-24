import hashlib
import json
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.domains.offline.schemas import (
    BankDownloadPackage,
    DownloadBankOut,
    DownloadBlankOut,
    DownloadOptionOut,
    DownloadOwnerOut,
    DownloadQuestionOut,
    DownloadTagOut,
    OfflinePracticeSessionIn,
    OfflinePracticeSyncFailure,
    OfflinePracticeSyncItem,
    OfflinePracticeSyncRequest,
    OfflinePracticeSyncResult,
)
from app.domains.practice.services import MistakeService, PracticeSessionService
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.models.practice import MistakeAttempt, PracticeAnswer, PracticeSession, PracticeSessionQuestion
from app.models.question import Question, QuestionBlank, QuestionOption
from app.models.question_bank import QuestionBank
from app.models.user import User


class BankDownloadPackageService:
    def __init__(self, db: Session):
        self.db = db

    def build_package(self, bank_id: int, user: User) -> BankDownloadPackage:
        bank = self.db.scalar(
            select(QuestionBank)
            .options(
                selectinload(QuestionBank.owner),
                selectinload(QuestionBank.tags),
                selectinload(QuestionBank.questions).selectinload(Question.options),
                selectinload(QuestionBank.questions).selectinload(Question.blanks),
            )
            .where(QuestionBank.id == bank_id)
        )
        if not QuestionBankPermissionService.can_read(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        assert bank is not None
        can_manage = QuestionBankPermissionService.can_manage(bank, user)
        bank_out = DownloadBankOut(
            id=bank.id,
            title=bank.title,
            description=bank.description,
            ai_context=bank.ai_context if can_manage else None,
            visibility=bank.visibility,
            generation_status=bank.generation_status,
            source_bank_id=bank.source_bank_id,
            is_shared_copy=bank.is_shared_copy,
            owner=DownloadOwnerOut(
                id=bank.owner_id,
                username=bank.owner.username if bank.owner else None,
                display_name=bank.owner.display_name if bank.owner else None,
                avatar_url=bank.owner.avatar_url if bank.owner else None,
            ),
            question_count=bank.question_count,
            favorite_count=bank.favorite_count,
            created_at=bank.created_at,
            updated_at=bank.updated_at,
        )
        tags = [DownloadTagOut(id=tag.id, name=tag.name) for tag in sorted(bank.tags, key=lambda item: item.name)]
        questions = [self._question_out(question) for question in sorted(bank.questions, key=lambda item: item.id)]
        exported_at = datetime.now(UTC)
        hash_payload = {
            "version": 1,
            "bank": bank_out.model_dump(mode="json"),
            "tags": [tag.model_dump(mode="json") for tag in tags],
            "questions": [question.model_dump(mode="json") for question in questions],
        }
        content_hash = hashlib.sha256(json.dumps(hash_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        return BankDownloadPackage(
            version=1,
            bank=bank_out,
            tags=tags,
            questions=questions,
            content_hash=content_hash,
            exported_at=exported_at,
        )

    @staticmethod
    def _question_out(question: Question) -> DownloadQuestionOut:
        options = sorted(question.options, key=lambda item: item.sort_order)
        blanks = sorted(question.blanks, key=lambda item: item.sort_order)
        return DownloadQuestionOut(
            id=question.id,
            bank_id=question.bank_id,
            type=question.type,
            stem=question.stem,
            explanation=question.explanation,
            difficulty=question.difficulty,
            source=question.source,
            generated_model=question.generated_model,
            options=[
                DownloadOptionOut(
                    id=option.id,
                    label=option.label,
                    content=option.content,
                    is_correct=option.is_correct,
                    sort_order=option.sort_order,
                )
                for option in options
            ],
            blanks=[
                DownloadBlankOut(
                    id=blank.id,
                    label=blank.label,
                    answers=blank.answers,
                    sort_order=blank.sort_order,
                )
                for blank in blanks
            ],
            created_at=question.created_at,
            updated_at=question.updated_at,
        )


class OfflinePracticeSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.practice = PracticeSessionService(db)
        self.mistakes = MistakeService(db)

    def sync(self, payload: OfflinePracticeSyncRequest, user: User) -> OfflinePracticeSyncResult:
        synced: list[OfflinePracticeSyncItem] = []
        failed: list[OfflinePracticeSyncFailure] = []
        for session_payload in payload.sessions:
            try:
                session = self._sync_one(payload.device_id, session_payload, user)
                self.db.commit()
                synced.append(OfflinePracticeSyncItem(client_session_id=session_payload.client_session_id, remote_session_id=session.id))
            except HTTPException as exc:
                self.db.rollback()
                failed.append(
                    OfflinePracticeSyncFailure(
                        client_session_id=session_payload.client_session_id,
                        code="SYNC_VALIDATION_FAILED",
                        message=str(exc.detail),
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive guard for batch isolation
                self.db.rollback()
                failed.append(
                    OfflinePracticeSyncFailure(
                        client_session_id=session_payload.client_session_id,
                        code="SYNC_FAILED",
                        message=str(exc),
                    )
                )
        return OfflinePracticeSyncResult(synced=synced, failed=failed)

    def _sync_one(self, device_id: str, payload: OfflinePracticeSessionIn, user: User) -> PracticeSession:
        existing = self.db.scalar(
            select(PracticeSession).where(
                PracticeSession.user_id == user.id,
                PracticeSession.offline_device_id == device_id,
                PracticeSession.offline_client_session_id == payload.client_session_id,
            )
        )
        if existing and existing.status == "submitted":
            return existing

        bank = self.db.get(QuestionBank, payload.remote_bank_id)
        if not QuestionBankPermissionService.can_practice(bank, user):
            raise HTTPException(status_code=404, detail="题库不可读或不可练习，无法同步")
        if len(set(payload.question_order)) != len(payload.question_order):
            raise HTTPException(status_code=422, detail="离线会话题目顺序包含重复题目")
        questions = self._questions_by_id(payload.remote_bank_id, payload.question_order)
        missing_question_ids = [question_id for question_id in payload.question_order if question_id not in questions]
        if missing_question_ids:
            raise HTTPException(status_code=422, detail=f"题目不属于当前题库：{missing_question_ids[:5]}")

        session = existing or PracticeSession(
            user_id=user.id,
            bank_id=payload.remote_bank_id,
            offline_device_id=device_id,
            offline_client_session_id=payload.client_session_id,
        )
        if not existing:
            self.db.add(session)
            self.db.flush()
        else:
            self._clear_synced_session(session, user.id)

        session.bank_id = payload.remote_bank_id
        session.mode = payload.mode
        session.status = payload.status
        session.total_questions = len(payload.question_order)
        session.correct_count = 0
        session.score = 0
        session.started_at = payload.started_at
        session.submitted_at = payload.submitted_at if payload.status == "submitted" else None
        session.offline_synced_at = datetime.now(UTC)

        for index, question_id in enumerate(payload.question_order):
            self.db.add(PracticeSessionQuestion(session_id=session.id, question_id=question_id, sort_order=index))
        self.db.flush()

        answers_by_question = {answer.question_id: answer for answer in payload.answers}
        persisted_answers: list[tuple[PracticeAnswer, Question, list[QuestionOption], list[QuestionBlank]]] = []
        for question_id in payload.question_order:
            answer_payload = answers_by_question.get(question_id)
            if not answer_payload:
                continue
            question = questions[question_id]
            options = sorted(question.options, key=lambda item: item.sort_order)
            blanks = sorted(question.blanks, key=lambda item: item.sort_order)
            text_answers = self.practice._normalize_text_answers_for_question(question, blanks, answer_payload.text_answers)
            selected_option_ids = list(answer_payload.selected_option_ids)
            if question.type in {"single", "multiple"}:
                self.practice._validate_option_ids(options, selected_option_ids)
                is_correct = self.practice._is_correct(options, selected_option_ids)
            else:
                selected_option_ids = []
                is_correct = self.practice._is_text_correct(question, blanks, text_answers)
            answer = PracticeAnswer(
                session_id=session.id,
                question_id=question.id,
                selected_option_ids=selected_option_ids,
                text_answers=text_answers,
                is_correct=is_correct,
                is_submitted=answer_payload.is_submitted,
                answered_at=answer_payload.answered_at or datetime.now(UTC),
            )
            self.db.add(answer)
            self.db.flush()
            persisted_answers.append((answer, question, options, blanks))

        submitted_answers = [answer for answer, _, _, _ in persisted_answers if answer.is_submitted]
        session.correct_count = sum(1 for answer in submitted_answers if answer.is_correct)
        session.score = round(session.correct_count / session.total_questions * 100, 2) if session.total_questions else 0
        if payload.status == "submitted" and not session.submitted_at:
            session.submitted_at = datetime.now(UTC)
        for answer, question, options, blanks in persisted_answers:
            if answer.is_submitted and not answer.is_correct:
                self.mistakes.record_wrong_answer(user.id, session, question, options, blanks, answer)
        self.db.flush()
        return session

    def _clear_synced_session(self, session: PracticeSession, user_id: int) -> None:
        affected_question_ids = set(
            self.db.scalars(
                select(MistakeAttempt.question_id).where(
                    MistakeAttempt.user_id == user_id,
                    MistakeAttempt.practice_session_id == session.id,
                )
            ).all()
        )
        self.db.execute(delete(MistakeAttempt).where(MistakeAttempt.practice_session_id == session.id))
        self.db.execute(delete(PracticeAnswer).where(PracticeAnswer.session_id == session.id))
        self.db.execute(delete(PracticeSessionQuestion).where(PracticeSessionQuestion.session_id == session.id))
        self.db.flush()
        for question_id in affected_question_ids:
            self.mistakes.rebuild_mistake_summary(user_id, session.bank_id, question_id)

    def _questions_by_id(self, bank_id: int, question_ids: list[int]) -> dict[int, Question]:
        if not question_ids:
            return {}
        questions = self.db.scalars(
            select(Question)
            .options(selectinload(Question.options), selectinload(Question.blanks))
            .where(Question.bank_id == bank_id, Question.id.in_(question_ids))
        ).all()
        return {question.id: question for question in questions}

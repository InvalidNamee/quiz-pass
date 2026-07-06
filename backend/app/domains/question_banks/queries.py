from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.ai_workflow import AIGenerationDraft, AIGenerationDraftQuestion, AIGenerationWorkflow
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.question_bank import QuestionBank, QuestionBankFavorite, QuestionBankTag, question_bank_tag_links
from app.models.user import User
from app.schemas.question_bank import QuestionBankTagOut
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.schemas import (
    ActiveWorkflowOut,
    BankPracticeProgressOut,
    QuestionBankOwnerOut,
    QuestionBankPermissionsOut,
    QuestionBankStatsOut,
    QuestionBankV2Out,
    ResumableSessionOut,
)


ACTIVE_WORKFLOW_STATUSES = {"pending", "extracting", "extracting_document", "calling_model", "validating", "repairing", "draft_ready"}
RESUMABLE_SENTINEL = object()
LATEST_PRACTICE_SENTINEL = object()


def parse_tag_ids(raw_tag_ids: str | None) -> list[int]:
    if not raw_tag_ids:
        return []
    tag_ids: list[int] = []
    for raw_id in raw_tag_ids.split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        if not raw_id.isdigit():
            raise ValueError("Invalid tag_ids")
        tag_ids.append(int(raw_id))
    return list(dict.fromkeys(tag_ids))


def apply_tag_filter(stmt, raw_tag_ids: str | None):
    tag_ids = parse_tag_ids(raw_tag_ids)
    if not tag_ids:
        return stmt
    bank_ids = select(question_bank_tag_links.c.bank_id).where(question_bank_tag_links.c.tag_id.in_(tag_ids))
    return stmt.where(QuestionBank.id.in_(bank_ids))


class QuestionBankQueryService:
    def __init__(self, db: Session):
        self.db = db

    def list_stmt(
        self,
        user: User,
        scope: str = "mine",
        keyword: str | None = None,
        owner_id: int | None = None,
        owner: str | None = None,
        tag_ids: str | None = None,
        visibility: str | None = None,
        generation_status: str | None = None,
    ):
        stmt = select(QuestionBank)
        if scope == "mine":
            stmt = stmt.where(QuestionBank.owner_id == user.id, QuestionBank.is_shared_copy.is_(False))
        elif scope == "shared":
            stmt = stmt.where(QuestionBank.owner_id == user.id, QuestionBank.is_shared_copy.is_(True))
        elif scope == "public":
            stmt = stmt.where(QuestionBank.visibility == "public", QuestionBank.generation_status.in_(["none", "succeeded"]))
        elif scope == "favorites":
            stmt = stmt.join(QuestionBankFavorite, QuestionBankFavorite.bank_id == QuestionBank.id).where(
                QuestionBankFavorite.user_id == user.id,
                or_(
                    QuestionBank.owner_id == user.id,
                    and_(QuestionBank.visibility == "public", QuestionBank.generation_status.in_(["none", "succeeded"])),
                    user.role == "admin",
                ),
            )
        elif scope == "admin":
            if user.role != "admin":
                stmt = stmt.where(False)
        else:
            raise ValueError("Invalid scope")

        if keyword:
            stmt = stmt.where(or_(QuestionBank.title.contains(keyword), QuestionBank.description.contains(keyword)))
        if scope not in {"mine", "shared"}:
            if owner_id:
                stmt = stmt.where(QuestionBank.owner_id == owner_id)
            elif owner and owner.strip():
                normalized_owner = owner.strip()
                if normalized_owner.isdigit():
                    stmt = stmt.where(QuestionBank.owner_id == int(normalized_owner))
                else:
                    owner_ids = select(User.id).where(or_(User.username.contains(normalized_owner), User.display_name.contains(normalized_owner)))
                    stmt = stmt.where(QuestionBank.owner_id.in_(owner_ids))
        if visibility:
            stmt = stmt.where(QuestionBank.visibility == visibility)
        if generation_status:
            stmt = stmt.where(QuestionBank.generation_status == generation_status)
        stmt = apply_tag_filter(stmt, tag_ids)
        if scope == "public":
            return stmt.order_by(QuestionBank.favorite_count.desc(), QuestionBank.updated_at.desc())
        return stmt.order_by(QuestionBank.updated_at.desc())

    def to_out(
        self,
        bank: QuestionBank,
        user: User | None,
        resumable_session: ResumableSessionOut | None | object = RESUMABLE_SENTINEL,
        latest_practice_session: BankPracticeProgressOut | None | object = LATEST_PRACTICE_SENTINEL,
    ) -> QuestionBankV2Out:
        favorite = False
        if user:
            favorite = bool(
                self.db.scalar(
                    select(QuestionBankFavorite).where(
                        QuestionBankFavorite.user_id == user.id,
                        QuestionBankFavorite.bank_id == bank.id,
                    )
                )
            )
        active_workflow = self._active_workflow(bank.id)
        if resumable_session is RESUMABLE_SENTINEL:
            resumable_session = self.resumable_session_for_bank(bank.id, user) if user else None
        if latest_practice_session is LATEST_PRACTICE_SENTINEL:
            latest_practice_session = self.latest_practice_session_for_bank(bank.id, user) if user else None
        owner = bank.owner
        permissions = QuestionBankPermissionService.permissions_for(bank, user)
        return QuestionBankV2Out(
            id=bank.id,
            owner_id=bank.owner_id,
            source_bank_id=bank.source_bank_id,
            is_shared_copy=bank.is_shared_copy,
            owner_username=owner.username if owner else None,
            owner_display_name=owner.display_name if owner else None,
            owner_avatar_url=owner.avatar_url if owner else None,
            title=bank.title,
            description=bank.description,
            ai_context=bank.ai_context if permissions.get("can_manage") else None,
            visibility=bank.visibility,
            desired_visibility=bank.desired_visibility,
            generation_status=bank.generation_status,
            owner=QuestionBankOwnerOut(
                id=bank.owner_id,
                username=owner.username if owner else None,
                display_name=owner.display_name if owner else None,
                avatar_url=owner.avatar_url if owner else None,
            ),
            tags=[QuestionBankTagOut.model_validate(tag, from_attributes=True) for tag in sorted(bank.tags, key=lambda item: item.name)],
            stats=QuestionBankStatsOut(question_count=bank.question_count, favorite_count=bank.favorite_count),
            question_count=bank.question_count,
            favorite_count=bank.favorite_count,
            permissions=QuestionBankPermissionsOut(**permissions),
            active_workflow=active_workflow,
            resumable_session=resumable_session,
            latest_practice_session=latest_practice_session,
            ai_model_name=bank.ai_model_name,
            is_favorited=favorite,
            created_at=bank.created_at,
            updated_at=bank.updated_at,
        )

    def to_out_many(self, banks: list[QuestionBank], user: User | None) -> list[QuestionBankV2Out]:
        bank_ids = [bank.id for bank in banks]
        resumable_by_bank = self.resumable_sessions_for_banks(bank_ids, user) if user else {}
        latest_by_bank = self.latest_practice_sessions_for_banks(bank_ids, user) if user else {}
        return [self.to_out(bank, user, resumable_by_bank.get(bank.id), latest_by_bank.get(bank.id)) for bank in banks]

    def latest_practice_session_for_bank(self, bank_id: int, user: User | None) -> BankPracticeProgressOut | None:
        if not user:
            return None
        return self.latest_practice_sessions_for_banks([bank_id], user).get(bank_id)

    def latest_practice_sessions_for_banks(self, bank_ids: list[int], user: User) -> dict[int, BankPracticeProgressOut]:
        sessions = self._sessions_for_banks(bank_ids, user)
        if not sessions:
            return {}
        session_ids = [session.id for session in sessions]
        last_answered, answered_counts = self._answer_metadata_for_sessions(session_ids)
        latest_by_bank: dict[int, PracticeSession] = {}
        for session in sessions:
            current = latest_by_bank.get(session.bank_id)
            if not current or self._practice_sort_key(session, last_answered) > self._practice_sort_key(current, last_answered):
                latest_by_bank[session.bank_id] = session
        return {
            bank_id: self._practice_progress_out(session, last_answered, answered_counts)
            for bank_id, session in latest_by_bank.items()
        }

    def recent_practice_banks_for_user(self, user: User, page_size: int = 6) -> list[QuestionBankV2Out]:
        page_size = max(1, min(page_size, 20))
        last_answered_subq = (
            select(PracticeAnswer.session_id, func.max(PracticeAnswer.answered_at).label("last_answered_at"))
            .group_by(PracticeAnswer.session_id)
            .subquery()
        )
        activity_at = func.coalesce(last_answered_subq.c.last_answered_at, PracticeSession.submitted_at, PracticeSession.started_at)
        sessions = self.db.scalars(
            select(PracticeSession)
            .outerjoin(last_answered_subq, last_answered_subq.c.session_id == PracticeSession.id)
            .where(PracticeSession.user_id == user.id)
            .order_by(activity_at.desc(), PracticeSession.id.desc())
        ).all()
        ordered_bank_ids: list[int] = []
        seen: set[int] = set()
        for session in sessions:
            if session.bank_id in seen:
                continue
            seen.add(session.bank_id)
            ordered_bank_ids.append(session.bank_id)
        if not ordered_bank_ids:
            return []
        banks = self.db.scalars(select(QuestionBank).where(QuestionBank.id.in_(ordered_bank_ids))).all()
        banks_by_id = {bank.id: bank for bank in banks}
        readable_banks: list[QuestionBank] = []
        for bank_id in ordered_bank_ids:
            bank = banks_by_id.get(bank_id)
            if QuestionBankPermissionService.can_read(bank, user):
                readable_banks.append(bank)
            if len(readable_banks) >= page_size:
                break
        return self.to_out_many(readable_banks, user)

    def resumable_session_for_bank(self, bank_id: int, user: User | None) -> ResumableSessionOut | None:
        if not user:
            return None
        return self.resumable_sessions_for_banks([bank_id], user).get(bank_id)

    def resumable_sessions_for_banks(self, bank_ids: list[int], user: User) -> dict[int, ResumableSessionOut]:
        sessions = self._sessions_for_banks(bank_ids, user, status="in_progress")
        if not sessions:
            return {}
        session_ids = [session.id for session in sessions]
        last_answered, answered_counts = self._answer_metadata_for_sessions(session_ids)
        latest_by_bank: dict[int, PracticeSession] = {}
        for session in sessions:
            current = latest_by_bank.get(session.bank_id)
            if not current or self._practice_sort_key(session, last_answered) > self._practice_sort_key(current, last_answered):
                latest_by_bank[session.bank_id] = session
        return {
            bank_id: ResumableSessionOut(
                id=session.id,
                mode=session.mode,
                total_questions=session.total_questions,
                answered_count=answered_counts.get(session.id, 0),
                started_at=session.started_at,
                last_answered_at=last_answered.get(session.id),
            )
            for bank_id, session in latest_by_bank.items()
        }

    def _sessions_for_banks(self, bank_ids: list[int], user: User, status: str | None = None) -> list[PracticeSession]:
        if not bank_ids:
            return []
        stmt = select(PracticeSession).where(
            PracticeSession.user_id == user.id,
            PracticeSession.bank_id.in_(bank_ids),
        )
        if status:
            stmt = stmt.where(PracticeSession.status == status)
        return list(self.db.scalars(stmt).all())

    def _answer_metadata_for_sessions(self, session_ids: list[int]) -> tuple[dict[int, datetime | None], dict[int, int]]:
        if not session_ids:
            return {}, {}
        last_answered = dict(
            self.db.execute(
                select(PracticeAnswer.session_id, func.max(PracticeAnswer.answered_at))
                .where(PracticeAnswer.session_id.in_(session_ids))
                .group_by(PracticeAnswer.session_id)
            ).all()
        )
        answered_counts = dict(
            self.db.execute(
                select(PracticeAnswer.session_id, func.count())
                .join(PracticeSession, PracticeSession.id == PracticeAnswer.session_id)
                .where(
                    PracticeAnswer.session_id.in_(session_ids),
                    or_(
                        PracticeAnswer.is_submitted.is_(True),
                        and_(PracticeSession.mode == "exam", PracticeSession.status == "in_progress"),
                    ),
                )
                .group_by(PracticeAnswer.session_id)
            ).all()
        )
        return last_answered, answered_counts

    @staticmethod
    def _practice_progress_out(session: PracticeSession, last_answered: dict[int, datetime | None], answered_counts: dict[int, int]) -> BankPracticeProgressOut:
        return BankPracticeProgressOut(
            id=session.id,
            mode=session.mode,
            status=session.status,
            total_questions=session.total_questions,
            answered_count=answered_counts.get(session.id, 0),
            correct_count=session.correct_count,
            score=session.score,
            started_at=session.started_at,
            submitted_at=session.submitted_at,
            last_answered_at=last_answered.get(session.id),
        )

    @staticmethod
    def _practice_sort_key(session: PracticeSession, last_answered: dict[int, datetime | None]) -> tuple[datetime, datetime, int]:
        return (last_answered.get(session.id) or session.submitted_at or session.started_at, session.started_at, session.id)

    def _active_workflow(self, bank_id: int) -> ActiveWorkflowOut | None:
        workflow = self.db.scalar(
            select(AIGenerationWorkflow)
            .where(AIGenerationWorkflow.bank_id == bank_id, AIGenerationWorkflow.status.in_(ACTIVE_WORKFLOW_STATUSES))
            .order_by(AIGenerationWorkflow.updated_at.desc(), AIGenerationWorkflow.id.desc())
        )
        if not workflow:
            return None
        draft = self.db.scalar(select(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        count = 0
        if draft:
            count = self.db.scalar(select(func.count()).select_from(AIGenerationDraftQuestion).where(AIGenerationDraftQuestion.draft_id == draft.id)) or 0
        return ActiveWorkflowOut(id=workflow.id, status=workflow.status, purpose=workflow.purpose, draft_question_count=count)


def list_tags_stmt(keyword: str | None = None, ids: str | None = None):
    stmt = select(QuestionBankTag)
    tag_ids = parse_tag_ids(ids)
    if tag_ids:
        stmt = stmt.where(QuestionBankTag.id.in_(tag_ids))
    if keyword:
        stmt = stmt.where(QuestionBankTag.name.contains(keyword.strip()))
    return stmt.order_by(QuestionBankTag.name.asc())

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
    QuestionBankOwnerOut,
    QuestionBankPermissionsOut,
    QuestionBankStatsOut,
    QuestionBankV2Out,
    ResumableSessionOut,
)


ACTIVE_WORKFLOW_STATUSES = {"pending", "extracting", "extracting_document", "calling_model", "validating", "repairing", "draft_ready"}
RESUMABLE_SENTINEL = object()


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
            stmt = stmt.where(QuestionBank.owner_id == user.id)
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
        if scope != "mine":
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

    def to_out(self, bank: QuestionBank, user: User | None, resumable_session: ResumableSessionOut | None | object = RESUMABLE_SENTINEL) -> QuestionBankV2Out:
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
            ai_model_name=bank.ai_model_name,
            is_favorited=favorite,
            created_at=bank.created_at,
            updated_at=bank.updated_at,
        )

    def to_out_many(self, banks: list[QuestionBank], user: User | None) -> list[QuestionBankV2Out]:
        resumable_by_bank = self.resumable_sessions_for_banks([bank.id for bank in banks], user) if user else {}
        return [self.to_out(bank, user, resumable_by_bank.get(bank.id)) for bank in banks]

    def resumable_session_for_bank(self, bank_id: int, user: User | None) -> ResumableSessionOut | None:
        if not user:
            return None
        return self.resumable_sessions_for_banks([bank_id], user).get(bank_id)

    def resumable_sessions_for_banks(self, bank_ids: list[int], user: User) -> dict[int, ResumableSessionOut]:
        if not bank_ids:
            return {}
        sessions = self.db.scalars(
            select(PracticeSession).where(
                PracticeSession.user_id == user.id,
                PracticeSession.bank_id.in_(bank_ids),
                PracticeSession.status == "in_progress",
            )
        ).all()
        if not sessions:
            return {}
        session_ids = [session.id for session in sessions]
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
                    or_(PracticeSession.mode == "exam", PracticeAnswer.is_submitted.is_(True)),
                )
                .group_by(PracticeAnswer.session_id)
            ).all()
        )
        latest_by_bank: dict[int, PracticeSession] = {}
        for session in sessions:
            current = latest_by_bank.get(session.bank_id)
            if not current or self._resumable_sort_key(session, last_answered) > self._resumable_sort_key(current, last_answered):
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

    @staticmethod
    def _resumable_sort_key(session: PracticeSession, last_answered: dict[int, datetime | None]) -> tuple[datetime, datetime, int]:
        return (last_answered.get(session.id) or session.started_at, session.started_at, session.id)

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

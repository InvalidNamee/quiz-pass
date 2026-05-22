from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.ai_workflow import AIGenerationDraft, AIGenerationDraftQuestion, AIGenerationWorkflow
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
)


ACTIVE_WORKFLOW_STATUSES = {"pending", "extracting", "extracting_document", "calling_model", "validating", "repairing", "draft_ready"}


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
        if owner_id and scope != "mine":
            stmt = stmt.where(QuestionBank.owner_id == owner_id)
        if visibility:
            stmt = stmt.where(QuestionBank.visibility == visibility)
        if generation_status:
            stmt = stmt.where(QuestionBank.generation_status == generation_status)
        stmt = apply_tag_filter(stmt, tag_ids)
        if scope == "public":
            return stmt.order_by(QuestionBank.favorite_count.desc(), QuestionBank.updated_at.desc())
        return stmt.order_by(QuestionBank.updated_at.desc())

    def to_out(self, bank: QuestionBank, user: User | None) -> QuestionBankV2Out:
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
        owner = bank.owner
        permissions = QuestionBankPermissionService.permissions_for(bank, user)
        return QuestionBankV2Out(
            id=bank.id,
            owner_id=bank.owner_id,
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
            ai_model_name=bank.ai_model_name,
            is_favorited=favorite,
            created_at=bank.created_at,
            updated_at=bank.updated_at,
        )

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

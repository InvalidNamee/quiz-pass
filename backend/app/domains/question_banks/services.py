from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domains.question_banks.lifecycle import QuestionBankLifecycleService
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.queries import QuestionBankQueryService
from app.domains.question_banks.schemas import QuestionBankAIContextUpdate, QuestionBankV2Create, QuestionBankV2Out, QuestionBankV2Update
from app.domains.question_banks.stats import QuestionBankStatsService
from app.models.question import Question, QuestionOption
from app.models.question_bank import QuestionBank, QuestionBankFavorite
from app.models.user import User
from app.domains.question_banks.tags import set_bank_tags
from app.infrastructure.audit import AuditService


class QuestionBankService:
    def __init__(self, db: Session):
        self.db = db
        self.query = QuestionBankQueryService(db)

    def get_readable(self, bank_id: int, user: User) -> QuestionBank:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_read(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        return bank

    def get_manageable(self, bank_id: int, user: User) -> QuestionBank:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_manage(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        return bank

    def create(self, payload: QuestionBankV2Create, user: User) -> QuestionBankV2Out:
        if payload.visibility == "public" and user.role != "admin":
            raise HTTPException(status_code=403, detail="普通用户只能通过分享生成公开题库")
        bank = QuestionBank(
            owner_id=user.id,
            title=payload.title,
            description=payload.description,
            ai_context=payload.ai_context,
            visibility=payload.visibility,
            desired_visibility=payload.visibility,
        )
        self.db.add(bank)
        self.db.flush()
        try:
            set_bank_tags(self.db, bank, payload.tag_names)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        self.db.commit()
        self.db.refresh(bank)
        return self.query.to_out(bank, user)

    def update(self, bank_id: int, payload: QuestionBankV2Update, user: User) -> QuestionBankV2Out:
        bank = self.get_manageable(bank_id, user)
        updates = payload.model_dump(exclude_unset=True)
        if updates.get("visibility") == "public" and user.role != "admin":
            raise HTTPException(status_code=403, detail="普通用户只能通过分享生成公开题库")
        tag_names = updates.pop("tag_names", None)
        for key, value in updates.items():
            setattr(bank, key, value)
            if key == "visibility":
                bank.desired_visibility = value
        if "tag_names" in payload.model_fields_set:
            try:
                set_bank_tags(self.db, bank, tag_names)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        self.db.commit()
        self.db.refresh(bank)
        return self.query.to_out(bank, user)

    def share(self, bank_id: int, user: User) -> QuestionBankV2Out:
        source = self.db.scalar(
            select(QuestionBank)
            .options(selectinload(QuestionBank.tags), selectinload(QuestionBank.questions).selectinload(Question.options))
            .where(QuestionBank.id == bank_id)
        )
        if not QuestionBankPermissionService.can_share(source, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        shared = QuestionBank(
            owner_id=user.id,
            source_bank_id=source.id,
            is_shared_copy=True,
            title=source.title,
            description=source.description,
            visibility="public",
            desired_visibility="public",
            generation_status="succeeded",
            ai_model_name=source.ai_model_name,
            ai_base_url_host=source.ai_base_url_host,
        )
        self.db.add(shared)
        self.db.flush()
        set_bank_tags(self.db, shared, [tag.name for tag in source.tags])
        for source_question in sorted(source.questions, key=lambda item: item.id):
            question = Question(
                bank_id=shared.id,
                type=source_question.type,
                stem=source_question.stem,
                explanation=source_question.explanation,
                difficulty=source_question.difficulty,
                source=source_question.source,
                generated_model=source_question.generated_model,
            )
            self.db.add(question)
            self.db.flush()
            for option in sorted(source_question.options, key=lambda item: item.sort_order):
                self.db.add(
                    QuestionOption(
                        question_id=question.id,
                        label=option.label,
                        content=option.content,
                        is_correct=option.is_correct,
                        sort_order=option.sort_order,
                    )
                )
        QuestionBankStatsService.rebuild_bank_stats(self.db, shared.id)
        AuditService(self.db).record(user.id, "bank.share", "bank", source.id, {"shared_bank_id": shared.id})
        self.db.commit()
        self.db.refresh(shared)
        return self.query.to_out(shared, user)

    def update_ai_context(self, bank_id: int, payload: QuestionBankAIContextUpdate, user: User) -> QuestionBankV2Out:
        bank = self.get_manageable(bank_id, user)
        bank.ai_context = (payload.ai_context or "").strip() or None
        self.db.commit()
        self.db.refresh(bank)
        return self.query.to_out(bank, user)

    def delete(self, bank_id: int, user: User) -> None:
        bank = self.get_manageable(bank_id, user)
        AuditService(self.db).record(user.id, "bank.delete", "bank", bank.id, {"title": bank.title})
        QuestionBankLifecycleService(self.db).delete_bank(bank)
        self.db.commit()

    def favorite(self, bank_id: int, user: User) -> None:
        bank = self.get_readable(bank_id, user)
        existing = self.db.scalar(select(QuestionBankFavorite).where(QuestionBankFavorite.user_id == user.id, QuestionBankFavorite.bank_id == bank_id))
        if not existing:
            self.db.add(QuestionBankFavorite(user_id=user.id, bank_id=bank_id))
            QuestionBankStatsService.increment_favorites(self.db, bank)
            self.db.commit()

    def unfavorite(self, bank_id: int, user: User) -> None:
        favorite = self.db.scalar(select(QuestionBankFavorite).where(QuestionBankFavorite.user_id == user.id, QuestionBankFavorite.bank_id == bank_id))
        if favorite:
            bank = self.db.get(QuestionBank, bank_id)
            self.db.delete(favorite)
            if bank:
                QuestionBankStatsService.decrement_favorites(self.db, bank)
            self.db.commit()

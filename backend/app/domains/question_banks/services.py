from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.question_banks.lifecycle import QuestionBankLifecycleService
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.queries import QuestionBankQueryService
from app.domains.question_banks.schemas import QuestionBankV2Create, QuestionBankV2Out, QuestionBankV2Update
from app.domains.question_banks.stats import QuestionBankStatsService
from app.models.question_bank import QuestionBank, QuestionBankFavorite
from app.models.user import User
from app.services.question_bank_tags import set_bank_tags


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
        bank = QuestionBank(
            owner_id=user.id,
            title=payload.title,
            description=payload.description,
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

    def delete(self, bank_id: int, user: User) -> None:
        bank = self.get_manageable(bank_id, user)
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

from app.models.question_bank import QuestionBank
from app.models.user import User


class QuestionBankPermissionService:
    """Centralized permission policy for question banks."""

    @staticmethod
    def can_read(bank: QuestionBank | None, user: User | None) -> bool:
        if not bank:
            return False
        if user and (bank.owner_id == user.id or user.role == "admin"):
            return True
        return bank.visibility == "public" and bank.generation_status in {"none", "succeeded"}

    @staticmethod
    def can_manage(bank: QuestionBank | None, user: User | None) -> bool:
        if not bank or not user:
            return False
        if user.role == "admin":
            return True
        if bank.visibility == "public" or bank.is_shared_copy:
            return False
        return bank.owner_id == user.id

    @classmethod
    def can_export(cls, bank: QuestionBank | None, user: User | None) -> bool:
        return cls.can_read(bank, user)

    @classmethod
    def can_practice(cls, bank: QuestionBank | None, user: User | None) -> bool:
        return cls.can_read(bank, user) and bool(bank and bank.generation_status in {"none", "succeeded"})

    @classmethod
    def can_view_own_mistakes(cls, bank: QuestionBank | None, user: User | None) -> bool:
        return cls.can_read(bank, user)

    @classmethod
    def can_extend_with_ai(cls, bank: QuestionBank | None, user: User | None) -> bool:
        return cls.can_manage(bank, user)

    @classmethod
    def can_share(cls, bank: QuestionBank | None, user: User | None) -> bool:
        if not bank or not user:
            return False
        if bank.is_shared_copy:
            return False
        if bank.question_count <= 0:
            return False
        if bank.generation_status not in {"none", "succeeded"}:
            return False
        return bank.owner_id == user.id or user.role == "admin"

    @classmethod
    def permissions_for(cls, bank: QuestionBank, user: User | None) -> dict[str, bool]:
        return {
            "can_read": cls.can_read(bank, user),
            "can_manage": cls.can_manage(bank, user),
            "can_export": cls.can_export(bank, user),
            "can_practice": cls.can_practice(bank, user),
            "can_view_mistakes": cls.can_view_own_mistakes(bank, user),
            "can_extend_ai": cls.can_extend_with_ai(bank, user),
            "can_share": cls.can_share(bank, user),
        }

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.users.services import AIProviderService, UserProfileService
from app.models.user import User
from app.schemas.ai import AIProviderConfigCreate, AIProviderConfigOut, AIProviderConfigUpdate
from app.schemas.common import Page
from app.schemas.question_bank import QuestionBankOut
from app.schemas.user import PasswordChange, UserMe, UserPublic, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserMe)
def update_me(payload: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserProfileService(db).update_me(current_user, payload)


@router.post("/me/change-password")
def change_password(payload: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserProfileService(db).change_password(current_user, payload)


@router.get("/search", response_model=Page[UserPublic])
def search_users(
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UserProfileService(db).search_users(page, page_size, keyword)


@router.get("/{user_id}", response_model=UserPublic)
def get_public_user(user_id: int, db: Session = Depends(get_db)):
    return UserProfileService(db).public_user(user_id)


@router.get("/{user_id}/public-question-banks", response_model=list[QuestionBankOut])
def get_public_user_banks(user_id: int, db: Session = Depends(get_db)):
    banks = UserProfileService(db).public_banks_for_user(user_id)
    return [
        QuestionBankOut.model_validate(bank, from_attributes=True).model_copy(
            update={
                "owner_username": bank.owner.username if bank.owner else None,
                "owner_display_name": bank.owner.display_name if bank.owner else None,
                "owner_avatar_url": bank.owner.avatar_url if bank.owner else None,
            }
        )
        for bank in banks
    ]


@router.get("/me/ai-provider-configs", response_model=list[AIProviderConfigOut])
def list_ai_configs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).list_configs(current_user)


@router.post("/me/ai-provider-configs", response_model=AIProviderConfigOut)
def create_ai_config(payload: AIProviderConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).create_config(current_user, payload)


@router.patch("/me/ai-provider-configs/{config_id}", response_model=AIProviderConfigOut)
def update_ai_config(config_id: int, payload: AIProviderConfigUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).update_config(config_id, current_user, payload)


@router.post("/me/ai-provider-configs/{config_id}/set-default", response_model=AIProviderConfigOut)
def set_default_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).set_default(config_id, current_user)


@router.post("/me/ai-provider-configs/{config_id}/test")
def test_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).test_config(config_id, current_user)


@router.delete("/me/ai-provider-configs/{config_id}")
def delete_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).delete_config(config_id, current_user)

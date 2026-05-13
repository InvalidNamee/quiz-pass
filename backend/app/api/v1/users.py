import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.ai import AIProviderConfigCreate, AIProviderConfigOut, AIProviderConfigUpdate
from app.schemas.question_bank import QuestionBankOut
from app.schemas.user import PasswordChange, UserMe, UserPublic, UserUpdate
from app.utils.avatar import build_qq_avatar_url
from app.utils.crypto import decrypt_secret, encrypt_secret

router = APIRouter()


@router.get("/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserMe)
def update_me(payload: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    updates = payload.model_dump(exclude_unset=True)
    if "avatar_source" in updates:
        source = updates["avatar_source"]
        current_user.avatar_source = source
        if source == "qq_email":
            current_user.avatar_url = build_qq_avatar_url(current_user.email)
        elif source == "default":
            current_user.avatar_url = None
    if updates.get("avatar_source") != "qq_email" and "avatar_url" in updates:
        current_user.avatar_url = updates["avatar_url"]
    for field in ("display_name", "bio"):
        if field in updates:
            setattr(current_user, field, updates[field])
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password")
def change_password(payload: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"ok": True}


@router.get("/{user_id}", response_model=UserPublic)
def get_public_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    count = db.scalar(
        select(func.count()).select_from(QuestionBank).where(
            QuestionBank.owner_id == user.id,
            QuestionBank.visibility == "public",
            QuestionBank.generation_status.in_(["none", "succeeded"]),
        )
    ) or 0
    return UserPublic.model_validate(user, from_attributes=True).model_copy(update={"public_bank_count": count})


@router.get("/{user_id}/public-question-banks", response_model=list[QuestionBankOut])
def get_public_user_banks(user_id: int, db: Session = Depends(get_db)):
    banks = db.scalars(
        select(QuestionBank).where(
            QuestionBank.owner_id == user_id,
            QuestionBank.visibility == "public",
            QuestionBank.generation_status.in_(["none", "succeeded"]),
        )
    ).all()
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
    return db.scalars(select(UserAIProviderConfig).where(UserAIProviderConfig.user_id == current_user.id)).all()


@router.post("/me/ai-provider-configs", response_model=AIProviderConfigOut)
def create_ai_config(payload: AIProviderConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.is_default:
        db.query(UserAIProviderConfig).filter(UserAIProviderConfig.user_id == current_user.id).update({"is_default": False})
    config = UserAIProviderConfig(
        user_id=current_user.id,
        name=payload.name,
        api_base_url=payload.api_base_url,
        api_key_encrypted=encrypt_secret(payload.api_key),
        model=payload.model,
        is_default=payload.is_default,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.patch("/me/ai-provider-configs/{config_id}", response_model=AIProviderConfigOut)
def update_ai_config(config_id: int, payload: AIProviderConfigUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = db.get(UserAIProviderConfig, config_id)
    if not config or config.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="AI config not found")
    updates = payload.model_dump(exclude_unset=True)
    if "api_key" in updates:
        raise HTTPException(status_code=400, detail="API Key 保存后不可修改，请删除配置后重新创建")
    if updates.get("is_default"):
        db.query(UserAIProviderConfig).filter(UserAIProviderConfig.user_id == current_user.id).update({"is_default": False})
    for field in ("name", "api_base_url", "model", "is_default", "is_active"):
        if field in updates:
            setattr(config, field, updates[field])
    db.commit()
    db.refresh(config)
    return config


@router.post("/me/ai-provider-configs/{config_id}/set-default", response_model=AIProviderConfigOut)
def set_default_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = db.get(UserAIProviderConfig, config_id)
    if not config or config.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="AI config not found")
    db.query(UserAIProviderConfig).filter(UserAIProviderConfig.user_id == current_user.id).update({"is_default": False})
    config.is_default = True
    config.is_active = True
    db.commit()
    db.refresh(config)
    return config


@router.post("/me/ai-provider-configs/{config_id}/test")
def test_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = db.get(UserAIProviderConfig, config_id)
    if not config or config.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="AI config not found")
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"{config.api_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {decrypt_secret(config.api_key_encrypted)}"},
            )
            response.raise_for_status()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AI 配置连通性测试失败: {exc}") from exc


@router.delete("/me/ai-provider-configs/{config_id}")
def delete_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = db.get(UserAIProviderConfig, config_id)
    if not config or config.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="AI config not found")
    db.delete(config)
    db.commit()
    return {"ok": True}

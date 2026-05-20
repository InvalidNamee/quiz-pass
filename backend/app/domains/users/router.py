from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.domains.users.services import AdminUserService, AIProviderService, UserAuthService, UserProfileService
from app.models.user import User
from app.schemas.ai import AIProviderConfigCreate, AIProviderConfigOut, AIProviderConfigUpdate
from app.schemas.common import Page
from app.schemas.user import AdminPasswordResetOut, AdminUserUpdate, AuthMessage, EmailRequest, PasswordChange, PasswordResetConfirm, RefreshTokenRequest, Token, UserCreate, UserLogin, UserMe, UserPublic, UserUpdate

router = APIRouter()


@router.post("/auth/register", response_model=AuthMessage)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    return UserAuthService(db).register(payload)


@router.post("/auth/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    return UserAuthService(db).login(payload.identifier, payload.email, payload.password)


@router.post("/auth/refresh", response_model=Token)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    return UserAuthService(db).refresh(payload.refresh_token)


@router.post("/auth/resend-verification", response_model=AuthMessage)
def resend_verification(payload: EmailRequest, db: Session = Depends(get_db)):
    return UserAuthService(db).resend_verification(str(payload.email))


@router.get("/auth/verify-email", response_model=AuthMessage)
def verify_email(token: str, db: Session = Depends(get_db)):
    return UserAuthService(db).verify_email(token)


@router.post("/auth/forgot-password", response_model=AuthMessage)
def forgot_password(payload: EmailRequest, db: Session = Depends(get_db)):
    return UserAuthService(db).forgot_password(str(payload.email))


@router.post("/auth/reset-password", response_model=AuthMessage)
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    return UserAuthService(db).reset_password(payload.token, payload.new_password)


@router.get("/auth/me", response_model=UserMe)
def auth_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/users/me", response_model=UserMe)
def update_me(payload: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserProfileService(db).update_me(current_user, payload)


@router.post("/users/me/change-password")
def change_password(payload: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserProfileService(db).change_password(current_user, payload)


@router.get("/users/search", response_model=Page[UserPublic])
def search_users(page: int = 1, page_size: int = 10, keyword: str | None = None, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserProfileService(db).search_users(page, page_size, keyword)


@router.get("/users/{user_id}", response_model=UserPublic)
def get_public_user(user_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserProfileService(db).public_user(user_id)


@router.get("/users/me/ai-provider-configs", response_model=list[AIProviderConfigOut])
def list_ai_configs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).list_configs(current_user)


@router.post("/users/me/ai-provider-configs", response_model=AIProviderConfigOut)
def create_ai_config(payload: AIProviderConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).create_config(current_user, payload)


@router.patch("/users/me/ai-provider-configs/{config_id}", response_model=AIProviderConfigOut)
def update_ai_config(config_id: int, payload: AIProviderConfigUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).update_config(config_id, current_user, payload)


@router.post("/users/me/ai-provider-configs/{config_id}/set-default", response_model=AIProviderConfigOut)
def set_default_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).set_default(config_id, current_user)


@router.post("/users/me/ai-provider-configs/{config_id}/test")
def test_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).test_config(config_id, current_user)


@router.delete("/users/me/ai-provider-configs/{config_id}")
def delete_ai_config(config_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIProviderService(db).delete_config(config_id, current_user)


@router.get("/admin/users", response_model=Page[UserMe])
def list_admin_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminUserService(db).list_users(page, page_size, keyword, role, is_active)


@router.patch("/admin/users/{user_id}", response_model=UserMe)
def update_admin_user(user_id: int, payload: AdminUserUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return AdminUserService(db).update_user(user_id, payload)


@router.post("/admin/users/{user_id}/reset-password", response_model=AdminPasswordResetOut)
def reset_admin_user_password(user_id: int, current_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return AdminUserService(db).reset_password(user_id, current_admin)

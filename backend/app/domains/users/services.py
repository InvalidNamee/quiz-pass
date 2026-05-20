import secrets
import string

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.ai import AIProviderConfigCreate, AIProviderConfigUpdate
from app.schemas.common import page_response
from app.schemas.user import AdminPasswordResetOut, AdminUserUpdate, PasswordChange, Token, UserCreate, UserPublic, UserUpdate
from app.utils.avatar import build_qq_avatar_url
from app.utils.crypto import decrypt_secret, encrypt_secret
from app.utils.pagination import paginate


class UserAuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, payload: UserCreate) -> Token:
        email = str(payload.email).strip()
        username = payload.username.strip()
        existing = self.db.scalar(select(User).where((User.email == email) | (User.username == username)))
        if existing:
            raise HTTPException(status_code=400, detail="Email or username already exists")
        user = User(
            email=email,
            username=username,
            display_name=username,
            password_hash=get_password_hash(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self.issue_tokens(user)

    def login(self, identifier: str | None, legacy_email: object, password: str) -> Token:
        normalized = (identifier or str(legacy_email or "")).strip()
        if not normalized:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名/邮箱或密码错误")
        field = User.email if "@" in normalized else User.username
        user = self.db.scalar(select(User).where(field == normalized))
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名/邮箱或密码错误")
        return self.issue_tokens(user)

    def refresh(self, refresh_token: str) -> Token:
        payload = decode_token(refresh_token)
        if not payload or payload.get("token_type") != "refresh" or not payload.get("sub"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user = self.db.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        return Token(access_token=create_access_token(str(user.id), user.role), refresh_token=refresh_token)

    @staticmethod
    def issue_tokens(user: User) -> Token:
        subject = str(user.id)
        return Token(
            access_token=create_access_token(subject, user.role),
            refresh_token=create_refresh_token(subject, user.role),
        )


class UserProfileService:
    def __init__(self, db: Session):
        self.db = db

    def update_me(self, user: User, payload: UserUpdate) -> User:
        updates = payload.model_dump(exclude_unset=True)
        if "avatar_source" in updates:
            source = updates["avatar_source"]
            user.avatar_source = source
            if source == "qq_email":
                user.avatar_url = build_qq_avatar_url(user.email)
            elif source == "default":
                user.avatar_url = None
        if updates.get("avatar_source") != "qq_email" and "avatar_url" in updates:
            user.avatar_url = updates["avatar_url"]
        for field in ("display_name", "bio"):
            if field in updates:
                setattr(user, field, updates[field])
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user: User, payload: PasswordChange) -> dict:
        if not verify_password(payload.old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="旧密码不正确")
        user.password_hash = get_password_hash(payload.new_password)
        self.db.commit()
        return {"ok": True}

    def public_user(self, user_id: int) -> UserPublic:
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        count = self.public_bank_count([user.id]).get(user.id, 0)
        return UserPublic.model_validate(user, from_attributes=True).model_copy(update={"public_bank_count": count})

    def public_banks_for_user(self, user_id: int) -> list[QuestionBank]:
        return self.db.scalars(
            select(QuestionBank).where(
                QuestionBank.owner_id == user_id,
                QuestionBank.visibility == "public",
                QuestionBank.generation_status.in_(["none", "succeeded"]),
            )
        ).all()

    def search_users(self, page: int = 1, page_size: int = 10, keyword: str | None = None):
        stmt = select(User).where(User.is_active.is_(True))
        if keyword:
            stmt = stmt.where(or_(User.username.contains(keyword), User.display_name.contains(keyword)))
        stmt = stmt.order_by(User.username.asc())
        users, total, page, page_size = paginate(self.db, stmt, page, page_size)
        counts = self.public_bank_count([user.id for user in users])
        items = [UserPublic.model_validate(user, from_attributes=True).model_copy(update={"public_bank_count": counts.get(user.id, 0)}) for user in users]
        return page_response(items, total, page, page_size)

    def public_bank_count(self, user_ids: list[int]) -> dict[int, int]:
        if not user_ids:
            return {}
        return dict(
            self.db.execute(
                select(QuestionBank.owner_id, func.count())
                .where(
                    QuestionBank.owner_id.in_(user_ids),
                    QuestionBank.visibility == "public",
                    QuestionBank.generation_status.in_(["none", "succeeded"]),
                )
                .group_by(QuestionBank.owner_id)
            ).all()
        )


class AIProviderService:
    def __init__(self, db: Session):
        self.db = db

    def list_configs(self, user: User) -> list[UserAIProviderConfig]:
        return self.db.scalars(select(UserAIProviderConfig).where(UserAIProviderConfig.user_id == user.id)).all()

    def create_config(self, user: User, payload: AIProviderConfigCreate) -> UserAIProviderConfig:
        if payload.is_default:
            self.clear_default(user.id)
        config = UserAIProviderConfig(
            user_id=user.id,
            name=payload.name,
            api_base_url=payload.api_base_url,
            api_key_encrypted=encrypt_secret(payload.api_key),
            model=payload.model,
            is_default=payload.is_default,
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update_config(self, config_id: int, user: User, payload: AIProviderConfigUpdate) -> UserAIProviderConfig:
        config = self.get_owned_config(config_id, user)
        updates = payload.model_dump(exclude_unset=True)
        if "api_key" in updates:
            raise HTTPException(status_code=400, detail="API Key 保存后不可修改，请删除配置后重新创建")
        if updates.get("is_default"):
            self.clear_default(user.id)
        for field in ("name", "api_base_url", "model", "is_default", "is_active"):
            if field in updates:
                setattr(config, field, updates[field])
        self.db.commit()
        self.db.refresh(config)
        return config

    def set_default(self, config_id: int, user: User) -> UserAIProviderConfig:
        config = self.get_owned_config(config_id, user)
        self.clear_default(user.id)
        config.is_default = True
        config.is_active = True
        self.db.commit()
        self.db.refresh(config)
        return config

    def test_config(self, config_id: int, user: User) -> dict:
        config = self.get_owned_config(config_id, user)
        try:
            client = OpenAI(api_key=decrypt_secret(config.api_key_encrypted), base_url=config.api_base_url.rstrip("/"), timeout=20)
            client.models.list()
            return {"ok": True}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"AI 配置连通性测试失败: {exc}") from exc

    def delete_config(self, config_id: int, user: User) -> dict:
        config = self.get_owned_config(config_id, user)
        self.db.delete(config)
        self.db.commit()
        return {"ok": True}

    def get_owned_config(self, config_id: int, user: User) -> UserAIProviderConfig:
        config = self.db.get(UserAIProviderConfig, config_id)
        if not config or config.user_id != user.id:
            raise HTTPException(status_code=404, detail="AI config not found")
        return config

    def clear_default(self, user_id: int) -> None:
        self.db.query(UserAIProviderConfig).filter(UserAIProviderConfig.user_id == user_id).update({"is_default": False})


class AdminUserService:
    def __init__(self, db: Session):
        self.db = db

    def list_users(self, page: int = 1, page_size: int = 20, keyword: str | None = None, role: str | None = None, is_active: bool | None = None):
        stmt = select(User)
        if keyword:
            stmt = stmt.where(or_(User.email.contains(keyword), User.username.contains(keyword), User.display_name.contains(keyword)))
        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        stmt = stmt.order_by(User.created_at.desc())
        items, total, page, page_size = paginate(self.db, stmt, page, page_size)
        return page_response(items, total, page, page_size)

    def update_user(self, user_id: int, payload: AdminUserUpdate) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        updates = payload.model_dump(exclude_unset=True)
        for field in ("display_name", "bio", "is_active"):
            if field in updates:
                setattr(user, field, updates[field])
        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_password(self, user_id: int, current_admin: User) -> AdminPasswordResetOut:
        if user_id == current_admin.id:
            raise HTTPException(status_code=400, detail="不能重置自己的密码，请使用修改密码功能")
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        temporary_password = self.temporary_password()
        user.password_hash = get_password_hash(temporary_password)
        self.db.commit()
        return AdminPasswordResetOut(temporary_password=temporary_password)

    @staticmethod
    def temporary_password(length: int = 14) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

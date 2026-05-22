import hashlib
import html
import secrets
import string
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.core.config import get_settings
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.question_bank import QuestionBank
from app.models.user import EmailAuthToken, User
from app.schemas.ai import AIProviderConfigCreate, AIProviderConfigUpdate
from app.schemas.common import page_response
from app.schemas.user import AdminPasswordResetOut, AdminUserUpdate, AuthMessage, PasswordChange, Token, UserCreate, UserPublic, UserUpdate
from app.utils.avatar import build_qq_avatar_url
from app.utils.crypto import decrypt_secret, encrypt_secret
from app.utils.pagination import paginate
from app.services.email_delivery import EmailDeliveryService


class UserAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.email_delivery = EmailDeliveryService()

    def register(self, payload: UserCreate) -> AuthMessage:
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
        self.db.flush()
        token = self.create_email_token(user, "email_verify", self.settings.email_verify_token_expire_hours * 60)
        self.db.commit()
        self.send_verification_email(user.email, token)
        return self.message("请查收邮箱完成验证", token)

    def login(self, identifier: str | None, legacy_email: object, password: str) -> Token:
        normalized = (identifier or str(legacy_email or "")).strip()
        if not normalized:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名/邮箱或密码错误")
        field = User.email if "@" in normalized else User.username
        user = self.db.scalar(select(User).where(field == normalized))
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名/邮箱或密码错误")
        if not user.email_verified_at:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="请先验证邮箱")
        return self.issue_tokens(user)

    def refresh(self, refresh_token: str) -> Token:
        payload = decode_token(refresh_token)
        if not payload or payload.get("token_type") != "refresh" or not payload.get("sub"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user = self.db.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        return Token(access_token=create_access_token(str(user.id), user.role), refresh_token=refresh_token)

    def resend_verification(self, email: str) -> AuthMessage:
        user = self.db.scalar(select(User).where(User.email == str(email).strip()))
        if not user:
            return AuthMessage(ok=True, message="如果邮箱存在，验证邮件已发送")
        if user.email_verified_at:
            return AuthMessage(ok=True, message="邮箱已验证")
        token = self.create_email_token(user, "email_verify", self.settings.email_verify_token_expire_hours * 60)
        self.db.commit()
        self.send_verification_email(user.email, token)
        return self.message("验证邮件已发送", token)

    def verify_email(self, token: str) -> AuthMessage:
        auth_token = self.consume_email_token(token, "email_verify")
        user = self.db.get(User, auth_token.user_id)
        if not user or user.email != auth_token.email:
            raise HTTPException(status_code=400, detail="验证链接无效或已过期")
        user.email_verified_at = datetime.now(UTC)
        self.db.commit()
        return AuthMessage(ok=True, message="邮箱验证成功")

    def forgot_password(self, email: str) -> AuthMessage:
        user = self.db.scalar(select(User).where(User.email == str(email).strip()))
        if not user or not user.is_active:
            return AuthMessage(ok=True, message="如果邮箱存在，重置密码邮件已发送")
        token = self.create_email_token(user, "password_reset", self.settings.password_reset_token_expire_minutes)
        self.db.commit()
        if not self.send_password_reset_email(user.email, token):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="重置密码邮件发送失败，请稍后重试")
        return self.message("如果邮箱存在，重置密码邮件已发送", token)

    def reset_password(self, token: str, new_password: str) -> AuthMessage:
        auth_token = self.consume_email_token(token, "password_reset")
        user = self.db.get(User, auth_token.user_id)
        if not user or user.email != auth_token.email:
            raise HTTPException(status_code=400, detail="重置链接无效或已过期")
        user.password_hash = get_password_hash(new_password)
        self.db.commit()
        return AuthMessage(ok=True, message="密码已重置")

    @staticmethod
    def issue_tokens(user: User) -> Token:
        subject = str(user.id)
        return Token(
            access_token=create_access_token(subject, user.role),
            refresh_token=create_refresh_token(subject, user.role),
        )

    def create_email_token(self, user: User, purpose: str, expire_minutes: int) -> str:
        token = secrets.token_urlsafe(32)
        self.db.add(
            EmailAuthToken(
                user_id=user.id,
                email=user.email,
                purpose=purpose,
                token_hash=self.hash_token(token),
                expires_at=datetime.now(UTC) + timedelta(minutes=expire_minutes),
            )
        )
        return token

    def consume_email_token(self, token: str, purpose: str) -> EmailAuthToken:
        auth_token = self.db.scalar(
            select(EmailAuthToken).where(
                EmailAuthToken.token_hash == self.hash_token(token),
                EmailAuthToken.purpose == purpose,
            )
        )
        if not auth_token or auth_token.used_at:
            raise HTTPException(status_code=400, detail="链接无效或已过期")
        now = datetime.now(UTC)
        expires_at = auth_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < now:
            raise HTTPException(status_code=400, detail="链接无效或已过期")
        auth_token.used_at = now
        return auth_token

    def send_verification_email(self, email: str, token: str) -> bool:
        link = f"{self.settings.frontend_base_url.rstrip('/')}/verify-email?token={token}"
        text = f"请点击下面的链接完成邮箱验证：\n\n{link}\n\n如果不是你本人操作，请忽略此邮件。"
        return self.email_delivery.send(email, "验证 Quiz Pass 邮箱", text, self.auth_email_html("验证邮箱", "点击下面的按钮完成邮箱验证。", "验证邮箱", link))

    def send_password_reset_email(self, email: str, token: str) -> bool:
        link = f"{self.settings.frontend_base_url.rstrip('/')}/reset-password?token={token}"
        text = f"请点击下面的链接重置密码：\n\n{link}\n\n如果不是你本人操作，请忽略此邮件。"
        return self.email_delivery.send(email, "重置 Quiz Pass 密码", text, self.auth_email_html("重置密码", "点击下面的按钮设置新密码。链接有效期较短，请尽快完成。", "重置密码", link))

    @staticmethod
    def auth_email_html(title: str, intro: str, button_text: str, link: str) -> str:
        escaped_title = html.escape(title)
        escaped_intro = html.escape(intro)
        escaped_button = html.escape(button_text)
        escaped_link = html.escape(link, quote=True)
        return f"""<!doctype html>
<html>
  <body style="margin:0;background:#f5f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f2937;">
    <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
      <div style="background:#ffffff;border:1px solid #d8dee9;border-radius:8px;padding:28px;">
        <div style="font-size:14px;color:#64748b;margin-bottom:12px;">Quiz Pass</div>
        <h1 style="font-size:22px;line-height:1.3;margin:0 0 12px;color:#0f172a;">{escaped_title}</h1>
        <p style="font-size:15px;line-height:1.7;margin:0 0 22px;">{escaped_intro}</p>
        <a href="{escaped_link}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:6px;padding:10px 16px;font-size:15px;">{escaped_button}</a>
        <p style="font-size:13px;line-height:1.6;color:#64748b;margin:22px 0 0;">如果按钮无法打开，请复制下面的链接到浏览器：</p>
        <p style="font-size:13px;line-height:1.6;word-break:break-all;margin:6px 0 0;color:#2563eb;">{escaped_link}</p>
        <p style="font-size:12px;line-height:1.6;color:#94a3b8;margin:24px 0 0;">如果不是你本人操作，请忽略此邮件。</p>
      </div>
    </div>
  </body>
</html>"""

    def message(self, text: str, token: str | None = None) -> AuthMessage:
        debug_token = token if self.settings.app_env in {"development", "test"} else None
        return AuthMessage(ok=True, message=text, debug_token=debug_token)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
            response_format_type=payload.response_format_type,
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
        for field in ("name", "api_base_url", "model", "response_format_type", "is_default", "is_active"):
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

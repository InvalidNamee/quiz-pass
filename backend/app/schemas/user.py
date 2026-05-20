from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class AuthMessage(BaseModel):
    ok: bool = True
    message: str
    debug_token: str | None = None


class EmailRequest(BaseModel):
    email: EmailStr


class UserLogin(BaseModel):
    identifier: str | None = None
    email: EmailStr | None = None
    password: str

    model_config = ConfigDict(populate_by_name=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserMe(BaseModel):
    id: int
    email: EmailStr
    username: str
    display_name: str | None
    avatar_url: str | None
    avatar_source: str
    bio: str | None
    role: str
    is_active: bool
    email_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    id: int
    username: str
    display_name: str | None
    avatar_url: str | None
    bio: str | None
    created_at: datetime
    public_bank_count: int = 0

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    avatar_url: str | None = Field(default=None, max_length=512)
    avatar_source: str | None = Field(default=None, pattern="^(manual|qq_email|default)$")
    bio: str | None = None


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class AdminUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    bio: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class AdminPasswordResetOut(BaseModel):
    temporary_password: str

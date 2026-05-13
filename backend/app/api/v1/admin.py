import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, page_response
from app.schemas.user import AdminPasswordResetOut, AdminUserUpdate, UserMe
from app.utils.pagination import paginate

router = APIRouter()


@router.get("/users", response_model=Page[UserMe])
def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if keyword:
        stmt = stmt.where(or_(User.email.contains(keyword), User.username.contains(keyword), User.display_name.contains(keyword)))
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(User.created_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response(items, total, page, page_size)


@router.patch("/users/{user_id}", response_model=UserMe)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updates = payload.model_dump(exclude_unset=True)
    for field in ("display_name", "bio", "is_active"):
        if field in updates:
            setattr(user, field, updates[field])
    db.commit()
    db.refresh(user)
    return user


def _temporary_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("/users/{user_id}/reset-password", response_model=AdminPasswordResetOut)
def reset_user_password(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能重置自己的密码，请使用修改密码功能")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    temporary_password = _temporary_password()
    user.password_hash = get_password_hash(temporary_password)
    db.commit()
    return AdminPasswordResetOut(temporary_password=temporary_password)

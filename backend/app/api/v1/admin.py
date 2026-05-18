from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.domains.users.services import AdminUserService
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import AdminPasswordResetOut, AdminUserUpdate, UserMe

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
    return AdminUserService(db).list_users(page, page_size, keyword, role, is_active)


@router.patch("/users/{user_id}", response_model=UserMe)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminUserService(db).update_user(user_id, payload)


@router.post("/users/{user_id}/reset-password", response_model=AdminPasswordResetOut)
def reset_user_password(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminUserService(db).reset_password(user_id, current_admin)

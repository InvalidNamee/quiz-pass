from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.users.services import UserAuthService
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserMe

router = APIRouter()


@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    return UserAuthService(db).register(payload)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    return UserAuthService(db).login(payload.identifier, payload.email, payload.password)


@router.get("/me", response_model=UserMe)
def me(current_user: User = Depends(get_current_user)):
    return current_user

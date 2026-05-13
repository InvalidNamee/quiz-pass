import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.question_bank import QuestionBank, QuestionBankFavorite
from app.models.user import User
from app.schemas.common import Page, page_response
from app.schemas.question_bank import QuestionBankCreate, QuestionBankOut, QuestionBankUpdate
from app.utils.json_io import create_question_from_payload, question_to_json
from app.utils.pagination import paginate

router = APIRouter()


def can_read(bank: QuestionBank, user: User | None) -> bool:
    return bank.visibility == "public" and bank.generation_status in ("none", "succeeded") or bool(user and bank.owner_id == user.id)


def to_bank_out(db: Session, bank: QuestionBank, user: User | None) -> QuestionBankOut:
    is_favorited = False
    if user:
        is_favorited = bool(db.scalar(select(QuestionBankFavorite).where(QuestionBankFavorite.user_id == user.id, QuestionBankFavorite.bank_id == bank.id)))
    owner = bank.owner
    return QuestionBankOut.model_validate(bank, from_attributes=True).model_copy(
        update={
            "is_favorited": is_favorited,
            "owner_username": owner.username if owner else None,
            "owner_display_name": owner.display_name if owner else None,
            "owner_avatar_url": owner.avatar_url if owner else None,
        }
    )


@router.get("", response_model=Page[QuestionBankOut])
def list_my_banks(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    visibility: str | None = None,
    generation_status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(QuestionBank).where(QuestionBank.owner_id == current_user.id)
    if keyword:
        stmt = stmt.where(or_(QuestionBank.title.contains(keyword), QuestionBank.description.contains(keyword)))
    if visibility:
        stmt = stmt.where(QuestionBank.visibility == visibility)
    if generation_status:
        stmt = stmt.where(QuestionBank.generation_status == generation_status)
    stmt = stmt.order_by(QuestionBank.updated_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([to_bank_out(db, item, current_user) for item in items], total, page, page_size)


@router.get("/public", response_model=Page[QuestionBankOut])
def list_public_banks(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    owner_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(QuestionBank).where(
        QuestionBank.visibility == "public",
        QuestionBank.generation_status.in_(["none", "succeeded"]),
    )
    if keyword:
        stmt = stmt.where(or_(QuestionBank.title.contains(keyword), QuestionBank.description.contains(keyword)))
    if owner_id:
        stmt = stmt.where(QuestionBank.owner_id == owner_id)
    stmt = stmt.order_by(QuestionBank.favorite_count.desc(), QuestionBank.updated_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([to_bank_out(db, item, current_user) for item in items], total, page, page_size)


@router.get("/favorites", response_model=Page[QuestionBankOut])
def list_favorite_banks(page: int = 1, page_size: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = (
        select(QuestionBank)
        .join(QuestionBankFavorite, QuestionBankFavorite.bank_id == QuestionBank.id)
        .where(
            QuestionBankFavorite.user_id == current_user.id,
            or_(
                QuestionBank.owner_id == current_user.id,
                and_(QuestionBank.visibility == "public", QuestionBank.generation_status.in_(["none", "succeeded"])),
            ),
        )
        .order_by(QuestionBankFavorite.created_at.desc())
    )
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([to_bank_out(db, item, current_user) for item in items], total, page, page_size)


@router.post("", response_model=QuestionBankOut)
def create_bank(payload: QuestionBankCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = QuestionBank(owner_id=current_user.id, title=payload.title, description=payload.description, visibility=payload.visibility, desired_visibility=payload.visibility)
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return to_bank_out(db, bank, current_user)


@router.get("/{bank_id}", response_model=QuestionBankOut)
def get_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not bank or not can_read(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    return to_bank_out(db, bank, current_user)


@router.get("/{bank_id}/export")
def export_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.scalar(select(QuestionBank).options(selectinload(QuestionBank.questions)).where(QuestionBank.id == bank_id))
    if not bank or not can_read(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    for question in bank.questions:
        _ = question.options
    payload = {
        "version": 1,
        "bank": {"title": bank.title, "description": bank.description},
        "questions": [question_to_json(question) for question in bank.questions],
    }
    return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="question-bank-{bank.id}.json"'})


@router.post("/{bank_id}/import-json", response_model=QuestionBankOut)
async def import_json_to_bank(bank_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not bank or bank.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Question bank not found")
    try:
        payload = json.loads((await file.read()).decode("utf-8"))
        questions = payload.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("questions 不能为空")
        for raw_question in questions:
            create_question_from_payload(db, bank.id, raw_question, source="json_import")
        bank.question_count += len(questions)
        db.commit()
        db.refresh(bank)
        return to_bank_out(db, bank, current_user)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"JSON 导入失败: {exc}") from exc


@router.post("/import-json", response_model=QuestionBankOut)
async def import_json_new_bank(file: UploadFile = File(...), visibility: str = "private", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        payload = json.loads((await file.read()).decode("utf-8"))
        bank_info = payload.get("bank") or {}
        title = str(bank_info.get("title") or file.filename or "导入题库")
        description = bank_info.get("description")
        questions = payload.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("questions 不能为空")
        bank = QuestionBank(owner_id=current_user.id, title=title, description=description, visibility=visibility, desired_visibility=visibility)
        db.add(bank)
        db.flush()
        for raw_question in questions:
            create_question_from_payload(db, bank.id, raw_question, source="json_import")
        bank.question_count = len(questions)
        db.commit()
        db.refresh(bank)
        return to_bank_out(db, bank, current_user)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"JSON 导入失败: {exc}") from exc


@router.patch("/{bank_id}", response_model=QuestionBankOut)
def update_bank(bank_id: int, payload: QuestionBankUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not bank or bank.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Question bank not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(bank, key, value)
        if key == "visibility":
            bank.desired_visibility = value
    db.commit()
    db.refresh(bank)
    return to_bank_out(db, bank, current_user)


@router.delete("/{bank_id}")
def delete_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not bank or bank.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Question bank not found")
    db.delete(bank)
    db.commit()
    return {"ok": True}


@router.post("/{bank_id}/favorite")
def favorite_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not bank or not can_read(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    existing = db.scalar(select(QuestionBankFavorite).where(QuestionBankFavorite.user_id == current_user.id, QuestionBankFavorite.bank_id == bank_id))
    if not existing:
        db.add(QuestionBankFavorite(user_id=current_user.id, bank_id=bank_id))
        bank.favorite_count += 1
        db.commit()
    return {"ok": True}


@router.delete("/{bank_id}/favorite")
def unfavorite_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favorite = db.scalar(select(QuestionBankFavorite).where(QuestionBankFavorite.user_id == current_user.id, QuestionBankFavorite.bank_id == bank_id))
    if favorite:
        bank = db.get(QuestionBank, bank_id)
        db.delete(favorite)
        if bank and bank.favorite_count > 0:
            bank.favorite_count -= 1
        db.commit()
    return {"ok": True}

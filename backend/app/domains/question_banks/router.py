from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.question_banks.import_export import QuestionBankImportExportService
from app.domains.question_banks.queries import QuestionBankQueryService, list_tags_stmt
from app.domains.question_banks.questions import QuestionService
from app.domains.question_banks.schemas import QuestionBankAIContextUpdate, QuestionBankV2Create, QuestionBankV2Out, QuestionBankV2Update
from app.domains.question_banks.services import QuestionBankService
from app.models.user import User
from app.schemas.common import Page, page_response
from app.schemas.question import QuestionCreate, QuestionOut, QuestionUpdate
from app.schemas.question_bank import QuestionBankTagOut
from app.utils.pagination import paginate

router = APIRouter()


@router.get("/banks", response_model=Page[QuestionBankV2Out])
def list_banks(
    scope: str = "mine",
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    owner_id: int | None = None,
    tag_ids: str | None = None,
    visibility: str | None = None,
    generation_status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = QuestionBankQueryService(db)
    try:
        stmt = service.list_stmt(current_user, scope, keyword, owner_id, tag_ids, visibility, generation_status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([service.to_out(item, current_user) for item in items], total, page, page_size)


@router.post("/banks", response_model=QuestionBankV2Out)
def create_bank(payload: QuestionBankV2Create, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionBankService(db).create(payload, current_user)


@router.post("/banks/import-json", response_model=QuestionBankV2Out)
async def import_json_new_bank(
    file: UploadFile = File(...),
    visibility: str = Form("private"),
    tag_names: str | None = Form(None),
    file_stem: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = QuestionBankImportExportService(db)
    payload = service.parse_upload(await file.read())
    parsed_tag_names = service.parse_tag_names(tag_names)
    return service.import_new_bank(payload, current_user, visibility, parsed_tag_names, file_stem=file_stem)


@router.get("/banks/tags", response_model=Page[QuestionBankTagOut])
def list_tags(page: int = 1, page_size: int = 20, keyword: str | None = None, ids: str | None = None, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        stmt = list_tags_stmt(keyword, ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response(items, total, page, page_size)


@router.get("/banks/{bank_id}", response_model=QuestionBankV2Out)
def get_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = QuestionBankService(db).get_readable(bank_id, current_user)
    return QuestionBankQueryService(db).to_out(bank, current_user)


@router.get("/banks/{bank_id}/export-json")
def export_bank_json(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionBankImportExportService(db).export_response(bank_id, current_user)


@router.post("/banks/{bank_id}/import-json", response_model=QuestionBankV2Out)
async def import_json_to_bank(bank_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = QuestionBankImportExportService(db)
    payload = service.parse_upload(await file.read())
    return service.import_to_existing(bank_id, payload, current_user)


@router.get("/banks/{bank_id}/questions", response_model=Page[QuestionOut])
def list_questions(bank_id: int, page: int = 1, page_size: int = 20, keyword: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).list_questions(bank_id, current_user, page, page_size, keyword)


@router.post("/banks/{bank_id}/questions", response_model=QuestionOut)
def create_question(bank_id: int, payload: QuestionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).create_question(bank_id, payload, current_user)


@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).get_question(question_id, current_user)


@router.patch("/questions/{question_id}", response_model=QuestionOut)
def update_question(question_id: int, payload: QuestionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionService(db).update_question(question_id, payload, current_user)


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    QuestionService(db).delete_question(question_id, current_user)
    return {"ok": True}


@router.patch("/banks/{bank_id}", response_model=QuestionBankV2Out)
def update_bank(bank_id: int, payload: QuestionBankV2Update, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionBankService(db).update(bank_id, payload, current_user)


@router.patch("/banks/{bank_id}/ai-context", response_model=QuestionBankV2Out)
def update_bank_ai_context(bank_id: int, payload: QuestionBankAIContextUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return QuestionBankService(db).update_ai_context(bank_id, payload, current_user)


@router.delete("/banks/{bank_id}")
def delete_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    QuestionBankService(db).delete(bank_id, current_user)
    return {"ok": True}


@router.post("/banks/{bank_id}/favorites")
def favorite_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    QuestionBankService(db).favorite(bank_id, current_user)
    return {"ok": True}


@router.delete("/banks/{bank_id}/favorites")
def unfavorite_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    QuestionBankService(db).unfavorite(bank_id, current_user)
    return {"ok": True}

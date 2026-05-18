import json
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.domains.question_banks.import_export import QuestionBankImportExportService
from app.models.ai_provider_config import UserAIProviderConfig
from app.domains.question_banks.lifecycle import QuestionBankLifecycleService
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.stats import QuestionBankStatsService
from app.models.ai_workflow import AIGenerationWorkflow
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank, QuestionBankFavorite, QuestionBankTag, question_bank_tag_links
from app.models.user import User
from app.schemas.ai import AIGenerationBankJobOut
from app.schemas.common import Page, page_response
from app.schemas.question_bank import QuestionBankCreate, QuestionBankOut, QuestionBankTagOut, QuestionBankUpdate
from app.services.ai_generation import generate_questions_from_ai
from app.services.question_bank_tags import set_bank_tags
from app.utils.document_extractors import extract_text
from app.utils.pagination import paginate

router = APIRouter()


def can_read(bank: QuestionBank, user: User | None) -> bool:
    return QuestionBankPermissionService.can_read(bank, user)


def can_manage(bank: QuestionBank, user: User | None) -> bool:
    return QuestionBankPermissionService.can_manage(bank, user)


ACTIVE_WORKFLOW_STATUSES = {"pending", "extracting", "extracting_document", "calling_model", "validating", "repairing", "draft_ready"}


def _active_generation_job_id(db: Session, bank_id: int) -> int | None:
    workflow = db.scalar(
        select(AIGenerationWorkflow)
        .where(AIGenerationWorkflow.bank_id == bank_id, AIGenerationWorkflow.status.in_(ACTIVE_WORKFLOW_STATUSES))
        .order_by(AIGenerationWorkflow.updated_at.desc(), AIGenerationWorkflow.id.desc())
    )
    if not workflow:
        return None
    job = db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id).order_by(ImportJob.id.desc()))
    return job.id if job else None


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
            "active_generation_job_id": _active_generation_job_id(db, bank.id),
            "tags": [QuestionBankTagOut.model_validate(tag, from_attributes=True) for tag in sorted(bank.tags, key=lambda item: item.name)],
        }
    )


def parse_tag_ids(raw_tag_ids: str | None) -> list[int]:
    if not raw_tag_ids:
        return []
    tag_ids: list[int] = []
    for raw_id in raw_tag_ids.split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        if not raw_id.isdigit():
            raise HTTPException(status_code=422, detail="Invalid tag_ids")
        tag_ids.append(int(raw_id))
    return list(dict.fromkeys(tag_ids))


def apply_tag_filter(stmt, raw_tag_ids: str | None):
    tag_ids = parse_tag_ids(raw_tag_ids)
    if not tag_ids:
        return stmt
    bank_ids = select(question_bank_tag_links.c.bank_id).where(question_bank_tag_links.c.tag_id.in_(tag_ids))
    return stmt.where(QuestionBank.id.in_(bank_ids))


def _run_generation(workflow_id: int, text: str, question_count: int | None, generate_description: bool, generation_mode: str, extra_instruction: str | None) -> None:
    db = SessionLocal()
    try:
        generate_questions_from_ai(db, workflow_id, text, question_count, generate_description, generation_mode, extra_instruction)
    finally:
        db.close()


def _pick_ai_config(db: Session, user_id: int, config_id: int | None) -> UserAIProviderConfig:
    stmt = select(UserAIProviderConfig).where(UserAIProviderConfig.user_id == user_id, UserAIProviderConfig.is_active.is_(True))
    if config_id:
        stmt = stmt.where(UserAIProviderConfig.id == config_id)
    else:
        stmt = stmt.where(UserAIProviderConfig.is_default.is_(True))
    config = db.scalar(stmt)
    if not config:
        raise HTTPException(status_code=400, detail="请先配置可用的 AI Provider")
    return config


@router.get("", response_model=Page[QuestionBankOut])
def list_my_banks(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    visibility: str | None = None,
    generation_status: str | None = None,
    tag_ids: str | None = None,
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
    stmt = apply_tag_filter(stmt, tag_ids)
    stmt = stmt.order_by(QuestionBank.updated_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([to_bank_out(db, item, current_user) for item in items], total, page, page_size)


@router.get("/public", response_model=Page[QuestionBankOut])
def list_public_banks(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    owner_id: int | None = None,
    tag_ids: str | None = None,
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
    stmt = apply_tag_filter(stmt, tag_ids)
    stmt = stmt.order_by(QuestionBank.favorite_count.desc(), QuestionBank.updated_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([to_bank_out(db, item, current_user) for item in items], total, page, page_size)


@router.get("/favorites", response_model=Page[QuestionBankOut])
def list_favorite_banks(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    owner_id: int | None = None,
    visibility: str | None = None,
    generation_status: str | None = None,
    tag_ids: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    if keyword:
        stmt = stmt.where(or_(QuestionBank.title.contains(keyword), QuestionBank.description.contains(keyword)))
    if owner_id:
        stmt = stmt.where(QuestionBank.owner_id == owner_id)
    if visibility:
        stmt = stmt.where(QuestionBank.visibility == visibility)
    if generation_status:
        stmt = stmt.where(QuestionBank.generation_status == generation_status)
    stmt = apply_tag_filter(stmt, tag_ids)
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response([to_bank_out(db, item, current_user) for item in items], total, page, page_size)


@router.get("/tags", response_model=Page[QuestionBankTagOut])
def list_tags(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    ids: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(QuestionBankTag)
    tag_ids = parse_tag_ids(ids)
    if tag_ids:
        stmt = stmt.where(QuestionBankTag.id.in_(tag_ids))
    if keyword:
        stmt = stmt.where(QuestionBankTag.name.contains(keyword.strip()))
    stmt = stmt.order_by(QuestionBankTag.name.asc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response(items, total, page, page_size)


@router.post("", response_model=QuestionBankOut)
def create_bank(payload: QuestionBankCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = QuestionBank(owner_id=current_user.id, title=payload.title, description=payload.description, visibility=payload.visibility, desired_visibility=payload.visibility)
    db.add(bank)
    db.flush()
    try:
        set_bank_tags(db, bank, payload.tag_names)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
    return QuestionBankImportExportService(db).export_response(bank_id, current_user)


@router.post("/{bank_id}/ai-generation/extend-jobs", response_model=AIGenerationBankJobOut)
async def create_extend_job(
    bank_id: int,
    background_tasks: BackgroundTasks,
    ai_provider_config_id: int | None = Form(None),
    question_count_mode: str = Form("fixed"),
    question_count: int | None = Form(None),
    generate_description: bool = Form(False),
    generation_mode: str = Form("knowledge_generate"),
    extra_instruction: str | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bank = db.get(QuestionBank, bank_id)
    if not can_manage(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    if generation_mode not in ("knowledge_generate", "bank_parse"):
        raise HTTPException(status_code=422, detail="Invalid generation_mode")
    if question_count_mode not in ("fixed", "adaptive"):
        raise HTTPException(status_code=422, detail="Invalid question_count_mode")
    normalized_extra_instruction = (extra_instruction or "").strip() or None
    if normalized_extra_instruction and len(normalized_extra_instruction) > 2000:
        raise HTTPException(status_code=422, detail="额外指令不能超过 2000 字")
    if generation_mode == "knowledge_generate" and question_count_mode == "fixed" and not question_count:
        raise HTTPException(status_code=422, detail="固定题数模式必须指定题数")
    effective_count = question_count if generation_mode == "knowledge_generate" and question_count_mode == "fixed" else None
    config = _pick_ai_config(db, current_user.id, ai_provider_config_id)
    content = await file.read()
    try:
        text = extract_text(file.filename or "upload.txt", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    parsed = urlparse(config.api_base_url)
    host = parsed.netloc or config.api_base_url
    workflow = AIGenerationWorkflow(
        bank_id=bank.id,
        user_id=current_user.id,
        purpose="extend_bank",
        generation_mode=generation_mode,
        status="pending",
        source_file_name=file.filename,
        source_text_snapshot=text,
        requested_count=effective_count,
        generate_description="true" if generate_description else "false",
        extra_instruction=normalized_extra_instruction,
        ai_provider_config_id=config.id,
        ai_base_url_snapshot=host,
        ai_model_snapshot=config.model,
    )
    db.add(workflow)
    db.flush()
    job = ImportJob(
        user_id=current_user.id,
        bank_id=bank.id,
        workflow_id=workflow.id,
        type="bank_parse_ai" if generation_mode == "bank_parse" else "document_ai",
        status="pending",
        desired_visibility=bank.desired_visibility,
        file_name=file.filename,
        ai_provider_config_id=config.id,
        ai_base_url_snapshot=host,
        ai_model_snapshot=config.model,
    )
    db.add(job)
    db.flush()
    bank.generation_status = "processing"
    db.commit()
    background_tasks.add_task(_run_generation, workflow.id, text, effective_count, generate_description, generation_mode, normalized_extra_instruction)
    return AIGenerationBankJobOut(bank_id=bank.id, job_id=job.id)


@router.post("/{bank_id}/import-json", response_model=QuestionBankOut)
async def import_json_to_bank(bank_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = QuestionBankImportExportService(db)
    payload = service.parse_upload(await file.read())
    bank_out = service.import_to_existing(bank_id, payload, current_user)
    bank = db.get(QuestionBank, bank_out.id)
    return to_bank_out(db, bank, current_user)


@router.post("/import-json", response_model=QuestionBankOut)
async def import_json_new_bank(file: UploadFile = File(...), visibility: str = Form("private"), tag_names: str | None = Form(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = QuestionBankImportExportService(db)
    payload = service.parse_upload(await file.read())
    parsed_tag_names = service.parse_tag_names(tag_names)
    bank_out = service.import_new_bank(payload, current_user, visibility, parsed_tag_names)
    bank = db.get(QuestionBank, bank_out.id)
    return to_bank_out(db, bank, current_user)


@router.patch("/{bank_id}", response_model=QuestionBankOut)
def update_bank(bank_id: int, payload: QuestionBankUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not can_manage(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    updates = payload.model_dump(exclude_unset=True)
    tag_names = updates.pop("tag_names", None)
    for key, value in updates.items():
        setattr(bank, key, value)
        if key == "visibility":
            bank.desired_visibility = value
    if "tag_names" in payload.model_fields_set:
        try:
            set_bank_tags(db, bank, tag_names)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(bank)
    return to_bank_out(db, bank, current_user)


@router.delete("/{bank_id}")
def delete_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bank = db.get(QuestionBank, bank_id)
    if not can_manage(bank, current_user):
        raise HTTPException(status_code=404, detail="Question bank not found")
    QuestionBankLifecycleService(db).delete_bank(bank)
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
        QuestionBankStatsService.increment_favorites(db, bank)
        db.commit()
    return {"ok": True}


@router.delete("/{bank_id}/favorite")
def unfavorite_bank(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favorite = db.scalar(select(QuestionBankFavorite).where(QuestionBankFavorite.user_id == current_user.id, QuestionBankFavorite.bank_id == bank_id))
    if favorite:
        bank = db.get(QuestionBank, bank_id)
        db.delete(favorite)
        if bank:
            QuestionBankStatsService.decrement_favorites(db, bank)
        db.commit()
    return {"ok": True}

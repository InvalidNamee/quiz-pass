from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.ai import AIGenerationBankJobOut, ImportJobOut
from app.schemas.common import Page, page_response
from app.services.ai_generation import generate_questions_from_ai
from app.utils.document_extractors import extract_text
from app.utils.pagination import paginate

router = APIRouter()


def _run_generation(job_id: int, text: str, question_count: int | None, generate_description: bool, generation_mode: str, extra_instruction: str | None) -> None:
    db = SessionLocal()
    try:
        generate_questions_from_ai(db, job_id, text, question_count, generate_description, generation_mode, extra_instruction)
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


@router.post("/question-bank-jobs", response_model=AIGenerationBankJobOut)
async def create_question_bank_job(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str | None = Form(None),
    desired_visibility: str = Form("private"),
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
    if desired_visibility not in ("private", "public"):
        raise HTTPException(status_code=422, detail="Invalid desired_visibility")
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
    bank = QuestionBank(
        owner_id=current_user.id,
        title=title,
        description=description,
        visibility="private",
        desired_visibility=desired_visibility,
        generation_status="pending",
        ai_provider_config_id=config.id,
        ai_model_name=config.model,
        ai_base_url_host=host,
    )
    db.add(bank)
    db.flush()
    job = ImportJob(
        user_id=current_user.id,
        bank_id=bank.id,
        type="bank_parse_ai" if generation_mode == "bank_parse" else "document_ai",
        status="pending",
        desired_visibility=desired_visibility,
        file_name=file.filename,
        ai_provider_config_id=config.id,
        ai_base_url_snapshot=host,
        ai_model_snapshot=config.model,
    )
    db.add(job)
    db.flush()
    bank.active_generation_job_id = job.id
    db.commit()
    background_tasks.add_task(_run_generation, job.id, text, effective_count, generate_description, generation_mode, normalized_extra_instruction)
    return AIGenerationBankJobOut(bank_id=bank.id, job_id=job.id)


@router.get("/jobs", response_model=Page[ImportJobOut])
def list_jobs(page: int = 1, page_size: int = 20, status: str | None = None, bank_id: int | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(ImportJob).where(ImportJob.user_id == current_user.id)
    if status:
        stmt = stmt.where(ImportJob.status == status)
    if bank_id:
        stmt = stmt.where(ImportJob.bank_id == bank_id)
    stmt = stmt.order_by(ImportJob.created_at.desc())
    items, total, page, page_size = paginate(db, stmt, page, page_size)
    return page_response(items, total, page, page_size)


@router.get("/jobs/{job_id}", response_model=ImportJobOut)
def get_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("pending", "processing"):
        job.status = "failed"
        job.error_message = "用户已取消"
        if job.bank_id:
            bank = db.get(QuestionBank, job.bank_id)
            if bank:
                bank.generation_status = "failed"
                bank.visibility = "private"
    db.commit()
    return {"ok": True}


@router.post("/jobs/{job_id}/confirm")
def confirm_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "message": "生成型题库首版会在任务成功后自动入库"}

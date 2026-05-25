from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.ai_generation.schemas import AIGenerationWorkflowCreatedOut
from app.domains.ai_generation.services import AIGenerationWorkflowService
from app.models.user import User
from app.schemas.ai import AIGenerationDraftOut, AIGenerationWorkflowDetailOut, AIGenerationWorkflowOut, AIGenerationWorkflowStepOut
from app.schemas.common import Page, page_response
from app.utils.pagination import paginate

router = APIRouter()


@router.post("/ai/workflows", response_model=AIGenerationWorkflowCreatedOut)
async def create_workflow(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str | None = Form(None),
    desired_visibility: str = Form("private"),
    ai_provider_config_id: int | None = Form(None),
    question_count_mode: str = Form("fixed"),
    question_count: int | None = Form(None),
    question_type_settings: str | None = Form(None),
    generate_description: bool = Form(False),
    generation_mode: str = Form("knowledge_generate"),
    extra_instruction: str | None = Form(None),
    inherit_context: bool = Form(False),
    tag_names: str | None = Form(None),
    file: UploadFile | None = File(None),
    files: list[UploadFile] | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await AIGenerationWorkflowService(db).create_bank_workflow(
        current_user,
        background_tasks,
        title,
        description,
        desired_visibility,
        ai_provider_config_id,
        question_count_mode,
        question_count,
        question_type_settings,
        generate_description,
        generation_mode,
        extra_instruction,
        inherit_context,
        tag_names,
        file,
        files,
    )


@router.post("/banks/{bank_id}/ai-workflows", response_model=AIGenerationWorkflowCreatedOut)
async def create_extend_workflow(
    bank_id: int,
    background_tasks: BackgroundTasks,
    ai_provider_config_id: int | None = Form(None),
    question_count_mode: str = Form("fixed"),
    question_count: int | None = Form(None),
    question_type_settings: str | None = Form(None),
    generate_description: bool = Form(False),
    generation_mode: str = Form("knowledge_generate"),
    extra_instruction: str | None = Form(None),
    inherit_context: bool = Form(True),
    include_existing_questions: bool = Form(False),
    file: UploadFile | None = File(None),
    files: list[UploadFile] | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await AIGenerationWorkflowService(db).create_extend_workflow(
        bank_id,
        current_user,
        background_tasks,
        ai_provider_config_id,
        question_count_mode,
        question_count,
        question_type_settings,
        generate_description,
        generation_mode,
        extra_instruction,
        inherit_context,
        include_existing_questions,
        file,
        files,
    )


@router.get("/ai/workflows", response_model=Page[AIGenerationWorkflowOut])
def list_workflows(page: int = 1, page_size: int = 20, status: str | None = None, bank_id: int | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AIGenerationWorkflowService(db)
    items, total, page, page_size = paginate(db, service.workflows_for_user_stmt(current_user, status, bank_id), page, page_size)
    return page_response(service.workflow_out_many(items), total, page, page_size)


@router.get("/banks/{bank_id}/ai-workflows", response_model=Page[AIGenerationWorkflowOut])
def list_bank_workflows(bank_id: int, page: int = 1, page_size: int = 20, status: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AIGenerationWorkflowService(db)
    items, total, page, page_size = paginate(db, service.workflows_for_readable_bank_stmt(bank_id, current_user, status), page, page_size)
    return page_response(service.workflow_out_many_for_bank_logs(items, current_user), total, page, page_size)


@router.get("/ai/workflows/{workflow_id}", response_model=AIGenerationWorkflowOut)
def get_workflow(workflow_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AIGenerationWorkflowService(db)
    return service.workflow_out(service.get_owned_workflow(workflow_id, current_user))


@router.get("/ai/workflows/{workflow_id}/detail", response_model=AIGenerationWorkflowDetailOut)
def get_workflow_detail(workflow_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIGenerationWorkflowService(db).workflow_detail(workflow_id, current_user)


@router.get("/ai/workflows/{workflow_id}/steps", response_model=list[AIGenerationWorkflowStepOut])
def get_workflow_steps(workflow_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIGenerationWorkflowService(db).workflow_steps(workflow_id, current_user)


@router.get("/ai/workflows/{workflow_id}/draft", response_model=AIGenerationDraftOut)
def get_draft(workflow_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIGenerationWorkflowService(db).draft_for_workflow(workflow_id, current_user)


@router.patch("/ai/workflows/{workflow_id}/draft", response_model=AIGenerationDraftOut)
def update_draft(workflow_id: int, payload: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIGenerationWorkflowService(db).update_draft(workflow_id, payload, current_user)


@router.post("/ai/workflows/{workflow_id}/draft/confirm")
def confirm_draft(workflow_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIGenerationWorkflowService(db).confirm_draft(workflow_id, current_user)


@router.post("/ai/workflows/{workflow_id}/draft/discard")
def discard_draft(workflow_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIGenerationWorkflowService(db).discard_draft(workflow_id, current_user)


@router.post("/ai/workflows/{workflow_id}/cancel")
def cancel_workflow(workflow_id: int, cancel_reason: str | None = Form(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIGenerationWorkflowService(db).cancel_workflow(workflow_id, current_user, cancel_reason)


@router.post("/ai/workflows/{workflow_id}/retry", response_model=AIGenerationWorkflowCreatedOut)
async def retry_workflow(
    workflow_id: int,
    background_tasks: BackgroundTasks,
    ai_provider_config_id: int | None = Form(None),
    question_count_mode: str | None = Form(None),
    question_count: int | None = Form(None),
    question_type_settings: str | None = Form(None),
    generate_description: bool | None = Form(None),
    generation_mode: str | None = Form(None),
    extra_instruction: str | None = Form(None),
    inherit_context: bool | None = Form(None),
    include_existing_questions: bool | None = Form(None),
    source_text: str | None = Form(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    desired_visibility: str | None = Form(None),
    file: UploadFile | None = File(None),
    files: list[UploadFile] | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await AIGenerationWorkflowService(db).retry_workflow(
        workflow_id,
        current_user,
        background_tasks,
        ai_provider_config_id,
        question_count_mode,
        question_count,
        question_type_settings,
        generate_description,
        generation_mode,
        extra_instruction,
        inherit_context,
        include_existing_questions,
        source_text,
        title,
        description,
        desired_visibility,
        file,
        files,
    )

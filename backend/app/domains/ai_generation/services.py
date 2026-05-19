import json
from urllib.parse import urlparse

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import SessionLocal
from app.domains.ai_generation.schemas import AIGenerationWorkflowCreatedOut
from app.domains.ai_generation.drafts import DraftService
from app.domains.ai_generation.errors import AIOutputValidationError
from app.domains.ai_generation.workflow_runtime import WorkflowRuntime
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.ai_workflow import AIGenerationDraft, AIGenerationDraftQuestion, AIGenerationWorkflow, AIGenerationWorkflowStep
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.ai import AIGenerationDraftOut, AIGenerationWorkflowOut, AIGenerationWorkflowStepOut
from app.services.question_bank_tags import set_bank_tags
from app.utils.document_extractors import extract_text


def run_generation_task(workflow_id: int, text: str, question_count: int | None, generate_description: bool, generation_mode: str, extra_instruction: str | None) -> None:
    db = SessionLocal()
    try:
        from app.services import ai_generation

        WorkflowRuntime(db, model_client=ai_generation._call_openai_compatible).run(
            workflow_id,
            text,
            question_count,
            generate_description,
            generation_mode,
            extra_instruction,
        )
    finally:
        db.close()


class AIGenerationWorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def pick_ai_config(self, user_id: int, config_id: int | None) -> UserAIProviderConfig:
        stmt = select(UserAIProviderConfig).where(UserAIProviderConfig.user_id == user_id, UserAIProviderConfig.is_active.is_(True))
        if config_id:
            stmt = stmt.where(UserAIProviderConfig.id == config_id)
        else:
            stmt = stmt.where(UserAIProviderConfig.is_default.is_(True))
        config = self.db.scalar(stmt)
        if not config:
            raise HTTPException(status_code=400, detail="请先配置可用的 AI Provider")
        return config

    async def create_bank_workflow(
        self,
        user: User,
        background_tasks: BackgroundTasks,
        title: str,
        description: str | None,
        desired_visibility: str,
        ai_provider_config_id: int | None,
        question_count_mode: str,
        question_count: int | None,
        generate_description: bool,
        generation_mode: str,
        extra_instruction: str | None,
        tag_names: str | None,
        file: UploadFile,
    ) -> AIGenerationWorkflowCreatedOut:
        if desired_visibility not in ("private", "public"):
            raise HTTPException(status_code=422, detail="Invalid desired_visibility")
        effective_count, normalized_extra_instruction = self._normalize_generation_inputs(question_count_mode, question_count, generation_mode, extra_instruction)
        try:
            parsed_tag_names = json.loads(tag_names) if tag_names else []
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="tag_names 必须是字符串数组") from exc
        if not isinstance(parsed_tag_names, list):
            raise HTTPException(status_code=422, detail="tag_names 必须是字符串数组")

        config = self.pick_ai_config(user.id, ai_provider_config_id)
        content = await file.read()
        try:
            text = extract_text(file.filename or "upload.txt", content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        host = urlparse(config.api_base_url).netloc or config.api_base_url
        bank = QuestionBank(
            owner_id=user.id,
            title=title,
            description=description,
            visibility="private",
            desired_visibility=desired_visibility,
            generation_status="pending",
            ai_provider_config_id=config.id,
            ai_model_name=config.model,
            ai_base_url_host=host,
        )
        self.db.add(bank)
        self.db.flush()
        try:
            set_bank_tags(self.db, bank, parsed_tag_names)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        workflow = AIGenerationWorkflow(
            bank_id=bank.id,
            user_id=user.id,
            purpose="create_bank",
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
        self.db.add(workflow)
        self.db.flush()
        job = ImportJob(
            user_id=user.id,
            bank_id=bank.id,
            workflow_id=workflow.id,
            type="bank_parse_ai" if generation_mode == "bank_parse" else "document_ai",
            status="pending",
            desired_visibility=desired_visibility,
            file_name=file.filename,
            ai_provider_config_id=config.id,
            ai_base_url_snapshot=host,
            ai_model_snapshot=config.model,
        )
        self.db.add(job)
        self.db.flush()
        self.db.commit()
        background_tasks.add_task(run_generation_task, workflow.id, text, effective_count, generate_description, generation_mode, normalized_extra_instruction)
        return AIGenerationWorkflowCreatedOut(workflow_id=workflow.id, bank_id=bank.id, job_id=job.id)

    async def create_extend_workflow(
        self,
        bank_id: int,
        user: User,
        background_tasks: BackgroundTasks,
        ai_provider_config_id: int | None,
        question_count_mode: str,
        question_count: int | None,
        generate_description: bool,
        generation_mode: str,
        extra_instruction: str | None,
        file: UploadFile,
    ) -> AIGenerationWorkflowCreatedOut:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_extend_with_ai(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        effective_count, normalized_extra_instruction = self._normalize_generation_inputs(question_count_mode, question_count, generation_mode, extra_instruction)
        config = self.pick_ai_config(user.id, ai_provider_config_id)
        content = await file.read()
        try:
            text = extract_text(file.filename or "upload.txt", content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        host = urlparse(config.api_base_url).netloc or config.api_base_url
        workflow = AIGenerationWorkflow(
            bank_id=bank.id,
            user_id=user.id,
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
        self.db.add(workflow)
        self.db.flush()
        job = ImportJob(
            user_id=user.id,
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
        self.db.add(job)
        self.db.flush()
        bank.generation_status = "processing"
        self.db.commit()
        background_tasks.add_task(run_generation_task, workflow.id, text, effective_count, generate_description, generation_mode, normalized_extra_instruction)
        return AIGenerationWorkflowCreatedOut(workflow_id=workflow.id, bank_id=bank.id, job_id=job.id)

    def workflows_for_user_stmt(self, user: User, status: str | None = None, bank_id: int | None = None):
        stmt = select(AIGenerationWorkflow).where(AIGenerationWorkflow.user_id == user.id)
        if status:
            stmt = stmt.where(AIGenerationWorkflow.status == status)
        if bank_id:
            stmt = stmt.where(AIGenerationWorkflow.bank_id == bank_id)
        return stmt.order_by(AIGenerationWorkflow.created_at.desc())

    def get_owned_workflow(self, workflow_id: int, user: User) -> AIGenerationWorkflow:
        workflow = self.db.get(AIGenerationWorkflow, workflow_id)
        if not workflow or workflow.user_id != user.id:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow

    def workflow_out(self, workflow: AIGenerationWorkflow) -> AIGenerationWorkflowOut:
        out = AIGenerationWorkflowOut.model_validate(workflow, from_attributes=True)
        out.workflow_id = workflow.id
        out.workflow_status = workflow.status
        job = self.db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        if job:
            out.job_id = job.id
            out.type = job.type
        draft = self.db.scalar(select(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if draft:
            out.draft_question_count = self.db.scalar(select(func.count()).select_from(AIGenerationDraftQuestion).where(AIGenerationDraftQuestion.draft_id == draft.id)) or 0
            out.can_confirm = workflow.status == "draft_ready"
        return out

    def workflow_steps(self, workflow_id: int, user: User) -> list[AIGenerationWorkflowStepOut]:
        workflow = self.get_owned_workflow(workflow_id, user)
        steps = self.db.scalars(
            select(AIGenerationWorkflowStep)
            .where(AIGenerationWorkflowStep.workflow_id == workflow.id)
            .order_by(AIGenerationWorkflowStep.id.asc())
        ).all()
        return [AIGenerationWorkflowStepOut.model_validate(step, from_attributes=True) for step in steps]

    def draft_for_workflow(self, workflow_id: int, user: User) -> AIGenerationDraftOut:
        workflow = self.get_owned_workflow(workflow_id, user)
        draft = self.db.scalar(select(AIGenerationDraft).options(selectinload(AIGenerationDraft.questions)).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        return DraftService.to_payload(draft)

    def update_draft(self, workflow_id: int, payload: dict, user: User) -> AIGenerationDraftOut:
        workflow = self.get_owned_workflow(workflow_id, user)
        draft = self.db.scalar(select(AIGenerationDraft).options(selectinload(AIGenerationDraft.questions)).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        try:
            DraftService(self.db).update(draft, payload.get("bank_description"), payload.get("questions") or [])
            self.db.commit()
            self.db.refresh(draft)
            draft = self.db.scalar(select(AIGenerationDraft).options(selectinload(AIGenerationDraft.questions)).where(AIGenerationDraft.id == draft.id))
            return DraftService.to_payload(draft)
        except AIOutputValidationError as exc:
            self.db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    def confirm_draft(self, workflow_id: int, user: User) -> dict:
        workflow = self.get_owned_workflow(workflow_id, user)
        job = self.db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        draft = self.db.scalar(select(AIGenerationDraft).options(selectinload(AIGenerationDraft.questions)).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if not draft:
            raise HTTPException(status_code=400, detail="没有可确认的草稿")
        try:
            bank = DraftService(self.db).confirm(job, draft)
            self.db.commit()
            return {"ok": True, "bank_id": bank.id}
        except AIOutputValidationError as exc:
            self.db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    def discard_draft(self, workflow_id: int, user: User) -> dict:
        workflow = self.get_owned_workflow(workflow_id, user)
        draft = self.db.scalar(select(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if draft:
            draft.status = "discarded"
        workflow.status = "cancelled"
        job = self.db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        if job:
            job.status = "cancelled"
        self.db.commit()
        return {"ok": True}

    @staticmethod
    def _normalize_generation_inputs(question_count_mode: str, question_count: int | None, generation_mode: str, extra_instruction: str | None) -> tuple[int | None, str | None]:
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
        return effective_count, normalized_extra_instruction

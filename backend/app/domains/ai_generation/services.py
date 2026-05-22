import json
from urllib.parse import urlparse

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import SessionLocal
from app.domains.ai_generation.schemas import AIGenerationWorkflowCreatedOut
from app.domains.ai_generation.drafts import DraftService
from app.domains.ai_generation.errors import AIOutputValidationError
from app.domains.ai_generation.workflow_runtime import WorkflowRuntime
from app.domains.ai_generation.workflow_state import now_utc
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
        inherit_context: bool,
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
            bank_title_snapshot=title,
            requested_count=effective_count,
            generate_description="true" if generate_description else "false",
            extra_instruction=normalized_extra_instruction,
            inherit_context=inherit_context,
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
        inherit_context: bool,
        include_existing_questions: bool,
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
            bank_title_snapshot=bank.title,
            requested_count=effective_count,
            generate_description="true" if generate_description else "false",
            extra_instruction=normalized_extra_instruction,
            inherit_context=inherit_context,
            include_existing_questions=include_existing_questions,
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
        self.db.commit()
        background_tasks.add_task(run_generation_task, workflow.id, text, effective_count, generate_description, generation_mode, normalized_extra_instruction)
        return AIGenerationWorkflowCreatedOut(workflow_id=workflow.id, bank_id=bank.id, job_id=job.id)

    async def retry_workflow(
        self,
        workflow_id: int,
        user: User,
        background_tasks: BackgroundTasks,
        ai_provider_config_id: int | None,
        question_count_mode: str | None,
        question_count: int | None,
        generate_description: bool | None,
        generation_mode: str | None,
        extra_instruction: str | None,
        inherit_context: bool | None,
        include_existing_questions: bool | None,
        source_text: str | None,
        title: str | None,
        description: str | None,
        desired_visibility: str | None,
        file: UploadFile | None,
    ) -> AIGenerationWorkflowCreatedOut:
        original = self.get_owned_workflow(workflow_id, user)
        if original.status != "failed":
            raise HTTPException(status_code=400, detail="只有失败的 workflow 可以重新生成")
        if self.retried_by_workflow_id(original.id):
            raise HTTPException(status_code=400, detail="该 workflow 已经重新生成，不能再次操作")

        old_bank = self.db.get(QuestionBank, original.bank_id) if original.bank_id else None
        if original.purpose == "extend_bank" and not QuestionBankPermissionService.can_extend_with_ai(old_bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")

        next_mode = generation_mode or original.generation_mode
        next_count_mode = question_count_mode or ("fixed" if original.requested_count else "adaptive")
        next_count = question_count if question_count is not None else original.requested_count
        next_generate_description = bool(generate_description) if generate_description is not None else original.generate_description == "true"
        next_extra_instruction = extra_instruction if extra_instruction is not None else original.extra_instruction
        next_inherit_context = bool(inherit_context) if inherit_context is not None else bool(original.inherit_context)
        next_include_existing_questions = bool(include_existing_questions) if include_existing_questions is not None else bool(original.include_existing_questions)
        effective_count, normalized_extra_instruction = self._normalize_generation_inputs(next_count_mode, next_count, next_mode, next_extra_instruction)
        config = self.pick_ai_config(user.id, ai_provider_config_id or original.ai_provider_config_id)

        source_file_name = original.source_file_name
        if file:
            content = await file.read()
            try:
                text = extract_text(file.filename or "upload.txt", content)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            source_file_name = file.filename
        else:
            text = (source_text or "").strip() or (original.source_text_snapshot or "")
        if not text.strip():
            raise HTTPException(status_code=422, detail="重新生成需要源文本或上传文件")

        host = urlparse(config.api_base_url).netloc or config.api_base_url
        if original.purpose == "create_bank":
            desired = desired_visibility or (old_bank.desired_visibility if old_bank else "private")
            if desired not in ("private", "public"):
                raise HTTPException(status_code=422, detail="Invalid desired_visibility")
            bank = QuestionBank(
                owner_id=user.id,
                title=(title or (old_bank.title if old_bank else original.bank_title_snapshot) or "重新生成题库").strip(),
                description=description if description is not None else (old_bank.description if old_bank else None),
                visibility="private",
                desired_visibility=desired,
                generation_status="pending",
                ai_provider_config_id=config.id,
                ai_model_name=config.model,
                ai_base_url_host=host,
            )
            self.db.add(bank)
            self.db.flush()
            if old_bank and old_bank.tags:
                set_bank_tags(self.db, bank, [tag.name for tag in old_bank.tags])
        else:
            if not old_bank:
                raise HTTPException(status_code=404, detail="Question bank not found")
            bank = old_bank

        workflow = AIGenerationWorkflow(
            bank_id=bank.id,
            user_id=user.id,
            purpose=original.purpose,
            generation_mode=next_mode,
            status="pending",
            source_file_name=source_file_name,
            source_text_snapshot=text,
            bank_title_snapshot=bank.title,
            requested_count=effective_count,
            generate_description="true" if next_generate_description else "false",
            extra_instruction=normalized_extra_instruction,
            inherit_context=next_inherit_context,
            include_existing_questions=next_include_existing_questions,
            retry_of_workflow_id=original.id,
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
            type="bank_parse_ai" if next_mode == "bank_parse" else "document_ai",
            status="pending",
            desired_visibility=bank.desired_visibility,
            file_name=source_file_name,
            ai_provider_config_id=config.id,
            ai_base_url_snapshot=host,
            ai_model_snapshot=config.model,
        )
        self.db.add(job)
        bank.generation_status = "processing"
        self.db.commit()
        background_tasks.add_task(run_generation_task, workflow.id, text, effective_count, next_generate_description, next_mode, normalized_extra_instruction)
        return AIGenerationWorkflowCreatedOut(workflow_id=workflow.id, bank_id=bank.id, job_id=job.id)

    def workflows_for_user_stmt(self, user: User, status: str | None = None, bank_id: int | None = None):
        stmt = select(AIGenerationWorkflow).where(AIGenerationWorkflow.user_id == user.id)
        if status:
            stmt = stmt.where(AIGenerationWorkflow.status == status)
        if bank_id:
            stmt = stmt.where(AIGenerationWorkflow.bank_id == bank_id)
        return stmt.order_by(AIGenerationWorkflow.created_at.desc())

    def workflows_for_readable_bank_stmt(self, bank_id: int, user: User, status: str | None = None):
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_read(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        stmt = select(AIGenerationWorkflow).where(AIGenerationWorkflow.bank_id == bank_id)
        if status:
            stmt = stmt.where(AIGenerationWorkflow.status == status)
        return stmt.order_by(AIGenerationWorkflow.created_at.desc(), AIGenerationWorkflow.id.desc())

    def get_owned_workflow(self, workflow_id: int, user: User) -> AIGenerationWorkflow:
        workflow = self.db.get(AIGenerationWorkflow, workflow_id)
        if not workflow or workflow.user_id != user.id:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow

    def workflow_out(self, workflow: AIGenerationWorkflow, *, redact_sensitive: bool = False) -> AIGenerationWorkflowOut:
        out = AIGenerationWorkflowOut.model_validate(workflow, from_attributes=True)
        out.workflow_id = workflow.id
        out.workflow_status = workflow.status
        out.retried_by_workflow_id = self.retried_by_workflow_id(workflow.id)
        job = self.db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        if job:
            out.job_id = job.id
            out.type = job.type
        draft = self.db.scalar(select(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if draft:
            out.draft_question_count = self.db.scalar(select(func.count()).select_from(AIGenerationDraftQuestion).where(AIGenerationDraftQuestion.draft_id == draft.id)) or 0
            out.can_confirm = workflow.status == "draft_ready"
        out.imported_question_count = self.imported_question_count(workflow.id)
        out.question_delta = out.imported_question_count
        out.error_summary = self.error_summary(workflow.error_message)
        if redact_sensitive:
            out.source_file_name = None
            out.source_text_snapshot = None
            out.extra_instruction = None
            out.error_message = None
            out.ai_provider_config_id = None
            out.can_confirm = False
        return out

    def imported_question_count(self, workflow_id: int) -> int:
        step = self.db.scalar(
            select(AIGenerationWorkflowStep)
            .where(AIGenerationWorkflowStep.workflow_id == workflow_id, AIGenerationWorkflowStep.step_name == "confirm_draft", AIGenerationWorkflowStep.status == "succeeded")
            .order_by(AIGenerationWorkflowStep.id.desc())
        )
        if not step or not step.output_json:
            return 0
        try:
            data = json.loads(step.output_json)
        except json.JSONDecodeError:
            return 0
        value = data.get("question_count")
        return value if isinstance(value, int) and value > 0 else 0

    @staticmethod
    def error_summary(message: str | None) -> str | None:
        if not message:
            return None
        compact = " ".join(line.strip() for line in message.splitlines() if line.strip())
        return compact[:160] + ("..." if len(compact) > 160 else "")

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
        return self.cancel_workflow(workflow_id, user, "用户丢弃草稿")

    def cancel_workflow(self, workflow_id: int, user: User, cancel_reason: str | None = None) -> dict:
        workflow = self.get_owned_workflow(workflow_id, user)
        if workflow.status not in {"draft_ready", "failed"}:
            raise HTTPException(status_code=400, detail="当前 workflow 状态不允许撤销")
        if self.retried_by_workflow_id(workflow.id):
            raise HTTPException(status_code=400, detail="该 workflow 已经重新生成，不能再次操作")
        draft = self.db.scalar(select(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if draft:
            draft.status = "discarded"
        bank = self.db.get(QuestionBank, workflow.bank_id) if workflow.bank_id else None
        if bank and not workflow.bank_title_snapshot:
            workflow.bank_title_snapshot = bank.title
        workflow.status = "cancelled"
        workflow.cancel_reason = (cancel_reason or "").strip() or "用户撤销"
        workflow.finished_at = now_utc()
        job = self.db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        if job:
            job.status = "cancelled"
            job.error_message = workflow.cancel_reason
            job.finished_at = now_utc()
        if workflow.purpose == "create_bank" and bank:
            workflow.bank_id = None
            if job:
                job.bank_id = None
            self.db.execute(delete(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow.id))
            self.db.delete(bank)
        elif bank:
            bank.generation_status = "none" if bank.question_count == 0 else "succeeded"
        self.db.commit()
        return {"ok": True}

    def retried_by_workflow_id(self, workflow_id: int) -> int | None:
        return self.db.scalar(
            select(AIGenerationWorkflow.id)
            .where(AIGenerationWorkflow.retry_of_workflow_id == workflow_id)
            .order_by(AIGenerationWorkflow.id.asc())
            .limit(1)
        )

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

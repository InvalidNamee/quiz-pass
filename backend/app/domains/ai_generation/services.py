import json
from urllib.parse import urlparse

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domains.ai_generation.schemas import AIGenerationWorkflowCreatedOut
from app.domains.ai_generation.drafts import DraftService
from app.domains.ai_generation.errors import AIOutputValidationError
from app.domains.ai_generation.watchdog import fail_stale_workflows
from app.domains.ai_generation.workflow_runtime import WorkflowRuntime
from app.domains.ai_generation.workflow_state import now_utc
from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.infrastructure.audit import AuditService
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.ai_workflow import AIGenerationDraft, AIGenerationDraftQuestion, AIGenerationWorkflow, AIGenerationWorkflowStep
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.ai import AIGenerationDraftOut, AIGenerationWorkflowDetailOut, AIGenerationWorkflowOut, AIGenerationWorkflowStepOut
from app.domains.question_banks.tags import set_bank_tags
from app.utils.document_extractors import extract_text


SOURCE_FILE_NAME_MAX_LENGTH = 255
AI_CONTEXT_MAX_LENGTH = 12000


def summarize_source_file_name(filenames: list[str]) -> str | None:
    if not filenames:
        return None
    if len(filenames) == 1:
        return filenames[0][:SOURCE_FILE_NAME_MAX_LENGTH]
    suffix = f" 等 {len(filenames)} 个文件"
    prefix_limit = max(0, SOURCE_FILE_NAME_MAX_LENGTH - len(suffix))
    return f"{filenames[0][:prefix_limit]}{suffix}"


def validate_source_text_size(text: str) -> None:
    max_chars = int(get_settings().ai_max_text_chars or 0)
    if max_chars > 0 and len(text) > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"材料过长：提取后 {len(text)} 字，超过上限 {max_chars} 字，请拆分文件或减少文本量",
        )


def normalize_ai_context(value: str | None) -> str | None:
    text = (value or "").strip()
    if len(text) > AI_CONTEXT_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=f"AI 背景知识不能超过 {AI_CONTEXT_MAX_LENGTH} 字")
    return text or None


async def extract_uploaded_sources(file: UploadFile | None = None, files: list[UploadFile] | None = None) -> tuple[str, str | None]:
    uploads: list[UploadFile] = []
    if files:
        uploads.extend(upload for upload in files if upload is not None)
    if file:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=422, detail="请上传文件")

    extracted: list[tuple[str, str]] = []
    for upload in uploads:
        filename = upload.filename or "upload.txt"
        content = await upload.read()
        try:
            extracted.append((filename, extract_text(filename, content)))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if len(extracted) == 1:
        validate_source_text_size(extracted[0][1])
        return extracted[0][1], summarize_source_file_name([extracted[0][0]])
    combined_text = "\n\n".join(f"===== 文件: {filename} =====\n{text}" for filename, text in extracted)
    validate_source_text_size(combined_text)
    return combined_text, summarize_source_file_name([filename for filename, _ in extracted])


def run_generation_task(workflow_id: int, text: str, question_count: int | None, generate_description: bool, generation_mode: str, extra_instruction: str | None) -> None:
    db = SessionLocal()
    try:
        from app.domains.ai_generation import facade as ai_generation

        workflow = db.get(AIGenerationWorkflow, workflow_id)
        if workflow:
            text = text or workflow.source_text_snapshot or ""
            question_count = question_count if question_count is not None else workflow.requested_count
            generate_description = generate_description if generate_description is not None else workflow.generate_description == "true"
            generation_mode = generation_mode or workflow.generation_mode
            extra_instruction = extra_instruction if extra_instruction is not None else workflow.extra_instruction
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

    def schedule_workflow(
        self,
        background_tasks: BackgroundTasks,
        workflow: AIGenerationWorkflow,
        job: ImportJob,
        text: str,
        question_count: int | None,
        generate_description: bool,
        generation_mode: str,
        extra_instruction: str | None,
    ) -> None:
        if get_settings().ai_workflow_execution_mode == "rq":
            from app.domains.ai_generation.queue import enqueue_workflow

            try:
                enqueue_workflow(workflow.id, job)
            except Exception as exc:
                self.mark_queue_enqueue_failed(workflow, job, exc)
                self.db.commit()
                return
            self.db.commit()
            return
        background_tasks.add_task(run_generation_task, workflow.id, text, question_count, generate_description, generation_mode, extra_instruction)

    def mark_queue_enqueue_failed(self, workflow: AIGenerationWorkflow, job: ImportJob, exc: Exception) -> None:
        message = f"队列入队失败：{type(exc).__name__}: {str(exc)[:500]}"
        workflow.status = "failed"
        workflow.error_message = message
        workflow.finished_at = now_utc()
        job.status = "failed"
        job.error_message = message
        job.finished_at = now_utc()
        bank = self.db.get(QuestionBank, workflow.bank_id) if workflow.bank_id else None
        if bank and workflow.purpose == "create_bank":
            bank.generation_status = "failed"
            bank.visibility = "private"
        elif bank:
            bank.generation_status = "succeeded" if bank.question_count > 0 else "none"
        self.db.flush()

    async def create_bank_workflow(
        self,
        user: User,
        background_tasks: BackgroundTasks,
        title: str,
        description: str | None,
        ai_context: str | None,
        desired_visibility: str,
        ai_provider_config_id: int | None,
        question_count_mode: str,
        question_count: int | None,
        question_type_settings: str | None,
        generate_description: bool,
        generation_mode: str,
        extra_instruction: str | None,
        inherit_context: bool,
        tag_names: str | None,
        file: UploadFile | None = None,
        files: list[UploadFile] | None = None,
    ) -> AIGenerationWorkflowCreatedOut:
        if desired_visibility not in ("private", "public"):
            raise HTTPException(status_code=422, detail="Invalid desired_visibility")
        if desired_visibility == "public" and user.role != "admin":
            raise HTTPException(status_code=403, detail="普通用户只能通过分享生成公开题库")
        effective_count, normalized_extra_instruction, normalized_type_settings = self._normalize_generation_inputs(question_count_mode, question_count, generation_mode, extra_instruction, question_type_settings)
        try:
            parsed_tag_names = json.loads(tag_names) if tag_names else []
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="tag_names 必须是字符串数组") from exc
        if not isinstance(parsed_tag_names, list):
            raise HTTPException(status_code=422, detail="tag_names 必须是字符串数组")
        normalized_ai_context = normalize_ai_context(ai_context)

        config = self.pick_ai_config(user.id, ai_provider_config_id)
        text, source_file_name = await extract_uploaded_sources(file, files)

        host = urlparse(config.api_base_url).netloc or config.api_base_url
        bank = QuestionBank(
            owner_id=user.id,
            title=title,
            description=description,
            ai_context=normalized_ai_context,
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
            source_file_name=source_file_name,
            source_text_snapshot=text,
            bank_title_snapshot=title,
            requested_count=effective_count,
            question_type_settings_json=json.dumps(normalized_type_settings, ensure_ascii=False) if normalized_type_settings else None,
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
            file_name=source_file_name,
            ai_provider_config_id=config.id,
            ai_base_url_snapshot=host,
            ai_model_snapshot=config.model,
        )
        self.db.add(job)
        self.db.flush()
        self.db.commit()
        self.schedule_workflow(background_tasks, workflow, job, text, effective_count, generate_description, generation_mode, normalized_extra_instruction)
        return AIGenerationWorkflowCreatedOut(workflow_id=workflow.id, bank_id=bank.id, job_id=job.id)

    async def create_extend_workflow(
        self,
        bank_id: int,
        user: User,
        background_tasks: BackgroundTasks,
        ai_provider_config_id: int | None,
        question_count_mode: str,
        question_count: int | None,
        question_type_settings: str | None,
        generate_description: bool,
        generation_mode: str,
        extra_instruction: str | None,
        inherit_context: bool,
        include_existing_questions: bool,
        file: UploadFile | None = None,
        files: list[UploadFile] | None = None,
    ) -> AIGenerationWorkflowCreatedOut:
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_extend_with_ai(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        effective_count, normalized_extra_instruction, normalized_type_settings = self._normalize_generation_inputs(question_count_mode, question_count, generation_mode, extra_instruction, question_type_settings)
        config = self.pick_ai_config(user.id, ai_provider_config_id)
        text, source_file_name = await extract_uploaded_sources(file, files)

        host = urlparse(config.api_base_url).netloc or config.api_base_url
        workflow = AIGenerationWorkflow(
            bank_id=bank.id,
            user_id=user.id,
            purpose="extend_bank",
            generation_mode=generation_mode,
            status="pending",
            source_file_name=source_file_name,
            source_text_snapshot=text,
            bank_title_snapshot=bank.title,
            requested_count=effective_count,
            question_type_settings_json=json.dumps(normalized_type_settings, ensure_ascii=False) if normalized_type_settings else None,
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
            file_name=source_file_name,
            ai_provider_config_id=config.id,
            ai_base_url_snapshot=host,
            ai_model_snapshot=config.model,
        )
        self.db.add(job)
        self.db.flush()
        self.db.commit()
        self.schedule_workflow(background_tasks, workflow, job, text, effective_count, generate_description, generation_mode, normalized_extra_instruction)
        return AIGenerationWorkflowCreatedOut(workflow_id=workflow.id, bank_id=bank.id, job_id=job.id)

    async def retry_workflow(
        self,
        workflow_id: int,
        user: User,
        background_tasks: BackgroundTasks,
        ai_provider_config_id: int | None,
        question_count_mode: str | None,
        question_count: int | None,
        question_type_settings: str | None,
        generate_description: bool | None,
        generation_mode: str | None,
        extra_instruction: str | None,
        inherit_context: bool | None,
        include_existing_questions: bool | None,
        source_text: str | None,
        title: str | None,
        description: str | None,
        ai_context: str | None,
        desired_visibility: str | None,
        file: UploadFile | None,
        files: list[UploadFile] | None = None,
    ) -> AIGenerationWorkflowCreatedOut:
        original = self.get_owned_workflow(workflow_id, user)
        if original.status not in {"failed", "cancelled", "draft_ready"}:
            raise HTTPException(status_code=400, detail="只有失败、已取消或草稿待确认的 workflow 可以重新生成")
        if self.retried_by_workflow_id(original.id):
            raise HTTPException(status_code=400, detail="该 workflow 已经重新生成，不能再次操作")

        old_bank = self.db.get(QuestionBank, original.bank_id) if original.bank_id else None
        if original.purpose == "extend_bank" and not QuestionBankPermissionService.can_extend_with_ai(old_bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")

        next_mode = generation_mode or original.generation_mode
        next_count_mode = question_count_mode or ("fixed" if original.requested_count else "adaptive")
        next_count = question_count if question_count is not None else original.requested_count
        next_question_type_settings = question_type_settings if question_type_settings is not None else original.question_type_settings_json
        next_generate_description = bool(generate_description) if generate_description is not None else original.generate_description == "true"
        next_extra_instruction = extra_instruction if extra_instruction is not None else original.extra_instruction
        next_inherit_context = bool(inherit_context) if inherit_context is not None else bool(original.inherit_context)
        next_include_existing_questions = bool(include_existing_questions) if include_existing_questions is not None else bool(original.include_existing_questions)
        effective_count, normalized_extra_instruction, normalized_type_settings = self._normalize_generation_inputs(next_count_mode, next_count, next_mode, next_extra_instruction, next_question_type_settings)
        config = self.pick_ai_config(user.id, ai_provider_config_id or original.ai_provider_config_id)

        source_file_name = original.source_file_name
        if file or files:
            text, source_file_name = await extract_uploaded_sources(file, files)
        else:
            text = (source_text or "").strip() or (original.source_text_snapshot or "")
        if not text.strip():
            raise HTTPException(status_code=422, detail="重新生成需要源文本或上传文件")
        validate_source_text_size(text)

        host = urlparse(config.api_base_url).netloc or config.api_base_url
        normalized_ai_context = normalize_ai_context(ai_context) if ai_context is not None else None
        if original.purpose == "create_bank":
            desired = desired_visibility or (old_bank.desired_visibility if old_bank else "private")
            if desired not in ("private", "public"):
                raise HTTPException(status_code=422, detail="Invalid desired_visibility")
            if desired == "public" and user.role != "admin":
                raise HTTPException(status_code=403, detail="普通用户只能通过分享生成公开题库")
            if old_bank:
                bank = old_bank
                bank.title = (title or old_bank.title or original.bank_title_snapshot or "重新生成题库").strip()
                bank.description = description if description is not None else old_bank.description
                if ai_context is not None:
                    bank.ai_context = normalized_ai_context
                bank.visibility = "private"
                bank.desired_visibility = desired
                bank.generation_status = "processing"
                bank.ai_provider_config_id = config.id
                bank.ai_model_name = config.model
                bank.ai_base_url_host = host
            else:
                bank = QuestionBank(
                    owner_id=user.id,
                    title=(title or original.bank_title_snapshot or "重新生成题库").strip(),
                    description=description,
                    ai_context=normalized_ai_context,
                    visibility="private",
                    desired_visibility=desired,
                    generation_status="pending",
                    ai_provider_config_id=config.id,
                    ai_model_name=config.model,
                    ai_base_url_host=host,
                )
                self.db.add(bank)
                self.db.flush()
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
            question_type_settings_json=json.dumps(normalized_type_settings, ensure_ascii=False) if normalized_type_settings else None,
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
        if original.purpose == "create_bank":
            bank.generation_status = "processing"
        AuditService(self.db).record(user.id, "workflow.retry", "workflow", original.id, {"new_workflow_id": workflow.id})
        self.db.commit()
        self.schedule_workflow(background_tasks, workflow, job, text, effective_count, next_generate_description, next_mode, normalized_extra_instruction)
        return AIGenerationWorkflowCreatedOut(workflow_id=workflow.id, bank_id=bank.id, job_id=job.id)

    def workflows_for_user_stmt(self, user: User, status: str | None = None, bank_id: int | None = None):
        fail_stale_workflows(self.db)
        stmt = select(AIGenerationWorkflow).where(AIGenerationWorkflow.user_id == user.id)
        if status:
            stmt = stmt.where(AIGenerationWorkflow.status == status)
        if bank_id:
            stmt = stmt.where(AIGenerationWorkflow.bank_id == bank_id)
        return stmt.order_by(AIGenerationWorkflow.created_at.desc())

    def workflows_for_readable_bank_stmt(self, bank_id: int, user: User, status: str | None = None):
        fail_stale_workflows(self.db)
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_read(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        stmt = select(AIGenerationWorkflow).where(AIGenerationWorkflow.bank_id == bank_id)
        if status:
            stmt = stmt.where(AIGenerationWorkflow.status == status)
        return stmt.order_by(AIGenerationWorkflow.created_at.desc(), AIGenerationWorkflow.id.desc())

    def get_owned_workflow(self, workflow_id: int, user: User) -> AIGenerationWorkflow:
        fail_stale_workflows(self.db)
        workflow = self.db.get(AIGenerationWorkflow, workflow_id)
        if not workflow or workflow.user_id != user.id:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow

    def workflow_out(self, workflow: AIGenerationWorkflow, *, redact_sensitive: bool = False) -> AIGenerationWorkflowOut:
        return self.workflow_out_many([workflow], redact_sensitive=redact_sensitive)[0]

    def workflow_out_many(self, workflows: list[AIGenerationWorkflow], *, redact_sensitive: bool = False) -> list[AIGenerationWorkflowOut]:
        if not workflows:
            return []
        workflow_ids = [workflow.id for workflow in workflows]
        jobs = {
            job.workflow_id: job
            for job in self.db.scalars(select(ImportJob).where(ImportJob.workflow_id.in_(workflow_ids))).all()
            if job.workflow_id is not None
        }
        ready_drafts = {
            draft.workflow_id: draft
            for draft in self.db.scalars(
                select(AIGenerationDraft).where(AIGenerationDraft.workflow_id.in_(workflow_ids), AIGenerationDraft.status == "ready")
            ).all()
        }
        draft_ids = [draft.id for draft in ready_drafts.values()]
        draft_question_counts: dict[int, int] = {}
        if draft_ids:
            draft_question_counts = {
                draft_id: count
                for draft_id, count in self.db.execute(
                    select(AIGenerationDraftQuestion.draft_id, func.count())
                    .where(AIGenerationDraftQuestion.draft_id.in_(draft_ids))
                    .group_by(AIGenerationDraftQuestion.draft_id)
                ).all()
            }
        imported_counts: dict[int, int] = {}
        confirm_steps = self.db.execute(
            select(AIGenerationWorkflowStep.workflow_id, AIGenerationWorkflowStep.output_json)
            .where(
                AIGenerationWorkflowStep.workflow_id.in_(workflow_ids),
                AIGenerationWorkflowStep.step_name == "confirm_draft",
                AIGenerationWorkflowStep.status == "succeeded",
            )
            .order_by(AIGenerationWorkflowStep.id.desc())
        ).all()
        for workflow_id, output_json in confirm_steps:
            if workflow_id in imported_counts:
                continue
            imported_counts[workflow_id] = self._question_count_from_step_output(output_json)
        retried_by = {
            parent_id: child_id
            for parent_id, child_id in self.db.execute(
                select(AIGenerationWorkflow.retry_of_workflow_id, func.min(AIGenerationWorkflow.id))
                .where(AIGenerationWorkflow.retry_of_workflow_id.in_(workflow_ids))
                .group_by(AIGenerationWorkflow.retry_of_workflow_id)
            ).all()
            if parent_id is not None
        }

        return [
            self._workflow_out_from_maps(
                workflow,
                job=jobs.get(workflow.id),
                draft=ready_drafts.get(workflow.id),
                draft_question_counts=draft_question_counts,
                imported_question_count=imported_counts.get(workflow.id, 0),
                retried_by_workflow_id=retried_by.get(workflow.id),
                redact_sensitive=redact_sensitive,
            )
            for workflow in workflows
        ]

    def workflow_out_many_for_bank_logs(self, workflows: list[AIGenerationWorkflow], user: User) -> list[AIGenerationWorkflowOut]:
        if not workflows:
            return []
        full_items = self.workflow_out_many(workflows, redact_sensitive=False)
        redacted_items = self.workflow_out_many(workflows, redact_sensitive=True)
        return [
            full_item if workflow.user_id == user.id else redacted_item
            for workflow, full_item, redacted_item in zip(workflows, full_items, redacted_items, strict=True)
        ]

    def _workflow_out_from_maps(
        self,
        workflow: AIGenerationWorkflow,
        *,
        job: ImportJob | None,
        draft: AIGenerationDraft | None,
        draft_question_counts: dict[int, int],
        imported_question_count: int,
        retried_by_workflow_id: int | None,
        redact_sensitive: bool,
    ) -> AIGenerationWorkflowOut:
        out = AIGenerationWorkflowOut.model_validate(workflow, from_attributes=True)
        out.workflow_id = workflow.id
        out.workflow_status = workflow.status
        out.question_type_settings = self.parse_question_type_settings_snapshot(workflow.question_type_settings_json)
        out.retried_by_workflow_id = retried_by_workflow_id
        if job:
            out.job_id = job.id
            out.type = job.type
            out.queue_job_id = job.queue_job_id
            out.enqueued_at = job.enqueued_at
            out.started_at = job.started_at
        if draft:
            out.draft_question_count = draft_question_counts.get(draft.id, 0)
            out.can_confirm = workflow.status == "draft_ready" and retried_by_workflow_id is None
        out.imported_question_count = imported_question_count
        out.question_delta = out.imported_question_count
        out.error_summary = self.error_summary(workflow.error_message)
        out.can_retry = workflow.status in {"failed", "cancelled", "draft_ready"} and retried_by_workflow_id is None
        out.can_cancel = workflow.status in {"pending", "extracting_document", "calling_model", "validating", "repairing", "draft_ready", "failed"} and retried_by_workflow_id is None
        if redact_sensitive:
            out.source_file_name = None
            out.source_text_snapshot = None
            out.extra_instruction = None
            out.error_message = None
            out.ai_provider_config_id = None
            out.can_confirm = False
            out.can_retry = False
            out.can_cancel = False
        return out

    def imported_question_count(self, workflow_id: int) -> int:
        step = self.db.scalar(
            select(AIGenerationWorkflowStep)
            .where(AIGenerationWorkflowStep.workflow_id == workflow_id, AIGenerationWorkflowStep.step_name == "confirm_draft", AIGenerationWorkflowStep.status == "succeeded")
            .order_by(AIGenerationWorkflowStep.id.desc())
        )
        if not step or not step.output_json:
            return 0
        return self._question_count_from_step_output(step.output_json)

    @staticmethod
    def _question_count_from_step_output(output_json: str | None) -> int:
        if not output_json:
            return 0
        try:
            data = json.loads(output_json)
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

    @staticmethod
    def parse_question_type_settings_snapshot(raw: str | None) -> dict | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def workflow_steps(self, workflow_id: int, user: User) -> list[AIGenerationWorkflowStepOut]:
        workflow = self.get_owned_workflow(workflow_id, user)
        steps = self.db.scalars(
            select(AIGenerationWorkflowStep)
            .where(AIGenerationWorkflowStep.workflow_id == workflow.id)
            .order_by(AIGenerationWorkflowStep.id.asc())
        ).all()
        return [AIGenerationWorkflowStepOut.model_validate(step, from_attributes=True) for step in steps]

    def workflow_detail(self, workflow_id: int, user: User) -> AIGenerationWorkflowDetailOut:
        workflow = self.get_owned_workflow(workflow_id, user)
        detail = AIGenerationWorkflowDetailOut.model_validate(self.workflow_out(workflow).model_dump())
        detail.steps = self.workflow_steps(workflow_id, user)
        detail.failed_payload_json = self._latest_step_payload_json(detail.steps, "validate_payload", "failed", "input")
        detail.failed_repaired_payload_json = self._latest_step_payload_json(detail.steps, "repair_payload", "succeeded", "output")
        return detail

    @staticmethod
    def _latest_step_payload_json(steps: list[AIGenerationWorkflowStepOut], step_name: str, status: str, side: str) -> str | None:
        for step in reversed(steps):
            if step.step_name != step_name or step.status != status:
                continue
            raw = step.output_json if side == "output" else step.input_json
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            payload = data.get("payload") if isinstance(data, dict) and "payload" in data else data
            return json.dumps(payload, ensure_ascii=False, indent=2)
        return None

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
        if self.retried_by_workflow_id(workflow.id):
            raise HTTPException(status_code=400, detail="该 workflow 已重新生成，不能确认旧草稿")
        job = self.db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        draft = self.db.scalar(select(AIGenerationDraft).options(selectinload(AIGenerationDraft.questions)).where(AIGenerationDraft.workflow_id == workflow.id, AIGenerationDraft.status == "ready"))
        if not draft:
            raise HTTPException(status_code=400, detail="没有可确认的草稿")
        try:
            bank = DraftService(self.db).confirm(job, draft)
            AuditService(self.db).record(user.id, "workflow.confirm_draft", "workflow", workflow.id, {"bank_id": bank.id})
            self.db.commit()
            return {"ok": True, "bank_id": bank.id}
        except AIOutputValidationError as exc:
            self.db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    def discard_draft(self, workflow_id: int, user: User) -> dict:
        return self.cancel_workflow(workflow_id, user, "用户丢弃草稿")

    def cancel_workflow(self, workflow_id: int, user: User, cancel_reason: str | None = None) -> dict:
        workflow = self.get_owned_workflow(workflow_id, user)
        if workflow.status not in {"pending", "extracting_document", "calling_model", "validating", "repairing", "draft_ready", "failed"}:
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
        AuditService(self.db).record(user.id, "workflow.cancel", "workflow", workflow.id, {"reason": workflow.cancel_reason})
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
    def _normalize_generation_inputs(question_count_mode: str, question_count: int | None, generation_mode: str, extra_instruction: str | None, question_type_settings: str | None = None) -> tuple[int | None, str | None, dict | None]:
        if generation_mode not in ("knowledge_generate", "bank_parse"):
            raise HTTPException(status_code=422, detail="Invalid generation_mode")
        if question_count_mode not in ("fixed", "adaptive"):
            raise HTTPException(status_code=422, detail="Invalid question_count_mode")
        normalized_extra_instruction = (extra_instruction or "").strip() or None
        if normalized_extra_instruction and len(normalized_extra_instruction) > 2000:
            raise HTTPException(status_code=422, detail="额外指令不能超过 2000 字")
        normalized_type_settings = AIGenerationWorkflowService._parse_question_type_settings(question_type_settings, generation_mode)
        if generation_mode == "knowledge_generate" and not normalized_type_settings and question_count_mode == "fixed" and not question_count:
            raise HTTPException(status_code=422, detail="固定题数模式必须指定题数")
        if normalized_type_settings:
            fixed_counts = [
                config.get("count")
                for config in normalized_type_settings.values()
                if config.get("enabled") and isinstance(config.get("count"), int) and config.get("count") > 0
            ]
            has_adaptive = any(config.get("enabled") and config.get("count") is None for config in normalized_type_settings.values())
            effective_count = None if generation_mode != "knowledge_generate" or has_adaptive else sum(fixed_counts) or None
        else:
            effective_count = question_count if generation_mode == "knowledge_generate" and question_count_mode == "fixed" else None
        return effective_count, normalized_extra_instruction, normalized_type_settings

    @staticmethod
    def _parse_question_type_settings(raw: str | None, generation_mode: str) -> dict | None:
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="question_type_settings 必须是 JSON 对象") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="question_type_settings 必须是 JSON 对象")
        allowed = {"single", "multiple", "blank", "short_answer"}
        normalized: dict[str, dict] = {}
        for key in allowed:
            config = payload.get(key) or {}
            if not isinstance(config, dict):
                raise HTTPException(status_code=422, detail="question_type_settings 中每个题型必须是对象")
            enabled = bool(config.get("enabled"))
            raw_count = config.get("count")
            count = None
            if generation_mode == "knowledge_generate" and enabled and raw_count is not None:
                if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count < 1 or raw_count > 100:
                    raise HTTPException(status_code=422, detail="题型数量必须是 1-100 的整数或 null")
                count = raw_count
            normalized[key] = {"enabled": enabled, "count": count}
        if not any(config["enabled"] for config in normalized.values()):
            raise HTTPException(status_code=422, detail="至少启用一种题型")
        return normalized

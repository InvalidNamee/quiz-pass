import json
from typing import Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.ai_generation.client import OpenAICompatibleClient, format_ai_error
from app.domains.ai_generation.context import WorkflowContextBuilder
from app.domains.ai_generation.drafts import DraftService
from app.domains.ai_generation.errors import AIGenerationError
from app.domains.ai_generation.prompts import PromptBuilder
from app.domains.ai_generation.validator import AIPayloadValidator
from app.domains.ai_generation.workflow_state import WorkflowStateService, now_utc
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.ai_workflow import AIGenerationWorkflow
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank


MAX_REPAIR_ATTEMPTS = 2


class AIGenerationState(TypedDict, total=False):
    db: Session
    workflow_id: int
    bank_id: int
    user_id: int
    config_id: int
    text: str
    context_text: str
    requested_count: int | None
    generate_description: bool
    generation_mode: str
    extra_instruction: str | None
    question_type_settings: dict | None
    raw_payload: dict
    repaired_payload: dict
    payload: dict
    questions: list[dict]
    bank_description: str | None
    validation_summary: str
    validation_error: str | None
    repair_attempts: int
    error_message: str | None
    route: str


ModelClient = Callable[[UserAIProviderConfig, str, int | None, bool, str, str | None, str | None, str | None], dict]


class WorkflowRuntime:
    def __init__(self, db: Session, model_client: ModelClient | None = None):
        self.db = db
        self.model_client = model_client or OpenAICompatibleClient().generate_json
        self.graph = self.build_graph()

    def run(
        self,
        workflow_id: int,
        text: str,
        requested_count: int | None,
        generate_description: bool = False,
        generation_mode: str = "knowledge_generate",
        extra_instruction: str | None = None,
    ) -> None:
        workflow = self.db.get(AIGenerationWorkflow, workflow_id)
        if not workflow:
            return
        job = self.db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        bank = self.db.get(QuestionBank, workflow.bank_id)
        config = self.db.get(UserAIProviderConfig, workflow.ai_provider_config_id) if workflow.ai_provider_config_id else None
        if not bank or not workflow or not config:
            return
        if workflow.status == "cancelled" or (job and job.status == "cancelled"):
            return
        if job:
            job.started_at = now_utc()
        workflow.source_text_snapshot = workflow.source_text_snapshot or text
        self.db.commit()
        try:
            self.graph.invoke(
                {
                    "db": self.db,
                    "workflow_id": workflow.id,
                    "bank_id": bank.id,
                    "user_id": workflow.user_id,
                    "config_id": config.id,
                    "text": workflow.source_text_snapshot or text,
                    "requested_count": requested_count if requested_count is not None else workflow.requested_count,
                    "generate_description": generate_description if generate_description is not None else workflow.generate_description == "true",
                    "generation_mode": generation_mode or workflow.generation_mode,
                    "extra_instruction": PromptBuilder.normalize_extra_instruction(extra_instruction if extra_instruction is not None else workflow.extra_instruction),
                    "question_type_settings": self.parse_question_type_settings(workflow.question_type_settings_json),
                    "repair_attempts": 0,
                }
            )
        except WorkflowCancelled:
            self.db.rollback()
            return

    def build_graph(self):
        graph = StateGraph(AIGenerationState)
        graph.add_node("extract_document", self.extract_document_node)
        graph.add_node("build_context", self.build_context_node)
        graph.add_node("generate_or_parse", self.generate_or_parse_node)
        graph.add_node("validate_payload", self.validate_payload_node)
        graph.add_node("repair_payload", self.repair_payload_node)
        graph.add_node("write_draft", self.write_draft_node)
        graph.add_node("fail", self.fail_node)
        graph.add_edge(START, "extract_document")
        graph.add_edge("extract_document", "build_context")
        graph.add_edge("build_context", "generate_or_parse")
        graph.add_conditional_edges("generate_or_parse", self.route_after_generation)
        graph.add_conditional_edges("validate_payload", self.route_after_validate)
        graph.add_conditional_edges("repair_payload", self.route_after_repair)
        graph.add_edge("write_draft", END)
        graph.add_edge("fail", END)
        return graph.compile()

    def load_objects(self, state: AIGenerationState):
        db = state["db"]
        db.expire_all()
        workflow = db.get(AIGenerationWorkflow, state["workflow_id"])
        job = db.scalar(select(ImportJob).where(ImportJob.workflow_id == state["workflow_id"]))
        if not job or not workflow:
            raise AIGenerationError("生成任务或 workflow 不存在")
        self.raise_if_cancelled(workflow, job)
        bank = db.get(QuestionBank, state["bank_id"])
        config = db.get(UserAIProviderConfig, state["config_id"])
        if not bank or not config:
            raise AIGenerationError("题库或 AI 配置不存在")
        return db, job, workflow, bank, config

    @staticmethod
    def raise_if_cancelled(workflow: AIGenerationWorkflow, job: ImportJob) -> None:
        if workflow.status == "cancelled" or job.status == "cancelled":
            raise WorkflowCancelled()

    def extract_document_node(self, state: AIGenerationState) -> AIGenerationState:
        db, job, workflow, bank, _ = self.load_objects(state)
        state_service = WorkflowStateService(db)
        state_service.set_status(workflow, job, bank, "extracting_document")
        state_service.record_step(workflow.id, "extract_document", "succeeded", {"file_name": workflow.source_file_name}, {"text_length": len(state["text"])})
        db.commit()
        return {"text": state["text"], "route": "ok"}

    def build_context_node(self, state: AIGenerationState) -> AIGenerationState:
        db, _, workflow, bank, _ = self.load_objects(state)
        context = WorkflowContextBuilder(db).build(bank, workflow)
        context_text = f"{context}\n\n{state['text']}" if context else state["text"]
        WorkflowStateService(db).record_step(workflow.id, "build_context", "succeeded", {"purpose": workflow.purpose}, {"context_length": len(context_text)})
        db.commit()
        return {"context_text": context_text}

    def generate_or_parse_node(self, state: AIGenerationState) -> AIGenerationState:
        db, job, workflow, bank, config = self.load_objects(state)
        state_service = WorkflowStateService(db)
        try:
            state_service.set_status(workflow, job, bank, "calling_model")
            db.commit()
            payload = self.model_client(
                config,
                state.get("context_text") or state["text"],
                state.get("requested_count"),
                state.get("generate_description", False),
                state.get("generation_mode", "knowledge_generate"),
                state.get("extra_instruction"),
                system_prompt=None,
                user_prompt=PromptBuilder.build_generation_prompt(
                    state.get("context_text") or state["text"],
                    state.get("requested_count"),
                    state.get("generate_description", False),
                    state.get("generation_mode", "knowledge_generate"),
                    state.get("extra_instruction"),
                    state.get("question_type_settings"),
                ),
            )
            state_service.record_step(workflow.id, "generate_or_parse", "succeeded", {"mode": workflow.generation_mode}, {"payload": payload})
            db.commit()
            return {"raw_payload": payload, "payload": payload, "route": "ok"}
        except Exception as exc:
            message = format_ai_error(exc, workflow.generation_mode, config)
            state_service.record_step(workflow.id, "generate_or_parse", "failed", {"mode": workflow.generation_mode}, error_message=message)
            db.commit()
            return {"validation_error": message, "error_message": message, "route": "fail"}

    def validate_payload_node(self, state: AIGenerationState) -> AIGenerationState:
        db, job, workflow, bank, _ = self.load_objects(state)
        state_service = WorkflowStateService(db)
        payload = state.get("payload") or {}
        try:
            state_service.set_status(workflow, job, bank, "validating")
            questions, summary = AIPayloadValidator.validate(payload, workflow.generation_mode, workflow.requested_count, self.parse_question_type_settings(workflow.question_type_settings_json))
            bank_description = payload.get("bank_description")
            state_service.record_step(workflow.id, "validate_payload", "succeeded", {"payload": payload}, {"summary": summary})
            db.commit()
            return {
                "questions": questions,
                "bank_description": bank_description.strip() if isinstance(bank_description, str) and bank_description.strip() else None,
                "validation_summary": summary,
                "validation_error": None,
                "route": "draft",
            }
        except Exception as exc:
            message = str(exc)
            attempts = state.get("repair_attempts", 0)
            state_service.record_step(workflow.id, "validate_payload", "failed", {"payload": payload}, error_message=message)
            db.commit()
            return {"validation_error": message, "route": "repair" if attempts < MAX_REPAIR_ATTEMPTS else "fail"}

    def repair_payload_node(self, state: AIGenerationState) -> AIGenerationState:
        db, job, workflow, bank, config = self.load_objects(state)
        state_service = WorkflowStateService(db)
        attempts = state.get("repair_attempts", 0) + 1
        payload = state.get("payload") or state.get("raw_payload") or {}
        try:
            state_service.set_status(workflow, job, bank, "repairing")
            workflow.repair_attempts = attempts
            job.error_message = f"正在自动修复第 {attempts} 次：{state.get('validation_error')}"
            db.commit()
            repaired = self.model_client(
                config,
                state.get("context_text") or state["text"],
                state.get("requested_count"),
                state.get("generate_description", False),
                workflow.generation_mode,
                state.get("extra_instruction"),
                PromptBuilder.REPAIR_SYSTEM_PROMPT,
                PromptBuilder.build_repair_prompt(payload, state.get("validation_error") or "未知错误"),
            )
            state_service.record_step(workflow.id, "repair_payload", "succeeded", {"attempt": attempts, "error": state.get("validation_error")}, {"payload": repaired})
            db.commit()
            return {"payload": repaired, "repaired_payload": repaired, "repair_attempts": attempts, "route": "ok"}
        except Exception as exc:
            message = format_ai_error(exc, workflow.generation_mode, config)
            state_service.record_step(workflow.id, "repair_payload", "failed", {"attempt": attempts}, error_message=message)
            db.commit()
            return {"validation_error": message, "error_message": message, "repair_attempts": attempts, "route": "fail"}

    def write_draft_node(self, state: AIGenerationState) -> AIGenerationState:
        db, job, workflow, bank, _ = self.load_objects(state)
        DraftService(db).write_ready_draft(
            workflow,
            job,
            bank,
            state.get("questions") or [],
            state.get("bank_description"),
            state.get("raw_payload") or state.get("payload") or {},
            state.get("repaired_payload") or state.get("payload") or {},
            state.get("validation_summary"),
            bool(state.get("generate_description")),
        )
        db.commit()
        return {"route": "done"}

    def fail_node(self, state: AIGenerationState) -> AIGenerationState:
        db, job, workflow, bank, config = self.load_objects(state)
        attempts = state.get("repair_attempts", workflow.repair_attempts)
        message = state.get("error_message") or format_ai_error(state.get("validation_error") or "生成失败", workflow.generation_mode, config, attempts)
        if state.get("validation_error") and attempts >= MAX_REPAIR_ATTEMPTS:
            message = format_ai_error(state["validation_error"], workflow.generation_mode, config, attempts)
        WorkflowStateService(db).fail(workflow, job, bank, message, attempts)
        db.commit()
        return {"error_message": message, "route": "done"}

    @staticmethod
    def route_after_generation(state: AIGenerationState) -> Literal["validate_payload", "fail"]:
        return "fail" if state.get("route") == "fail" else "validate_payload"

    @staticmethod
    def route_after_validate(state: AIGenerationState) -> Literal["repair_payload", "write_draft", "fail"]:
        if state.get("route") == "draft":
            return "write_draft"
        if state.get("route") == "repair":
            return "repair_payload"
        return "fail"

    @staticmethod
    def route_after_repair(state: AIGenerationState) -> Literal["validate_payload", "fail"]:
        return "fail" if state.get("route") == "fail" else "validate_payload"

    @staticmethod
    def parse_question_type_settings(raw: str | None) -> dict | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None


class WorkflowCancelled(Exception):
    pass

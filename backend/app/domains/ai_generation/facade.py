"""Compatibility facade for AI generation tests and runtime injection.

Core AI workflow logic lives in this package. This module keeps a narrow,
patchable surface for tests and background task execution without preserving
the old top-level services package.
"""

from sqlalchemy.orm import Session

from app.domains.ai_generation.client import OpenAICompatibleClient, extract_json, format_ai_error
from app.domains.ai_generation.drafts import DraftService
from app.domains.ai_generation.errors import AIGenerationError, AIOutputValidationError
from app.domains.ai_generation.prompts import ANSWER_RULES, QUESTION_JSON_SCHEMA, PromptBuilder
from app.domains.ai_generation.validator import AIPayloadValidator
from app.domains.ai_generation.workflow_runtime import MAX_REPAIR_ATTEMPTS, WorkflowRuntime
from app.models.ai_provider_config import UserAIProviderConfig
from app.models.ai_workflow import AIGenerationDraft
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank

KNOWLEDGE_GENERATE_SYSTEM_PROMPT = PromptBuilder.KNOWLEDGE_GENERATE_SYSTEM_PROMPT
BANK_PARSE_SYSTEM_PROMPT = PromptBuilder.BANK_PARSE_SYSTEM_PROMPT
REPAIR_SYSTEM_PROMPT = PromptBuilder.REPAIR_SYSTEM_PROMPT
SYSTEM_PROMPT = KNOWLEDGE_GENERATE_SYSTEM_PROMPT


def _normalize_extra_instruction(extra_instruction: str | None) -> str | None:
    return PromptBuilder.normalize_extra_instruction(extra_instruction)


def _extract_json(text: str) -> dict:
    return extract_json(text)


def _system_prompt(generation_mode: str) -> str:
    return PromptBuilder.system_prompt(generation_mode)


def _build_user_prompt(
    text: str,
    requested_count: int | None,
    generate_description: bool = False,
    generation_mode: str = "knowledge_generate",
    extra_instruction: str | None = None,
    question_type_settings: dict | None = None,
) -> str:
    return PromptBuilder.build_generation_prompt(text, requested_count, generate_description, generation_mode, extra_instruction, question_type_settings)


def _build_repair_prompt(payload: dict, validation_error: str) -> str:
    return PromptBuilder.build_repair_prompt(payload, validation_error)


def _format_error(exc: Exception | str, generation_mode: str, config: UserAIProviderConfig | None = None, repair_attempts: int = 0) -> str:
    return format_ai_error(exc, generation_mode, config, repair_attempts)


def _call_openai_compatible(
    config: UserAIProviderConfig,
    text: str,
    requested_count: int | None,
    generate_description: bool = False,
    generation_mode: str = "knowledge_generate",
    extra_instruction: str | None = None,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> dict:
    return OpenAICompatibleClient().generate_json(config, text, requested_count, generate_description, generation_mode, extra_instruction, system_prompt, user_prompt)


def validate_generated_payload(payload: dict, generation_mode: str, requested_count: int | None) -> tuple[list[dict], str]:
    return AIPayloadValidator.validate(payload, generation_mode, requested_count)


def generate_questions_from_ai(
    db: Session,
    workflow_id: int,
    text: str,
    requested_count: int | None,
    generate_description: bool = False,
    generation_mode: str = "knowledge_generate",
    extra_instruction: str | None = None,
) -> None:
    WorkflowRuntime(db, model_client=_call_openai_compatible).run(
        workflow_id,
        text,
        requested_count,
        generate_description,
        generation_mode,
        extra_instruction,
    )


def draft_to_payload(draft: AIGenerationDraft) -> dict:
    return DraftService.to_payload(draft)


def replace_draft_questions(db: Session, draft: AIGenerationDraft, bank_description: str | None, questions: list[dict]) -> None:
    DraftService(db).update(draft, bank_description, questions)


def confirm_draft(db: Session, job: ImportJob, draft: AIGenerationDraft) -> QuestionBank:
    return DraftService(db).confirm(job, draft)

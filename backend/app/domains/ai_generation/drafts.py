import json

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.domains.ai_generation.errors import AIGenerationError, AIOutputValidationError
from app.domains.ai_generation.validator import AIPayloadValidator, question_context
from app.domains.ai_generation.workflow_state import WorkflowStateService, now_utc
from app.domains.question_banks.stats import QuestionBankStatsService
from app.models.ai_workflow import AIGenerationDraft, AIGenerationDraftQuestion, AIGenerationWorkflow
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank
from app.utils.json_io import create_question_from_payload, normalize_question_payload


def json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


class DraftService:
    def __init__(self, db: Session):
        self.db = db

    def write_ready_draft(
        self,
        workflow: AIGenerationWorkflow,
        job: ImportJob,
        bank: QuestionBank,
        questions: list[dict],
        bank_description: str | None,
        raw_payload: dict,
        repaired_payload: dict,
        validation_summary: str | None,
        include_description: bool,
    ) -> AIGenerationDraft:
        self.db.execute(delete(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow.id))
        draft = AIGenerationDraft(
            workflow_id=workflow.id,
            bank_id=bank.id,
            user_id=workflow.user_id,
            bank_description=bank_description if include_description else None,
            raw_payload_json=json_dumps(raw_payload),
            repaired_payload_json=json_dumps(repaired_payload),
            validation_summary=validation_summary,
            status="ready",
        )
        self.db.add(draft)
        self.db.flush()
        for index, question in enumerate(questions, start=1):
            self.db.add(
                AIGenerationDraftQuestion(
                    draft_id=draft.id,
                    sort_order=index,
                    type=question["type"],
                    stem=question["stem"],
                    explanation=question.get("explanation"),
                    difficulty=question.get("difficulty"),
                    options_json=json_dumps(question["options"]),
                    validation_status="valid",
                )
            )
        state = WorkflowStateService(self.db)
        state.set_status(workflow, job, bank, "draft_ready")
        workflow.error_message = None
        job.error_message = None
        workflow.finished_at = now_utc()
        job.finished_at = now_utc()
        state.record_step(workflow.id, "write_draft", "succeeded", output_data={"draft_id": draft.id, "question_count": len(questions)})
        return draft

    @staticmethod
    def to_payload(draft: AIGenerationDraft) -> dict:
        questions = []
        for question in sorted(draft.questions, key=lambda item: item.sort_order):
            questions.append(
                {
                    "id": question.id,
                    "type": question.type,
                    "stem": question.stem,
                    "explanation": question.explanation,
                    "difficulty": question.difficulty,
                    "options": json.loads(question.options_json),
                    "validation_status": question.validation_status,
                    "validation_message": question.validation_message,
                }
            )
        return {
            "id": draft.id,
            "workflow_id": draft.workflow_id,
            "job_id": None,
            "bank_id": draft.bank_id,
            "bank_description": draft.bank_description,
            "validation_summary": draft.validation_summary,
            "status": draft.status,
            "questions": questions,
        }

    def update(self, draft: AIGenerationDraft, bank_description: str | None, questions: list[dict]) -> None:
        normalized_questions = []
        for index, raw_question in enumerate(questions, start=1):
            try:
                normalized_questions.append(normalize_question_payload(raw_question))
            except ValueError as exc:
                raise AIOutputValidationError(question_context(index, raw_question if isinstance(raw_question, dict) else {}, str(exc))) from exc
        if not normalized_questions:
            raise AIOutputValidationError("草稿题目不能为空")
        draft.bank_description = (bank_description or "").strip() or None
        draft.validation_summary = f"校验通过，共 {len(normalized_questions)} 道题"
        self.db.execute(delete(AIGenerationDraftQuestion).where(AIGenerationDraftQuestion.draft_id == draft.id))
        self.db.flush()
        for index, question in enumerate(normalized_questions, start=1):
            self.db.add(
                AIGenerationDraftQuestion(
                    draft_id=draft.id,
                    sort_order=index,
                    type=question["type"],
                    stem=question["stem"],
                    explanation=question.get("explanation"),
                    difficulty=question.get("difficulty"),
                    options_json=json_dumps(question["options"]),
                    validation_status="valid",
                )
            )

    def confirm(self, job: ImportJob, draft: AIGenerationDraft) -> QuestionBank:
        workflow = self.db.get(AIGenerationWorkflow, draft.workflow_id)
        bank = self.db.get(QuestionBank, draft.bank_id)
        if not workflow or not bank:
            raise AIGenerationError("草稿关联的 workflow 或题库不存在")
        payload = self.to_payload(draft)
        questions, _ = AIPayloadValidator.validate({"questions": payload["questions"]}, workflow.generation_mode, workflow.requested_count)
        for question in questions:
            create_question_from_payload(self.db, bank.id, question, source="ai_generated", generated_model=job.ai_model_snapshot)
        QuestionBankStatsService.increment_questions(self.db, bank, len(questions))
        if draft.bank_description:
            bank.description = draft.bank_description
        bank.generation_status = "succeeded"
        if workflow.purpose == "create_bank":
            bank.visibility = bank.desired_visibility if bank.question_count > 0 else "private"
        bank.ai_model_name = job.ai_model_snapshot
        workflow.status = "imported"
        workflow.finished_at = now_utc()
        job.status = "imported"
        job.finished_at = now_utc()
        draft.status = "imported"
        WorkflowStateService(self.db).record_step(workflow.id, "confirm_draft", "succeeded", output_data={"question_count": len(questions)})
        return bank

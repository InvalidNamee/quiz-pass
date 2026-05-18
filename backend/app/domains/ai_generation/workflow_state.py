import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.ai_workflow import AIGenerationWorkflow, AIGenerationWorkflowStep
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank


def now_utc() -> datetime:
    return datetime.now(UTC)


class WorkflowStateService:
    def __init__(self, db: Session):
        self.db = db

    def set_status(self, workflow: AIGenerationWorkflow, job: ImportJob, bank: QuestionBank, status: str) -> None:
        workflow.status = status
        job.status = status
        if status in {"pending", "extracting_document", "calling_model", "validating", "repairing", "draft_ready"}:
            bank.generation_status = "processing"
        elif status == "imported":
            bank.generation_status = "succeeded"
        elif status in {"failed", "cancelled"}:
            bank.generation_status = "failed"
        self.db.flush()

    def fail(self, workflow: AIGenerationWorkflow, job: ImportJob, bank: QuestionBank, message: str, repair_attempts: int) -> None:
        workflow.status = "failed"
        workflow.repair_attempts = repair_attempts
        workflow.error_message = message
        workflow.finished_at = now_utc()
        job.status = "failed"
        job.error_message = message
        job.finished_at = now_utc()
        bank.generation_status = "failed"
        if workflow.purpose == "create_bank":
            bank.visibility = "private"
        self.record_step(workflow.id, "fail", "failed", error_message=message)

    def record_step(self, workflow_id: int, step_name: str, status: str, input_data=None, output_data=None, error_message: str | None = None) -> None:
        now = now_utc()
        self.db.add(
            AIGenerationWorkflowStep(
                workflow_id=workflow_id,
                step_name=step_name,
                status=status,
                input_json=json.dumps(input_data, ensure_ascii=False, default=str) if input_data is not None else None,
                output_json=json.dumps(output_data, ensure_ascii=False, default=str) if output_data is not None else None,
                error_message=error_message,
                started_at=now,
                finished_at=now,
            )
        )
        self.db.flush()

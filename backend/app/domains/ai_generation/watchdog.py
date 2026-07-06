from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domains.ai_generation.workflow_state import WorkflowStateService, now_utc
from app.models.ai_workflow import AIGenerationWorkflow
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank

RUNNING_WORKFLOW_STATUSES = {"pending", "extracting_document", "calling_model", "validating", "repairing"}


def stale_workflow_message(timeout_minutes: int) -> str:
    return f"AI workflow 超时未更新，已自动标记失败（超过 {timeout_minutes} 分钟）。请检查模型服务、网络或 RQ worker 日志后重新生成。"


def fail_stale_workflows(db: Session, older_than_minutes: int | None = None) -> int:
    timeout_minutes = older_than_minutes if older_than_minutes is not None else get_settings().ai_workflow_stale_timeout_minutes
    cutoff = now_utc() - timedelta(minutes=timeout_minutes)
    workflows = db.scalars(
        select(AIGenerationWorkflow)
        .where(AIGenerationWorkflow.status.in_(RUNNING_WORKFLOW_STATUSES), AIGenerationWorkflow.updated_at < cutoff)
        .order_by(AIGenerationWorkflow.updated_at.asc(), AIGenerationWorkflow.id.asc())
    ).all()
    state = WorkflowStateService(db)
    message = stale_workflow_message(timeout_minutes)
    failed_count = 0
    for workflow in workflows:
        job = db.scalar(select(ImportJob).where(ImportJob.workflow_id == workflow.id))
        bank = db.get(QuestionBank, workflow.bank_id) if workflow.bank_id else None
        if job and bank:
            state.fail(workflow, job, bank, message, workflow.repair_attempts)
        else:
            workflow.status = "failed"
            workflow.error_message = message
            workflow.finished_at = now_utc()
            if job:
                job.status = "failed"
                job.error_message = message
                job.finished_at = now_utc()
            state.record_step(workflow.id, "fail", "failed", error_message=message)
        failed_count += 1
    db.commit()
    return failed_count

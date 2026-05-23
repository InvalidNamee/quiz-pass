from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domains.ai_generation.services import run_generation_task
from app.domains.ai_generation.workflow_state import now_utc
from app.models.import_job import ImportJob


def execute_workflow_by_id(workflow_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(ImportJob).filter(ImportJob.workflow_id == workflow_id).first()
        if not job:
            return
        run_generation_task(
            workflow_id,
            text="",
            question_count=None,
            generate_description=False,
            generation_mode="knowledge_generate",
            extra_instruction=None,
        )
    finally:
        db.close()


def enqueue_workflow(workflow_id: int, job: ImportJob) -> None:
    settings = get_settings()
    try:
        from redis import Redis
        from rq import Queue
    except ModuleNotFoundError as exc:
        raise RuntimeError("RQ execution mode requires redis and rq packages. Run pip install -r requirements.txt") from exc

    queue = Queue(settings.ai_workflow_queue_name, connection=Redis.from_url(settings.redis_url))
    rq_job = queue.enqueue("app.domains.ai_generation.queue.execute_workflow_by_id", workflow_id)
    job.queue_job_id = rq_job.id
    job.enqueued_at = now_utc()

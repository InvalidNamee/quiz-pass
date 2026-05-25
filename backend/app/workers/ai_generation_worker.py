import multiprocessing
import os
import socket

from app.core.config import get_settings
from app.core.config import Settings


def worker_name(queue_name: str, worker_number: int) -> str:
    return f"{queue_name}-{worker_number}-{socket.gethostname()}-{os.getpid()}"


def run_single_worker(worker_number: int, queue_name: str) -> None:
    settings = get_settings()
    try:
        from redis import Redis
        from rq import Queue, Worker
    except ModuleNotFoundError as exc:
        raise RuntimeError("RQ worker requires redis and rq packages. Run pip install -r requirements.txt") from exc

    connection = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(queue_name, connection=connection)], connection=connection, name=worker_name(queue_name, worker_number))
    worker.work()


def run_configured_workers(settings: Settings) -> None:
    worker_count = max(1, int(settings.ai_workflow_worker_count or 1))
    if worker_count == 1:
        run_single_worker(1, settings.ai_workflow_queue_name)
        return

    processes = [
        multiprocessing.Process(target=run_single_worker, args=(worker_number, settings.ai_workflow_queue_name))
        for worker_number in range(1, worker_count + 1)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()


def main() -> None:
    run_configured_workers(get_settings())


if __name__ == "__main__":
    main()

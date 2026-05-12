from celery import Celery

from .config import get_settings

settings = get_settings()

celery_app = Celery(
    "docscan",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.scan_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=240,
    task_time_limit=300,
)


def scan_document_task(scan_id: str):
    """Прокси для вызова из эндпоинта до импорта задачи."""
    from .tasks.scan_task import process_scan
    return process_scan.delay(scan_id)

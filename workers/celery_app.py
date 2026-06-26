"""Celery application configuration for async task processing."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ecom_ai_studio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker (long-running)
    task_soft_time_limit=600,       # 10 minutes soft limit
    task_time_limit=900,            # 15 minutes hard limit
    result_expires=86400,           # Results expire after 24 hours
)

# Import tasks so they're registered
celery_app.autodiscover_tasks(["workers.tasks"])

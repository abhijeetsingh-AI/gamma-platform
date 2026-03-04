# app/celery_app.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    "gamma",
    broker  = settings.redis_url,
    backend = settings.redis_url,
    include = ["app.tasks.call_tasks"],
)

celery_app.conf.update(
    task_serializer          = "json",
    result_serializer        = "json",
    accept_content           = ["json"],
    timezone                 = "UTC",
    enable_utc               = True,
    task_track_started       = True,
    worker_prefetch_multiplier = 1,
    task_acks_late           = True,
)

# Start worker:
# celery -A app.celery_app worker --loglevel=info --concurrency=4

from celery import Celery

from app.core.config import settings

__all__ = ["celery_app"]

celery_app = Celery(
    "worker",
    broker=settings.rabbitmq.url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

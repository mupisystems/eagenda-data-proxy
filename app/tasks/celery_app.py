"""Celery application factory."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "data_proxy",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.webhook_relay",
        "app.tasks.notifications",
        "app.tasks.audit_cleanup",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "audit-cleanup-daily": {
            "task": "app.tasks.audit_cleanup.cleanup_expired_records",
            "schedule": 86400.0,  # 24 hours
        },
    },
)

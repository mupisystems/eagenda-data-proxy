"""Webhook relay task — forward enriched webhooks to client's internal systems."""
import logging

import requests

from app.config import get_settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def relay_webhook(self, payload: dict, event: str):
    """Relay an enriched webhook payload to the client's target URL."""
    settings = get_settings()
    target_url = settings.webhook_relay_target_url

    if not target_url:
        logger.warning("No webhook relay target configured, skipping relay for event %s", event)
        return

    headers = {"Content-Type": "application/json"}
    if settings.webhook_relay_auth_header:
        headers["Authorization"] = settings.webhook_relay_auth_header

    try:
        response = requests.post(target_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info("Webhook relayed: event=%s status=%s", event, response.status_code)
    except requests.RequestException as exc:
        logger.warning("Webhook relay failed: event=%s error=%s", event, exc)
        raise self.retry(exc=exc, countdown=settings.webhook_relay_retry_delay * (self.request.retries + 1))

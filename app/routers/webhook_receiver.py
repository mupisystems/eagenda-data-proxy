"""Webhook receiver — eagendas cloud sends webhooks here, proxy enriches and relays."""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_enricher
from app.proxy.enricher import PIIEnricher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhook Receiver"])


@router.post("/receive/")
async def receive_webhook(
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """
    Receive webhook from eagendas cloud.
    Enrich payload with local PII and dispatch relay + notification tasks.
    """
    event = body.get("event", "UNKNOWN")
    resource_type = _detect_resource_type(body)

    # Enrich if it's an appointment (contains attendees with PII)
    if resource_type == "appointment":
        enriched = await enricher.enrich_appointment(body, db)
    else:
        enriched = body

    # Dispatch async tasks (imported here to avoid circular imports with celery)
    try:
        from app.tasks.webhook_relay import relay_webhook
        relay_webhook.delay(enriched, event)
    except Exception:
        logger.exception("Failed to dispatch webhook relay task")

    if event in ("CREATED", "UPDATED", "CANCELED", "DELETED") and resource_type == "appointment":
        try:
            from app.tasks.notifications import send_appointment_notification
            send_appointment_notification.delay(enriched)
        except Exception:
            logger.exception("Failed to dispatch notification task")

    return {"status": "accepted", "event": event}


def _detect_resource_type(payload: dict) -> str:
    """Detect the resource type from a webhook payload."""
    if "appointment_key" in payload:
        return "appointment"
    if "calendar_key" in payload and "appointment_key" not in payload:
        return "calendar"
    if "user_profile_key" in payload:
        return "membership"
    return "unknown"

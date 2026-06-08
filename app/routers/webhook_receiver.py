"""Webhook receiver — eagendas cloud sends webhooks here, proxy enriches and relays."""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_booking_limiter, get_db, get_enricher
from app.proxy.enricher import PIIEnricher
from app.services.booking_limiter import BookingLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhook Receiver"])

# Maps eagendas webhook events to local_appointment status values
_STATUS_MAP = {
    "NO_SHOW": "noshow",
    "NOSHOW": "noshow",
    "COMPLETED": "completed",
    "FINISHED": "completed",
    "CANCELED": "canceled",
    "DELETED": "canceled",
}


@router.post("/receive/")
async def receive_webhook(
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    enricher: PIIEnricher = Depends(get_enricher),
    limiter: BookingLimiter = Depends(get_booking_limiter),
):
    """
    Receive webhook from eagendas cloud.
    Enrich payload with local PII, update local appointment status, and dispatch relay + notification tasks.
    """
    event = body.get("event", "UNKNOWN")
    resource_type = _detect_resource_type(body)

    # Enrich if it's an appointment (contains attendees with PII)
    if resource_type == "appointment":
        enriched = await enricher.enrich_appointment(body, db)
    else:
        enriched = body

    # Update local appointment status based on webhook event
    if resource_type == "appointment":
        await _update_appointment_status(limiter, db, body, event)

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


async def _update_appointment_status(
    limiter: BookingLimiter, db: AsyncSession, body: dict, event: str
) -> None:
    """Update local_appointment status from webhook events."""
    appointment_key = body.get("appointment_key")
    if not appointment_key:
        return

    new_status = _STATUS_MAP.get(event.upper())
    if not new_status:
        return

    try:
        appt = await limiter.update_status(db, appointment_key, new_status)
        if appt:
            await db.commit()
            logger.debug("Updated local appointment %s -> %s", appointment_key, new_status)
        else:
            # Appointment not tracked locally — create it from webhook data
            external_id = _extract_first_external_id(body)
            if external_id:
                await limiter.record_appointment(
                    db,
                    appointment_key=appointment_key,
                    external_id=external_id,
                    service_key=body.get("service_key"),
                    scheduled_at=None,
                )
                await limiter.update_status(db, appointment_key, new_status)
                await db.commit()
                logger.debug("Created + updated local appointment %s -> %s", appointment_key, new_status)
    except Exception:
        logger.exception("Failed to update local appointment status for %s", appointment_key)


def _extract_first_external_id(payload: dict) -> str | None:
    """Extract the first external_id from a webhook payload."""
    if payload.get("external_id"):
        return payload["external_id"]
    for attendee in payload.get("attendees", []):
        ext_id = attendee.get("external_id")
        if ext_id:
            return ext_id
    return None


def _detect_resource_type(payload: dict) -> str:
    """Detect the resource type from a webhook payload."""
    if "appointment_key" in payload:
        return "appointment"
    if "calendar_key" in payload and "appointment_key" not in payload:
        return "calendar"
    if "user_profile_key" in payload:
        return "membership"
    return "unknown"

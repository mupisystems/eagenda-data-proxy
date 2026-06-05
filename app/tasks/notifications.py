"""Notification tasks — send emails using enriched PII data."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_appointment_notification(self, enriched_payload: dict):
    """Send email notification for an appointment event using real PII."""
    asyncio.run(_send_notification(enriched_payload))


async def _send_notification(payload: dict):
    from app.services.notification import send_email, render_template

    event = payload.get("event", "CREATED")
    calendar = payload.get("calendar", {})
    calendar_name = calendar.get("calendar_name", "Agendamento")
    start = payload.get("start", {}).get("dateTime", "")

    for attendee in payload.get("attendees", []):
        email = attendee.get("email")
        if not email:
            continue

        name = attendee.get("name", "")

        subject_map = {
            "CREATED": f"Agendamento confirmado - {calendar_name}",
            "UPDATED": f"Agendamento atualizado - {calendar_name}",
            "CANCELED": f"Agendamento cancelado - {calendar_name}",
            "DELETED": f"Agendamento cancelado - {calendar_name}",
        }
        subject = subject_map.get(event, f"Notificacao - {calendar_name}")

        try:
            body_html = render_template(
                "appointment_notification.html",
                name=name,
                calendar_name=calendar_name,
                start=start,
                event=event,
                status=payload.get("status", ""),
            )
        except Exception:
            body_html = (
                f"<p>Ola {name},</p>"
                f"<p>Seu agendamento em <b>{calendar_name}</b> para <b>{start}</b> "
                f"foi <b>{event.lower()}</b>.</p>"
            )

        await send_email(to=email, subject=subject, body_html=body_html)
        logger.info("Notification sent: email=%s event=%s", email, event)

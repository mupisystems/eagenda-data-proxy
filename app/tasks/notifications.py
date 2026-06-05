"""Notification tasks — send emails/SMS/WhatsApp using enriched PII data."""
import asyncio
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_appointment_notification(self, enriched_payload: dict):
    """Send notifications for an appointment event using real PII."""
    asyncio.run(_send_notification(enriched_payload))


async def _send_notification(payload: dict):
    from app.db.engine import create_engine, create_session_factory
    from app.config import get_settings
    from app.models.notification_log import NotificationLog
    from app.services.notification import send_email, render_template

    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    event = payload.get("event", "CREATED")
    calendar = payload.get("calendar", {})
    calendar_name = calendar.get("calendar_name", "Appointment")
    start = payload.get("start", {}).get("dateTime", "")
    appointment_key = payload.get("appointment_key", "")

    for attendee in payload.get("attendees", []):
        external_id = attendee.get("external_id", "")
        name = attendee.get("name", "")
        email = attendee.get("email")
        phone = attendee.get("phone")

        subject_map = {
            "CREATED": f"Appointment confirmed - {calendar_name}",
            "UPDATED": f"Appointment updated - {calendar_name}",
            "CANCELED": f"Appointment canceled - {calendar_name}",
            "DELETED": f"Appointment canceled - {calendar_name}",
        }
        subject = subject_map.get(event, f"Notification - {calendar_name}")

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
                f"<p>Hello {name},</p>"
                f"<p>Your appointment at <b>{calendar_name}</b> for <b>{start}</b> "
                f"has been <b>{event.lower()}</b>.</p>"
            )

        # Email
        if email and settings.email_enabled:
            success = await send_email(to=email, subject=subject, body_html=body_html)
            async with session_factory() as db:
                db.add(NotificationLog(
                    external_id=external_id,
                    appointment_key=appointment_key,
                    channel="email",
                    recipient=email,
                    subject=subject,
                    status="sent" if success else "failed",
                    sent_at=datetime.now(timezone.utc) if success else None,
                ))
                await db.commit()
            logger.info("Email %s: to=%s event=%s", "sent" if success else "failed", email, event)

        # SMS (provider must be configured)
        if phone and settings.sms_enabled:
            from app.services.sms import send_sms
            sms_text = f"Your appointment at {calendar_name} for {start} has been {event.lower()}."
            success = await send_sms(to=phone, body=sms_text)
            async with session_factory() as db:
                db.add(NotificationLog(
                    external_id=external_id,
                    appointment_key=appointment_key,
                    channel="sms",
                    recipient=phone,
                    subject=None,
                    status="sent" if success else "failed",
                    sent_at=datetime.now(timezone.utc) if success else None,
                ))
                await db.commit()
            logger.info("SMS %s: to=%s event=%s", "sent" if success else "failed", phone, event)

        # WhatsApp (provider must be configured)
        if phone and settings.whatsapp_enabled:
            from app.services.whatsapp import send_whatsapp
            wa_text = f"Your appointment at {calendar_name} for {start} has been {event.lower()}."
            success = await send_whatsapp(to=phone, body=wa_text)
            async with session_factory() as db:
                db.add(NotificationLog(
                    external_id=external_id,
                    appointment_key=appointment_key,
                    channel="whatsapp",
                    recipient=phone,
                    subject=None,
                    status="sent" if success else "failed",
                    sent_at=datetime.now(timezone.utc) if success else None,
                ))
                await db.commit()
            logger.info("WhatsApp %s: to=%s event=%s", "sent" if success else "failed", phone, event)

    await engine.dispose()

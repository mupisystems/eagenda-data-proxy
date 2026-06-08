"""SMS notification provider.

Configure in .env:
    SMS_ENABLED=true
    SMS_PROVIDER=twilio       # supported: twilio, vonage
    SMS_API_KEY=...
    SMS_API_SECRET=...
    SMS_FROM_NUMBER=+1234567890
"""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_sms(to: str, body: str) -> bool:
    """Send an SMS message. Returns True on success."""
    settings = get_settings()
    if not settings.sms_enabled:
        logger.warning("SMS not enabled, skipping send to %s", to)
        return False

    provider = settings.sms_provider.lower()

    if provider == "twilio":
        return await _send_twilio(to, body, settings)
    elif provider == "vonage":
        return await _send_vonage(to, body, settings)
    else:
        logger.error("Unknown SMS provider: %s", provider)
        return False


async def _send_twilio(to: str, body: str, settings) -> bool:
    """Send SMS via Twilio REST API."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.sms_api_key}/Messages.json",
                auth=(settings.sms_api_key, settings.sms_api_secret),
                data={"From": settings.sms_from_number, "To": to, "Body": body},
            )
            if response.status_code == 201:
                logger.info("Twilio SMS sent to %s", to)
                return True
            logger.error("Twilio SMS failed: %s %s", response.status_code, response.text)
            return False
    except Exception:
        logger.exception("Twilio SMS error sending to %s", to)
        return False


async def _send_vonage(to: str, body: str, settings) -> bool:
    """Send SMS via Vonage (Nexmo) REST API."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://rest.nexmo.com/sms/json",
                json={
                    "api_key": settings.sms_api_key,
                    "api_secret": settings.sms_api_secret,
                    "from": settings.sms_from_number,
                    "to": to,
                    "text": body,
                },
            )
            data = response.json()
            if data.get("messages", [{}])[0].get("status") == "0":
                logger.info("Vonage SMS sent to %s", to)
                return True
            logger.error("Vonage SMS failed: %s", data)
            return False
    except Exception:
        logger.exception("Vonage SMS error sending to %s", to)
        return False

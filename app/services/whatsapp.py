"""WhatsApp notification provider.

Configure in .env:
    WHATSAPP_ENABLED=true
    WHATSAPP_PROVIDER=evolution    # supported: evolution, meta
    WHATSAPP_API_URL=https://your-evolution-api.com
    WHATSAPP_API_KEY=...
    WHATSAPP_FROM_NUMBER=+5511999999999
"""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_whatsapp(to: str, body: str) -> bool:
    """Send a WhatsApp message. Returns True on success."""
    settings = get_settings()
    if not settings.whatsapp_enabled:
        logger.warning("WhatsApp not enabled, skipping send to %s", to)
        return False

    provider = settings.whatsapp_provider.lower()

    if provider == "evolution":
        return await _send_evolution(to, body, settings)
    elif provider == "meta":
        return await _send_meta(to, body, settings)
    else:
        logger.error("Unknown WhatsApp provider: %s", provider)
        return False


async def _send_evolution(to: str, body: str, settings) -> bool:
    """Send WhatsApp via Evolution API."""
    try:
        import httpx

        base_url = settings.whatsapp_api_url.rstrip("/")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/message/sendText/{settings.whatsapp_from_number}",
                headers={"apikey": settings.whatsapp_api_key},
                json={"number": to, "text": body},
            )
            if response.status_code in (200, 201):
                logger.info("Evolution WhatsApp sent to %s", to)
                return True
            logger.error("Evolution WhatsApp failed: %s %s", response.status_code, response.text)
            return False
    except Exception:
        logger.exception("Evolution WhatsApp error sending to %s", to)
        return False


async def _send_meta(to: str, body: str, settings) -> bool:
    """Send WhatsApp via Meta Cloud API."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v21.0/{settings.whatsapp_from_number}/messages",
                headers={"Authorization": f"Bearer {settings.whatsapp_api_key}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": body},
                },
            )
            if response.status_code in (200, 201):
                logger.info("Meta WhatsApp sent to %s", to)
                return True
            logger.error("Meta WhatsApp failed: %s %s", response.status_code, response.text)
            return False
    except Exception:
        logger.exception("Meta WhatsApp error sending to %s", to)
        return False

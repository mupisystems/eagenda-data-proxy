"""Email notification service."""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
from jinja2 import Environment, PackageLoader, select_autoescape

from app.config import get_settings

logger = logging.getLogger(__name__)

# Jinja2 template environment — templates in app/templates/
try:
    _jinja_env = Environment(
        loader=PackageLoader("app", "templates"),
        autoescape=select_autoescape(["html"]),
    )
except Exception:
    _jinja_env = None


async def send_email(
    to: str,
    subject: str,
    body_html: str,
) -> bool:
    """Send an email via SMTP. Returns True on success."""
    settings = get_settings()
    if not settings.email_enabled or not settings.smtp_host:
        logger.warning("Email not configured, skipping send to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def render_template(template_name: str, **context) -> str:
    """Render a Jinja2 email template."""
    if _jinja_env is None:
        return f"<p>{context}</p>"
    template = _jinja_env.get_template(template_name)
    return template.render(**context)

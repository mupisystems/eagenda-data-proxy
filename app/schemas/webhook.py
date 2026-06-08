from pydantic import BaseModel


class WebhookPayload(BaseModel):
    """Incoming webhook payload from eagendas cloud."""

    event: str | None = None
    appointment_key: str | None = None
    # Other fields are dynamic — handled as raw dicts

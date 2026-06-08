"""PII interception — strips PII from outbound payloads, stores locally."""

import logging
from copy import deepcopy

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.pii_person import PIIPerson
from app.proxy.pii_fields import PERSON_PII_FIELDS
from app.services.pii_store import PIIStore

logger = logging.getLogger(__name__)


class PIIInterceptor:
    """Strips PII from client payloads before forwarding to eagendas cloud."""

    def __init__(self, settings: Settings, pii_store: PIIStore):
        self.prefix = settings.pii_pseudonym_prefix
        self.pii_store = pii_store

    def _pseudonymize_name(self, external_id: str) -> str:
        return f"{self.prefix}-{external_id}"

    def _extract_pii(self, body: dict) -> dict:
        """Extract PII fields from a person-like dict."""
        pii = {}
        for field in PERSON_PII_FIELDS:
            if field in body:
                pii[field] = body[field]
        return pii

    def _strip_pii(self, body: dict, external_id: str) -> dict:
        """Return a copy of body with PII removed/pseudonymized."""
        cleaned = {}
        for key, value in body.items():
            if key in PERSON_PII_FIELDS:
                action = PERSON_PII_FIELDS[key]["action"]
                if action == "pseudonymize":
                    cleaned[key] = self._pseudonymize_name(external_id)
                # "strip" fields are omitted entirely
            else:
                cleaned[key] = value
        return cleaned

    async def intercept_person(self, body: dict, db: AsyncSession) -> tuple[dict, PIIPerson]:
        """
        Intercept a person creation/update payload.
        Returns (cleaned_body_for_cloud, pii_person_record).
        """
        external_id = body.get("external_id")
        if not external_id:
            import uuid

            external_id = str(uuid.uuid4())
            body["external_id"] = external_id

        # Extract and store PII locally
        pii_data = self._extract_pii(body)
        pii_record = await self.pii_store.upsert_person(db, external_id=external_id, **pii_data)

        # Build cleaned payload for cloud
        cleaned = self._strip_pii(body, external_id)
        return cleaned, pii_record

    async def intercept_appointment(self, body: dict, db: AsyncSession) -> dict:
        """
        Intercept an appointment creation payload — strips/pseudonymizes each
        attendee's PII and stores it locally. Person data lives inside
        ``attendees``, matching the eagendas API shape. Questionnaire answers are
        handled separately by ``QuestionnaireProcessor`` at the router level,
        where the calendar's form (and thus question types) is available.
        """
        cleaned = deepcopy(body)

        # Intercept each attendee's PII (eagendas nests person data in attendees)
        attendees = cleaned.get("attendees")
        if attendees:
            cleaned_attendees = []
            for attendee in attendees:
                stripped, _ = await self.intercept_person(attendee, db)
                cleaned_attendees.append(stripped)
            cleaned["attendees"] = cleaned_attendees

        return cleaned

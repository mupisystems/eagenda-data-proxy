"""Response enrichment — merges local PII into cloud responses."""
import logging
from copy import deepcopy

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.custom_data_store import CustomDataStore
from app.services.pii_store import PIIStore

logger = logging.getLogger(__name__)


class PIIEnricher:
    """Enriches eagendas cloud responses with local PII and custom data."""

    def __init__(self, pii_store: PIIStore, custom_data_store: CustomDataStore | None = None):
        self.pii_store = pii_store
        self.custom_data_store = custom_data_store or CustomDataStore()

    async def enrich_person(self, data: dict, db: AsyncSession) -> dict:
        """Enrich a single person response with local PII."""
        external_id = data.get("external_id")
        if not external_id:
            return data

        pii = await self.pii_store.get_person(db, external_id)
        if not pii:
            return data

        enriched = dict(data)
        if pii.name:
            enriched["name"] = pii.name
        if pii.email:
            enriched["email"] = pii.email
        if pii.phone:
            enriched["phone"] = pii.phone
        if pii.identification_code:
            enriched["identification_code"] = pii.identification_code
        if pii.identification_type:
            enriched["identification_type"] = pii.identification_type
        return enriched

    async def enrich_appointment(self, data: dict, db: AsyncSession) -> dict:
        """Enrich an appointment response — attendees and questionnaire answers."""
        enriched = deepcopy(data)

        # Enrich attendees
        attendees = enriched.get("attendees", [])
        if attendees:
            external_ids = [a.get("external_id") for a in attendees if a.get("external_id")]
            pii_map = await self.pii_store.get_persons_batch(db, external_ids)
            for attendee in attendees:
                ext_id = attendee.get("external_id")
                if ext_id and ext_id in pii_map:
                    pii = pii_map[ext_id]
                    if pii.name:
                        attendee["name"] = pii.name
                    if pii.email:
                        attendee["email"] = pii.email
                    if pii.phone:
                        attendee["phone"] = pii.phone
                    if pii.identification_code:
                        attendee["identification_code"] = pii.identification_code
                    if pii.identification_type:
                        attendee["identification_type"] = pii.identification_type

        # Enrich questionnaire answers
        appointment_key = enriched.get("appointment_key")
        questionnaires = enriched.get("questionnaires", [])
        if appointment_key and questionnaires:
            answers_map = await self.pii_store.get_questionnaire_answers(db, appointment_key)
            for questionnaire in questionnaires:
                for answer in questionnaire.get("answers", []):
                    q_key = answer.get("question_key")
                    if q_key and q_key in answers_map:
                        answer["body"] = answers_map[q_key]

        # Enrich with local custom data
        if appointment_key:
            custom = await self.custom_data_store.get(db, "appointment", appointment_key)
            if custom:
                enriched["custom_data"] = custom

        return enriched

    async def enrich_paginated(
        self, data: dict, resource_type: str, db: AsyncSession
    ) -> dict:
        """Enrich all items in a paginated response."""
        enriched = dict(data)
        results = enriched.get("results", [])

        if resource_type == "person":
            external_ids = [r.get("external_id") for r in results if r.get("external_id")]
            pii_map = await self.pii_store.get_persons_batch(db, external_ids)
            enriched["results"] = [
                self._merge_person_pii(r, pii_map) for r in results
            ]
        elif resource_type == "appointment":
            enriched["results"] = [
                await self.enrich_appointment(r, db) for r in results
            ]

        return enriched

    def _merge_person_pii(self, person_data: dict, pii_map: dict) -> dict:
        """Merge PII into a person dict using pre-fetched map."""
        ext_id = person_data.get("external_id")
        if not ext_id or ext_id not in pii_map:
            return person_data

        pii = pii_map[ext_id]
        merged = dict(person_data)
        if pii.name:
            merged["name"] = pii.name
        if pii.email:
            merged["email"] = pii.email
        if pii.phone:
            merged["phone"] = pii.phone
        if pii.identification_code:
            merged["identification_code"] = pii.identification_code
        if pii.identification_type:
            merged["identification_type"] = pii.identification_type
        return merged

"""Tests for PII enricher."""

import pytest
from app.proxy.enricher import PIIEnricher
from app.services.pii_store import PIIStore


@pytest.fixture
def enricher():
    return PIIEnricher(pii_store=PIIStore())


@pytest.fixture
async def seed_pii(db_session):
    """Seed a PII person for enrichment tests."""
    store = PIIStore()
    await store.upsert_person(
        db_session,
        external_id="EXT-100",
        name="Maria Santos",
        email="maria@example.com",
        phone="+5511999990000",
        identification_code="12345678900",
    )


class TestEnrichPerson:
    async def test_enriches_with_real_name(self, enricher, db_session, seed_pii):
        cloud_data = {"person_key": "uuid-1", "name": "Citizen-EXT-100", "external_id": "EXT-100"}
        enriched = await enricher.enrich_person(cloud_data, db_session)

        assert enriched["name"] == "Maria Santos"
        assert enriched["email"] == "maria@example.com"
        assert enriched["phone"] == "+5511999990000"

    async def test_returns_unchanged_if_no_pii(self, enricher, db_session):
        cloud_data = {"person_key": "uuid-1", "name": "Citizen-UNKNOWN", "external_id": "UNKNOWN"}
        enriched = await enricher.enrich_person(cloud_data, db_session)

        assert enriched["name"] == "Citizen-UNKNOWN"
        assert "email" not in enriched

    async def test_returns_unchanged_if_no_external_id(self, enricher, db_session):
        cloud_data = {"person_key": "uuid-1", "name": "Someone"}
        enriched = await enricher.enrich_person(cloud_data, db_session)

        assert enriched["name"] == "Someone"


class TestEnrichAppointment:
    async def test_enriches_attendees(self, enricher, db_session, seed_pii):
        cloud_data = {
            "appointment_key": "appt-1",
            "attendees": [
                {"person_key": "uuid-1", "name": "Citizen-EXT-100", "external_id": "EXT-100"},
            ],
        }
        enriched = await enricher.enrich_appointment(cloud_data, db_session)

        assert enriched["attendees"][0]["name"] == "Maria Santos"
        assert enriched["attendees"][0]["email"] == "maria@example.com"

    async def test_handles_empty_attendees(self, enricher, db_session):
        cloud_data = {"appointment_key": "appt-2", "attendees": []}
        enriched = await enricher.enrich_appointment(cloud_data, db_session)
        assert enriched["attendees"] == []

    async def test_restores_redacted_questionnaire_answer(self, enricher, db_session):
        await PIIStore().store_questionnaire_answer(
            db_session,
            appointment_key="appt-q",
            question_key="q1",
            question_text="Observações",
            answer_body="Tenho alergia a penicilina",
            pseudonymized_body="[REDACTED]:q1",
        )
        cloud_data = {
            "appointment_key": "appt-q",
            "questionnaires": [
                {
                    "type": "appointment_form",
                    "answers": [
                        {"order": 1, "question": "Observações", "answer_data_type": "text", "answer": "[REDACTED]:q1"},
                    ],
                }
            ],
        }
        enriched = await enricher.enrich_appointment(cloud_data, db_session)

        assert enriched["questionnaires"][0]["answers"][0]["answer"] == "Tenho alergia a penicilina"


class TestEnrichPaginated:
    async def test_enriches_person_results(self, enricher, db_session, seed_pii):
        cloud_data = {
            "count": 1,
            "results": [
                {"person_key": "uuid-1", "name": "Citizen-EXT-100", "external_id": "EXT-100"},
            ],
        }
        enriched = await enricher.enrich_paginated(cloud_data, "person", db_session)

        assert enriched["results"][0]["name"] == "Maria Santos"

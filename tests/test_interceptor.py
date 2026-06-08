"""Tests for PII interceptor."""

import pytest
from app.proxy.interceptor import PIIInterceptor
from app.services.pii_store import PIIStore
from app.config import Settings


@pytest.fixture
def interceptor():
    settings = Settings(pii_pseudonym_prefix="Citizen", pii_redacted_placeholder="[REDACTED]")
    return PIIInterceptor(settings=settings, pii_store=PIIStore())


class TestInterceptPerson:
    async def test_strips_email_and_phone(self, interceptor, db_session):
        body = {
            "name": "Maria Santos",
            "email": "maria@example.com",
            "phone": "+5511999997777",
            "external_id": "EXT-001",
        }
        cleaned, pii = await interceptor.intercept_person(body, db_session)

        assert "email" not in cleaned
        assert "phone" not in cleaned
        assert cleaned["external_id"] == "EXT-001"

    async def test_pseudonymizes_name(self, interceptor, db_session):
        body = {"name": "Maria Santos", "external_id": "EXT-001"}
        cleaned, _ = await interceptor.intercept_person(body, db_session)

        assert cleaned["name"] == "Citizen-EXT-001"

    async def test_stores_pii_locally(self, interceptor, db_session):
        body = {
            "name": "Maria Santos",
            "email": "maria@example.com",
            "phone": "+5511999997777",
            "external_id": "EXT-002",
        }
        _, pii = await interceptor.intercept_person(body, db_session)

        assert pii.name == "Maria Santos"
        assert pii.email == "maria@example.com"
        assert pii.phone == "+5511999997777"
        assert pii.external_id == "EXT-002"

    async def test_generates_external_id_if_missing(self, interceptor, db_session):
        body = {"name": "John Smith"}
        cleaned, pii = await interceptor.intercept_person(body, db_session)

        assert cleaned["external_id"] is not None
        assert pii.external_id is not None

    async def test_strips_identification_code(self, interceptor, db_session):
        body = {
            "name": "Maria",
            "identification_code": "12345678900",
            "identification_type": "CPF",
            "external_id": "EXT-003",
        }
        cleaned, pii = await interceptor.intercept_person(body, db_session)

        assert "identification_code" not in cleaned
        assert "identification_type" not in cleaned
        assert pii.identification_code == "12345678900"
        assert pii.identification_type == "CPF"


class TestInterceptAppointment:
    async def test_strips_attendee_pii(self, interceptor, db_session):
        body = {
            "service_key": "srv-vistoria",
            "attendees": [
                {
                    "name": "Maria Santos",
                    "email": "maria@example.com",
                    "phone": "+5511999997777",
                    "external_id": "EXT-010",
                }
            ],
        }
        cleaned = await interceptor.intercept_appointment(body, db_session)

        attendee = cleaned["attendees"][0]
        assert attendee["name"] == "Citizen-EXT-010"
        assert "email" not in attendee
        assert "phone" not in attendee
        assert attendee["external_id"] == "EXT-010"
        assert cleaned["service_key"] == "srv-vistoria"

    async def test_stores_each_attendee_locally(self, interceptor, db_session):
        body = {
            "attendees": [
                {"name": "Maria Santos", "email": "maria@example.com", "external_id": "EXT-011"},
                {"name": "João Silva", "email": "joao@example.com", "external_id": "EXT-012"},
            ],
        }
        await interceptor.intercept_appointment(body, db_session)

        maria = await interceptor.pii_store.get_person(db_session, "EXT-011")
        joao = await interceptor.pii_store.get_person(db_session, "EXT-012")
        assert maria.email == "maria@example.com"
        assert joao.email == "joao@example.com"

    async def test_generates_external_id_for_attendee_without_one(self, interceptor, db_session):
        body = {"attendees": [{"name": "Anon"}]}
        cleaned = await interceptor.intercept_appointment(body, db_session)

        assert cleaned["attendees"][0]["external_id"] is not None

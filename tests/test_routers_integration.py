"""HTTP integration tests for the PII write paths, with the eagendas cloud
emulated via respx. Asserts the proxy strips PII outbound, forwards unmodeled
fields untouched, re-enriches responses, and passes cloud errors through.
"""

import json

import respx
from httpx import Response

from app.services import questionnaire as questionnaire_module

BASE = "https://eagendas.com/api/v3"


def _capture(store: dict, response: Response):
    """respx side-effect that records the forwarded body and returns a response."""

    def handler(request):
        store["body"] = json.loads(request.content)
        return response

    return handler


class TestCreatePerson:
    async def test_strips_pii_forwards_extras_and_enriches(self, client):
        sent = {}
        with respx.mock(assert_all_called=False) as router:
            router.post(f"{BASE}/people/").mock(
                side_effect=_capture(
                    sent,
                    Response(201, json={"person_key": "pk-1", "name": "Citizen-EXT-9", "external_id": "EXT-9"}),
                )
            )
            resp = await client.post(
                "/api/v3/people/",
                json={
                    "name": "Maria Santos",
                    "email": "maria@example.com",
                    "phone": "+5511999997777",
                    "external_id": "EXT-9",
                    "owner_user": {"email": "agent@example.com"},  # unmodeled → must pass through
                },
            )

        assert resp.status_code == 201
        # Outbound: name pseudonymized, contact PII stripped, extras preserved
        assert sent["body"]["name"] == "Citizen-EXT-9"
        assert "email" not in sent["body"]
        assert "phone" not in sent["body"]
        assert sent["body"]["external_id"] == "EXT-9"
        assert sent["body"]["owner_user"] == {"email": "agent@example.com"}
        # Response re-enriched with real PII from the local store
        data = resp.json()
        assert data["name"] == "Maria Santos"
        assert data["email"] == "maria@example.com"

    async def test_passes_cloud_error_through(self, client):
        with respx.mock(assert_all_called=False) as router:
            router.post(f"{BASE}/people/").mock(
                return_value=Response(400, json={"detail": "invalid identification_code"})
            )
            resp = await client.post("/api/v3/people/", json={"name": "X", "external_id": "EXT-err"})

        assert resp.status_code == 400
        assert resp.json() == {"detail": "invalid identification_code"}


class TestCreateAppointment:
    async def test_strips_attendee_pii_keeps_custom_data_and_enriches(self, client):
        sent = {}
        with respx.mock(assert_all_called=False) as router:
            router.post(f"{BASE}/appointments/").mock(
                side_effect=_capture(
                    sent,
                    Response(
                        201,
                        json={
                            "appointment_key": "appt-1",
                            "attendees": [{"person_key": "pk-9", "name": "Citizen-EXT-9", "external_id": "EXT-9"}],
                        },
                    ),
                )
            )
            resp = await client.post(
                "/api/v3/appointments/",
                json={
                    "calendar_key": "cal-1",
                    "start": {"dateTime": "2026-06-15T10:00:00-03:00"},
                    "attendees": [{"name": "Maria Santos", "email": "maria@example.com", "external_id": "EXT-9"}],
                    "service_list": [{"service_key": "srv-1"}],
                    "custom_data": {"plate": "ABC-1234"},
                    "description": "keep me",  # unmodeled-ish passthrough
                },
            )

        assert resp.status_code == 201
        # Outbound: attendee PII stripped, custom_data removed, other fields forwarded
        attendee = sent["body"]["attendees"][0]
        assert attendee["name"] == "Citizen-EXT-9"
        assert "email" not in attendee
        assert "custom_data" not in sent["body"]
        assert sent["body"]["service_list"] == [{"service_key": "srv-1"}]
        assert sent["body"]["description"] == "keep me"
        # Response: PII + custom data merged back
        data = resp.json()
        assert data["attendees"][0]["email"] == "maria@example.com"
        assert data["custom_data"] == {"plate": "ABC-1234"}

    async def test_redacts_pii_questionnaire_answer_and_restores(self, client):
        questionnaire_module._form_cache.clear()
        sent = {}

        def appointment_handler(request):
            sent["body"] = json.loads(request.content)
            token = sent["body"]["questionnaire_answers"][0]["body"]  # cloud echoes our token
            return Response(
                201,
                json={
                    "appointment_key": "appt-q",
                    "attendees": [{"external_id": "EXT-9", "name": "Citizen-EXT-9"}],
                    "questionnaires": [
                        {
                            "type": "appointment_form",
                            "answers": [
                                {"order": 1, "question": "Obs", "answer_data_type": "text", "answer": token},
                            ],
                        }
                    ],
                },
            )

        with respx.mock(assert_all_called=False) as router:
            router.get(f"{BASE}/calendars/cal-q/forms/").mock(
                return_value=Response(
                    200,
                    json={"results": [{"questions": [{"question_key": "q1", "type": "text", "text": "Obs"}]}]},
                )
            )
            router.post(f"{BASE}/appointments/").mock(side_effect=appointment_handler)
            resp = await client.post(
                "/api/v3/appointments/",
                json={
                    "calendar_key": "cal-q",
                    "start": {"dateTime": "2026-06-15T10:00:00-03:00"},
                    "attendees": [{"name": "Maria", "external_id": "EXT-9"}],
                    "questionnaire_answers": [{"question_key": "q1", "body": "Tenho alergia a penicilina"}],
                },
            )

        assert resp.status_code == 201
        # Outbound answer redacted to a token (real value never reaches the cloud)
        assert sent["body"]["questionnaire_answers"][0]["body"] == "[REDACTED]:q1"
        # Response restored to the real answer
        data = resp.json()
        assert data["questionnaires"][0]["answers"][0]["answer"] == "Tenho alergia a penicilina"

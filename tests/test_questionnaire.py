"""Tests for the questionnaire PII processor."""

import pytest

from app.config import Settings
from app.services import questionnaire as q
from app.services.pii_store import PIIStore
from app.services.questionnaire import QuestionnaireProcessor


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class FakeForwarder:
    """Stand-in for CloudForwarder that returns a canned form response."""

    def __init__(self, response=None, raises=False):
        self._response = response
        self._raises = raises
        self.calls = []

    async def forward(self, method, path, **kwargs):
        self.calls.append((method, path))
        if self._raises:
            raise RuntimeError("cloud unavailable")
        return self._response


@pytest.fixture(autouse=True)
def clear_form_cache():
    q._form_cache.clear()
    yield
    q._form_cache.clear()


def _settings():
    return Settings(pii_redacted_placeholder="[REDACTED]", pii_questionnaire_pii_types=["text", "short-text"])


def _form(questions):
    return FakeResponse(200, {"results": [{"questions": questions}]})


def _processor(forwarder):
    return QuestionnaireProcessor(forwarder=forwarder, pii_store=PIIStore(), settings=_settings())


class TestRedactOutbound:
    async def test_redacts_pii_type_with_token(self):
        forwarder = FakeForwarder(_form([{"question_key": "q-text", "type": "text", "text": "Obs"}]))
        proc = _processor(forwarder)

        outgoing, pending = await proc.redact_outbound("cal-1", [{"question_key": "q-text", "body": "segredo"}])

        assert outgoing[0]["body"] == "[REDACTED]:q-text"
        assert len(pending) == 1
        assert pending[0]["answer_body"] == "segredo"
        assert pending[0]["token"] == "[REDACTED]:q-text"
        assert pending[0]["question_text"] == "Obs"

    async def test_passes_through_non_pii_type(self):
        forwarder = FakeForwarder(_form([{"question_key": "q-date", "type": "date", "text": "Quando"}]))
        proc = _processor(forwarder)

        outgoing, pending = await proc.redact_outbound("cal-2", [{"question_key": "q-date", "body": "2026-06-10"}])

        assert outgoing[0]["body"] == "2026-06-10"
        assert pending == []

    async def test_fail_safe_redacts_when_form_unavailable(self):
        forwarder = FakeForwarder(raises=True)
        proc = _processor(forwarder)

        outgoing, pending = await proc.redact_outbound("cal-3", [{"question_key": "q-x", "body": "valor"}])

        assert outgoing[0]["body"] == "[REDACTED]:q-x"
        assert len(pending) == 1

    async def test_fail_safe_redacts_unknown_question(self):
        forwarder = FakeForwarder(_form([{"question_key": "q-known", "type": "date", "text": "Quando"}]))
        proc = _processor(forwarder)

        outgoing, pending = await proc.redact_outbound("cal-4", [{"question_key": "q-unlisted", "body": "valor"}])

        assert outgoing[0]["body"] == "[REDACTED]:q-unlisted"
        assert len(pending) == 1

    async def test_caches_form_lookup(self):
        forwarder = FakeForwarder(_form([{"question_key": "q-text", "type": "text", "text": "Obs"}]))
        proc = _processor(forwarder)

        await proc.redact_outbound("cal-5", [{"question_key": "q-text", "body": "a"}])
        await proc.redact_outbound("cal-5", [{"question_key": "q-text", "body": "b"}])

        assert len(forwarder.calls) == 1  # second call served from cache

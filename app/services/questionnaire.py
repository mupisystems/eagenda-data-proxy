"""Questionnaire answer interception.

Free-text questionnaire answers can carry PII, so they must not reach the
eagendas cloud in clear text. On appointment creation the proxy classifies each
answer by its question *type* (fetched from the calendar's form), replaces the
body of PII answers with a unique redaction token before forwarding, and stores
the real answer locally. The enricher restores the real value on read by
matching that token in the cloud response.

Classification is fail-safe: if the form can't be fetched or a question type is
unknown, the answer is treated as PII and redacted.
"""

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.proxy.forwarder import CloudForwarder
from app.services.pii_store import PIIStore

logger = logging.getLogger(__name__)

# Process-wide cache of {calendar_key: (expires_at, {question_key: {type, text}})}
_form_cache: dict[str, tuple[float, dict]] = {}
_FORM_TTL_SECONDS = 300


class QuestionnaireProcessor:
    """Redacts PII questionnaire answers outbound and persists them locally."""

    def __init__(self, forwarder: CloudForwarder, pii_store: PIIStore, settings: Settings):
        self.forwarder = forwarder
        self.pii_store = pii_store
        self.placeholder = settings.pii_redacted_placeholder
        self.pii_types = set(settings.pii_questionnaire_pii_types)

    def _token(self, question_key: str) -> str:
        """Unique, deterministic redaction token that round-trips via the cloud."""
        return f"{self.placeholder}:{question_key}"

    async def _resolve_types(self, calendar_key: str) -> dict:
        """Return {question_key: {"type", "text"}} for a calendar's form (cached)."""
        cached = _form_cache.get(calendar_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        types: dict[str, dict] = {}
        try:
            resp = await self.forwarder.forward("GET", f"/calendars/{calendar_key}/forms/")
            if resp.status_code == 200:
                for form in resp.json().get("results", []):
                    for question in form.get("questions", []):
                        qkey = question.get("question_key")
                        if qkey:
                            types[qkey] = {"type": question.get("type"), "text": question.get("text")}
        except Exception:
            logger.exception("Failed to fetch form for calendar %s; redacting all answers", calendar_key)
            return {}  # fail-safe: caller treats unknown questions as PII

        _form_cache[calendar_key] = (time.monotonic() + _FORM_TTL_SECONDS, types)
        return types

    async def redact_outbound(self, calendar_key: str, answers: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Split answers into the redacted list to forward and the PII answers to
        store locally. Returns (outgoing_answers, pending_pii_answers).
        """
        types = await self._resolve_types(calendar_key) if calendar_key else {}

        outgoing: list[dict] = []
        pending: list[dict] = []
        for answer in answers:
            question_key = answer.get("question_key")
            body = answer.get("body")
            info = types.get(question_key)
            # Fail-safe: unknown question (no form / not found) is treated as PII.
            is_pii = info is None or info.get("type") in self.pii_types

            if question_key and body and is_pii:
                token = self._token(question_key)
                pending.append(
                    {
                        "question_key": question_key,
                        "question_text": (info or {}).get("text"),
                        "answer_body": body,
                        "token": token,
                    }
                )
                outgoing.append({**answer, "body": token})
            else:
                outgoing.append(answer)

        return outgoing, pending

    async def store(self, db: AsyncSession, appointment_key: str, pending: list[dict]) -> None:
        """Persist redacted PII answers locally, keyed by the new appointment_key."""
        for answer in pending:
            await self.pii_store.store_questionnaire_answer(
                db,
                appointment_key=appointment_key,
                question_key=answer["question_key"],
                question_text=answer["question_text"],
                answer_body=answer["answer_body"],
                pseudonymized_body=answer["token"],
            )

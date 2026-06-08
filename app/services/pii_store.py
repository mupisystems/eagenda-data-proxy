"""CRUD operations on PII tables."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.pii_person import PIIPerson
from app.models.pii_questionnaire import PIIQuestionnaireAnswer

logger = logging.getLogger(__name__)


class PIIStore:
    """Service for managing PII data in the local store."""

    async def upsert_person(
        self,
        db: AsyncSession,
        external_id: str,
        **pii_fields,
    ) -> PIIPerson:
        """Insert or update a person by external_id (ON CONFLICT)."""
        # Build values dict with only non-None fields
        values = {"external_id": external_id}
        for field in ("name", "email", "phone", "identification_code", "identification_type", "date_of_birth"):
            if field in pii_fields and pii_fields[field] is not None:
                values[field] = pii_fields[field]

        stmt = pg_insert(PIIPerson).values(**values)
        update_fields = {k: v for k, v in values.items() if k != "external_id"}
        if update_fields:
            stmt = stmt.on_conflict_do_update(
                index_elements=["external_id"],
                set_=update_fields,
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=["external_id"])

        await db.execute(stmt)
        await db.commit()

        # Fetch the record
        result = await db.execute(select(PIIPerson).where(PIIPerson.external_id == external_id))
        return result.scalar_one()

    async def get_person(self, db: AsyncSession, external_id: str) -> Optional[PIIPerson]:
        """Get a person by external_id."""
        result = await db.execute(
            select(PIIPerson).where(
                PIIPerson.external_id == external_id,
                PIIPerson.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_person_key(self, db: AsyncSession, person_key: str) -> Optional[PIIPerson]:
        """Get a person by person_key (eagendas UUID)."""
        result = await db.execute(
            select(PIIPerson).where(
                PIIPerson.person_key == person_key,
                PIIPerson.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_persons_batch(self, db: AsyncSession, external_ids: list[str]) -> dict[str, PIIPerson]:
        """Batch fetch persons by external_ids. Returns {external_id: PIIPerson}."""
        if not external_ids:
            return {}
        result = await db.execute(
            select(PIIPerson).where(
                PIIPerson.external_id.in_(external_ids),
                PIIPerson.is_active.is_(True),
            )
        )
        persons = result.scalars().all()
        return {p.external_id: p for p in persons}

    async def update_person_key(self, db: AsyncSession, external_id: str, person_key: str) -> None:
        """Cache the person_key from eagendas cloud response."""
        result = await db.execute(select(PIIPerson).where(PIIPerson.external_id == external_id))
        person = result.scalar_one_or_none()
        if person and person_key:
            person.person_key = person_key
            await db.commit()

    async def delete_person(self, db: AsyncSession, external_id: str) -> bool:
        """Hard delete a person's PII (right to be forgotten)."""
        result = await db.execute(select(PIIPerson).where(PIIPerson.external_id == external_id))
        person = result.scalar_one_or_none()
        if person:
            await db.delete(person)
            await db.commit()
            return True
        return False

    async def store_questionnaire_answer(
        self,
        db: AsyncSession,
        appointment_key: str,
        question_key: str,
        question_text: str,
        answer_body: str,
        pseudonymized_body: str,
    ) -> PIIQuestionnaireAnswer:
        """Store a PII questionnaire answer locally."""
        answer = PIIQuestionnaireAnswer(
            appointment_key=appointment_key,
            question_key=question_key,
            question_text=question_text,
            answer_body=answer_body,
            pseudonymized_body=pseudonymized_body,
        )
        db.add(answer)
        await db.commit()
        await db.refresh(answer)
        return answer

    async def get_questionnaire_answers(self, db: AsyncSession, appointment_key: str) -> dict[str, str]:
        """Get PII answers for an appointment. Returns {question_key: real_answer_body}."""
        result = await db.execute(
            select(PIIQuestionnaireAnswer).where(PIIQuestionnaireAnswer.appointment_key == appointment_key)
        )
        answers = result.scalars().all()
        return {a.question_key: a.answer_body for a in answers}

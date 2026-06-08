"""Data privacy service — right to erasure, data export, and PII purge."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.custom_data import LocalCustomData
from app.models.local_appointment import LocalAppointment
from app.models.pii_person import PIIPerson
from app.models.pii_questionnaire import PIIQuestionnaireAnswer

logger = logging.getLogger(__name__)


class DataPrivacyService:
    """Handles data subject rights: erasure, export, and automated purge."""

    async def forget_person(
        self,
        db: AsyncSession,
        external_id: str,
        client_ip: Optional[str] = None,
        request_path: Optional[str] = None,
    ) -> dict:
        """
        Right to erasure — delete all PII for a person.

        Removes: pii_person, pii_questionnaire_answer (by appointment linkage),
        local_appointment, custom_data. Audit log entries are kept (legal basis)
        but external_id is recorded in the erasure audit entry for traceability.

        Returns a summary of what was deleted.
        """
        summary = {
            "external_id": external_id,
            "person_deleted": False,
            "questionnaire_answers_deleted": 0,
            "appointments_deleted": 0,
            "custom_data_deleted": 0,
        }

        # 1. Find the person
        result = await db.execute(select(PIIPerson).where(PIIPerson.external_id == external_id))
        person = result.scalar_one_or_none()
        if not person:
            return summary

        person_key = person.person_key

        # 2. Get appointment keys from local_appointment (more reliable than audit logs)
        appt_result = await db.execute(
            select(LocalAppointment.appointment_key).where(LocalAppointment.external_id == external_id)
        )
        appointment_keys = [r[0] for r in appt_result.all()]

        # Also check audit logs for any appointments not tracked locally
        audit_result = await db.execute(
            select(AuditLog.resource_id)
            .where(
                AuditLog.external_id == external_id,
                AuditLog.resource_type == "appointment",
            )
            .distinct()
        )
        audit_keys = [r[0] for r in audit_result.all() if r[0]]
        all_appointment_keys = list(set(appointment_keys + audit_keys))

        # 3. Delete questionnaire answers linked to appointments
        if all_appointment_keys:
            qa_result = await db.execute(
                delete(PIIQuestionnaireAnswer).where(PIIQuestionnaireAnswer.appointment_key.in_(all_appointment_keys))
            )
            summary["questionnaire_answers_deleted"] = qa_result.rowcount

        # 4. Delete local appointment records
        la_result = await db.execute(delete(LocalAppointment).where(LocalAppointment.external_id == external_id))
        summary["appointments_deleted"] = la_result.rowcount

        # 5. Delete custom data (person-level + appointment-level)
        cd_result = await db.execute(
            delete(LocalCustomData).where(
                LocalCustomData.entity_type == "person",
                LocalCustomData.entity_key == external_id,
            )
        )
        custom_deleted = cd_result.rowcount
        if all_appointment_keys:
            cd_appt_result = await db.execute(
                delete(LocalCustomData).where(
                    LocalCustomData.entity_type == "appointment",
                    LocalCustomData.entity_key.in_(all_appointment_keys),
                )
            )
            custom_deleted += cd_appt_result.rowcount
        summary["custom_data_deleted"] = custom_deleted

        # 6. Delete the person record (hard delete)
        await db.delete(person)
        summary["person_deleted"] = True

        # 7. Audit the erasure (we keep audit logs as they serve a legal basis)
        audit_entry = AuditLog(
            action="ERASURE",
            resource_type="person",
            resource_id=person_key,
            external_id=external_id,
            client_ip=client_ip,
            request_method="DELETE",
            request_path=request_path,
            details={
                "reason": "right_to_erasure",
                "records_deleted": summary,
            },
        )
        db.add(audit_entry)

        await db.commit()

        logger.info(
            "Erasure completed for %s: person=%s, answers=%d, appointments=%d",
            external_id,
            summary["person_deleted"],
            summary["questionnaire_answers_deleted"],
            summary["appointments_deleted"],
        )

        return summary

    async def export_person_data(
        self,
        db: AsyncSession,
        external_id: str,
        client_ip: Optional[str] = None,
        request_path: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Data portability — export all data held about a person.

        Returns a structured dict with all PII, questionnaire answers,
        local appointments, custom data, and audit history.
        """
        result = await db.execute(select(PIIPerson).where(PIIPerson.external_id == external_id))
        person = result.scalar_one_or_none()
        if not person:
            return None

        export = {
            "subject": {
                "external_id": person.external_id,
                "person_key": person.person_key,
                "name": person.name,
                "email": person.email,
                "phone": person.phone,
                "identification_code": person.identification_code,
                "identification_type": person.identification_type,
                "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
                "address": person.address_json,
                "created_at": person.created_at.isoformat() if person.created_at else None,
                "updated_at": person.updated_at.isoformat() if person.updated_at else None,
            },
            "questionnaire_answers": [],
            "appointments": [],
            "custom_data": {},
            "audit_history": [],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        # Local appointments
        appt_result = await db.execute(
            select(LocalAppointment)
            .where(LocalAppointment.external_id == external_id)
            .order_by(LocalAppointment.scheduled_at.desc())
        )
        appointment_keys = []
        for appt in appt_result.scalars().all():
            appointment_keys.append(appt.appointment_key)
            export["appointments"].append(
                {
                    "appointment_key": appt.appointment_key,
                    "service_key": appt.service_key,
                    "scheduled_at": appt.scheduled_at.isoformat() if appt.scheduled_at else None,
                    "status": appt.status,
                    "created_at": appt.created_at.isoformat() if appt.created_at else None,
                }
            )

        # Also check audit logs for appointments not tracked locally
        audit_result = await db.execute(
            select(AuditLog.resource_id)
            .where(
                AuditLog.external_id == external_id,
                AuditLog.resource_type == "appointment",
            )
            .distinct()
        )
        audit_keys = [r[0] for r in audit_result.all() if r[0]]
        all_appointment_keys = list(set(appointment_keys + audit_keys))

        # Questionnaire answers
        if all_appointment_keys:
            qa_result = await db.execute(
                select(PIIQuestionnaireAnswer).where(PIIQuestionnaireAnswer.appointment_key.in_(all_appointment_keys))
            )
            for qa in qa_result.scalars().all():
                export["questionnaire_answers"].append(
                    {
                        "appointment_key": qa.appointment_key,
                        "question_key": qa.question_key,
                        "question_text": qa.question_text,
                        "answer_body": qa.answer_body,
                        "created_at": qa.created_at.isoformat() if qa.created_at else None,
                    }
                )

        # Custom data (person-level)
        cd_person = await db.execute(
            select(LocalCustomData).where(
                LocalCustomData.entity_type == "person",
                LocalCustomData.entity_key == external_id,
            )
        )
        cd_person_record = cd_person.scalar_one_or_none()
        if cd_person_record:
            export["custom_data"]["person"] = cd_person_record.data

        # Custom data (appointment-level)
        if all_appointment_keys:
            cd_appt = await db.execute(
                select(LocalCustomData).where(
                    LocalCustomData.entity_type == "appointment",
                    LocalCustomData.entity_key.in_(all_appointment_keys),
                )
            )
            for cd in cd_appt.scalars().all():
                export["custom_data"][f"appointment:{cd.entity_key}"] = cd.data

        # Audit history (actions performed on this person's data)
        audit_entries = await db.execute(
            select(AuditLog).where(AuditLog.external_id == external_id).order_by(AuditLog.timestamp.desc())
        )
        for entry in audit_entries.scalars().all():
            export["audit_history"].append(
                {
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    "action": entry.action,
                    "resource_type": entry.resource_type,
                    "resource_id": entry.resource_id,
                    "request_method": entry.request_method,
                    "request_path": entry.request_path,
                    "pii_fields_accessed": entry.pii_fields_accessed,
                }
            )

        # Audit the export itself
        audit_entry = AuditLog(
            action="EXPORT",
            resource_type="person",
            resource_id=person.person_key,
            external_id=external_id,
            client_ip=client_ip,
            request_method="GET",
            request_path=request_path,
        )
        db.add(audit_entry)
        await db.commit()

        return export

    async def purge_expired(self, db: AsyncSession) -> dict:
        """
        Automated purge — delete all PII records past their purge_after date.

        Unlike the simple delete in audit_cleanup, this properly cleans up
        all related records and audits each erasure.
        """
        today = date.today()

        result = await db.execute(
            select(PIIPerson).where(
                PIIPerson.purge_after.isnot(None),
                PIIPerson.purge_after <= today,
            )
        )
        expired = result.scalars().all()

        summary = {
            "persons_purged": 0,
            "questionnaire_answers_deleted": 0,
            "appointments_deleted": 0,
        }

        for person in expired:
            result = await self.forget_person(
                db,
                external_id=person.external_id,
                request_path="/system/purge",
            )
            if result["person_deleted"]:
                summary["persons_purged"] += 1
                summary["questionnaire_answers_deleted"] += result["questionnaire_answers_deleted"]
                summary["appointments_deleted"] += result["appointments_deleted"]

        if summary["persons_purged"]:
            logger.info(
                "Automated purge completed: %d persons, %d answers, %d appointments",
                summary["persons_purged"],
                summary["questionnaire_answers_deleted"],
                summary["appointments_deleted"],
            )

        return summary

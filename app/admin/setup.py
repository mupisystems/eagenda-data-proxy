"""SQLAdmin configuration for the Data Proxy admin panel."""

from fastapi import FastAPI
from sqladmin import Admin, ModelView

from app.models.pii_person import PIIPerson
from app.models.pii_questionnaire import PIIQuestionnaireAnswer
from app.models.audit_log import AuditLog
from app.models.notification_log import NotificationLog
from app.models.local_appointment import LocalAppointment
from app.models.custom_data import LocalCustomData
from app.models.proxy_token import ProxyToken


class PIIPersonAdmin(ModelView, model=PIIPerson):
    name = "Person (PII)"
    name_plural = "People (PII)"
    icon = "fa-solid fa-user"
    column_list = [
        PIIPerson.id,
        PIIPerson.external_id,
        PIIPerson.person_key,
        PIIPerson.name,
        PIIPerson.email,
        PIIPerson.phone,
        PIIPerson.is_active,
        PIIPerson.created_at,
    ]
    column_searchable_list = [PIIPerson.name, PIIPerson.email, PIIPerson.external_id]
    column_sortable_list = [PIIPerson.id, PIIPerson.created_at, PIIPerson.name]
    can_delete = False  # Deletion must go through audit (right to be forgotten)


class PIIQuestionnaireAdmin(ModelView, model=PIIQuestionnaireAnswer):
    name = "PII Answer"
    name_plural = "PII Answers"
    icon = "fa-solid fa-file-lines"
    column_list = [
        PIIQuestionnaireAnswer.id,
        PIIQuestionnaireAnswer.appointment_key,
        PIIQuestionnaireAnswer.question_key,
        PIIQuestionnaireAnswer.question_text,
        PIIQuestionnaireAnswer.created_at,
    ]
    can_create = False
    can_edit = False
    can_delete = False


class AuditLogAdmin(ModelView, model=AuditLog):
    name = "Audit Log"
    name_plural = "Audit Logs"
    icon = "fa-solid fa-clipboard-list"
    column_list = [
        AuditLog.id,
        AuditLog.timestamp,
        AuditLog.action,
        AuditLog.resource_type,
        AuditLog.external_id,
        AuditLog.client_ip,
        AuditLog.request_method,
    ]
    column_sortable_list = [AuditLog.id, AuditLog.timestamp]
    can_create = False
    can_edit = False
    can_delete = False


class NotificationLogAdmin(ModelView, model=NotificationLog):
    name = "Notification Log"
    name_plural = "Notification Logs"
    icon = "fa-solid fa-envelope"
    column_list = [
        NotificationLog.id,
        NotificationLog.external_id,
        NotificationLog.channel,
        NotificationLog.recipient,
        NotificationLog.status,
        NotificationLog.created_at,
    ]
    column_sortable_list = [NotificationLog.id, NotificationLog.created_at]
    can_create = False
    can_edit = False
    can_delete = False


class ProxyTokenAdmin(ModelView, model=ProxyToken):
    name = "Token"
    name_plural = "Tokens"
    icon = "fa-solid fa-key"
    column_list = [
        ProxyToken.id,
        ProxyToken.label,
        ProxyToken.is_active,
        ProxyToken.created_at,
        ProxyToken.expires_at,
        ProxyToken.last_used_at,
    ]
    form_excluded_columns = [ProxyToken.token_hash, ProxyToken.last_used_at]


class LocalAppointmentAdmin(ModelView, model=LocalAppointment):
    name = "Local Appointment"
    name_plural = "Local Appointments"
    icon = "fa-solid fa-calendar-check"
    column_list = [
        LocalAppointment.id,
        LocalAppointment.appointment_key,
        LocalAppointment.external_id,
        LocalAppointment.service_key,
        LocalAppointment.scheduled_at,
        LocalAppointment.status,
        LocalAppointment.created_at,
        LocalAppointment.updated_at,
    ]
    column_searchable_list = [LocalAppointment.appointment_key, LocalAppointment.external_id]
    column_sortable_list = [
        LocalAppointment.id,
        LocalAppointment.scheduled_at,
        LocalAppointment.status,
        LocalAppointment.created_at,
        LocalAppointment.updated_at,
    ]


class LocalCustomDataAdmin(ModelView, model=LocalCustomData):
    name = "Custom Data"
    name_plural = "Custom Data"
    icon = "fa-solid fa-database"
    column_list = [
        LocalCustomData.id,
        LocalCustomData.entity_type,
        LocalCustomData.entity_key,
        LocalCustomData.created_at,
        LocalCustomData.updated_at,
    ]
    column_searchable_list = [LocalCustomData.entity_key]
    column_sortable_list = [LocalCustomData.id, LocalCustomData.entity_type, LocalCustomData.updated_at]


def setup_admin(app: FastAPI, engine) -> Admin:
    """Configure and mount SQLAdmin on the FastAPI app."""
    admin = Admin(app, engine, title="eagendas Data Proxy")
    admin.add_view(PIIPersonAdmin)
    admin.add_view(PIIQuestionnaireAdmin)
    admin.add_view(AuditLogAdmin)
    admin.add_view(NotificationLogAdmin)
    admin.add_view(ProxyTokenAdmin)
    admin.add_view(LocalAppointmentAdmin)
    admin.add_view(LocalCustomDataAdmin)
    return admin

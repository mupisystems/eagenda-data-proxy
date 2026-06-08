from pydantic import BaseModel, ConfigDict


class _Passthrough(BaseModel):
    """Base that keeps unmodeled fields so the proxy forwards them untouched.

    Convert back to the outbound payload with ``model_dump(exclude_unset=True)``
    so omitted optional fields are not sent as ``null``.
    """

    model_config = ConfigDict(extra="allow")


class QuestionnaireAnswer(_Passthrough):
    question_key: str
    body: str


class AttendeeInput(_Passthrough):
    name: str
    email: str | None = None
    phone: str | None = None
    identification_code: str | None = None
    identification_type: str | None = None
    external_id: str | None = None


class DateTimeInput(_Passthrough):
    dateTime: str  # noqa: N815 — matches the eagendas API field name


class ServiceRef(_Passthrough):
    service_key: str


class TagRef(_Passthrough):
    tag_key: str


class AppointmentCreate(_Passthrough):
    """Appointment creation payload — eagendas shape plus the proxy-only
    ``custom_data`` field (stripped before forwarding)."""

    calendar_key: str
    start: DateTimeInput
    attendees: list[AttendeeInput]
    service_list: list[ServiceRef] | None = None
    tag_list: list[TagRef] | None = None
    status: str | None = None
    description: str | None = None
    questionnaire_answers: list[QuestionnaireAnswer] | None = None
    custom_data: dict | None = None

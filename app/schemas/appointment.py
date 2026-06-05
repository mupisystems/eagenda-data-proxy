from pydantic import BaseModel


class QuestionnaireAnswer(BaseModel):
    question_key: str
    body: str


class AttendeeInput(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    identification_code: str | None = None
    identification_type: str | None = None
    external_id: str | None = None

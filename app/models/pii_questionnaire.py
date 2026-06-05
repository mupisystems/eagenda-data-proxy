from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PIIQuestionnaireAnswer(Base):
    __tablename__ = "pii_questionnaire_answer"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_key: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    question_key: Mapped[str] = mapped_column(String(36), nullable=False)
    question_text: Mapped[Optional[str]] = mapped_column(String(500))
    answer_body: Mapped[str] = mapped_column(Text, nullable=False)
    pseudonymized_body: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PIIAnswer appointment={self.appointment_key!r} question={self.question_key!r}>"

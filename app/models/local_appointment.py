from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LocalAppointment(Base):
    __tablename__ = "local_appointment"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    service_key: Mapped[Optional[str]] = mapped_column(String(255))
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_local_appt_ext_status", "external_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<LocalAppointment {self.appointment_key} ext={self.external_id} status={self.status}>"

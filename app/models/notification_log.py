from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    appointment_key: Mapped[Optional[str]] = mapped_column(String(36))
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email, sms, whatsapp
    recipient: Mapped[str] = mapped_column(String(254), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # queued, sent, failed, delivered
    error_detail: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<NotificationLog {self.channel} {self.recipient} {self.status}>"

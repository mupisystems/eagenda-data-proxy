from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # CREATE, READ, UPDATE, DELETE, FORWARD, ENRICH
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # person, appointment, webhook
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    external_id: Mapped[Optional[str]] = mapped_column(String(255))
    client_ip: Mapped[Optional[str]] = mapped_column(String(45))
    token_id: Mapped[Optional[int]] = mapped_column(ForeignKey("proxy_token.id"))
    request_method: Mapped[Optional[str]] = mapped_column(String(10))
    request_path: Mapped[Optional[str]] = mapped_column(String(500))
    pii_fields_accessed: Mapped[Optional[list]] = mapped_column(JSON)
    details: Mapped[Optional[dict]] = mapped_column(JSON)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type} {self.resource_id}>"

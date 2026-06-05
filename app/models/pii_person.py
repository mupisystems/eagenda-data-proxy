from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PIIPerson(Base):
    __tablename__ = "pii_person"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    person_key: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # PII fields — stored locally, never sent to cloud
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(254))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    identification_code: Mapped[Optional[str]] = mapped_column(String(30))
    identification_type: Mapped[Optional[str]] = mapped_column(String(20))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    address_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Metadata
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    purge_after: Mapped[Optional[date]] = mapped_column(Date)

    def __repr__(self) -> str:
        return f"<PIIPerson external_id={self.external_id!r} name={self.name!r}>"

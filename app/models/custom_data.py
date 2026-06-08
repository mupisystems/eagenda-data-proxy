from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LocalCustomData(Base):
    __tablename__ = "local_custom_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # person, appointment
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)  # external_id or appointment_key
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_custom_data_entity", "entity_type", "entity_key", unique=True),)

    def __repr__(self) -> str:
        return f"<LocalCustomData {self.entity_type}:{self.entity_key}>"

"""Audit logging service."""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for recording audit log entries."""

    async def log(
        self,
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        token_id: Optional[int] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        pii_fields_accessed: Optional[list[str]] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            external_id=external_id,
            client_ip=client_ip,
            token_id=token_id,
            request_method=request_method,
            request_path=request_path,
            pii_fields_accessed=pii_fields_accessed,
            details=details,
        )
        db.add(entry)
        await db.commit()
        return entry

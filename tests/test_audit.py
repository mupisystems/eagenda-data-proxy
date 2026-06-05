"""Tests for audit logging."""
import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.services.audit import AuditService


class TestAuditService:
    async def test_creates_audit_entry(self, db_session):
        service = AuditService()
        entry = await service.log(
            db_session,
            action="CREATE",
            resource_type="person",
            resource_id="uuid-123",
            external_id="EXT-001",
            client_ip="10.0.0.1",
            request_method="POST",
            request_path="/api/v3/people/",
            pii_fields_accessed=["name", "email", "phone"],
        )

        assert entry.id is not None
        assert entry.action == "CREATE"
        assert entry.resource_type == "person"
        assert entry.pii_fields_accessed == ["name", "email", "phone"]

    async def test_audit_entry_has_timestamp(self, db_session):
        service = AuditService()
        entry = await service.log(db_session, action="READ", resource_type="person")

        assert entry.timestamp is not None

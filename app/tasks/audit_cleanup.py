"""Audit cleanup task — retention policy enforcement."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.config import get_settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_records():
    """Delete audit logs past retention and PII records past purge_after."""
    import asyncio
    asyncio.run(_cleanup())


async def _cleanup():
    from app.db.engine import create_engine, create_session_factory
    from app.models.audit_log import AuditLog
    from app.models.pii_person import PIIPerson

    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    async with session_factory() as db:
        # Clean up old audit logs
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
        result = await db.execute(
            delete(AuditLog).where(AuditLog.timestamp < cutoff)
        )
        audit_deleted = result.rowcount
        if audit_deleted:
            logger.info("Deleted %d audit log entries older than %s", audit_deleted, cutoff.date())

        # Clean up PII past purge_after
        today = datetime.now(timezone.utc).date()
        result = await db.execute(
            delete(PIIPerson).where(PIIPerson.purge_after <= today)
        )
        pii_deleted = result.rowcount
        if pii_deleted:
            logger.info("Purged %d PII records past retention date", pii_deleted)

        await db.commit()

    await engine.dispose()

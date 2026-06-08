from typing import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.proxy.forwarder import CloudForwarder
from app.proxy.interceptor import PIIInterceptor
from app.proxy.enricher import PIIEnricher
from app.services.pii_store import PIIStore
from app.services.audit import AuditService
from app.services.booking_limiter import BookingLimiter
from app.services.custom_data_store import CustomDataStore
from app.services.data_privacy import DataPrivacyService
from app.services.questionnaire import QuestionnaireProcessor


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session per request."""
    async with request.app.state.session_factory() as session:
        yield session


def get_forwarder(request: Request, settings: Settings = Depends(get_settings)) -> CloudForwarder:
    """Get the cloud forwarder using the shared httpx client."""
    return CloudForwarder(
        client=request.app.state.http_client,
        base_url=settings.eagendas_url,
        token=settings.eagendas_api_token,
    )


def get_pii_store() -> PIIStore:
    return PIIStore()


def get_interceptor(
    settings: Settings = Depends(get_settings),
    pii_store: PIIStore = Depends(get_pii_store),
) -> PIIInterceptor:
    return PIIInterceptor(settings=settings, pii_store=pii_store)


def get_custom_data_store() -> CustomDataStore:
    return CustomDataStore()


def get_questionnaire_processor(
    settings: Settings = Depends(get_settings),
    forwarder: CloudForwarder = Depends(get_forwarder),
    pii_store: PIIStore = Depends(get_pii_store),
) -> QuestionnaireProcessor:
    return QuestionnaireProcessor(forwarder=forwarder, pii_store=pii_store, settings=settings)


def get_enricher(
    pii_store: PIIStore = Depends(get_pii_store),
    custom_data_store: CustomDataStore = Depends(get_custom_data_store),
) -> PIIEnricher:
    return PIIEnricher(pii_store=pii_store, custom_data_store=custom_data_store)


def get_audit() -> AuditService:
    return AuditService()


def get_booking_limiter() -> BookingLimiter:
    return BookingLimiter()


def get_data_privacy() -> DataPrivacyService:
    return DataPrivacyService()

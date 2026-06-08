"""Appointments proxy router — intercepts attendee PII and questionnaire answers."""

import logging
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.bearer import verify_proxy_token
from app.dependencies import (
    get_booking_limiter,
    get_custom_data_store,
    get_db,
    get_enricher,
    get_forwarder,
    get_interceptor,
)
from app.proxy.enricher import PIIEnricher
from app.proxy.forwarder import CloudForwarder
from app.proxy.interceptor import PIIInterceptor
from app.services.booking_limiter import BookingLimitDenied, BookingLimiter
from app.services.custom_data_store import CustomDataStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/appointments", tags=["Appointments"], dependencies=[Depends(verify_proxy_token)])


def _primary_external_id(body: dict) -> str | None:
    """Resolve the external_id used for booking limits and local tracking.

    Person data lives inside ``attendees`` (eagendas shape); fall back to a
    top-level ``external_id`` for flat payloads.
    """
    if body.get("external_id"):
        return body["external_id"]
    for attendee in body.get("attendees", []):
        if attendee.get("external_id"):
            return attendee["external_id"]
    return None


@router.get("/")
async def list_appointments(
    request: Request,
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """List appointments — forward, enrich attendees with PII."""
    cloud_resp = await forwarder.forward("GET", "/appointments/", params=dict(request.query_params))
    data = cloud_resp.json()
    enriched = await enricher.enrich_paginated(data, "appointment", db)
    return JSONResponse(content=enriched, status_code=cloud_resp.status_code)


@router.post("/")
async def create_appointment(
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    interceptor: PIIInterceptor = Depends(get_interceptor),
    enricher: PIIEnricher = Depends(get_enricher),
    limiter: BookingLimiter = Depends(get_booking_limiter),
    custom_store: CustomDataStore = Depends(get_custom_data_store),
):
    """Create appointment — check limits, intercept attendee PII, forward, enrich."""
    external_id = _primary_external_id(body)

    # Enforce booking limits before processing
    if external_id:
        try:
            await limiter.check(
                db,
                external_id=external_id,
                service_key=body.get("service_key"),
                tag=body.get("tag"),
            )
        except BookingLimitDenied as exc:
            logger.info("Booking denied for %s: %s", external_id, exc.reason)
            return JSONResponse(
                content={"error": exc.reason, "message": exc.message, "details": exc.details},
                status_code=429,
            )

    # Extract custom_data before forwarding (stored locally, never sent to cloud)
    custom_data = body.pop("custom_data", None)

    cleaned = await interceptor.intercept_appointment(body, db)

    # The interceptor may have generated an external_id for an attendee that
    # lacked one — re-resolve so local tracking uses the same key as the cloud.
    external_id = _primary_external_id(cleaned) or external_id

    cloud_resp = await forwarder.forward("POST", "/appointments/", body=cleaned)

    if cloud_resp.status_code == 201:
        cloud_data = cloud_resp.json()
        appointment_key = cloud_data.get("appointment_key")

        # Record appointment locally for limit tracking
        if external_id and appointment_key:
            scheduled_at = None
            if body.get("date_time"):
                try:
                    scheduled_at = datetime.fromisoformat(body["date_time"])
                except (ValueError, TypeError):
                    pass
            await limiter.record_appointment(
                db,
                appointment_key=appointment_key,
                external_id=external_id,
                service_key=body.get("service_key"),
                scheduled_at=scheduled_at,
            )

        # Store custom data locally
        if custom_data and appointment_key:
            await custom_store.upsert(db, "appointment", appointment_key, custom_data)

        enriched = await enricher.enrich_appointment(cloud_data, db)
        return JSONResponse(content=enriched, status_code=201)

    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.get("/{appointment_key}/")
async def retrieve_appointment(
    appointment_key: str,
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """Retrieve appointment — forward, enrich."""
    cloud_resp = await forwarder.forward("GET", f"/appointments/{appointment_key}/")
    if cloud_resp.status_code == 200:
        enriched = await enricher.enrich_appointment(cloud_resp.json(), db)
        return JSONResponse(content=enriched, status_code=200)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.patch("/{appointment_key}/")
async def update_appointment(
    appointment_key: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """Update appointment status — no PII, forward and enrich."""
    cloud_resp = await forwarder.forward("PATCH", f"/appointments/{appointment_key}/", body=body)
    if cloud_resp.status_code == 200:
        enriched = await enricher.enrich_appointment(cloud_resp.json(), db)
        return JSONResponse(content=enriched, status_code=200)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.delete("/{appointment_key}/")
async def cancel_appointment(
    appointment_key: str,
    request: Request,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    """Cancel appointment — forward with query params."""
    cloud_resp = await forwarder.forward(
        "DELETE", f"/appointments/{appointment_key}/", params=dict(request.query_params)
    )
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.patch("/{appointment_key}/reschedule/")
async def reschedule_appointment(
    appointment_key: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """Reschedule appointment — no PII in payload, forward and enrich."""
    cloud_resp = await forwarder.forward("PATCH", f"/appointments/{appointment_key}/reschedule/", body=body)
    if cloud_resp.status_code == 200:
        enriched = await enricher.enrich_appointment(cloud_resp.json(), db)
        return JSONResponse(content=enriched, status_code=200)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)

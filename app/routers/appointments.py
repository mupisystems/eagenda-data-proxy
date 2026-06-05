"""Appointments proxy router — intercepts attendee PII and questionnaire answers."""
from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.bearer import verify_proxy_token
from app.dependencies import get_db, get_enricher, get_forwarder, get_interceptor
from app.proxy.enricher import PIIEnricher
from app.proxy.forwarder import CloudForwarder
from app.proxy.interceptor import PIIInterceptor

router = APIRouter(
    prefix="/api/v3/appointments", tags=["Appointments"], dependencies=[Depends(verify_proxy_token)]
)


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
):
    """Create appointment — intercept attendee PII and text answers, forward, enrich."""
    cleaned = await interceptor.intercept_appointment(body, db)
    cloud_resp = await forwarder.forward("POST", "/appointments/", body=cleaned)

    if cloud_resp.status_code == 201:
        enriched = await enricher.enrich_appointment(cloud_resp.json(), db)
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

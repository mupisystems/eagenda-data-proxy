"""People proxy router — intercepts PII on write, enriches on read."""
import logging

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.bearer import verify_proxy_token
from app.dependencies import get_data_privacy, get_db, get_enricher, get_forwarder, get_interceptor, get_audit
from app.proxy.enricher import PIIEnricher
from app.proxy.forwarder import CloudForwarder
from app.proxy.interceptor import PIIInterceptor
from app.services.audit import AuditService
from app.services.data_privacy import DataPrivacyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/people", tags=["People"], dependencies=[Depends(verify_proxy_token)])


@router.get("/")
async def list_people(
    request: Request,
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """List people — forward to cloud, enrich with PII."""
    cloud_resp = await forwarder.forward("GET", "/people/", params=dict(request.query_params))
    data = cloud_resp.json()
    enriched = await enricher.enrich_paginated(data, "person", db)
    return JSONResponse(content=enriched, status_code=cloud_resp.status_code)


@router.post("/")
async def create_person(
    request: Request,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    interceptor: PIIInterceptor = Depends(get_interceptor),
    enricher: PIIEnricher = Depends(get_enricher),
    audit: AuditService = Depends(get_audit),
):
    """Create person — intercept PII, forward pseudonymized, enrich response."""
    cleaned, pii = await interceptor.intercept_person(body, db)
    cloud_resp = await forwarder.forward("POST", "/people/", body=cleaned)

    if cloud_resp.status_code in (200, 201):
        data = cloud_resp.json()
        from app.services.pii_store import PIIStore
        store = PIIStore()
        await store.update_person_key(db, pii.external_id, data.get("person_key"))
        enriched = await enricher.enrich_person(data, db)
        await audit.log(
            db, action="CREATE", resource_type="person",
            resource_id=data.get("person_key"), external_id=pii.external_id,
            client_ip=request.client.host if request.client else None,
            request_method="POST", request_path="/api/v3/people/",
            pii_fields_accessed=list(body.keys()),
        )
        return JSONResponse(content=enriched, status_code=cloud_resp.status_code)

    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.get("/{person_key}/")
async def retrieve_person(
    person_key: str,
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """Retrieve person — forward, enrich with PII."""
    cloud_resp = await forwarder.forward("GET", f"/people/{person_key}/")
    if cloud_resp.status_code == 200:
        enriched = await enricher.enrich_person(cloud_resp.json(), db)
        return JSONResponse(content=enriched, status_code=200)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.put("/{person_key}/")
async def update_person(
    person_key: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    interceptor: PIIInterceptor = Depends(get_interceptor),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """Update person — intercept PII, forward, enrich."""
    cleaned, _ = await interceptor.intercept_person(body, db)
    cloud_resp = await forwarder.forward("PUT", f"/people/{person_key}/", body=cleaned)
    if cloud_resp.status_code == 200:
        enriched = await enricher.enrich_person(cloud_resp.json(), db)
        return JSONResponse(content=enriched, status_code=200)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.patch("/{person_key}/")
async def partial_update_person(
    person_key: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    interceptor: PIIInterceptor = Depends(get_interceptor),
    enricher: PIIEnricher = Depends(get_enricher),
):
    """Partial update person — intercept PII fields present, forward, enrich."""
    cleaned, _ = await interceptor.intercept_person(body, db)
    cloud_resp = await forwarder.forward("PATCH", f"/people/{person_key}/", body=cleaned)
    if cloud_resp.status_code == 200:
        enriched = await enricher.enrich_person(cloud_resp.json(), db)
        return JSONResponse(content=enriched, status_code=200)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.get("/{external_id}/export/")
async def export_person_data(
    external_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    privacy: DataPrivacyService = Depends(get_data_privacy),
):
    """Data portability — export all data held about a person."""
    data = await privacy.export_person_data(
        db,
        external_id=external_id,
        client_ip=request.client.host if request.client else None,
        request_path=f"/api/v3/people/{external_id}/export/",
    )
    if data is None:
        return JSONResponse(content={"error": "not_found", "message": "Person not found."}, status_code=404)
    return JSONResponse(content=data)


@router.delete("/{external_id}/forget/")
async def forget_person(
    external_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    forwarder: CloudForwarder = Depends(get_forwarder),
    privacy: DataPrivacyService = Depends(get_data_privacy),
):
    """
    Right to erasure — delete all local PII for a person.

    Also pseudonymizes the person in eagendas cloud by updating their
    name to the redacted placeholder.
    """
    result = await privacy.forget_person(
        db,
        external_id=external_id,
        client_ip=request.client.host if request.client else None,
        request_path=f"/api/v3/people/{external_id}/forget/",
    )

    if not result["person_deleted"]:
        return JSONResponse(content={"error": "not_found", "message": "Person not found."}, status_code=404)

    # Best-effort: pseudonymize in eagendas cloud
    try:
        from app.services.pii_store import PIIStore
        store = PIIStore()
        await store.get_by_person_key(db, result.get("person_key", ""))
        # Person is already deleted locally, but we try to update cloud
        await forwarder.forward("PATCH", f"/people/{external_id}/", body={
            "name": "[ERASED]",
            "email": "",
            "phone": "",
        })
    except Exception:
        logger.warning("Could not pseudonymize person %s in cloud (best-effort)", external_id)

    return JSONResponse(content={
        "status": "erased",
        "summary": result,
    })

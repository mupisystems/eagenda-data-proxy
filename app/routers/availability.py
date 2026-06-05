"""Availability proxy routers — pass-through (no PII)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.auth.bearer import verify_proxy_token
from app.dependencies import get_forwarder
from app.proxy.forwarder import CloudForwarder

router = APIRouter(tags=["Availability"], dependencies=[Depends(verify_proxy_token)])


@router.get("/api/v3/days/")
async def list_days(
    request: Request,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("GET", "/days/", params=dict(request.query_params))
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.get("/api/v3/date-times/")
async def list_date_times(
    request: Request,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("GET", "/date-times/", params=dict(request.query_params))
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.get("/api/v3/available-date-times/")
async def list_available_date_times(
    request: Request,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("GET", "/available-date-times/", params=dict(request.query_params))
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)

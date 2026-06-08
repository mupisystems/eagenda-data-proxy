"""Services proxy router — pass-through (no PII)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.auth.bearer import verify_proxy_token
from app.dependencies import get_forwarder
from app.proxy.forwarder import CloudForwarder

router = APIRouter(prefix="/api/v3/services", tags=["Services"], dependencies=[Depends(verify_proxy_token)])


@router.get("/")
async def list_services(
    request: Request,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("GET", "/services/", params=dict(request.query_params))
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.get("/{service_key}/")
async def retrieve_service(
    service_key: str,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("GET", f"/services/{service_key}/")
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)

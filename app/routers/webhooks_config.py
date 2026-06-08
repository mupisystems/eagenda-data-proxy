"""Webhooks configuration proxy router."""

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from app.auth.bearer import verify_proxy_token
from app.dependencies import get_forwarder
from app.proxy.forwarder import CloudForwarder

router = APIRouter(prefix="/api/v3/webhooks", tags=["Webhooks"], dependencies=[Depends(verify_proxy_token)])


@router.get("/")
async def list_webhooks(
    request: Request,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("GET", "/webhooks/", params=dict(request.query_params))
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.post("/")
async def create_webhook(
    body: dict = Body(...),
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    """Create webhook — forward to cloud."""
    cloud_resp = await forwarder.forward("POST", "/webhooks/", body=body)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.get("/{webhook_key}/")
async def retrieve_webhook(
    webhook_key: str,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("GET", f"/webhooks/{webhook_key}/")
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.put("/{webhook_key}/")
async def update_webhook(
    webhook_key: str,
    body: dict = Body(...),
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("PUT", f"/webhooks/{webhook_key}/", body=body)
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)


@router.delete("/{webhook_key}/")
async def delete_webhook(
    webhook_key: str,
    forwarder: CloudForwarder = Depends(get_forwarder),
):
    cloud_resp = await forwarder.forward("DELETE", f"/webhooks/{webhook_key}/")
    return JSONResponse(content=cloud_resp.json(), status_code=cloud_resp.status_code)

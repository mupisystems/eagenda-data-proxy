"""Local custom data router — direct CRUD for custom fields stored locally."""

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.bearer import verify_proxy_token
from app.dependencies import get_custom_data_store, get_db
from app.services.custom_data_store import CustomDataStore

router = APIRouter(prefix="/api/v3/local-data", tags=["Local Data"], dependencies=[Depends(verify_proxy_token)])


@router.get("/person/{external_id}/")
async def get_person_custom_data(
    external_id: str,
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Get custom data for a person."""
    data = await store.get(db, "person", external_id)
    if data is None:
        return JSONResponse(content={"error": "not_found", "message": "No custom data found."}, status_code=404)
    return JSONResponse(content={"entity_type": "person", "entity_key": external_id, "data": data})


@router.put("/person/{external_id}/")
async def set_person_custom_data(
    external_id: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Set (replace) custom data for a person."""
    data = await store.replace(db, "person", external_id, body)
    return JSONResponse(content={"entity_type": "person", "entity_key": external_id, "data": data})


@router.patch("/person/{external_id}/")
async def update_person_custom_data(
    external_id: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Update (merge) custom data for a person."""
    data = await store.upsert(db, "person", external_id, body)
    return JSONResponse(content={"entity_type": "person", "entity_key": external_id, "data": data})


@router.delete("/person/{external_id}/")
async def delete_person_custom_data(
    external_id: str,
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Delete custom data for a person."""
    deleted = await store.delete(db, "person", external_id)
    if not deleted:
        return JSONResponse(content={"error": "not_found", "message": "No custom data found."}, status_code=404)
    return JSONResponse(content={"status": "deleted"})


@router.get("/appointment/{appointment_key}/")
async def get_appointment_custom_data(
    appointment_key: str,
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Get custom data for an appointment."""
    data = await store.get(db, "appointment", appointment_key)
    if data is None:
        return JSONResponse(content={"error": "not_found", "message": "No custom data found."}, status_code=404)
    return JSONResponse(content={"entity_type": "appointment", "entity_key": appointment_key, "data": data})


@router.put("/appointment/{appointment_key}/")
async def set_appointment_custom_data(
    appointment_key: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Set (replace) custom data for an appointment."""
    data = await store.replace(db, "appointment", appointment_key, body)
    return JSONResponse(content={"entity_type": "appointment", "entity_key": appointment_key, "data": data})


@router.patch("/appointment/{appointment_key}/")
async def update_appointment_custom_data(
    appointment_key: str,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Update (merge) custom data for an appointment."""
    data = await store.upsert(db, "appointment", appointment_key, body)
    return JSONResponse(content={"entity_type": "appointment", "entity_key": appointment_key, "data": data})


@router.delete("/appointment/{appointment_key}/")
async def delete_appointment_custom_data(
    appointment_key: str,
    db: AsyncSession = Depends(get_db),
    store: CustomDataStore = Depends(get_custom_data_store),
):
    """Delete custom data for an appointment."""
    deleted = await store.delete(db, "appointment", appointment_key)
    if not deleted:
        return JSONResponse(content={"error": "not_found", "message": "No custom data found."}, status_code=404)
    return JSONResponse(content={"status": "deleted"})

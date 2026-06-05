"""Health check endpoint."""
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["Health"])


@router.get("/health/")
async def health_check(request: Request):
    """Check proxy health: DB connectivity and eagendas cloud reachability."""
    checks = {"status": "ok", "db": "ok", "eagendas": "ok"}

    # DB check
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        checks["db"] = f"error: {e}"
        checks["status"] = "degraded"

    # eagendas cloud check
    try:
        from app.config import get_settings
        settings = get_settings()
        response = await request.app.state.http_client.get(
            f"{settings.eagendas_base_url}/schema/",
            headers={"Authorization": f"Bearer {settings.eagendas_api_token}"},
            timeout=5.0,
        )
        if response.status_code >= 500:
            checks["eagendas"] = f"error: HTTP {response.status_code}"
            checks["status"] = "degraded"
    except Exception as e:
        checks["eagendas"] = f"error: {e}"
        checks["status"] = "degraded"

    return checks

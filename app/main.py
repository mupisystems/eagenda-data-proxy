import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import get_settings
from app.db.engine import create_engine, create_session_factory, create_sync_engine


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level))

    # Async httpx client for eagendas cloud
    app.state.http_client = httpx.AsyncClient(timeout=settings.eagendas_timeout)

    # Async DB engine + session factory
    app.state.engine = create_engine(settings.database_url)
    app.state.session_factory = create_session_factory(app.state.engine)

    # Dev-only: create the schema from the models (use Alembic in production).
    if settings.db_auto_create:
        from app.db.base import Base
        from app import models as _models  # noqa: F401 — register all models on Base.metadata

        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.warning("db_auto_create is ON — tables created from models (dev only)")

    logger.info("eagendas Data Proxy started — region: %s, cloud: %s", settings.eagendas_region, settings.eagendas_url)

    yield

    await app.state.http_client.aclose()
    await app.state.engine.dispose()
    logger.info("eagendas Data Proxy stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="eagendas Data Proxy",
        description="On-premise PII proxy for eagendas API v3",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Import and include routers
    from app.routers import (
        people,
        appointments,
        calendars,
        availability,
        services,
        tags,
        webhooks_config,
        webhook_receiver,
        local_data,
        health,
    )

    app.include_router(health.router)
    app.include_router(people.router)
    app.include_router(appointments.router)
    app.include_router(calendars.router)
    app.include_router(availability.router)
    app.include_router(services.router)
    app.include_router(tags.router)
    app.include_router(webhooks_config.router)
    app.include_router(webhook_receiver.router)
    app.include_router(local_data.router)

    # Admin panel
    if settings.admin_enabled:
        from app.admin.setup import setup_admin

        sync_engine = create_sync_engine(settings.database_url_sync)
        setup_admin(app, sync_engine)

    return app


app = create_app()

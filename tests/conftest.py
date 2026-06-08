import hashlib

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import *  # noqa: F401,F403


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def proxy_token(db_session):
    """Create a valid proxy token for tests."""
    from app.models.proxy_token import ProxyToken

    raw_token = "test-token-123"
    token = ProxyToken(
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        label="Test Token",
        is_active=True,
    )
    db_session.add(token)
    await db_session.commit()
    return raw_token


@pytest_asyncio.fixture
async def client(engine, db_session, proxy_token):
    """Test client with mocked dependencies."""
    from app.main import create_app
    from app.dependencies import get_db

    app = create_app()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {proxy_token}"},
    ) as ac:
        yield ac

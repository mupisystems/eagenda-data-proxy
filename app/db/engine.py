from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine as sa_create_engine


def create_engine(database_url: str):
    """Create async SQLAlchemy engine (asyncpg)."""
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def create_sync_engine(database_url_sync: str):
    """Create sync SQLAlchemy engine (psycopg2) for SQLAdmin."""
    return sa_create_engine(database_url_sync, echo=False, pool_pre_ping=True)

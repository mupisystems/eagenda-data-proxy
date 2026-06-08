"""CRUD for local custom data attached to persons or appointments."""
import logging
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_data import LocalCustomData

logger = logging.getLogger(__name__)


class CustomDataStore:
    """Service for managing custom data stored locally."""

    async def get(
        self, db: AsyncSession, entity_type: str, entity_key: str
    ) -> Optional[dict]:
        """Get custom data for an entity. Returns the data dict or None."""
        result = await db.execute(
            select(LocalCustomData).where(
                LocalCustomData.entity_type == entity_type,
                LocalCustomData.entity_key == entity_key,
            )
        )
        record = result.scalar_one_or_none()
        return record.data if record else None

    async def get_batch(
        self, db: AsyncSession, entity_type: str, entity_keys: list[str]
    ) -> dict[str, dict]:
        """Batch fetch custom data. Returns {entity_key: data}."""
        if not entity_keys:
            return {}
        result = await db.execute(
            select(LocalCustomData).where(
                LocalCustomData.entity_type == entity_type,
                LocalCustomData.entity_key.in_(entity_keys),
            )
        )
        records = result.scalars().all()
        return {r.entity_key: r.data for r in records}

    async def upsert(
        self, db: AsyncSession, entity_type: str, entity_key: str, data: dict
    ) -> dict:
        """Insert or update custom data (merge with existing)."""
        existing = await self.get(db, entity_type, entity_key)

        if existing is not None:
            merged = {**existing, **data}
        else:
            merged = data

        stmt = pg_insert(LocalCustomData).values(
            entity_type=entity_type,
            entity_key=entity_key,
            data=merged,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["entity_type", "entity_key"],
            set_={"data": merged},
        )
        await db.execute(stmt)
        await db.commit()
        return merged

    async def replace(
        self, db: AsyncSession, entity_type: str, entity_key: str, data: dict
    ) -> dict:
        """Replace custom data entirely (overwrite, not merge)."""
        stmt = pg_insert(LocalCustomData).values(
            entity_type=entity_type,
            entity_key=entity_key,
            data=data,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["entity_type", "entity_key"],
            set_={"data": data},
        )
        await db.execute(stmt)
        await db.commit()
        return data

    async def delete(
        self, db: AsyncSession, entity_type: str, entity_key: str
    ) -> bool:
        """Delete custom data for an entity."""
        result = await db.execute(
            delete(LocalCustomData).where(
                LocalCustomData.entity_type == entity_type,
                LocalCustomData.entity_key == entity_key,
            )
        )
        await db.commit()
        return result.rowcount > 0

    async def delete_all_for_entity(
        self, db: AsyncSession, entity_key: str
    ) -> int:
        """Delete all custom data for an entity key (any type). Used by erasure."""
        result = await db.execute(
            delete(LocalCustomData).where(
                LocalCustomData.entity_key == entity_key,
            )
        )
        await db.commit()
        return result.rowcount

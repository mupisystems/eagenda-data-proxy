"""Booking limit enforcement — controls appointment limits per client."""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.local_appointment import LocalAppointment

logger = logging.getLogger(__name__)

_config_cache: Optional[dict] = None
_config_mtime: float = 0


def _load_config(path: str = "booking_limits.json") -> dict:
    """Load booking limits config with file-modification caching."""
    global _config_cache, _config_mtime
    config_path = Path(path)
    if not config_path.exists():
        return {"enabled": False}

    mtime = config_path.stat().st_mtime
    if _config_cache is not None and mtime == _config_mtime:
        return _config_cache

    with open(config_path, encoding="utf-8") as f:
        _config_cache = json.load(f)
    _config_mtime = mtime
    return _config_cache


def resolve_penalty(penalties: list[dict], noshow_count: int) -> Optional[dict]:
    """Find the applicable penalty tier for a given no-show count."""
    for penalty in sorted(penalties, key=lambda p: p["from"], reverse=True):
        if noshow_count >= penalty["from"]:
            return penalty
    return None


def resolve_rule(config: dict, context: dict) -> dict:
    """
    Resolve the effective limits by merging defaults with the first matching rule.

    context can contain: service_key, location_key, tag, noshow_count
    """
    defaults = dict(config.get("defaults", {}))

    for rule in config.get("rules", []):
        match = rule.get("match", {})
        if _matches(match, context):
            merged = dict(defaults)
            for key, value in rule.items():
                if key not in ("name", "match"):
                    merged[key] = value
            return merged

    return defaults


def _matches(match: dict, context: dict) -> bool:
    """Check if a rule's match criteria applies to the given context."""
    for key, expected in match.items():
        if key.endswith("__gte"):
            field = key[:-5]
            actual = context.get(field, 0)
            if actual < expected:
                return False
        elif key.endswith("__lte"):
            field = key[:-5]
            actual = context.get(field, 0)
            if actual > expected:
                return False
        else:
            if context.get(key) != expected:
                return False
    return True


class BookingLimitDenied(Exception):
    """Raised when a booking is denied due to limit rules."""

    def __init__(self, reason: str, message: str, details: dict):
        self.reason = reason
        self.message = message
        self.details = details
        super().__init__(message)


class BookingLimiter:
    """Evaluates booking limits for a client by querying local_appointment."""

    def __init__(self, config_path: str = "booking_limits.json"):
        self.config_path = config_path

    @property
    def config(self) -> dict:
        return _load_config(self.config_path)

    async def check(
        self,
        db: AsyncSession,
        external_id: str,
        service_key: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> None:
        """
        Check if a client is allowed to book. Raises BookingLimitDenied if not.

        All counts are derived from local_appointment queries — no counters.
        """
        cfg = self.config
        if not cfg.get("enabled", False):
            return

        messages = cfg.get("messages", {})
        now = datetime.now().astimezone()

        # Count no-shows within the window (need it for rule resolution)
        defaults = cfg.get("defaults", {})
        window_days = defaults.get("noshow_window_days", 90)
        window_start = now - timedelta(days=window_days)

        noshow_count = await self._count_noshows(db, external_id, window_start)

        context = {
            "service_key": service_key,
            "tag": tag,
            "noshow_count": noshow_count,
        }
        limits = resolve_rule(cfg, context)

        # Re-read window from resolved rule (a specific rule may override it)
        rule_window = limits.get("noshow_window_days", window_days)
        if rule_window != window_days:
            window_start = now - timedelta(days=rule_window)
            noshow_count = await self._count_noshows(db, external_id, window_start)

        # 1. Check no-show penalty (block period)
        penalties = limits.get("noshow_penalties", [])
        penalty = resolve_penalty(penalties, noshow_count)
        if penalty:
            last_noshow_at = await self._last_noshow_at(db, external_id)
            if last_noshow_at:
                block_until = last_noshow_at + timedelta(days=penalty["block_days"])
                if now < block_until:
                    msg = messages.get("noshow_blocked", "Blocked due to no-shows.")
                    raise BookingLimitDenied(
                        reason="noshow_blocked",
                        message=msg.format(
                            noshow_count=noshow_count,
                            unblock_date=block_until.strftime("%d/%m/%Y"),
                        ),
                        details={
                            "noshow_count": noshow_count,
                            "block_until": block_until.isoformat(),
                        },
                    )

        # 2. Resolve effective max_future after penalty overrides
        max_future = limits.get("max_future_appointments", 3)
        if penalty and "max_future_appointments" in penalty:
            max_future = penalty["max_future_appointments"]

        # 3. Check future appointment limit
        future_count = await self._count_future(db, external_id, now)
        if future_count >= max_future:
            msg = messages.get("future_limit_reached", "Future appointment limit reached.")
            raise BookingLimitDenied(
                reason="future_limit_reached",
                message=msg.format(count=future_count, max=max_future),
                details={
                    "future_count": future_count,
                    "max_future": max_future,
                },
            )

        # 4. Check cooldown
        cooldown_minutes = limits.get("cooldown_minutes", 0)
        if cooldown_minutes:
            last_booking = await self._last_booking_at(db, external_id)
            if last_booking:
                cooldown_until = last_booking + timedelta(minutes=cooldown_minutes)
                if now < cooldown_until:
                    msg = messages.get("cooldown_active", "Cooldown active.")
                    raise BookingLimitDenied(
                        reason="cooldown_active",
                        message=msg.format(minutes=cooldown_minutes),
                        details={
                            "cooldown_until": cooldown_until.isoformat(),
                        },
                    )

    async def record_appointment(
        self,
        db: AsyncSession,
        appointment_key: str,
        external_id: str,
        service_key: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> LocalAppointment:
        """Record a new appointment locally after successful creation."""
        appt = LocalAppointment(
            appointment_key=appointment_key,
            external_id=external_id,
            service_key=service_key,
            scheduled_at=scheduled_at,
            status="scheduled",
        )
        db.add(appt)
        await db.flush()
        return appt

    async def update_status(
        self, db: AsyncSession, appointment_key: str, status: str
    ) -> Optional[LocalAppointment]:
        """Update the status of a local appointment record."""
        result = await db.execute(
            select(LocalAppointment).where(
                LocalAppointment.appointment_key == appointment_key
            )
        )
        appt = result.scalar_one_or_none()
        if appt:
            appt.status = status
            await db.flush()
        return appt

    # -- Query helpers --

    async def _count_future(
        self, db: AsyncSession, external_id: str, now: datetime
    ) -> int:
        """Count scheduled appointments in the future."""
        result = await db.execute(
            select(func.count()).where(
                LocalAppointment.external_id == external_id,
                LocalAppointment.status == "scheduled",
                LocalAppointment.scheduled_at > now,
            )
        )
        return result.scalar_one()

    async def _count_noshows(
        self, db: AsyncSession, external_id: str, since: datetime
    ) -> int:
        """Count no-shows since a given date."""
        result = await db.execute(
            select(func.count()).where(
                LocalAppointment.external_id == external_id,
                LocalAppointment.status == "noshow",
                LocalAppointment.updated_at >= since,
            )
        )
        return result.scalar_one()

    async def _last_noshow_at(
        self, db: AsyncSession, external_id: str
    ) -> Optional[datetime]:
        """Get the timestamp of the most recent no-show."""
        result = await db.execute(
            select(func.max(LocalAppointment.updated_at)).where(
                LocalAppointment.external_id == external_id,
                LocalAppointment.status == "noshow",
            )
        )
        return result.scalar_one()

    async def _last_booking_at(
        self, db: AsyncSession, external_id: str
    ) -> Optional[datetime]:
        """Get the creation timestamp of the most recent booking."""
        result = await db.execute(
            select(func.max(LocalAppointment.created_at)).where(
                LocalAppointment.external_id == external_id,
            )
        )
        return result.scalar_one()

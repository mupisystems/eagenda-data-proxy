"""CLI to issue a client proxy token.

Generates a cryptographically random bearer token, stores only its SHA-256 hash
in the ``proxy_token`` table, and prints the raw token **once** — it cannot be
recovered afterwards.

Usage::

    python -m app.auth.create_token --label "My System"
    python -m app.auth.create_token --label "ERP" --scopes people appointments --expires-days 90
"""

import argparse
import asyncio
import hashlib
import secrets

from app.config import get_settings
from app.db.engine import create_engine, create_session_factory
from app.models.proxy_token import ProxyToken


async def _create(label: str, scopes: list[str], expires_days: int | None) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    expires_at = None
    if expires_days is not None:
        from datetime import datetime, timedelta, timezone

        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as db:
            token = ProxyToken(
                token_hash=token_hash,
                label=label,
                scopes=scopes or [],
                expires_at=expires_at,
            )
            db.add(token)
            await db.commit()
    finally:
        await engine.dispose()

    return raw_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a client proxy token.")
    parser.add_argument("--label", required=True, help="Human-readable label for the token owner.")
    parser.add_argument(
        "--scopes",
        nargs="*",
        default=[],
        help="Optional list of scopes to attach to the token.",
    )
    parser.add_argument(
        "--expires-days",
        type=int,
        default=None,
        help="Optional expiry in days (default: never expires).",
    )
    args = parser.parse_args()

    raw_token = asyncio.run(_create(args.label, args.scopes, args.expires_days))

    print("Token created. Store it securely — it will not be shown again:")
    print()
    print(f"  {raw_token}")
    print()
    print(f"Use it as: Authorization: Bearer {raw_token}")


if __name__ == "__main__":
    main()

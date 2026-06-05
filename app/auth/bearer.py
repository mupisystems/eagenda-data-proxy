"""Bearer token authentication for proxy clients."""
import hashlib

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.dependencies import get_db
from app.models.proxy_token import ProxyToken

security = HTTPBearer()


async def verify_proxy_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ProxyToken:
    """Verify the client's bearer token against the proxy_token table."""
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()

    result = await db.execute(
        select(ProxyToken).where(
            ProxyToken.token_hash == token_hash,
            ProxyToken.is_active.is_(True),
            or_(
                ProxyToken.expires_at.is_(None),
                ProxyToken.expires_at > func.now(),
            ),
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Update last_used_at
    token.last_used_at = func.now()
    await db.commit()
    return token

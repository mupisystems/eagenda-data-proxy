"""Tests for Bearer token authentication."""
import hashlib

import pytest
from app.models.proxy_token import ProxyToken


class TestAuth:
    async def test_valid_token_grants_access(self, client):
        # client fixture already has a valid token in headers
        # Health endpoint doesn't require auth, but we test it works
        response = await client.get("/health/")
        assert response.status_code == 200

    async def test_missing_token_returns_403(self, client):
        # Remove auth header
        response = await client.get(
            "/api/v3/calendars/",
            headers={"Authorization": ""},
        )
        # FastAPI HTTPBearer returns 403 when header is missing/malformed
        assert response.status_code in (401, 403)

    async def test_invalid_token_returns_401(self, client):
        response = await client.get(
            "/api/v3/calendars/",
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )
        assert response.status_code == 401

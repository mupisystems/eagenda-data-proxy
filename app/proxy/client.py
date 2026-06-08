"""httpx AsyncClient lifecycle — created in app lifespan, injected via dependencies."""

import httpx


def create_http_client(timeout: int = 30) -> httpx.AsyncClient:
    """Create an async HTTP client for eagendas cloud."""
    return httpx.AsyncClient(timeout=timeout)

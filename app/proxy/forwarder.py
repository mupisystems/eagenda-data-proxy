"""Generic HTTP request forwarding to eagendas cloud."""

import logging

import httpx

logger = logging.getLogger(__name__)


class CloudForwarder:
    """Forwards requests to eagendas cloud API with Bearer token auth."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, token: str):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.auth_headers = {"Authorization": f"Bearer {token}"}

    async def forward(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """Forward an HTTP request to eagendas cloud."""
        url = f"{self.base_url}{path}"
        merged_headers = {**self.auth_headers}
        if headers:
            merged_headers.update(headers)

        logger.debug("Forwarding %s %s", method, url)

        response = await self.client.request(
            method=method,
            url=url,
            json=body,
            params=params,
            headers=merged_headers,
        )

        logger.debug("Cloud responded %s for %s %s", response.status_code, method, url)
        return response

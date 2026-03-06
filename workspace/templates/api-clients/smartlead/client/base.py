"""
Smartlead API Base Client

Provides HTTP foundation with authentication and error handling.
"""

from typing import Any
from urllib.parse import urljoin

import httpx


class SmartleadError(Exception):
    """Base exception for Smartlead API errors."""

    def __init__(
        self, message: str, status_code: int | None = None, response: Any = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class BaseClient:
    """Base client with HTTP handling for Smartlead API."""

    BASE_URL = "https://server.smartlead.ai/api/v1/"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        base_url: str | None = None,
    ):
        """
        Initialize Smartlead client.

        Args:
            api_key: Your Smartlead API key (from Settings > API)
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> Any:
        """Make authenticated request to Smartlead API."""
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        # Add API key to query params
        params = params or {}
        params["api_key"] = self.api_key

        try:
            response = self._client.request(
                method=method,
                url=url,
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            raise SmartleadError(
                message=f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
                response=e.response,
            ) from e
        except httpx.RequestError as e:
            raise SmartleadError(f"Request failed: {e}") from e

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "BaseClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncBaseClient:
    """Async base client with HTTP handling for Smartlead API."""

    BASE_URL = "https://server.smartlead.ai/api/v1/"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        base_url: str | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> Any:
        """Make authenticated request to Smartlead API."""
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        params = params or {}
        params["api_key"] = self.api_key

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            raise SmartleadError(
                message=f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
                response=e.response,
            ) from e
        except httpx.RequestError as e:
            raise SmartleadError(f"Request failed: {e}") from e

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncBaseClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

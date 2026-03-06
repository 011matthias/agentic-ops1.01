"""
Base HTTP client for ClickUp API.

Handles authentication, request building, and error handling.
"""

import httpx
from typing import Any


class ClickUpError(Exception):
    """Exception raised for ClickUp API errors."""

    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class BaseClient:
    """
    Base HTTP client for ClickUp API v2.

    Handles authentication, request building, and error handling.

    Rate limits by plan:
    - Free/Unlimited/Business: 100 requests/minute
    - Business Plus: 1,000 requests/minute
    - Enterprise: 10,000 requests/minute
    """

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(
        self,
        api_token: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the ClickUp client.

        Args:
            api_token: Personal API token (starts with 'pk_')
            access_token: OAuth access token
            timeout: Request timeout in seconds
        """
        if not api_token and not access_token:
            raise ValueError("Either api_token or access_token must be provided")

        self._token = api_token or access_token
        self._is_oauth = access_token is not None

        # Build authorization header
        if self._is_oauth:
            auth_header = f"Bearer {self._token}"
        else:
            auth_header = self._token

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> "BaseClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make an HTTP request to the ClickUp API."""
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        # Filter out None values from json body
        if json:
            json = {k: v for k, v in json.items() if v is not None}

        response = await self._client.request(
            method=method,
            url=path,
            params=params,
            json=json,
            **kwargs,
        )

        if response.status_code == 429:
            raise ClickUpError(
                "Rate limit exceeded",
                status_code=429,
                error_code="RATE_LIMIT",
            )

        if response.status_code >= 400:
            try:
                error_data = response.json()
                raise ClickUpError(
                    message=error_data.get("err", response.text),
                    status_code=response.status_code,
                    error_code=error_data.get("ECODE"),
                )
            except (ValueError, KeyError):
                raise ClickUpError(
                    message=response.text,
                    status_code=response.status_code,
                )

        if response.status_code == 204:
            return {}

        return response.json()

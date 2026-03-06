"""
Airtable Base Client - HTTP Foundation

Handles authentication, request execution, rate limiting, and error handling.
"""

import asyncio
from typing import Any, Iterator

import httpx
from pydantic import BaseModel, Field


# =============================================================================
# Configuration
# =============================================================================


class AirtableConfig(BaseModel):
    """Airtable API configuration."""

    api_key: str = Field(description="Personal access token (pat...) or API key")
    base_url: str = Field(default="https://api.airtable.com")
    timeout: float = Field(default=30.0)
    max_retries: int = Field(default=5, description="Max retries on 429 rate limit")
    retry_delay: float = Field(default=1.0, description="Base delay between retries")


# =============================================================================
# Exceptions
# =============================================================================


class AirtableError(Exception):
    """Base exception for Airtable API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_type: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(message)


class AirtableRateLimitError(AirtableError):
    """Rate limit exceeded (429)."""

    pass


class AirtableNotFoundError(AirtableError):
    """Resource not found (404)."""

    pass


class AirtableAuthError(AirtableError):
    """Authentication failed (401/403)."""

    pass


class AirtableValidationError(AirtableError):
    """Invalid request data (422)."""

    pass


# =============================================================================
# Base Client
# =============================================================================


class BaseClient:
    """
    Base Airtable client with HTTP handling.

    Provides:
    - Request execution with auth headers
    - Rate limit handling with exponential backoff
    - Error mapping to typed exceptions
    - Batch chunking helpers

    Rate limits:
    - Free/Plus: 5 requests/second per base
    - Pro: 15 requests/second per base
    - Batch operations: max 10 records per request
    """

    BASE_URL = "https://api.airtable.com"
    MAX_RECORDS_PER_BATCH = 10
    MAX_PAGE_SIZE = 100

    def __init__(self, config: AirtableConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BaseClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager."
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """
        Make an API request with retry logic for rate limits.

        Args:
            method: HTTP method (GET, POST, PATCH, PUT, DELETE)
            path: API path (e.g., /v0/{baseId}/{tableId})
            json: Request body as dict
            params: Query parameters

        Returns:
            Response JSON as dict

        Raises:
            AirtableAuthError: Invalid API key (401/403)
            AirtableNotFoundError: Resource not found (404)
            AirtableValidationError: Invalid request (422)
            AirtableRateLimitError: Rate limit exceeded after retries (429)
            AirtableError: Other API errors
        """
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        for attempt in range(self.config.max_retries + 1):
            response = await self.client.request(
                method, path, json=json, params=params
            )

            if response.status_code == 429:
                if attempt < self.config.max_retries:
                    # Exponential backoff
                    delay = self.config.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise AirtableRateLimitError(
                    "Rate limit exceeded after max retries",
                    status_code=429,
                )

            if response.status_code == 401:
                raise AirtableAuthError("Invalid API key", status_code=401)

            if response.status_code == 403:
                raise AirtableAuthError("Access denied", status_code=403)

            if response.status_code == 404:
                raise AirtableNotFoundError("Resource not found", status_code=404)

            if response.status_code == 422:
                error_data = response.json()
                raise AirtableValidationError(
                    error_data.get("error", {}).get("message", "Validation error"),
                    status_code=422,
                    error_type=error_data.get("error", {}).get("type"),
                )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise AirtableError(
                    error_data.get("error", {}).get(
                        "message", f"HTTP {response.status_code}"
                    ),
                    status_code=response.status_code,
                    error_type=error_data.get("error", {}).get("type"),
                )

            return response.json() if response.content else {}

        raise AirtableError("Request failed after retries")

    @staticmethod
    def _chunk(items: list, size: int) -> Iterator[list]:
        """Split a list into chunks of specified size."""
        for i in range(0, len(items), size):
            yield items[i : i + size]

"""
Base HTTP client for Google Sheets API.

Handles OAuth token management and authenticated requests.
Uses refresh_token from environment variables for Railway deployments.
"""

import time
from typing import Any

import httpx


class GoogleSheetsError(Exception):
    """Exception raised for Google Sheets API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class BaseClient:
    """
    Base HTTP client for Google Sheets API v4.

    Handles OAuth 2.0 authentication with automatic token refresh.

    Usage:
        async with GoogleSheetsClient(
            client_id="xxx",
            client_secret="xxx",
            refresh_token="xxx",
        ) as client:
            values = await client.get_values("spreadsheet_id", "Sheet1!A1:D10")
    """

    BASE_URL = "https://sheets.googleapis.com/v4"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        timeout: float = 30.0,
    ):
        """
        Initialize the Google Sheets client.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            refresh_token: Refresh token from OAuth setup
            timeout: Request timeout in seconds
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._timeout = timeout

        # Token state
        self._access_token: str | None = None
        self._token_expiry: float = 0

        # HTTP client (created on enter)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BaseClient":
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_token(self) -> str:
        """
        Ensure we have a valid access token.

        Refreshes the token if it's expired or about to expire (within 60s).
        """
        # Check if token is still valid (with 60s buffer)
        if self._access_token and time.time() < (self._token_expiry - 60):
            return self._access_token

        # Refresh the token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
            )

        if response.status_code != 200:
            error_data = response.json()
            raise GoogleSheetsError(
                message=f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}",
                status_code=response.status_code,
                error_code=error_data.get("error"),
            )

        token_data = response.json()
        self._access_token = token_data["access_token"]
        # Google access tokens expire in 3600 seconds (1 hour)
        self._token_expiry = time.time() + token_data.get("expires_in", 3600)

        return self._access_token

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make an authenticated HTTP request to the Google Sheets API.

        Automatically refreshes the access token if needed.
        Retries once on 401 (token might have been revoked/expired).
        """
        if not self._client:
            raise GoogleSheetsError("Client not initialized. Use 'async with' context manager.")

        # Get valid access token
        token = await self._ensure_token()

        # Filter out None values
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        if json:
            json = {k: v for k, v in json.items() if v is not None}

        # Make request
        response = await self._client.request(
            method=method,
            url=path,
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )

        # Handle 401 - try refreshing token once
        if response.status_code == 401:
            self._access_token = None  # Force refresh
            token = await self._ensure_token()
            response = await self._client.request(
                method=method,
                url=path,
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
                **kwargs,
            )

        # Handle rate limiting
        if response.status_code == 429:
            raise GoogleSheetsError(
                "Rate limit exceeded. Google Sheets API allows 60 read/60 write requests per minute per user.",
                status_code=429,
                error_code="RATE_LIMIT_EXCEEDED",
            )

        # Handle errors
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_info = error_data.get("error", {})
                raise GoogleSheetsError(
                    message=error_info.get("message", response.text),
                    status_code=response.status_code,
                    error_code=error_info.get("status"),
                )
            except (ValueError, KeyError):
                raise GoogleSheetsError(
                    message=response.text,
                    status_code=response.status_code,
                )

        # Handle empty response
        if response.status_code == 204:
            return {}

        return response.json()

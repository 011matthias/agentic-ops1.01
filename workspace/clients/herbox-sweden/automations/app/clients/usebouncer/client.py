# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///

"""
Usebouncer API client for email verification.

API Reference:
- Verify Email: https://api.usebouncer.com/v1.1/email/verify
"""

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

USEBOUNCER_API_URL = "https://api.usebouncer.com"


class UsebouncerClient:
    """
    Async Usebouncer API client.

    Usage:
        client = UsebouncerClient(api_key="...")
        result = await client.verify("john@example.com")
        # Returns: {"status": "deliverable", "score": 0.9, ...}
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=USEBOUNCER_API_URL,
                headers={
                    "X-API-Key": self.api_key,
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def verify(self, email: str) -> dict[str, Any]:
        """
        Verify email deliverability.

        Args:
            email: Email address to verify

        Returns:
            Dict with keys:
                - status: str (e.g., "deliverable", "undeliverable", "risky")
                - score: float (0.0 to 1.0 confidence)
                - reason: str (explanation of status)
                - ... (other Usebouncer fields)
        """
        client = await self._get_client()

        logger.info(f"Usebouncer verify: {email}")

        try:
            response = await client.get(
                "/v1.1/email/verify",
                params={"email": email},
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"Verification result: {data.get('status')} (score: {data.get('score')})")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Usebouncer API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                raise ValueError("Invalid Usebouncer API key") from e
            if e.response.status_code == 429:
                logger.warning("Usebouncer rate limit exceeded")
            # Return error status on failure
            return {"status": "unknown", "score": 0.0, "error": str(e)}

        except httpx.RequestError as e:
            logger.error(f"Usebouncer request error: {e}")
            return {"status": "unknown", "score": 0.0, "error": str(e)}

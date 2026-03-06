# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///

"""
Trykitt API client for email enrichment.

API Reference:
- Find Email: https://api.trykitt.ai/job/find_email
"""

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

TRYKITT_API_URL = "https://api.trykitt.ai"


class TrykittClient:
    """
    Async Trykitt API client.

    Usage:
        client = TrykittClient(api_key="...")
        email = await client.find_email("John Doe", "example.com", linkedin_url="...")
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=TRYKITT_API_URL,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def find_email(
        self,
        full_name: str,
        domain: str | None = None,
        linkedin_url: str | None = None,
        realtime: bool = True,
    ) -> dict[str, Any]:
        """
        Find email using name and optionally domain or LinkedIn.

        Args:
            full_name: Full name (e.g., "John Doe")
            domain: Company domain (e.g., "example.com")
            linkedin_url: LinkedIn profile URL
            realtime: Whether to use realtime processing

        Returns:
            Dict with "email" key (str | null) or "no-results-found"
        """
        client = await self._get_client()

        payload = {
            "fullName": full_name,
            "realtime": realtime,
        }

        if domain:
            payload["domain"] = domain
        if linkedin_url:
            payload["linkedinStandardProfileURL"] = linkedin_url

        logger.info(f"Trykitt find_email: {full_name}")

        try:
            response = await client.post(
                "/job/find_email",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            email = data.get("email")
            if email and email != "no-results-found":
                logger.info(f"Email found: {email}")
            else:
                logger.info(f"No email found: {email}")

            return data

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Trykitt API error: {e.response.status_code} - {error_text}")

            # 402 = No credits / Free tier busy, skip gracefully
            if e.response.status_code == 402:
                logger.warning("Trykitt: No credits available, skipping enrichment")
                return {"email": None, "skipped": "no_credits"}

            if e.response.status_code == 401:
                raise ValueError("Invalid Trykitt API key") from e
            if e.response.status_code == 429:
                logger.warning("Trykitt rate limit exceeded")

            return {"email": None, "error": str(e)}

        except httpx.RequestError as e:
            logger.error(f"Trykitt request error: {e}")
            return {"email": None, "error": str(e)}

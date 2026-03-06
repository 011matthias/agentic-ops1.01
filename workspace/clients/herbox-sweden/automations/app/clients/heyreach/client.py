"""
Heyreach API client for LinkedIn campaign integration.

API Reference: https://docs.heyreach.com/ (TBD)
Rate Limit: TBD
"""

import httpx
import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

HEYREACH_API_URL = "https://api.heyreach.com/v1"


class AddedLead(BaseModel):
    """Result of adding a lead to a campaign."""
    lead_id: str
    campaign_id: str
    status: str


class HeyreachClient:
    """
    Async Heyreach API client for LinkedIn outreach.

    Usage:
        client = HeyreachClient(api_key="hr_...")
        result = await client.add_lead_to_campaign(
            campaign_id="camp_123",
            linkedin_url="https://linkedin.com/in/john-doe"
        )
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=HEYREACH_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        retries: int = 3,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        for attempt in range(retries):
            try:
                response = await client.request(
                    method,
                    endpoint,
                    json=json,
                    params=params,
                )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Heyreach API error: {e.response.status_code} - {e.response.text}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as e:
                logger.error(f"Heyreach request error: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Max retries exceeded")

    async def add_lead_to_campaign(
        self,
        campaign_id: str,
        linkedin_url: str,
    ) -> AddedLead | None:
        """
        Add a lead to a LinkedIn campaign.

        Args:
            campaign_id: The Heyreach campaign ID
            linkedin_url: LinkedIn profile URL of the lead

        Returns:
            AddedLead with lead_id, campaign_id, and status, or None on failure
        """
        logger.info(f"Adding lead to Heyreach campaign {campaign_id}")

        try:
            # Note: Endpoint structure is TBD pending API documentation
            # This is a placeholder implementation
            response = await self._request(
                "POST",
                f"/campaigns/{campaign_id}/leads",
                json={
                    "linkedin_url": linkedin_url,
                },
            )

            return AddedLead(
                lead_id=response.get("id", ""),
                campaign_id=campaign_id,
                status=response.get("status", "added"),
            )

        except Exception as e:
            logger.error(f"Failed to add lead to Heyreach campaign: {e}")
            # Return None to make this non-blocking
            return None

    async def get_campaigns(self) -> list[dict[str, Any]]:
        """
        Get list of available campaigns.

        Returns:
            List of campaign dictionaries
        """
        logger.info("Fetching Heyreach campaigns")

        try:
            response = await self._request("GET", "/campaigns")
            return response.get("campaigns", [])

        except Exception as e:
            logger.error(f"Failed to fetch campaigns: {e}")
            return []


# Import at module level for retry logic
import asyncio

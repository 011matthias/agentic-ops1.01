"""
Smartlead API client with rate limiting and retry logic.

API Reference: https://api.smartlead.ai/reference
Rate Limit: ~5 requests per second
"""

import httpx
import asyncio
import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

SMARTLEAD_API_URL = "https://server.smartlead.ai/api/v1"


class CampaignLeadStats(BaseModel):
    """Campaign lead statistics."""
    total: int = 0
    inprogress: int = 0
    completed: int = 0
    interested: int = 0
    notStarted: int = 0


class CampaignAnalytics(BaseModel):
    """Campaign analytics data from Smartlead."""
    id: int
    name: str
    status: str
    campaign_lead_stats: CampaignLeadStats
    unique_sent_count: int = 0
    sent_count: int = 0
    open_count: int = 0
    reply_count: int = 0
    bounce_count: int = 0
    sequence_count: int = 0


class CampaignListItem(BaseModel):
    """Campaign item from campaign list endpoint."""
    id: int
    name: str | None = None
    status: str | None = None


class SmartleadClient:
    """
    Async Smartlead API client.

    Usage:
        client = SmartleadClient(api_key="sl_...")
        campaigns = await client.get_campaign_list()
        stats = await client.get_campaign_analytics(campaign_id)
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_delay = 0.2  # 5 req/sec = 200ms between requests

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=SMARTLEAD_API_URL,
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
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        retries: int = 5,
    ) -> dict:
        """Make API request with rate limiting and retry."""
        client = await self._get_client()

        # Add API key to query params
        request_params = params.copy() if params else {}
        request_params["api_key"] = self.api_key

        for attempt in range(retries):
            try:
                # Rate limiting
                await asyncio.sleep(self._rate_limit_delay)

                response = await client.request(
                    method,
                    path,
                    json=json,
                    params=request_params,
                )

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", 30))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Smartlead API error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 401:
                    raise ValueError("Invalid Smartlead API key") from e
                if attempt == retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s (attempt {attempt + 1}/{retries})")
                await asyncio.sleep(wait_time)

            except httpx.RequestError as e:
                logger.error(f"Smartlead request error: {e}")
                if attempt == retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s (attempt {attempt + 1}/{retries})")
                await asyncio.sleep(wait_time)

        raise RuntimeError("Max retries exceeded")

    async def get_campaign_list(self, include_drafts: bool = True) -> list[CampaignListItem]:
        """
        Get list of all campaigns.

        Args:
            include_drafts: If True, include draft campaigns. Default True.

        Returns:
            List of campaigns with basic info (id, name, status)
        """
        logger.info("Fetching campaign list from Smartlead")
        # Use /campaigns endpoint which returns all campaigns including drafts
        data = await self._request("GET", "/campaigns")

        campaigns: list[CampaignListItem] = []

        # Response is a list directly (not nested in data.campaign_list)
        campaign_list = data if isinstance(data, list) else data.get("data", data)
        if isinstance(campaign_list, dict):
            campaign_list = campaign_list.get("campaign_list", [])

        for campaign in campaign_list:
            status = campaign.get("status")
            # Filter out drafts if not requested
            if not include_drafts and status and status.upper() == "DRAFTED":
                continue
            campaigns.append(CampaignListItem(
                id=campaign["id"],
                name=campaign.get("name"),
                status=status,
            ))

        logger.info(f"Found {len(campaigns)} campaigns (include_drafts={include_drafts})")
        return campaigns

    async def get_campaign_analytics(self, campaign_id: int) -> CampaignAnalytics:
        """
        Get detailed analytics for a specific campaign.

        Args:
            campaign_id: Smartlead campaign ID

        Returns:
            CampaignAnalytics with full stats
        """
        logger.info(f"Fetching analytics for campaign {campaign_id}")
        data = await self._request("GET", f"/campaigns/{campaign_id}/analytics")

        # Parse campaign lead stats
        lead_stats_data = data.get("campaign_lead_stats", {})
        lead_stats = CampaignLeadStats(
            total=lead_stats_data.get("total", 0),
            inprogress=lead_stats_data.get("inprogress", 0),
            completed=lead_stats_data.get("completed", 0),
            interested=lead_stats_data.get("interested", 0),
            notStarted=lead_stats_data.get("notStarted", 0),
        )

        return CampaignAnalytics(
            id=data.get("id", campaign_id),
            name=data.get("name", ""),
            status=data.get("status", ""),
            campaign_lead_stats=lead_stats,
            unique_sent_count=data.get("unique_sent_count", 0),
            sent_count=data.get("sent_count", 0),
            open_count=data.get("open_count", 0),
            reply_count=data.get("reply_count", 0),
            bounce_count=data.get("bounce_count", 0),
            sequence_count=data.get("sequence_count", 0),
        )

    async def add_leads_to_campaign(
        self,
        campaign_id: int,
        leads: list[dict[str, Any]],
        *,
        ignore_global_block_list: bool = False,
        ignore_unsubscribe_list: bool = False,
        ignore_community_bounce_list: bool = False,
        ignore_duplicate_leads_in_other_campaign: bool = False,
        return_lead_ids: bool = True,
    ) -> dict[str, Any]:
        """
        Add leads to a Smartlead campaign.

        Args:
            campaign_id: Smartlead campaign ID
            leads: List of lead dictionaries with fields:
                - first_name: str
                - last_name: str
                - email: str
                - company_name: str (optional)
                - website: str (optional)
                - location: str (optional)
                - custom_fields: dict (optional)
                - linkedin_profile: str (optional)
            ignore_global_block_list: Skip global block list check
            ignore_unsubscribe_list: Skip unsubscribe list check
            ignore_community_bounce_list: Skip community bounce list check
            ignore_duplicate_leads_in_other_campaign: Allow duplicates
            return_lead_ids: Return lead IDs in response

        Returns:
            Response with lead_ids array if return_lead_ids=True

        API Reference: https://api.smartlead.ai/reference/add-leads-to-campaign
        """
        logger.info(f"Adding {len(leads)} leads to campaign {campaign_id}")

        payload = {
            "lead_list": leads,
            "settings": {
                "ignore_global_block_list": ignore_global_block_list,
                "ignore_unsubscribe_list": ignore_unsubscribe_list,
                "ignore_community_bounce_list": ignore_community_bounce_list,
                "ignore_duplicate_leads_in_other_campaign": ignore_duplicate_leads_in_other_campaign,
                "return_lead_ids": return_lead_ids,
            },
        }

        return await self._request(
            "POST",
            f"/campaigns/{campaign_id}/leads",
            json=payload,
        )

    async def create_campaign(
        self,
        name: str,
        *,
        from_email: str | None = None,
        from_name: str | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new Smartlead campaign (for testing purposes).

        Args:
            name: Campaign name
            from_email: Default sender email (optional)
            from_name: Default sender name (optional)
            reply_to: Reply-to email (optional)

        Returns:
            Created campaign data with campaign ID

        API Reference: https://api.smartlead.ai/reference/create-campaign

        Note: Status cannot be set during creation. New campaigns start
        in "draft" status by default.
        """
        logger.info(f"Creating campaign: {name}")

        payload = {"name": name}

        if from_email:
            payload["default_from_email"] = from_email
        if from_name:
            payload["default_from_name"] = from_name
        if reply_to:
            payload["default_reply_to"] = reply_to

        return await self._request(
            "POST",
            "/campaigns/create",
            json=payload,
        )

    async def delete_campaign(self, campaign_id: int) -> dict[str, Any]:
        """
        Delete a Smartlead campaign.

        Args:
            campaign_id: Smartlead campaign ID to delete

        Returns:
            Deletion response

        API Reference: https://api.smartlead.ai/reference/delete-campaign
        """
        logger.info(f"Deleting campaign {campaign_id}")

        return await self._request(
            "DELETE",
            f"/campaigns/{campaign_id}",
        )

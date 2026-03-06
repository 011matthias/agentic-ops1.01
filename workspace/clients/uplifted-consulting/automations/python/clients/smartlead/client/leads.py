"""
Smartlead Leads Mixin

Endpoints for managing leads in campaigns.
"""

from typing import TYPE_CHECKING, Any

from ..models import Lead, LeadCreate

if TYPE_CHECKING:
    from .base import AsyncBaseClient, BaseClient


class LeadsMixin:
    """Mixin for lead operations."""

    def list_leads_by_campaign(
        self: "BaseClient",
        campaign_id: int,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Lead]:
        """
        List all leads in a campaign.

        Args:
            campaign_id: The campaign ID
            offset: Pagination offset
            limit: Number of leads to return

        Returns:
            List of leads
        """
        data = self._request(
            "GET",
            f"/campaigns/{campaign_id}/leads",
            params={"offset": offset, "limit": limit},
        )
        if isinstance(data, list):
            return [Lead.model_validate(item) for item in data]
        return []

    def add_leads_to_campaign(
        self: "BaseClient",
        campaign_id: int,
        leads: list[dict[str, Any] | LeadCreate],
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Add leads to a campaign.

        Args:
            campaign_id: The campaign ID
            leads: List of lead data dictionaries or LeadCreate objects
            settings: Optional import settings

        Returns:
            Response with import results
        """
        lead_list = [
            lead.model_dump(exclude_none=True) if isinstance(lead, LeadCreate) else lead
            for lead in leads
        ]
        payload: dict[str, Any] = {"lead_list": lead_list}
        if settings:
            payload["settings"] = settings

        return self._request("POST", f"/campaigns/{campaign_id}/leads", json=payload)

    def get_global_leads(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
    ) -> list[Lead]:
        """
        Fetch all leads from entire account.

        Args:
            offset: Pagination offset
            limit: Number of leads to return

        Returns:
            List of all leads
        """
        data = self._request(
            "GET",
            "/leads/global-leads",
            params={"offset": offset, "limit": limit},
        )
        if isinstance(data, list):
            return [Lead.model_validate(item) for item in data]
        return []

    def get_lead_by_email(self: "BaseClient", email: str) -> Lead | None:
        """
        Fetch a lead by email address.

        Args:
            email: Lead email address

        Returns:
            Lead data or None if not found
        """
        data = self._request("GET", "/leads/", params={"email": email})
        if data:
            return Lead.model_validate(data)
        return None

    def get_lead_message_history(
        self: "BaseClient", campaign_id: int, lead_id: int
    ) -> list[dict[str, Any]]:
        """
        Fetch lead message history for a specific campaign.

        Args:
            campaign_id: The campaign ID
            lead_id: The lead ID

        Returns:
            Message history
        """
        return self._request(
            "GET",
            f"/campaigns/{campaign_id}/leads/{lead_id}/message-history",
        )

    def get_lead_statistics(self: "BaseClient", campaign_id: int) -> dict[str, Any]:
        """
        Fetch lead statistics for a campaign.

        Args:
            campaign_id: The campaign ID

        Returns:
            Lead statistics
        """
        return self._request("GET", f"/campaigns/{campaign_id}/lead-statistics")

    def get_lead_sequence_details(
        self: "BaseClient", campaign_id: int, lead_id: int
    ) -> dict[str, Any]:
        """
        Get sequence details for a specific lead.

        Args:
            campaign_id: The campaign ID
            lead_id: The lead ID

        Returns:
            Sequence details
        """
        return self._request(
            "GET", f"/campaigns/{campaign_id}/leads/{lead_id}/sequence-details"
        )

    def resume_lead(
        self: "BaseClient", campaign_id: int, lead_id: int
    ) -> dict[str, Any]:
        """
        Resume a paused lead in a campaign.

        Args:
            campaign_id: The campaign ID
            lead_id: The lead ID

        Returns:
            Response data
        """
        return self._request(
            "POST", f"/campaigns/{campaign_id}/leads/{lead_id}/resume"
        )


class AsyncLeadsMixin:
    """Async mixin for lead operations."""

    async def list_leads_by_campaign(
        self: "AsyncBaseClient", campaign_id: int, offset: int = 0, limit: int = 100
    ) -> list[Lead]:
        data = await self._request(
            "GET",
            f"/campaigns/{campaign_id}/leads",
            params={"offset": offset, "limit": limit},
        )
        return (
            [Lead.model_validate(item) for item in data]
            if isinstance(data, list)
            else []
        )

    async def add_leads_to_campaign(
        self: "AsyncBaseClient",
        campaign_id: int,
        leads: list[dict[str, Any] | LeadCreate],
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        lead_list = [
            lead.model_dump(exclude_none=True) if isinstance(lead, LeadCreate) else lead
            for lead in leads
        ]
        payload: dict[str, Any] = {"lead_list": lead_list}
        if settings:
            payload["settings"] = settings
        return await self._request(
            "POST", f"/campaigns/{campaign_id}/leads", json=payload
        )

    async def get_global_leads(
        self: "AsyncBaseClient", offset: int = 0, limit: int = 100
    ) -> list[Lead]:
        data = await self._request(
            "GET", "/leads/global-leads", params={"offset": offset, "limit": limit}
        )
        return (
            [Lead.model_validate(item) for item in data]
            if isinstance(data, list)
            else []
        )

    async def get_lead_by_email(self: "AsyncBaseClient", email: str) -> Lead | None:
        data = await self._request("GET", "/leads/", params={"email": email})
        return Lead.model_validate(data) if data else None

    async def get_lead_message_history(
        self: "AsyncBaseClient", campaign_id: int, lead_id: int
    ) -> list[dict[str, Any]]:
        return await self._request(
            "GET", f"/campaigns/{campaign_id}/leads/{lead_id}/message-history"
        )

    async def get_lead_statistics(
        self: "AsyncBaseClient", campaign_id: int
    ) -> dict[str, Any]:
        return await self._request("GET", f"/campaigns/{campaign_id}/lead-statistics")

    async def get_lead_sequence_details(
        self: "AsyncBaseClient", campaign_id: int, lead_id: int
    ) -> dict[str, Any]:
        return await self._request(
            "GET", f"/campaigns/{campaign_id}/leads/{lead_id}/sequence-details"
        )

    async def resume_lead(
        self: "AsyncBaseClient", campaign_id: int, lead_id: int
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/campaigns/{campaign_id}/leads/{lead_id}/resume"
        )

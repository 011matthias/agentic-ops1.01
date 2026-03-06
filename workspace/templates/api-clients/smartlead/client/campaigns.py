"""
Smartlead Campaigns Mixin

Endpoints for managing campaigns, sequences, and campaign settings.
"""

from typing import TYPE_CHECKING, Any

from ..models import CampaignSettings, CampaignStats, SequenceStep

if TYPE_CHECKING:
    from .base import AsyncBaseClient, BaseClient


class CampaignsMixin:
    """Mixin for campaign operations."""

    def get_campaign_statistics(self: "BaseClient", campaign_id: int) -> CampaignStats:
        """
        Fetch campaign statistics by campaign ID.

        Args:
            campaign_id: The campaign ID

        Returns:
            Campaign statistics
        """
        data = self._request("GET", f"/campaigns/{campaign_id}/statistics")
        return CampaignStats.model_validate(data)

    def update_campaign_settings(
        self: "BaseClient", campaign_id: int, settings: CampaignSettings
    ) -> dict[str, Any]:
        """
        Update campaign general settings.

        Args:
            campaign_id: The campaign ID
            settings: Updated settings

        Returns:
            Response data
        """
        return self._request(
            "PATCH",
            f"/campaigns/{campaign_id}/settings",
            json=settings.model_dump(exclude_none=True),
        )

    def save_campaign_sequences(
        self: "BaseClient", campaign_id: int, sequences: list[SequenceStep]
    ) -> dict[str, Any]:
        """
        Save campaign email sequences.

        Args:
            campaign_id: The campaign ID
            sequences: List of sequence steps with variants

        Returns:
            Response data

        Note:
            - Pass id to update existing sequence, omit to create new
            - Empty array deletes all sequences and associated analytics
        """
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/sequences",
            json=[s.model_dump(exclude_none=True) for s in sequences],
        )

    def get_campaign_sequence_analytics(
        self: "BaseClient", campaign_id: int
    ) -> dict[str, Any]:
        """
        Get analytics for campaign sequences.

        Args:
            campaign_id: The campaign ID

        Returns:
            Sequence analytics data
        """
        return self._request("GET", f"/campaigns/{campaign_id}/sequences/analytics")

    def get_campaign_mailbox_statistics(
        self: "BaseClient", campaign_id: int
    ) -> dict[str, Any]:
        """
        Fetch mailbox statistics for a campaign.

        Args:
            campaign_id: The campaign ID

        Returns:
            Mailbox statistics
        """
        return self._request("GET", f"/campaigns/{campaign_id}/mailbox-statistics")

    def get_campaign_top_level_analytics(
        self: "BaseClient", campaign_id: int
    ) -> dict[str, Any]:
        """
        Fetch top level analytics for a campaign.

        Args:
            campaign_id: The campaign ID

        Returns:
            Top level analytics
        """
        return self._request("GET", f"/campaigns/{campaign_id}/analytics")


class AsyncCampaignsMixin:
    """Async mixin for campaign operations."""

    async def get_campaign_statistics(
        self: "AsyncBaseClient", campaign_id: int
    ) -> CampaignStats:
        data = await self._request("GET", f"/campaigns/{campaign_id}/statistics")
        return CampaignStats.model_validate(data)

    async def update_campaign_settings(
        self: "AsyncBaseClient", campaign_id: int, settings: CampaignSettings
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/campaigns/{campaign_id}/settings",
            json=settings.model_dump(exclude_none=True),
        )

    async def save_campaign_sequences(
        self: "AsyncBaseClient", campaign_id: int, sequences: list[SequenceStep]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/campaigns/{campaign_id}/sequences",
            json=[s.model_dump(exclude_none=True) for s in sequences],
        )

    async def get_campaign_sequence_analytics(
        self: "AsyncBaseClient", campaign_id: int
    ) -> dict[str, Any]:
        return await self._request(
            "GET", f"/campaigns/{campaign_id}/sequences/analytics"
        )

    async def get_campaign_mailbox_statistics(
        self: "AsyncBaseClient", campaign_id: int
    ) -> dict[str, Any]:
        return await self._request(
            "GET", f"/campaigns/{campaign_id}/mailbox-statistics"
        )

    async def get_campaign_top_level_analytics(
        self: "AsyncBaseClient", campaign_id: int
    ) -> dict[str, Any]:
        return await self._request("GET", f"/campaigns/{campaign_id}/analytics")

"""
Smartlead Subsequences Mixin

Endpoints for managing campaign subsequences.
"""

from typing import TYPE_CHECKING, Any

from ..models import SequenceStep

if TYPE_CHECKING:
    from .base import AsyncBaseClient, BaseClient


class SubsequencesMixin:
    """Mixin for subsequence operations."""

    def create_subsequence(
        self: "BaseClient",
        campaign_id: int,
        name: str,
        trigger_condition: str,
        sequences: list[SequenceStep],
    ) -> dict[str, Any]:
        """
        Create a subsequence for a campaign.

        Args:
            campaign_id: The campaign ID
            name: Subsequence name
            trigger_condition: When to trigger the subsequence
            sequences: Sequence steps

        Returns:
            Created subsequence data
        """
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/subsequence",
            json={
                "name": name,
                "trigger_condition": trigger_condition,
                "sequences": [s.model_dump(exclude_none=True) for s in sequences],
            },
        )

    def push_lead_to_subsequence(
        self: "BaseClient",
        campaign_id: int,
        lead_id: int,
        subsequence_id: int,
    ) -> dict[str, Any]:
        """
        Push a lead to a subsequence.

        Args:
            campaign_id: The campaign ID
            lead_id: The lead ID
            subsequence_id: The subsequence ID

        Returns:
            Response data
        """
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/leads/{lead_id}/subsequence/{subsequence_id}",
        )

    def get_subsequences(
        self: "BaseClient",
        campaign_id: int,
    ) -> list[dict[str, Any]]:
        """
        Get all subsequences for a campaign.

        Args:
            campaign_id: The campaign ID

        Returns:
            List of subsequences
        """
        data = self._request("GET", f"/campaigns/{campaign_id}/subsequences")
        return data if isinstance(data, list) else []


class AsyncSubsequencesMixin:
    """Async mixin for subsequence operations."""

    async def create_subsequence(
        self: "AsyncBaseClient",
        campaign_id: int,
        name: str,
        trigger_condition: str,
        sequences: list[SequenceStep],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/campaigns/{campaign_id}/subsequence",
            json={
                "name": name,
                "trigger_condition": trigger_condition,
                "sequences": [s.model_dump(exclude_none=True) for s in sequences],
            },
        )

    async def push_lead_to_subsequence(
        self: "AsyncBaseClient",
        campaign_id: int,
        lead_id: int,
        subsequence_id: int,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/campaigns/{campaign_id}/leads/{lead_id}/subsequence/{subsequence_id}",
        )

    async def get_subsequences(
        self: "AsyncBaseClient",
        campaign_id: int,
    ) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/campaigns/{campaign_id}/subsequences")
        return data if isinstance(data, list) else []

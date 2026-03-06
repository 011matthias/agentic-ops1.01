"""
Smartlead Analytics Mixin

Endpoints for fetching analytics and statistics.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import AsyncBaseClient, BaseClient


class AnalyticsMixin:
    """Mixin for analytics operations."""

    def get_overall_stats(self: "BaseClient") -> dict[str, Any]:
        """
        Get overall account statistics.

        Returns:
            Overall stats data
        """
        return self._request("GET", "/analytics/overall-stats-v2")

    def get_campaign_analytics(
        self: "BaseClient",
        campaign_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get analytics for a specific campaign.

        Args:
            campaign_id: The campaign ID
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            Campaign analytics
        """
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self._request(
            "GET",
            f"/analytics/campaign/{campaign_id}",
            params=params if params else None,
        )

    def get_campaign_overall_stats(
        self: "BaseClient",
        campaign_ids: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get overall stats for campaigns.

        Args:
            campaign_ids: Optional list of campaign IDs to filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            Campaign overall stats
        """
        params: dict[str, Any] = {}
        if campaign_ids:
            params["campaign_ids"] = ",".join(str(id) for id in campaign_ids)
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self._request(
            "GET",
            "/analytics/campaign-overall-stats",
            params=params if params else None,
        )

    def get_campaign_response_stats(
        self: "BaseClient",
        campaign_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Get response statistics for campaigns.

        Args:
            campaign_ids: Optional list of campaign IDs to filter

        Returns:
            Response stats
        """
        params: dict[str, Any] = {}
        if campaign_ids:
            params["campaign_ids"] = ",".join(str(id) for id in campaign_ids)

        return self._request(
            "GET",
            "/analytics/campaign-response-stats",
            params=params if params else None,
        )

    def get_campaign_status_stats(
        self: "BaseClient",
        campaign_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Get status statistics for campaigns.

        Args:
            campaign_ids: Optional list of campaign IDs to filter

        Returns:
            Status stats
        """
        params: dict[str, Any] = {}
        if campaign_ids:
            params["campaign_ids"] = ",".join(str(id) for id in campaign_ids)

        return self._request(
            "GET",
            "/analytics/campaign-status-stats",
            params=params if params else None,
        )

    def get_follow_up_reply_rate(
        self: "BaseClient",
        campaign_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Get follow-up reply rate analytics.

        Args:
            campaign_ids: Optional list of campaign IDs to filter

        Returns:
            Follow-up reply rate data
        """
        params: dict[str, Any] = {}
        if campaign_ids:
            params["campaign_ids"] = ",".join(str(id) for id in campaign_ids)

        return self._request(
            "GET",
            "/analytics/campaign-follow-up-reply-rate",
            params=params if params else None,
        )

    def get_lead_to_reply_time(
        self: "BaseClient",
        campaign_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Get lead to reply time analytics.

        Args:
            campaign_ids: Optional list of campaign IDs to filter

        Returns:
            Lead to reply time data
        """
        params: dict[str, Any] = {}
        if campaign_ids:
            params["campaign_ids"] = ",".join(str(id) for id in campaign_ids)

        return self._request(
            "GET",
            "/analytics/campaign-lead-to-reply-time",
            params=params if params else None,
        )

    def get_mailbox_health_metrics(self: "BaseClient") -> dict[str, Any]:
        """
        Get domain-wise mailbox health metrics.

        Returns:
            Health metrics by domain
        """
        return self._request("GET", "/analytics/mailbox-domain-wise-health-metrics")

    def get_mailbox_name_health_metrics(self: "BaseClient") -> dict[str, Any]:
        """
        Get email-id-wise mailbox health metrics.

        Returns:
            Health metrics by email
        """
        return self._request("GET", "/analytics/mailbox-name-wise-health-metrics")

    def get_mailbox_overall_stats(self: "BaseClient") -> dict[str, Any]:
        """
        Get overall mailbox statistics.

        Returns:
            Mailbox stats
        """
        return self._request("GET", "/analytics/mailbox-overall-stats")

    def get_provider_performance(self: "BaseClient") -> dict[str, Any]:
        """
        Get provider-wise overall performance.

        Returns:
            Provider performance data
        """
        return self._request(
            "GET", "/analytics/mailbox-provider-wise-overall-performance"
        )

    def get_lead_overall_stats(self: "BaseClient") -> dict[str, Any]:
        """
        Get overall lead statistics.

        Returns:
            Lead stats data
        """
        return self._request("GET", "/analytics/lead-overall-stats")

    def get_lead_category_response(self: "BaseClient") -> dict[str, Any]:
        """
        Get lead category-wise response analytics.

        Returns:
            Category response data
        """
        return self._request("GET", "/analytics/lead-category-wise-response")

    def get_day_wise_stats(
        self: "BaseClient",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get day-wise overall statistics.

        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            Day-wise stats
        """
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self._request(
            "GET",
            "/analytics/day-wise-overall-stats",
            params=params if params else None,
        )

    def get_day_wise_positive_reply_stats(
        self: "BaseClient",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get day-wise positive reply statistics.

        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            Day-wise positive reply stats
        """
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self._request(
            "GET",
            "/analytics/day-wise-positive-reply-stats",
            params=params if params else None,
        )

    def get_client_list(self: "BaseClient") -> dict[str, Any]:
        """
        Get list of clients (for agency accounts).

        Returns:
            Client list
        """
        return self._request("GET", "/analytics/client-list")

    def get_client_overall_stats(self: "BaseClient") -> dict[str, Any]:
        """
        Get overall client statistics.

        Returns:
            Client stats
        """
        return self._request("GET", "/analytics/client-overall-stats")

    def get_team_board_stats(self: "BaseClient") -> dict[str, Any]:
        """
        Get team board overall statistics.

        Returns:
            Team board stats
        """
        return self._request("GET", "/analytics/team-board-overall-stats")


class AsyncAnalyticsMixin:
    """Async mixin for analytics operations."""

    async def get_overall_stats(self: "AsyncBaseClient") -> dict[str, Any]:
        return await self._request("GET", "/analytics/overall-stats-v2")

    async def get_campaign_analytics(
        self: "AsyncBaseClient",
        campaign_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._request(
            "GET",
            f"/analytics/campaign/{campaign_id}",
            params=params if params else None,
        )

    async def get_mailbox_health_metrics(self: "AsyncBaseClient") -> dict[str, Any]:
        return await self._request(
            "GET", "/analytics/mailbox-domain-wise-health-metrics"
        )

    async def get_lead_overall_stats(self: "AsyncBaseClient") -> dict[str, Any]:
        return await self._request("GET", "/analytics/lead-overall-stats")

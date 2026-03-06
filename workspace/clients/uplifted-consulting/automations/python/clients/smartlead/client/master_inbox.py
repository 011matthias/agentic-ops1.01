"""
Smartlead Master Inbox Mixin

Endpoints for managing replies, inbox, and lead interactions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..models import InboxLead

if TYPE_CHECKING:
    from .base import AsyncBaseClient, BaseClient


class MasterInboxMixin:
    """Mixin for master inbox operations."""

    def get_inbox_replies(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
        campaign_id: int | None = None,
        sort_by: str | None = None,
    ) -> list[InboxLead]:
        """
        Fetch all leads that have replied to email campaigns.

        Args:
            offset: Pagination offset
            limit: Number of results to return
            campaign_id: Optional filter by campaign
            sort_by: Sort order (e.g., LAST_REPLY_TIME_DESC)

        Returns:
            List of inbox leads with reply history
        """
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if campaign_id:
            params["campaign_id"] = campaign_id
        if sort_by:
            params["sortBy"] = sort_by

        data = self._request("POST", "/master-inbox/inbox-replies", json=params)
        if isinstance(data, list):
            return [InboxLead.model_validate(item) for item in data]
        return []

    def get_unread_replies(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
    ) -> list[InboxLead]:
        """
        Fetch unread replies.

        Args:
            offset: Pagination offset
            limit: Number of results to return

        Returns:
            List of leads with unread replies
        """
        data = self._request(
            "POST",
            "/master-inbox/unread-replies",
            json={"offset": offset, "limit": limit},
        )
        if isinstance(data, list):
            return [InboxLead.model_validate(item) for item in data]
        return []

    def get_archived_messages(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
    ) -> list[InboxLead]:
        """
        Fetch archived messages.

        Args:
            offset: Pagination offset
            limit: Number of results to return

        Returns:
            List of archived leads
        """
        data = self._request(
            "POST",
            "/master-inbox/archived",
            json={"offset": offset, "limit": limit},
        )
        if isinstance(data, list):
            return [InboxLead.model_validate(item) for item in data]
        return []

    def get_snoozed_messages(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
    ) -> list[InboxLead]:
        """
        Fetch snoozed messages.

        Args:
            offset: Pagination offset
            limit: Number of results to return

        Returns:
            List of snoozed leads
        """
        data = self._request(
            "POST",
            "/master-inbox/snoozed",
            json={"offset": offset, "limit": limit},
        )
        if isinstance(data, list):
            return [InboxLead.model_validate(item) for item in data]
        return []

    def get_important_messages(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
    ) -> list[InboxLead]:
        """
        Fetch important marked messages.

        Args:
            offset: Pagination offset
            limit: Number of results to return

        Returns:
            List of important leads
        """
        data = self._request(
            "POST",
            "/master-inbox/important",
            json={"offset": offset, "limit": limit},
        )
        if isinstance(data, list):
            return [InboxLead.model_validate(item) for item in data]
        return []

    def get_scheduled_messages(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
        sort_by: str = "SCHEDULED_TIME_DESC",
    ) -> list[InboxLead]:
        """
        Fetch scheduled messages.

        Args:
            offset: Pagination offset
            limit: Number of results to return
            sort_by: SCHEDULED_TIME_DESC or SCHEDULED_TIME_ASC

        Returns:
            List of leads with scheduled messages
        """
        data = self._request(
            "POST",
            "/master-inbox/scheduled",
            json={"offset": offset, "limit": limit, "sortBy": sort_by},
        )
        if isinstance(data, list):
            return [InboxLead.model_validate(item) for item in data]
        return []

    def get_messages_with_reminders(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
        sort_by: str = "REMINDER_TIME_DESC",
    ) -> list[InboxLead]:
        """
        Fetch messages with reminders.

        Args:
            offset: Pagination offset
            limit: Number of results to return
            sort_by: REMINDER_TIME_DESC or REMINDER_TIME_ASC

        Returns:
            List of leads with reminders
        """
        data = self._request(
            "POST",
            "/master-inbox/reminders",
            json={"offset": offset, "limit": limit, "sortBy": sort_by},
        )
        if isinstance(data, list):
            return [InboxLead.model_validate(item) for item in data]
        return []

    def update_lead_category(
        self: "BaseClient",
        lead_id: int,
        category: str,
        campaign_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Update the category for a lead in master inbox.

        Args:
            lead_id: The lead ID
            category: New category (e.g., "Interested", "Meeting Booked")
            campaign_id: Optional campaign ID

        Returns:
            Response data
        """
        payload: dict[str, Any] = {"lead_id": lead_id, "category": category}
        if campaign_id:
            payload["campaign_id"] = campaign_id

        return self._request("PATCH", "/master-inbox/update-category", json=payload)

    def mark_as_read(
        self: "BaseClient", lead_id: int, is_read: bool = True
    ) -> dict[str, Any]:
        """
        Mark a lead's messages as read/unread.

        Args:
            lead_id: The lead ID
            is_read: Read status

        Returns:
            Response data
        """
        return self._request(
            "PATCH",
            "/master-inbox/change-read-status",
            json={"lead_id": lead_id, "is_read": is_read},
        )

    def mark_as_important(
        self: "BaseClient", lead_id: int, is_important: bool = True
    ) -> dict[str, Any]:
        """
        Mark a lead as important/not important.

        Args:
            lead_id: The lead ID
            is_important: Important status

        Returns:
            Response data
        """
        return self._request(
            "PATCH",
            "/master-inbox/mark-important",
            json={"lead_id": lead_id, "is_important": is_important},
        )

    def archive_lead(self: "BaseClient", lead_id: int) -> dict[str, Any]:
        """
        Archive a lead in master inbox.

        Args:
            lead_id: The lead ID

        Returns:
            Response data
        """
        return self._request(
            "POST",
            "/master-inbox/archive",
            json={"lead_id": lead_id},
        )

    def snooze_lead(
        self: "BaseClient", lead_id: int, snooze_until: datetime
    ) -> dict[str, Any]:
        """
        Snooze a lead until a specified time.

        Args:
            lead_id: The lead ID
            snooze_until: When to unsnooze

        Returns:
            Response data
        """
        return self._request(
            "POST",
            "/master-inbox/snooze",
            json={"lead_id": lead_id, "snooze_until": snooze_until.isoformat()},
        )

    def set_reminder(
        self: "BaseClient", lead_id: int, reminder_time: datetime
    ) -> dict[str, Any]:
        """
        Set a reminder for a lead.

        Args:
            lead_id: The lead ID
            reminder_time: When to remind

        Returns:
            Response data
        """
        return self._request(
            "POST",
            "/master-inbox/set-reminder",
            json={"lead_id": lead_id, "reminder_time": reminder_time.isoformat()},
        )

    def get_master_inbox_lead(self: "BaseClient", lead_id: int) -> InboxLead:
        """
        Fetch a specific lead from master inbox by ID.

        Args:
            lead_id: The lead ID

        Returns:
            Inbox lead with full details
        """
        data = self._request("GET", f"/master-inbox/lead/{lead_id}")
        return InboxLead.model_validate(data)

    def update_lead_revenue(
        self: "BaseClient", lead_id: int, revenue: float
    ) -> dict[str, Any]:
        """
        Update revenue value for a lead.

        Args:
            lead_id: The lead ID
            revenue: Revenue amount

        Returns:
            Response data
        """
        return self._request(
            "PATCH",
            "/master-inbox/update-revenue",
            json={"lead_id": lead_id, "revenue": revenue},
        )

    def assign_team_member(
        self: "BaseClient", lead_id: int, team_member_id: int
    ) -> dict[str, Any]:
        """
        Assign a team member to a lead.

        Args:
            lead_id: The lead ID
            team_member_id: The team member ID

        Returns:
            Response data
        """
        return self._request(
            "PATCH",
            "/master-inbox/assign-team-member",
            json={"lead_id": lead_id, "team_member_id": team_member_id},
        )

    def create_lead_note(
        self: "BaseClient", lead_id: int, note: str
    ) -> dict[str, Any]:
        """
        Create a note for a lead.

        Args:
            lead_id: The lead ID
            note: Note content

        Returns:
            Response data
        """
        return self._request(
            "POST",
            "/master-inbox/create-note",
            json={"lead_id": lead_id, "note": note},
        )

    def create_lead_task(
        self: "BaseClient",
        lead_id: int,
        task: str,
        due_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a task for a lead.

        Args:
            lead_id: The lead ID
            task: Task description
            due_date: Optional due date

        Returns:
            Response data
        """
        payload: dict[str, Any] = {"lead_id": lead_id, "task": task}
        if due_date:
            payload["due_date"] = due_date.isoformat()
        return self._request("POST", "/master-inbox/create-task", json=payload)

    def forward_reply(
        self: "BaseClient",
        stats_id: str,
        forward_to: list[str],
        message: str | None = None,
    ) -> dict[str, Any]:
        """
        Forward a reply to other email addresses.

        Args:
            stats_id: The stats ID from email history
            forward_to: List of email addresses to forward to
            message: Optional additional message

        Returns:
            Response data
        """
        payload: dict[str, Any] = {"stats_id": stats_id, "forward_to": forward_to}
        if message:
            payload["message"] = message
        return self._request("POST", "/master-inbox/forward-reply", json=payload)


class AsyncMasterInboxMixin:
    """Async mixin for master inbox operations."""

    async def get_inbox_replies(
        self: "AsyncBaseClient",
        offset: int = 0,
        limit: int = 100,
        campaign_id: int | None = None,
    ) -> list[InboxLead]:
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if campaign_id:
            params["campaign_id"] = campaign_id
        data = await self._request("POST", "/master-inbox/inbox-replies", json=params)
        return (
            [InboxLead.model_validate(item) for item in data]
            if isinstance(data, list)
            else []
        )

    async def get_unread_replies(
        self: "AsyncBaseClient", offset: int = 0, limit: int = 100
    ) -> list[InboxLead]:
        data = await self._request(
            "POST",
            "/master-inbox/unread-replies",
            json={"offset": offset, "limit": limit},
        )
        return (
            [InboxLead.model_validate(item) for item in data]
            if isinstance(data, list)
            else []
        )

    async def update_lead_category(
        self: "AsyncBaseClient",
        lead_id: int,
        category: str,
        campaign_id: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"lead_id": lead_id, "category": category}
        if campaign_id:
            payload["campaign_id"] = campaign_id
        return await self._request(
            "PATCH", "/master-inbox/update-category", json=payload
        )

    async def mark_as_read(
        self: "AsyncBaseClient", lead_id: int, is_read: bool = True
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            "/master-inbox/change-read-status",
            json={"lead_id": lead_id, "is_read": is_read},
        )

    async def get_master_inbox_lead(self: "AsyncBaseClient", lead_id: int) -> InboxLead:
        data = await self._request("GET", f"/master-inbox/lead/{lead_id}")
        return InboxLead.model_validate(data)

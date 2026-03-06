"""
ClickUp Time Tracking endpoints.
"""

from typing import Any, TYPE_CHECKING

from ..models import TimeEntriesResponse, TimeEntry, TimeEntryCreate

if TYPE_CHECKING:
    from .base import BaseClient


class TimeTrackingMixin:
    """Time tracking-related API methods."""

    async def get_time_entries(
        self: "BaseClient",
        team_id: str,
        start_date: int | None = None,
        end_date: int | None = None,
        assignee: int | None = None,
        include_task_tags: bool = False,
        include_location_names: bool = False,
        space_id: str | None = None,
        folder_id: str | None = None,
        list_id: str | None = None,
        task_id: str | None = None,
    ) -> TimeEntriesResponse:
        """
        Get time entries within a date range.

        Args:
            team_id: Workspace (Team) ID
            start_date: Start date (Unix ms)
            end_date: End date (Unix ms)
            assignee: Filter by user ID
            include_task_tags: Include task tags in response
            include_location_names: Include location names
            space_id: Filter by Space
            folder_id: Filter by Folder
            list_id: Filter by List
            task_id: Filter by Task
        """
        params: dict[str, Any] = {
            "include_task_tags": str(include_task_tags).lower(),
            "include_location_names": str(include_location_names).lower(),
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if assignee:
            params["assignee"] = assignee
        if space_id:
            params["space_id"] = space_id
        if folder_id:
            params["folder_id"] = folder_id
        if list_id:
            params["list_id"] = list_id
        if task_id:
            params["task_id"] = task_id

        data = await self._request("GET", f"/team/{team_id}/time_entries", params=params)
        return TimeEntriesResponse.model_validate(data)

    async def create_time_entry(
        self: "BaseClient",
        team_id: str,
        task_id: str,
        entry: TimeEntryCreate,
    ) -> TimeEntry:
        """Create a time entry on a task."""
        json_body = entry.model_dump(exclude_none=True)
        json_body["tid"] = task_id

        data = await self._request("POST", f"/team/{team_id}/time_entries", json=json_body)
        return TimeEntry.model_validate(data.get("data", data))

    async def get_time_entry(
        self: "BaseClient",
        team_id: str,
        timer_id: str,
    ) -> TimeEntry:
        """Get a single time entry."""
        data = await self._request("GET", f"/team/{team_id}/time_entries/{timer_id}")
        return TimeEntry.model_validate(data.get("data", data))

    async def delete_time_entry(
        self: "BaseClient",
        team_id: str,
        timer_id: str,
    ) -> None:
        """Delete a time entry."""
        await self._request("DELETE", f"/team/{team_id}/time_entries/{timer_id}")

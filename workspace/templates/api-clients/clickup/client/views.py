"""
ClickUp View endpoints.
"""

from typing import TYPE_CHECKING

from ..models import TasksResponse, View, ViewsResponse

if TYPE_CHECKING:
    from .base import BaseClient


class ViewsMixin:
    """View-related API methods."""

    async def get_team_views(self: "BaseClient", team_id: str) -> ViewsResponse:
        """Get all views at the Workspace level."""
        data = await self._request("GET", f"/team/{team_id}/view")
        return ViewsResponse.model_validate(data)

    async def get_space_views(self: "BaseClient", space_id: str) -> ViewsResponse:
        """Get all views in a Space."""
        data = await self._request("GET", f"/space/{space_id}/view")
        return ViewsResponse.model_validate(data)

    async def get_folder_views(self: "BaseClient", folder_id: str) -> ViewsResponse:
        """Get all views in a Folder."""
        data = await self._request("GET", f"/folder/{folder_id}/view")
        return ViewsResponse.model_validate(data)

    async def get_list_views(self: "BaseClient", list_id: str) -> ViewsResponse:
        """Get all views in a List."""
        data = await self._request("GET", f"/list/{list_id}/view")
        return ViewsResponse.model_validate(data)

    async def get_view(self: "BaseClient", view_id: str) -> View:
        """Get a view by ID."""
        data = await self._request("GET", f"/view/{view_id}")
        return View.model_validate(data.get("view", data))

    async def get_view_tasks(
        self: "BaseClient",
        view_id: str,
        page: int = 0,
    ) -> TasksResponse:
        """Get tasks from a view."""
        data = await self._request("GET", f"/view/{view_id}/task", params={"page": page})
        return TasksResponse.model_validate(data)

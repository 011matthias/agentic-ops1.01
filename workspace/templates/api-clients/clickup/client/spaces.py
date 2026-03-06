"""
ClickUp Space endpoints.
"""

from typing import TYPE_CHECKING

from ..models import Space, SpaceCreate

if TYPE_CHECKING:
    from .base import BaseClient


class SpacesMixin:
    """Space-related API methods."""

    async def get_spaces(self: "BaseClient", team_id: str, archived: bool = False) -> list[Space]:
        """
        Get all Spaces in a Workspace.

        Args:
            team_id: Workspace (Team) ID
            archived: Include archived Spaces
        """
        data = await self._request(
            "GET",
            f"/team/{team_id}/space",
            params={"archived": str(archived).lower()},
        )
        return [Space.model_validate(s) for s in data.get("spaces", [])]

    async def create_space(self: "BaseClient", team_id: str, space: SpaceCreate) -> Space:
        """Create a new Space in a Workspace."""
        data = await self._request(
            "POST",
            f"/team/{team_id}/space",
            json=space.model_dump(exclude_none=True),
        )
        return Space.model_validate(data)

    async def get_space(self: "BaseClient", space_id: str) -> Space:
        """Get a Space by ID."""
        data = await self._request("GET", f"/space/{space_id}")
        return Space.model_validate(data)

    async def update_space(self: "BaseClient", space_id: str, name: str, **kwargs) -> Space:
        """Update a Space."""
        data = await self._request(
            "PUT",
            f"/space/{space_id}",
            json={"name": name, **kwargs},
        )
        return Space.model_validate(data)

    async def delete_space(self: "BaseClient", space_id: str) -> None:
        """Delete a Space."""
        await self._request("DELETE", f"/space/{space_id}")

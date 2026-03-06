"""
ClickUp Tag endpoints.
"""

from typing import Any, TYPE_CHECKING

from ..models import TagsResponse

if TYPE_CHECKING:
    from .base import BaseClient


class TagsMixin:
    """Tag-related API methods."""

    async def get_space_tags(self: "BaseClient", space_id: str) -> TagsResponse:
        """Get all tags in a Space."""
        data = await self._request("GET", f"/space/{space_id}/tag")
        return TagsResponse.model_validate(data)

    async def create_space_tag(
        self: "BaseClient",
        space_id: str,
        name: str,
        tag_fg: str | None = None,
        tag_bg: str | None = None,
    ) -> None:
        """
        Create a tag in a Space.

        Args:
            space_id: Space ID
            name: Tag name
            tag_fg: Foreground color (hex)
            tag_bg: Background color (hex)
        """
        json_body: dict[str, Any] = {"tag": {"name": name}}
        if tag_fg:
            json_body["tag"]["tag_fg"] = tag_fg
        if tag_bg:
            json_body["tag"]["tag_bg"] = tag_bg

        await self._request("POST", f"/space/{space_id}/tag", json=json_body)

    async def update_space_tag(
        self: "BaseClient",
        space_id: str,
        tag_name: str,
        new_name: str | None = None,
        tag_fg: str | None = None,
        tag_bg: str | None = None,
    ) -> None:
        """Update a tag in a Space."""
        json_body: dict[str, Any] = {"tag": {}}
        if new_name:
            json_body["tag"]["name"] = new_name
        if tag_fg:
            json_body["tag"]["tag_fg"] = tag_fg
        if tag_bg:
            json_body["tag"]["tag_bg"] = tag_bg

        await self._request("PUT", f"/space/{space_id}/tag/{tag_name}", json=json_body)

    async def delete_space_tag(
        self: "BaseClient",
        space_id: str,
        tag_name: str,
    ) -> None:
        """Delete a tag from a Space."""
        await self._request("DELETE", f"/space/{space_id}/tag/{tag_name}")

    async def add_tag_to_task(
        self: "BaseClient",
        task_id: str,
        tag_name: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """Add a tag to a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        await self._request(
            "POST",
            f"/task/{task_id}/tag/{tag_name}",
            params=params if params else None,
        )

    async def remove_tag_from_task(
        self: "BaseClient",
        task_id: str,
        tag_name: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """Remove a tag from a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        await self._request(
            "DELETE",
            f"/task/{task_id}/tag/{tag_name}",
            params=params if params else None,
        )

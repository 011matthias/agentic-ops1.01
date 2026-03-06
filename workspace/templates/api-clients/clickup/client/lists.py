"""
ClickUp List endpoints.
"""

from typing import TYPE_CHECKING

from ..models import List, ListCreate

if TYPE_CHECKING:
    from .base import BaseClient


class ListsMixin:
    """List-related API methods."""

    async def get_lists(self: "BaseClient", folder_id: str, archived: bool = False) -> list[List]:
        """Get all Lists in a Folder."""
        data = await self._request(
            "GET",
            f"/folder/{folder_id}/list",
            params={"archived": str(archived).lower()},
        )
        return [List.model_validate(lst) for lst in data.get("lists", [])]

    async def get_folderless_lists(self: "BaseClient", space_id: str, archived: bool = False) -> list[List]:
        """Get all Lists in a Space that are not in a Folder."""
        data = await self._request(
            "GET",
            f"/space/{space_id}/list",
            params={"archived": str(archived).lower()},
        )
        return [List.model_validate(lst) for lst in data.get("lists", [])]

    async def create_list(self: "BaseClient", folder_id: str, list_data: ListCreate) -> List:
        """Create a new List in a Folder."""
        data = await self._request(
            "POST",
            f"/folder/{folder_id}/list",
            json=list_data.model_dump(exclude_none=True),
        )
        return List.model_validate(data)

    async def create_folderless_list(self: "BaseClient", space_id: str, list_data: ListCreate) -> List:
        """Create a new List in a Space (not in a Folder)."""
        data = await self._request(
            "POST",
            f"/space/{space_id}/list",
            json=list_data.model_dump(exclude_none=True),
        )
        return List.model_validate(data)

    async def get_list(self: "BaseClient", list_id: str) -> List:
        """Get a List by ID."""
        data = await self._request("GET", f"/list/{list_id}")
        return List.model_validate(data)

    async def update_list(self: "BaseClient", list_id: str, **kwargs) -> List:
        """Update a List."""
        data = await self._request("PUT", f"/list/{list_id}", json=kwargs)
        return List.model_validate(data)

    async def delete_list(self: "BaseClient", list_id: str) -> None:
        """Delete a List."""
        await self._request("DELETE", f"/list/{list_id}")

"""
ClickUp Folder endpoints.
"""

from typing import TYPE_CHECKING

from ..models import Folder, FolderCreate

if TYPE_CHECKING:
    from .base import BaseClient


class FoldersMixin:
    """Folder-related API methods."""

    async def get_folders(self: "BaseClient", space_id: str, archived: bool = False) -> list[Folder]:
        """Get all Folders in a Space."""
        data = await self._request(
            "GET",
            f"/space/{space_id}/folder",
            params={"archived": str(archived).lower()},
        )
        return [Folder.model_validate(f) for f in data.get("folders", [])]

    async def create_folder(self: "BaseClient", space_id: str, folder: FolderCreate) -> Folder:
        """Create a new Folder in a Space."""
        data = await self._request(
            "POST",
            f"/space/{space_id}/folder",
            json=folder.model_dump(exclude_none=True),
        )
        return Folder.model_validate(data)

    async def get_folder(self: "BaseClient", folder_id: str) -> Folder:
        """Get a Folder by ID."""
        data = await self._request("GET", f"/folder/{folder_id}")
        return Folder.model_validate(data)

    async def update_folder(self: "BaseClient", folder_id: str, name: str) -> Folder:
        """Update a Folder name."""
        data = await self._request(
            "PUT",
            f"/folder/{folder_id}",
            json={"name": name},
        )
        return Folder.model_validate(data)

    async def delete_folder(self: "BaseClient", folder_id: str) -> None:
        """Delete a Folder."""
        await self._request("DELETE", f"/folder/{folder_id}")

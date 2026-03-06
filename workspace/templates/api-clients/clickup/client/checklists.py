"""
ClickUp Checklist endpoints.
"""

from typing import Any, TYPE_CHECKING

from ..models import Checklist, ChecklistCreate, ChecklistItemCreate, ChecklistItemUpdate

if TYPE_CHECKING:
    from .base import BaseClient


class ChecklistsMixin:
    """Checklist-related API methods."""

    async def create_checklist(
        self: "BaseClient",
        task_id: str,
        checklist: ChecklistCreate,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> Checklist:
        """Create a checklist on a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        data = await self._request(
            "POST",
            f"/task/{task_id}/checklist",
            params=params if params else None,
            json=checklist.model_dump(exclude_none=True),
        )
        return Checklist.model_validate(data.get("checklist", data))

    async def update_checklist(
        self: "BaseClient",
        checklist_id: str,
        name: str | None = None,
        position: int | None = None,
    ) -> Checklist:
        """Update a checklist."""
        json_body: dict[str, Any] = {}
        if name is not None:
            json_body["name"] = name
        if position is not None:
            json_body["position"] = position

        data = await self._request("PUT", f"/checklist/{checklist_id}", json=json_body)
        return Checklist.model_validate(data.get("checklist", data))

    async def delete_checklist(self: "BaseClient", checklist_id: str) -> None:
        """Delete a checklist."""
        await self._request("DELETE", f"/checklist/{checklist_id}")

    async def create_checklist_item(
        self: "BaseClient",
        checklist_id: str,
        item: ChecklistItemCreate,
    ) -> Checklist:
        """Add an item to a checklist."""
        data = await self._request(
            "POST",
            f"/checklist/{checklist_id}/checklist_item",
            json=item.model_dump(exclude_none=True),
        )
        return Checklist.model_validate(data.get("checklist", data))

    async def update_checklist_item(
        self: "BaseClient",
        checklist_id: str,
        checklist_item_id: str,
        item: ChecklistItemUpdate,
    ) -> Checklist:
        """Update a checklist item."""
        data = await self._request(
            "PUT",
            f"/checklist/{checklist_id}/checklist_item/{checklist_item_id}",
            json=item.model_dump(exclude_none=True),
        )
        return Checklist.model_validate(data.get("checklist", data))

    async def delete_checklist_item(
        self: "BaseClient",
        checklist_id: str,
        checklist_item_id: str,
    ) -> None:
        """Delete a checklist item."""
        await self._request(
            "DELETE",
            f"/checklist/{checklist_id}/checklist_item/{checklist_item_id}",
        )

"""
ClickUp Task endpoints.
"""

import json as json_module
from typing import Any, TYPE_CHECKING

from ..models import Task, TaskCreate, TasksResponse, TaskUpdate

if TYPE_CHECKING:
    from .base import BaseClient


class TasksMixin:
    """Task-related API methods."""

    async def get_tasks(
        self: "BaseClient",
        list_id: str,
        archived: bool = False,
        include_closed: bool = False,
        page: int = 0,
        order_by: str | None = None,
        reverse: bool = False,
        subtasks: bool = False,
        statuses: list[str] | None = None,
        assignees: list[int] | None = None,
        tags: list[str] | None = None,
        due_date_gt: int | None = None,
        due_date_lt: int | None = None,
        date_created_gt: int | None = None,
        date_created_lt: int | None = None,
        date_updated_gt: int | None = None,
        date_updated_lt: int | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
    ) -> TasksResponse:
        """
        Get tasks from a List.

        Args:
            list_id: List ID
            archived: Include archived tasks
            include_closed: Include closed tasks
            page: Page number (0-indexed)
            order_by: Field to order by (id, created, updated, due_date)
            reverse: Reverse sort order
            subtasks: Include subtasks
            statuses: Filter by statuses
            assignees: Filter by assignee user IDs
            tags: Filter by tag names
            due_date_gt: Due date greater than (Unix ms)
            due_date_lt: Due date less than (Unix ms)
            date_created_gt: Created date greater than (Unix ms)
            date_created_lt: Created date less than (Unix ms)
            date_updated_gt: Updated date greater than (Unix ms)
            date_updated_lt: Updated date less than (Unix ms)
            custom_fields: Filter by custom field values
        """
        params: dict[str, Any] = {
            "archived": str(archived).lower(),
            "include_closed": str(include_closed).lower(),
            "page": page,
            "reverse": str(reverse).lower(),
            "subtasks": str(subtasks).lower(),
        }

        if order_by:
            params["order_by"] = order_by
        if statuses:
            params["statuses[]"] = statuses
        if assignees:
            params["assignees[]"] = assignees
        if tags:
            params["tags[]"] = tags
        if due_date_gt:
            params["due_date_gt"] = due_date_gt
        if due_date_lt:
            params["due_date_lt"] = due_date_lt
        if date_created_gt:
            params["date_created_gt"] = date_created_gt
        if date_created_lt:
            params["date_created_lt"] = date_created_lt
        if date_updated_gt:
            params["date_updated_gt"] = date_updated_gt
        if date_updated_lt:
            params["date_updated_lt"] = date_updated_lt
        if custom_fields:
            params["custom_fields"] = json_module.dumps(custom_fields)

        data = await self._request("GET", f"/list/{list_id}/task", params=params)
        return TasksResponse.model_validate(data)

    async def get_filtered_team_tasks(
        self: "BaseClient",
        team_id: str,
        page: int = 0,
        order_by: str | None = None,
        reverse: bool = False,
        subtasks: bool = False,
        space_ids: list[str] | None = None,
        project_ids: list[str] | None = None,
        list_ids: list[str] | None = None,
        statuses: list[str] | None = None,
        include_closed: bool = False,
        assignees: list[int] | None = None,
        tags: list[str] | None = None,
        due_date_gt: int | None = None,
        due_date_lt: int | None = None,
        date_created_gt: int | None = None,
        date_created_lt: int | None = None,
        date_updated_gt: int | None = None,
        date_updated_lt: int | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
    ) -> TasksResponse:
        """Get filtered tasks across a Workspace."""
        params: dict[str, Any] = {
            "page": page,
            "reverse": str(reverse).lower(),
            "subtasks": str(subtasks).lower(),
            "include_closed": str(include_closed).lower(),
        }

        if order_by:
            params["order_by"] = order_by
        if space_ids:
            params["space_ids[]"] = space_ids
        if project_ids:
            params["project_ids[]"] = project_ids
        if list_ids:
            params["list_ids[]"] = list_ids
        if statuses:
            params["statuses[]"] = statuses
        if assignees:
            params["assignees[]"] = assignees
        if tags:
            params["tags[]"] = tags
        if due_date_gt:
            params["due_date_gt"] = due_date_gt
        if due_date_lt:
            params["due_date_lt"] = due_date_lt
        if date_created_gt:
            params["date_created_gt"] = date_created_gt
        if date_created_lt:
            params["date_created_lt"] = date_created_lt
        if date_updated_gt:
            params["date_updated_gt"] = date_updated_gt
        if date_updated_lt:
            params["date_updated_lt"] = date_updated_lt
        if custom_fields:
            params["custom_fields"] = json_module.dumps(custom_fields)

        data = await self._request("GET", f"/team/{team_id}/task", params=params)
        return TasksResponse.model_validate(data)

    async def get_task(
        self: "BaseClient",
        task_id: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
        include_subtasks: bool = False,
    ) -> Task:
        """
        Get a task by ID.

        Args:
            task_id: Task ID (or custom task ID if custom_task_ids=True)
            custom_task_ids: Use custom task IDs instead of system IDs
            team_id: Required when using custom_task_ids
            include_subtasks: Include subtasks in response
        """
        params: dict[str, Any] = {
            "include_subtasks": str(include_subtasks).lower(),
        }
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        data = await self._request("GET", f"/task/{task_id}", params=params)
        return Task.model_validate(data)

    async def create_task(
        self: "BaseClient",
        list_id: str,
        task: TaskCreate,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> Task:
        """
        Create a new task in a List.

        Args:
            list_id: List ID
            task: Task creation data
            custom_task_ids: Use custom task IDs for parent/links_to
            team_id: Required when using custom_task_ids
        """
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        data = await self._request(
            "POST",
            f"/list/{list_id}/task",
            params=params if params else None,
            json=task.model_dump(exclude_none=True),
        )
        return Task.model_validate(data)

    async def update_task(
        self: "BaseClient",
        task_id: str,
        task: TaskUpdate,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> Task:
        """Update a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        data = await self._request(
            "PUT",
            f"/task/{task_id}",
            params=params if params else None,
            json=task.model_dump(exclude_none=True),
        )
        return Task.model_validate(data)

    async def delete_task(
        self: "BaseClient",
        task_id: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """Delete a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        await self._request(
            "DELETE",
            f"/task/{task_id}",
            params=params if params else None,
        )

    async def set_custom_field_value(
        self: "BaseClient",
        task_id: str,
        field_id: str,
        value: Any,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """Set a custom field value on a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        await self._request(
            "POST",
            f"/task/{task_id}/field/{field_id}",
            params=params if params else None,
            json={"value": value},
        )

    async def remove_custom_field_value(
        self: "BaseClient",
        task_id: str,
        field_id: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """Remove a custom field value from a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        await self._request(
            "DELETE",
            f"/task/{task_id}/field/{field_id}",
            params=params if params else None,
        )

    async def add_dependency(
        self: "BaseClient",
        task_id: str,
        depends_on: str | None = None,
        dependency_of: str | None = None,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """
        Add a dependency relationship between tasks.

        Args:
            task_id: Task ID
            depends_on: Task ID that this task depends on (blocking)
            dependency_of: Task ID that depends on this task (waiting on)
        """
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        json_body = {}
        if depends_on:
            json_body["depends_on"] = depends_on
        if dependency_of:
            json_body["dependency_of"] = dependency_of

        await self._request(
            "POST",
            f"/task/{task_id}/dependency",
            params=params if params else None,
            json=json_body,
        )

    async def delete_dependency(
        self: "BaseClient",
        task_id: str,
        depends_on: str | None = None,
        dependency_of: str | None = None,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """Remove a dependency relationship."""
        params: dict[str, Any] = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id
        if depends_on:
            params["depends_on"] = depends_on
        if dependency_of:
            params["dependency_of"] = dependency_of

        await self._request(
            "DELETE",
            f"/task/{task_id}/dependency",
            params=params if params else None,
        )

    async def add_task_link(
        self: "BaseClient",
        task_id: str,
        links_to: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> Task:
        """Link two tasks together."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        data = await self._request(
            "POST",
            f"/task/{task_id}/link/{links_to}",
            params=params if params else None,
        )
        return Task.model_validate(data.get("task", data))

    async def delete_task_link(
        self: "BaseClient",
        task_id: str,
        links_to: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> None:
        """Remove a link between two tasks."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        await self._request(
            "DELETE",
            f"/task/{task_id}/link/{links_to}",
            params=params if params else None,
        )

    async def get_task_members(self: "BaseClient", task_id: str) -> list[dict[str, Any]]:
        """Get members with access to a task."""
        data = await self._request("GET", f"/task/{task_id}/member")
        return data.get("members", [])

    async def get_list_members(self: "BaseClient", list_id: str) -> list[dict[str, Any]]:
        """Get members with access to a List."""
        data = await self._request("GET", f"/list/{list_id}/member")
        return data.get("members", [])

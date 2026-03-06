"""
ClickUp Comment endpoints.
"""

from typing import Any, TYPE_CHECKING

from ..models import Comment, CommentCreate, CommentsResponse

if TYPE_CHECKING:
    from .base import BaseClient


class CommentsMixin:
    """Comment-related API methods."""

    async def get_task_comments(
        self: "BaseClient",
        task_id: str,
        custom_task_ids: bool = False,
        team_id: str | None = None,
        start: int | None = None,
        start_id: str | None = None,
    ) -> CommentsResponse:
        """Get comments on a task."""
        params: dict[str, Any] = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id
        if start:
            params["start"] = start
        if start_id:
            params["start_id"] = start_id

        data = await self._request(
            "GET",
            f"/task/{task_id}/comment",
            params=params if params else None,
        )
        return CommentsResponse.model_validate(data)

    async def create_task_comment(
        self: "BaseClient",
        task_id: str,
        comment: CommentCreate,
        custom_task_ids: bool = False,
        team_id: str | None = None,
    ) -> Comment:
        """Add a comment to a task."""
        params = {}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
            if team_id:
                params["team_id"] = team_id

        data = await self._request(
            "POST",
            f"/task/{task_id}/comment",
            params=params if params else None,
            json=comment.model_dump(exclude_none=True),
        )
        return Comment.model_validate(data)

    async def get_list_comments(
        self: "BaseClient",
        list_id: str,
        start: int | None = None,
        start_id: str | None = None,
    ) -> CommentsResponse:
        """Get comments on a List."""
        params: dict[str, Any] = {}
        if start:
            params["start"] = start
        if start_id:
            params["start_id"] = start_id

        data = await self._request(
            "GET",
            f"/list/{list_id}/comment",
            params=params if params else None,
        )
        return CommentsResponse.model_validate(data)

    async def create_list_comment(
        self: "BaseClient",
        list_id: str,
        comment: CommentCreate,
    ) -> Comment:
        """Add a comment to a List."""
        data = await self._request(
            "POST",
            f"/list/{list_id}/comment",
            json=comment.model_dump(exclude_none=True),
        )
        return Comment.model_validate(data)

    async def get_chat_view_comments(
        self: "BaseClient",
        view_id: str,
        start: int | None = None,
        start_id: str | None = None,
    ) -> CommentsResponse:
        """Get comments from a Chat view."""
        params: dict[str, Any] = {}
        if start:
            params["start"] = start
        if start_id:
            params["start_id"] = start_id

        data = await self._request(
            "GET",
            f"/view/{view_id}/comment",
            params=params if params else None,
        )
        return CommentsResponse.model_validate(data)

    async def create_chat_view_comment(
        self: "BaseClient",
        view_id: str,
        comment: CommentCreate,
    ) -> Comment:
        """Add a comment to a Chat view."""
        data = await self._request(
            "POST",
            f"/view/{view_id}/comment",
            json=comment.model_dump(exclude_none=True),
        )
        return Comment.model_validate(data)

    async def update_comment(
        self: "BaseClient",
        comment_id: str,
        comment_text: str,
        assignee: int | None = None,
        resolved: bool | None = None,
    ) -> Comment:
        """Update a comment."""
        json_body: dict[str, Any] = {"comment_text": comment_text}
        if assignee is not None:
            json_body["assignee"] = assignee
        if resolved is not None:
            json_body["resolved"] = resolved

        data = await self._request("PUT", f"/comment/{comment_id}", json=json_body)
        return Comment.model_validate(data)

    async def delete_comment(self: "BaseClient", comment_id: str) -> None:
        """Delete a comment."""
        await self._request("DELETE", f"/comment/{comment_id}")

    async def get_threaded_comments(
        self: "BaseClient",
        comment_id: str,
        start: int | None = None,
        start_id: str | None = None,
    ) -> CommentsResponse:
        """Get threaded replies to a comment."""
        params: dict[str, Any] = {}
        if start:
            params["start"] = start
        if start_id:
            params["start_id"] = start_id

        data = await self._request(
            "GET",
            f"/comment/{comment_id}/reply",
            params=params if params else None,
        )
        return CommentsResponse.model_validate(data)

    async def create_threaded_comment(
        self: "BaseClient",
        comment_id: str,
        comment: CommentCreate,
    ) -> Comment:
        """Add a threaded reply to a comment."""
        data = await self._request(
            "POST",
            f"/comment/{comment_id}/reply",
            json=comment.model_dump(exclude_none=True),
        )
        return Comment.model_validate(data)

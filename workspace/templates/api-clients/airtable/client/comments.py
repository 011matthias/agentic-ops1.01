"""
Airtable Comments Mixin

Operations for record comments.
"""

from typing import TYPE_CHECKING

from ..models import Comment, CommentList

if TYPE_CHECKING:
    from .base import BaseClient


class CommentsMixin:
    """Mixin providing comment operations."""

    async def list_comments(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        record_id: str,
        *,
        offset: str | None = None,
    ) -> CommentList:
        """
        List comments on a record.

        Args:
            base_id: Base ID (appXXXXXX)
            table_id_or_name: Table ID or name
            record_id: Record ID (recXXXXXX)
            offset: Pagination offset
        """
        params = {"offset": offset} if offset else None
        data = await self._request(
            "GET",
            f"/v0/{base_id}/{table_id_or_name}/{record_id}/comments",
            params=params,
        )
        return CommentList.model_validate(data)

    async def create_comment(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        record_id: str,
        text: str,
    ) -> Comment:
        """
        Add a comment to a record.

        Args:
            base_id: Base ID (appXXXXXX)
            table_id_or_name: Table ID or name
            record_id: Record ID (recXXXXXX)
            text: Comment text (supports @mentions)
        """
        data = await self._request(
            "POST",
            f"/v0/{base_id}/{table_id_or_name}/{record_id}/comments",
            json={"text": text},
        )
        return Comment.model_validate(data)

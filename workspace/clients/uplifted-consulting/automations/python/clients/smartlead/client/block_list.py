"""
Smartlead Block List Mixin

Endpoints for managing global block list (emails and domains).
"""

from typing import TYPE_CHECKING, Any

from ..models import BlockListEntry

if TYPE_CHECKING:
    from .base import AsyncBaseClient, BaseClient


class BlockListMixin:
    """Mixin for block list operations."""

    def get_global_block_list(
        self: "BaseClient",
        offset: int = 0,
        limit: int = 100,
    ) -> list[BlockListEntry]:
        """
        Fetch leads/domains from global block list.

        Args:
            offset: Pagination offset
            limit: Number of results to return

        Returns:
            List of blocked entries
        """
        data = self._request(
            "GET",
            "/leads/block-list",
            params={"offset": offset, "limit": limit},
        )
        if isinstance(data, list):
            return [BlockListEntry.model_validate(item) for item in data]
        return []

    def add_to_block_list(
        self: "BaseClient",
        email: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """
        Add an email or domain to global block list.

        Args:
            email: Email address to block
            domain: Domain to block

        Returns:
            Response data
        """
        payload: dict[str, Any] = {}
        if email:
            payload["email"] = email
        if domain:
            payload["domain"] = domain

        return self._request("POST", "/leads/block-list", json=payload)

    def remove_from_block_list(
        self: "BaseClient",
        email: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """
        Remove an email or domain from global block list.

        Args:
            email: Email address to unblock
            domain: Domain to unblock

        Returns:
            Response data
        """
        payload: dict[str, Any] = {}
        if email:
            payload["email"] = email
        if domain:
            payload["domain"] = domain

        return self._request("DELETE", "/leads/block-list", json=payload)

    def block_domains(
        self: "BaseClient",
        domains: list[str],
    ) -> dict[str, Any]:
        """
        Block multiple domains at once.

        Args:
            domains: List of domains to block

        Returns:
            Response data
        """
        return self._request(
            "POST",
            "/leads/block-domains",
            json={"domains": domains},
        )


class AsyncBlockListMixin:
    """Async mixin for block list operations."""

    async def get_global_block_list(
        self: "AsyncBaseClient",
        offset: int = 0,
        limit: int = 100,
    ) -> list[BlockListEntry]:
        data = await self._request(
            "GET",
            "/leads/block-list",
            params={"offset": offset, "limit": limit},
        )
        return (
            [BlockListEntry.model_validate(item) for item in data]
            if isinstance(data, list)
            else []
        )

    async def add_to_block_list(
        self: "AsyncBaseClient",
        email: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if email:
            payload["email"] = email
        if domain:
            payload["domain"] = domain
        return await self._request("POST", "/leads/block-list", json=payload)

    async def remove_from_block_list(
        self: "AsyncBaseClient",
        email: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if email:
            payload["email"] = email
        if domain:
            payload["domain"] = domain
        return await self._request("DELETE", "/leads/block-list", json=payload)

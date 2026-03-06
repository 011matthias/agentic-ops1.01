"""
Smartlead Email Accounts Mixin

Endpoints for managing email accounts and warmup settings.
"""

from typing import TYPE_CHECKING, Any

from ..models import (
    EmailAccount,
    EmailAccountCreate,
    EmailAccountUpdate,
    WarmupSettings,
    WarmupStats,
)

if TYPE_CHECKING:
    from .base import AsyncBaseClient, BaseClient


class EmailAccountsMixin:
    """Mixin for email account operations."""

    def list_email_accounts(self: "BaseClient") -> list[EmailAccount]:
        """
        Fetch all email accounts associated to the user.

        Returns:
            List of email accounts
        """
        data = self._request("GET", "/email-accounts/")
        if isinstance(data, list):
            return [EmailAccount.model_validate(item) for item in data]
        return []

    def get_email_account(self: "BaseClient", email_account_id: int) -> EmailAccount:
        """
        Fetch a specific email account by ID.

        Args:
            email_account_id: The email account ID

        Returns:
            Email account details
        """
        data = self._request("GET", f"/email-accounts/{email_account_id}")
        return EmailAccount.model_validate(data)

    def create_email_account(
        self: "BaseClient", account: EmailAccountCreate
    ) -> EmailAccount:
        """
        Create a new email account.

        Args:
            account: Email account details

        Returns:
            Created email account
        """
        data = self._request(
            "POST",
            "/email-accounts/save",
            json=account.model_dump(exclude_none=True),
        )
        return EmailAccount.model_validate(data)

    def update_email_account(
        self: "BaseClient", email_account_id: int, account: EmailAccountUpdate
    ) -> EmailAccount:
        """
        Update an existing email account.

        Args:
            email_account_id: The email account ID
            account: Updated fields

        Returns:
            Updated email account
        """
        data = self._request(
            "POST",
            f"/email-accounts/{email_account_id}",
            json=account.model_dump(exclude_none=True),
        )
        return EmailAccount.model_validate(data)

    def update_warmup_settings(
        self: "BaseClient", email_account_id: int, settings: WarmupSettings
    ) -> dict[str, Any]:
        """
        Add or update warmup configuration for an email account.

        Args:
            email_account_id: The email account ID
            settings: Warmup configuration

        Returns:
            Response data
        """
        return self._request(
            "POST",
            f"/email-accounts/{email_account_id}/warmup",
            json=settings.model_dump(exclude_none=True),
        )

    def get_warmup_stats(self: "BaseClient", email_account_id: int) -> WarmupStats:
        """
        Fetch warmup statistics for an email account.

        Args:
            email_account_id: The email account ID

        Returns:
            Warmup statistics
        """
        data = self._request("GET", f"/email-accounts/{email_account_id}/warmup")
        return WarmupStats.model_validate(data)

    def reconnect_email_account(
        self: "BaseClient", email_account_id: int
    ) -> dict[str, Any]:
        """
        Reconnect a failed email account.

        Args:
            email_account_id: The email account ID

        Returns:
            Response data
        """
        return self._request("POST", f"/email-accounts/{email_account_id}/reconnect")


class AsyncEmailAccountsMixin:
    """Async mixin for email account operations."""

    async def list_email_accounts(self: "AsyncBaseClient") -> list[EmailAccount]:
        data = await self._request("GET", "/email-accounts/")
        return (
            [EmailAccount.model_validate(item) for item in data]
            if isinstance(data, list)
            else []
        )

    async def get_email_account(
        self: "AsyncBaseClient", email_account_id: int
    ) -> EmailAccount:
        data = await self._request("GET", f"/email-accounts/{email_account_id}")
        return EmailAccount.model_validate(data)

    async def create_email_account(
        self: "AsyncBaseClient", account: EmailAccountCreate
    ) -> EmailAccount:
        data = await self._request(
            "POST", "/email-accounts/save", json=account.model_dump(exclude_none=True)
        )
        return EmailAccount.model_validate(data)

    async def update_email_account(
        self: "AsyncBaseClient", email_account_id: int, account: EmailAccountUpdate
    ) -> EmailAccount:
        data = await self._request(
            "POST",
            f"/email-accounts/{email_account_id}",
            json=account.model_dump(exclude_none=True),
        )
        return EmailAccount.model_validate(data)

    async def update_warmup_settings(
        self: "AsyncBaseClient", email_account_id: int, settings: WarmupSettings
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/email-accounts/{email_account_id}/warmup",
            json=settings.model_dump(exclude_none=True),
        )

    async def get_warmup_stats(
        self: "AsyncBaseClient", email_account_id: int
    ) -> WarmupStats:
        data = await self._request("GET", f"/email-accounts/{email_account_id}/warmup")
        return WarmupStats.model_validate(data)

    async def reconnect_email_account(
        self: "AsyncBaseClient", email_account_id: int
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/email-accounts/{email_account_id}/reconnect"
        )

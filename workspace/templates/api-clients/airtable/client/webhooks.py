"""
Airtable Webhooks Mixin

Operations for webhook management.
"""

from typing import TYPE_CHECKING, Any

from ..models import Webhook, WebhookList, WebhookPayload

if TYPE_CHECKING:
    from .base import BaseClient


class WebhooksMixin:
    """Mixin providing webhook operations."""

    async def list_webhooks(
        self: "BaseClient",
        base_id: str,
    ) -> WebhookList:
        """List all webhooks for a base."""
        data = await self._request("GET", f"/v0/bases/{base_id}/webhooks")
        return WebhookList.model_validate(data)

    async def create_webhook(
        self: "BaseClient",
        base_id: str,
        specification: dict[str, Any],
        notification_url: str | None = None,
    ) -> Webhook:
        """
        Create a webhook for a base.

        Args:
            base_id: Base ID (appXXXXXX)
            specification: Webhook specification with filters
            notification_url: URL to receive webhook notifications

        Example specification:
            {
                "options": {
                    "filters": {
                        "dataTypes": ["tableData"],
                        "recordChangeScope": "tblXXXXXX"
                    }
                }
            }
        """
        body: dict[str, Any] = {"specification": specification}
        if notification_url:
            body["notificationUrl"] = notification_url

        data = await self._request("POST", f"/v0/bases/{base_id}/webhooks", json=body)
        return Webhook.model_validate(data)

    async def delete_webhook(
        self: "BaseClient",
        base_id: str,
        webhook_id: str,
    ) -> None:
        """Delete a webhook."""
        await self._request("DELETE", f"/v0/bases/{base_id}/webhooks/{webhook_id}")

    async def get_webhook_payloads(
        self: "BaseClient",
        base_id: str,
        webhook_id: str,
        cursor: int | None = None,
    ) -> WebhookPayload:
        """
        Get payloads for a webhook.

        Args:
            base_id: Base ID (appXXXXXX)
            webhook_id: Webhook ID
            cursor: Cursor for pagination (from previous response)
        """
        params = {"cursor": cursor} if cursor else None
        data = await self._request(
            "GET",
            f"/v0/bases/{base_id}/webhooks/{webhook_id}/payloads",
            params=params,
        )
        return WebhookPayload.model_validate(data)

    async def refresh_webhook(
        self: "BaseClient",
        base_id: str,
        webhook_id: str,
    ) -> None:
        """Refresh a webhook to extend its expiration."""
        await self._request(
            "POST", f"/v0/bases/{base_id}/webhooks/{webhook_id}/refresh"
        )

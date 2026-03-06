"""
ClickUp Webhook endpoints.
"""

from typing import Any, TYPE_CHECKING

from ..models import Webhook, WebhookCreate, WebhooksResponse

if TYPE_CHECKING:
    from .base import BaseClient


class WebhooksMixin:
    """Webhook-related API methods."""

    async def get_webhooks(self: "BaseClient", team_id: str) -> WebhooksResponse:
        """Get all webhooks for a Workspace."""
        data = await self._request("GET", f"/team/{team_id}/webhook")
        return WebhooksResponse.model_validate(data)

    async def create_webhook(
        self: "BaseClient",
        team_id: str,
        webhook: WebhookCreate,
    ) -> Webhook:
        """
        Create a webhook.

        Available events:
        - taskCreated, taskUpdated, taskDeleted, taskPriorityUpdated,
          taskStatusUpdated, taskAssigneeUpdated, taskDueDateUpdated,
          taskTagUpdated, taskMoved, taskCommentPosted, taskCommentUpdated,
          taskTimeEstimateUpdated, taskTimeTrackedUpdated
        - listCreated, listUpdated, listDeleted
        - folderCreated, folderUpdated, folderDeleted
        - spaceCreated, spaceUpdated, spaceDeleted
        - goalCreated, goalUpdated, goalDeleted
        - keyResultCreated, keyResultUpdated, keyResultDeleted
        """
        data = await self._request(
            "POST",
            f"/team/{team_id}/webhook",
            json=webhook.model_dump(exclude_none=True),
        )
        return Webhook.model_validate(data)

    async def update_webhook(
        self: "BaseClient",
        webhook_id: str,
        endpoint: str | None = None,
        events: list[str] | None = None,
        status: str | None = None,
    ) -> Webhook:
        """Update a webhook."""
        json_body: dict[str, Any] = {}
        if endpoint:
            json_body["endpoint"] = endpoint
        if events:
            json_body["events"] = events
        if status:
            json_body["status"] = status

        data = await self._request("PUT", f"/webhook/{webhook_id}", json=json_body)
        return Webhook.model_validate(data)

    async def delete_webhook(self: "BaseClient", webhook_id: str) -> None:
        """Delete a webhook."""
        await self._request("DELETE", f"/webhook/{webhook_id}")

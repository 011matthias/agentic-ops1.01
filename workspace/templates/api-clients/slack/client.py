"""
Slack Web API Client

Python client for Slack's Web API.
https://api.slack.com/methods
"""

from typing import Any
from urllib.parse import urljoin

import httpx

from .models import (
    Attachment,
    AuthTestResponse,
    Block,
    ConversationInfo,
    ConversationsListResponse,
    MessageResponse,
    SlackResponse,
    UserInfo,
    UserInfoResponse,
    UsersListResponse,
)


class SlackError(Exception):
    """Base exception for Slack API errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        response: Any = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.response = response


class AuthenticationError(SlackError):
    """Authentication failed (invalid_auth, account_inactive, token_revoked)."""

    pass


class RateLimitError(SlackError):
    """Rate limit exceeded (ratelimited)."""

    pass


class ChannelNotFoundError(SlackError):
    """Channel not found (channel_not_found)."""

    pass


class SlackClient:
    """
    Slack Web API client.

    Usage:
        client = SlackClient(token="xoxb-...")

        # Post a simple message
        response = client.post_message(
            channel="#general",
            text="Hello from the bot!"
        )

        # Post a message with Block Kit
        response = client.post_message(
            channel="C123456",
            text="Fallback text",
            blocks=[
                {"type": "header", "text": {"type": "plain_text", "text": "Hello!"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "This is *bold*"}}
            ]
        )

        # List channels
        channels = client.list_conversations()
    """

    BASE_URL = "https://slack.com/api/"

    def __init__(
        self,
        token: str,
        timeout: float = 30.0,
        base_url: str | None = None,
    ):
        """
        Initialize Slack client.

        Args:
            token: Bot token (xoxb-...) or user token (xoxp-...)
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.token = token
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to Slack API."""
        url = urljoin(self.base_url, endpoint)

        try:
            response = self._client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=json,
            )
            response.raise_for_status()
            data = response.json()

            # Slack returns 200 even for errors, check "ok" field
            if not data.get("ok", False):
                self._handle_error(data)

            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After", "unknown")
                raise RateLimitError(
                    f"Rate limited. Retry after {retry_after} seconds",
                    error_code="ratelimited",
                    response=e.response,
                )
            raise SlackError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                response=e.response,
            )
        except httpx.RequestError as e:
            raise SlackError(f"Request failed: {e}")

    def _handle_error(self, data: dict[str, Any]) -> None:
        """Handle Slack API errors from response body."""
        error = data.get("error", "unknown_error")
        message = f"Slack API error: {error}"

        if error in ("invalid_auth", "account_inactive", "token_revoked", "not_authed"):
            raise AuthenticationError(message, error_code=error, response=data)
        elif error == "ratelimited":
            raise RateLimitError(message, error_code=error, response=data)
        elif error == "channel_not_found":
            raise ChannelNotFoundError(message, error_code=error, response=data)
        else:
            raise SlackError(message, error_code=error, response=data)

    # ========================================================================
    # Auth
    # ========================================================================

    def auth_test(self) -> AuthTestResponse:
        """
        Test authentication and get info about the token.

        Returns:
            Authentication info including team, user, and bot IDs
        """
        data = self._request("POST", "auth.test")
        return AuthTestResponse.model_validate(data)

    # ========================================================================
    # Chat
    # ========================================================================

    def post_message(
        self,
        channel: str,
        text: str | None = None,
        blocks: list[Block | dict[str, Any]] | None = None,
        attachments: list[Attachment | dict[str, Any]] | None = None,
        thread_ts: str | None = None,
        reply_broadcast: bool | None = None,
        unfurl_links: bool | None = None,
        unfurl_media: bool | None = None,
        mrkdwn: bool = True,
        username: str | None = None,
        icon_url: str | None = None,
        icon_emoji: str | None = None,
    ) -> MessageResponse:
        """
        Post a message to a channel.

        Args:
            channel: Channel ID (C123456) or name (#general)
            text: Message text (required if no blocks)
            blocks: Block Kit blocks for rich formatting
            attachments: Legacy attachments
            thread_ts: Thread timestamp to reply to
            reply_broadcast: Also send reply to channel
            unfurl_links: Enable link unfurling
            unfurl_media: Enable media unfurling
            mrkdwn: Enable mrkdwn formatting
            username: Custom username
            icon_url: Custom icon URL
            icon_emoji: Custom icon emoji (e.g., ":robot_face:")

        Returns:
            Message response with channel and timestamp
        """
        payload: dict[str, Any] = {"channel": channel}

        if text:
            payload["text"] = text
        if blocks:
            payload["blocks"] = [
                b.model_dump() if hasattr(b, "model_dump") else b for b in blocks
            ]
        if attachments:
            payload["attachments"] = [
                a.model_dump() if hasattr(a, "model_dump") else a for a in attachments
            ]
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if reply_broadcast is not None:
            payload["reply_broadcast"] = reply_broadcast
        if unfurl_links is not None:
            payload["unfurl_links"] = unfurl_links
        if unfurl_media is not None:
            payload["unfurl_media"] = unfurl_media
        if mrkdwn is not None:
            payload["mrkdwn"] = mrkdwn
        if username:
            payload["username"] = username
        if icon_url:
            payload["icon_url"] = icon_url
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji

        data = self._request("POST", "chat.postMessage", json=payload)
        return MessageResponse.model_validate(data)

    def update_message(
        self,
        channel: str,
        ts: str,
        text: str | None = None,
        blocks: list[Block | dict[str, Any]] | None = None,
        attachments: list[Attachment | dict[str, Any]] | None = None,
    ) -> MessageResponse:
        """
        Update an existing message.

        Args:
            channel: Channel ID containing the message
            ts: Timestamp of the message to update
            text: New message text
            blocks: New Block Kit blocks
            attachments: New attachments

        Returns:
            Updated message response
        """
        payload: dict[str, Any] = {"channel": channel, "ts": ts}

        if text:
            payload["text"] = text
        if blocks:
            payload["blocks"] = [
                b.model_dump() if hasattr(b, "model_dump") else b for b in blocks
            ]
        if attachments:
            payload["attachments"] = [
                a.model_dump() if hasattr(a, "model_dump") else a for a in attachments
            ]

        data = self._request("POST", "chat.update", json=payload)
        return MessageResponse.model_validate(data)

    def delete_message(self, channel: str, ts: str) -> SlackResponse:
        """
        Delete a message.

        Args:
            channel: Channel ID containing the message
            ts: Timestamp of the message to delete

        Returns:
            Confirmation response
        """
        data = self._request(
            "POST", "chat.delete", json={"channel": channel, "ts": ts}
        )
        return SlackResponse.model_validate(data)

    # ========================================================================
    # Conversations
    # ========================================================================

    def list_conversations(
        self,
        types: str = "public_channel,private_channel",
        exclude_archived: bool = True,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[ConversationInfo]:
        """
        List conversations (channels).

        Args:
            types: Comma-separated types (public_channel, private_channel, mpim, im)
            exclude_archived: Exclude archived channels
            limit: Max results per page
            cursor: Pagination cursor

        Returns:
            List of conversation info
        """
        params: dict[str, Any] = {
            "types": types,
            "exclude_archived": exclude_archived,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        data = self._request("GET", "conversations.list", params=params)
        response = ConversationsListResponse.model_validate(data)
        return response.channels or []

    def get_conversation_info(self, channel: str) -> ConversationInfo:
        """
        Get information about a conversation.

        Args:
            channel: Channel ID

        Returns:
            Conversation info
        """
        data = self._request(
            "GET", "conversations.info", params={"channel": channel}
        )
        return ConversationInfo.model_validate(data.get("channel", {}))

    # ========================================================================
    # Users
    # ========================================================================

    def list_users(
        self,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[UserInfo]:
        """
        List users in the workspace.

        Args:
            limit: Max results per page
            cursor: Pagination cursor

        Returns:
            List of user info
        """
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        data = self._request("GET", "users.list", params=params)
        response = UsersListResponse.model_validate(data)
        return response.members or []

    def get_user_info(self, user: str) -> UserInfo:
        """
        Get information about a user.

        Args:
            user: User ID

        Returns:
            User info
        """
        data = self._request("GET", "users.info", params={"user": user})
        response = UserInfoResponse.model_validate(data)
        return response.user or UserInfo(id=user)

    # ========================================================================
    # Lifecycle
    # ========================================================================

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "SlackClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncSlackClient:
    """
    Async Slack Web API client.

    Usage:
        async with AsyncSlackClient(token="xoxb-...") as client:
            response = await client.post_message(
                channel="#general",
                text="Hello from the bot!"
            )
    """

    BASE_URL = "https://slack.com/api/"

    def __init__(
        self,
        token: str,
        timeout: float = 30.0,
        base_url: str | None = None,
    ):
        self.token = token
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self.base_url, endpoint)

        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=json,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok", False):
                self._handle_error(data)

            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After", "unknown")
                raise RateLimitError(
                    f"Rate limited. Retry after {retry_after} seconds",
                    error_code="ratelimited",
                    response=e.response,
                )
            raise SlackError(f"HTTP {e.response.status_code}: {e.response.text}")

    def _handle_error(self, data: dict[str, Any]) -> None:
        error = data.get("error", "unknown_error")
        message = f"Slack API error: {error}"

        if error in ("invalid_auth", "account_inactive", "token_revoked", "not_authed"):
            raise AuthenticationError(message, error_code=error, response=data)
        elif error == "ratelimited":
            raise RateLimitError(message, error_code=error, response=data)
        elif error == "channel_not_found":
            raise ChannelNotFoundError(message, error_code=error, response=data)
        else:
            raise SlackError(message, error_code=error, response=data)

    async def auth_test(self) -> AuthTestResponse:
        """Test authentication."""
        data = await self._request("POST", "auth.test")
        return AuthTestResponse.model_validate(data)

    async def post_message(
        self,
        channel: str,
        text: str | None = None,
        blocks: list[Block | dict[str, Any]] | None = None,
        attachments: list[Attachment | dict[str, Any]] | None = None,
        thread_ts: str | None = None,
        reply_broadcast: bool | None = None,
        unfurl_links: bool | None = None,
        unfurl_media: bool | None = None,
        mrkdwn: bool = True,
        username: str | None = None,
        icon_url: str | None = None,
        icon_emoji: str | None = None,
    ) -> MessageResponse:
        """Post a message to a channel."""
        payload: dict[str, Any] = {"channel": channel}

        if text:
            payload["text"] = text
        if blocks:
            payload["blocks"] = [
                b.model_dump() if hasattr(b, "model_dump") else b for b in blocks
            ]
        if attachments:
            payload["attachments"] = [
                a.model_dump() if hasattr(a, "model_dump") else a for a in attachments
            ]
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if reply_broadcast is not None:
            payload["reply_broadcast"] = reply_broadcast
        if unfurl_links is not None:
            payload["unfurl_links"] = unfurl_links
        if unfurl_media is not None:
            payload["unfurl_media"] = unfurl_media
        if mrkdwn is not None:
            payload["mrkdwn"] = mrkdwn
        if username:
            payload["username"] = username
        if icon_url:
            payload["icon_url"] = icon_url
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji

        data = await self._request("POST", "chat.postMessage", json=payload)
        return MessageResponse.model_validate(data)

    async def list_conversations(
        self,
        types: str = "public_channel,private_channel",
        exclude_archived: bool = True,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[ConversationInfo]:
        """List conversations."""
        params: dict[str, Any] = {
            "types": types,
            "exclude_archived": exclude_archived,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", "conversations.list", params=params)
        response = ConversationsListResponse.model_validate(data)
        return response.channels or []

    async def get_user_info(self, user: str) -> UserInfo:
        """Get user info."""
        data = await self._request("GET", "users.info", params={"user": user})
        response = UserInfoResponse.model_validate(data)
        return response.user or UserInfo(id=user)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncSlackClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

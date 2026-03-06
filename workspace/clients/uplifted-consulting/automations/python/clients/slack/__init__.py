"""
Slack Web API Client

Python client for Slack's Web API.

Usage:
    from slack import SlackClient

    client = SlackClient(token="xoxb-...")

    # Post a simple message
    response = client.post_message(
        channel="#general",
        text="Hello from the bot!"
    )

    # Post with Block Kit
    response = client.post_message(
        channel="C123456",
        text="Fallback text",
        blocks=[
            {"type": "header", "text": {"type": "plain_text", "text": "Hello!"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "This is *bold*"}}
        ]
    )

    # Async client
    from slack import AsyncSlackClient

    async with AsyncSlackClient(token="xoxb-...") as client:
        response = await client.post_message(
            channel="#general",
            text="Hello!"
        )
"""

from .client import (
    AsyncSlackClient,
    AuthenticationError,
    ChannelNotFoundError,
    RateLimitError,
    SlackClient,
    SlackError,
)
from .models import (
    ActionsBlock,
    Attachment,
    AttachmentField,
    AuthTestResponse,
    Block,
    ButtonElement,
    ContextBlock,
    ConversationInfo,
    ConversationsListResponse,
    DividerBlock,
    HeaderBlock,
    ImageBlock,
    ImageElement,
    MessageResponse,
    SectionBlock,
    SlackResponse,
    TextObject,
    UserInfo,
    UserInfoResponse,
    UsersListResponse,
)

__all__ = [
    # Clients
    "SlackClient",
    "AsyncSlackClient",
    # Errors
    "SlackError",
    "AuthenticationError",
    "RateLimitError",
    "ChannelNotFoundError",
    # Block Kit types
    "Block",
    "HeaderBlock",
    "SectionBlock",
    "DividerBlock",
    "ContextBlock",
    "ActionsBlock",
    "ImageBlock",
    "TextObject",
    "ButtonElement",
    "ImageElement",
    # Attachment types
    "Attachment",
    "AttachmentField",
    # Response types
    "SlackResponse",
    "MessageResponse",
    "ConversationInfo",
    "ConversationsListResponse",
    "UserInfo",
    "UserInfoResponse",
    "UsersListResponse",
    "AuthTestResponse",
]

"""
Slack API Pydantic Models

Request and response types for Slack Web API.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Block Kit Types
# ============================================================================


class TextObject(BaseModel):
    """Text object for Block Kit."""

    type: Literal["plain_text", "mrkdwn"]
    text: str
    emoji: bool | None = None
    verbatim: bool | None = None


class ButtonElement(BaseModel):
    """Button element for Block Kit."""

    type: Literal["button"] = "button"
    text: TextObject
    action_id: str | None = None
    url: str | None = None
    value: str | None = None
    style: Literal["primary", "danger"] | None = None


class ImageElement(BaseModel):
    """Image element for Block Kit."""

    type: Literal["image"] = "image"
    image_url: str
    alt_text: str


class HeaderBlock(BaseModel):
    """Header block."""

    type: Literal["header"] = "header"
    text: TextObject
    block_id: str | None = None


class SectionBlock(BaseModel):
    """Section block."""

    type: Literal["section"] = "section"
    text: TextObject | None = None
    block_id: str | None = None
    fields: list[TextObject] | None = None
    accessory: ButtonElement | ImageElement | dict[str, Any] | None = None


class DividerBlock(BaseModel):
    """Divider block."""

    type: Literal["divider"] = "divider"
    block_id: str | None = None


class ContextBlock(BaseModel):
    """Context block."""

    type: Literal["context"] = "context"
    elements: list[TextObject | ImageElement | dict[str, Any]]
    block_id: str | None = None


class ActionsBlock(BaseModel):
    """Actions block."""

    type: Literal["actions"] = "actions"
    elements: list[ButtonElement | dict[str, Any]]
    block_id: str | None = None


class ImageBlock(BaseModel):
    """Image block."""

    type: Literal["image"] = "image"
    image_url: str
    alt_text: str
    title: TextObject | None = None
    block_id: str | None = None


# Union of all block types
Block = (
    HeaderBlock
    | SectionBlock
    | DividerBlock
    | ContextBlock
    | ActionsBlock
    | ImageBlock
    | dict[str, Any]
)


# ============================================================================
# Attachment Types (Legacy but still used)
# ============================================================================


class AttachmentField(BaseModel):
    """Field in an attachment."""

    title: str
    value: str
    short: bool = False


class Attachment(BaseModel):
    """Message attachment (legacy but widely used)."""

    fallback: str | None = None
    color: str | None = None
    pretext: str | None = None
    author_name: str | None = None
    author_link: str | None = None
    author_icon: str | None = None
    title: str | None = None
    title_link: str | None = None
    text: str | None = None
    fields: list[AttachmentField] | None = None
    image_url: str | None = None
    thumb_url: str | None = None
    footer: str | None = None
    footer_icon: str | None = None
    ts: int | None = None
    mrkdwn_in: list[str] | None = None


# ============================================================================
# Request Types
# ============================================================================


class PostMessageRequest(BaseModel):
    """Request for chat.postMessage."""

    channel: str
    text: str | None = None
    blocks: list[Block] | None = None
    attachments: list[Attachment] | None = None
    thread_ts: str | None = None
    reply_broadcast: bool | None = None
    unfurl_links: bool | None = None
    unfurl_media: bool | None = None
    mrkdwn: bool | None = None
    metadata: dict[str, Any] | None = None
    username: str | None = None
    icon_url: str | None = None
    icon_emoji: str | None = None


class UpdateMessageRequest(BaseModel):
    """Request for chat.update."""

    channel: str
    ts: str
    text: str | None = None
    blocks: list[Block] | None = None
    attachments: list[Attachment] | None = None


# ============================================================================
# Response Types
# ============================================================================


class SlackResponse(BaseModel):
    """Base Slack API response."""

    ok: bool
    error: str | None = None
    warning: str | None = None
    response_metadata: dict[str, Any] | None = None


class MessageResponse(SlackResponse):
    """Response from chat.postMessage and chat.update."""

    channel: str | None = None
    ts: str | None = None
    message: dict[str, Any] | None = None


class ConversationInfo(BaseModel):
    """Conversation/Channel information."""

    id: str
    name: str | None = None
    is_channel: bool | None = None
    is_group: bool | None = None
    is_im: bool | None = None
    is_mpim: bool | None = None
    is_private: bool | None = None
    is_archived: bool | None = None
    is_member: bool | None = None
    topic: dict[str, Any] | None = None
    purpose: dict[str, Any] | None = None
    num_members: int | None = None


class ConversationsListResponse(SlackResponse):
    """Response from conversations.list."""

    channels: list[ConversationInfo] | None = None
    response_metadata: dict[str, Any] | None = None


class UserInfo(BaseModel):
    """User information."""

    id: str
    name: str | None = None
    real_name: str | None = None
    profile: dict[str, Any] | None = None
    is_bot: bool | None = None
    is_admin: bool | None = None


class UsersListResponse(SlackResponse):
    """Response from users.list."""

    members: list[UserInfo] | None = None
    response_metadata: dict[str, Any] | None = None


class UserInfoResponse(SlackResponse):
    """Response from users.info."""

    user: UserInfo | None = None


class AuthTestResponse(SlackResponse):
    """Response from auth.test."""

    url: str | None = None
    team: str | None = None
    user: str | None = None
    team_id: str | None = None
    user_id: str | None = None
    bot_id: str | None = None

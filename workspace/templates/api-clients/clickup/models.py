"""
Pydantic models for ClickUp API v2.

Generated from: https://developer.clickup.com/
API Docs: https://developer.clickup.com/reference
"""

from datetime import datetime
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field


class Priority(IntEnum):
    """Task priority levels in ClickUp."""

    URGENT = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


# ============================================================================
# User & Team (Workspace) Models
# ============================================================================


class User(BaseModel):
    """ClickUp user."""

    id: int
    username: str
    email: str | None = None
    color: str | None = None
    initials: str | None = None
    profilePicture: str | None = None


class Team(BaseModel):
    """ClickUp Team (Workspace in v3 terminology)."""

    id: str
    name: str
    color: str | None = None
    avatar: str | None = None
    members: list[dict[str, Any]] | None = None


class AuthorizedUser(BaseModel):
    """Authorized user response from GET /user."""

    user: User


class AuthorizedTeams(BaseModel):
    """Authorized teams response from GET /team."""

    teams: list[Team]


# ============================================================================
# Space Models
# ============================================================================


class SpaceFeatures(BaseModel):
    """Feature flags for a Space."""

    due_dates: dict[str, Any] | None = None
    time_tracking: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    time_estimates: dict[str, Any] | None = None
    checklists: dict[str, Any] | None = None
    custom_fields: dict[str, Any] | None = None
    remap_dependencies: dict[str, Any] | None = None
    dependency_warning: dict[str, Any] | None = None
    portfolios: dict[str, Any] | None = None


class Space(BaseModel):
    """ClickUp Space."""

    id: str
    name: str
    private: bool = False
    statuses: list[dict[str, Any]] | None = None
    multiple_assignees: bool = False
    features: SpaceFeatures | None = None
    archived: bool = False


class SpaceCreate(BaseModel):
    """Request body for creating a Space."""

    name: str
    multiple_assignees: bool = False
    features: dict[str, Any] | None = None


# ============================================================================
# Folder Models
# ============================================================================


class Folder(BaseModel):
    """ClickUp Folder."""

    id: str
    name: str
    orderindex: int | None = None
    override_statuses: bool = False
    hidden: bool = False
    space: dict[str, Any] | None = None
    task_count: str | None = None
    archived: bool = False
    lists: list[dict[str, Any]] | None = None


class FolderCreate(BaseModel):
    """Request body for creating a Folder."""

    name: str


# ============================================================================
# List Models
# ============================================================================


class Status(BaseModel):
    """Task status definition."""

    id: str | None = None
    status: str
    color: str
    orderindex: int | None = None
    type: str | None = None


class List(BaseModel):
    """ClickUp List."""

    id: str
    name: str
    orderindex: int | None = None
    content: str | None = None
    status: Status | None = None
    priority: dict[str, Any] | None = None
    assignee: User | None = None
    task_count: int | None = None
    due_date: str | None = None
    start_date: str | None = None
    folder: dict[str, Any] | None = None
    space: dict[str, Any] | None = None
    archived: bool = False
    override_statuses: bool = False
    permission_level: str | None = None


class ListCreate(BaseModel):
    """Request body for creating a List."""

    name: str
    content: str | None = None
    due_date: int | None = None  # Unix timestamp in milliseconds
    due_date_time: bool = False
    priority: int | None = None
    assignee: int | None = None  # User ID
    status: str | None = None


# ============================================================================
# Task Models
# ============================================================================


class CustomFieldValue(BaseModel):
    """Custom field with value for task creation/update."""

    id: str
    value: Any


class LinkedTask(BaseModel):
    """Linked task reference."""

    task_id: str
    link_id: str
    date_created: str
    userid: str
    workspace_id: str


class TaskDependency(BaseModel):
    """Task dependency reference."""

    task_id: str
    depends_on: str
    type: int
    date_created: str
    userid: str
    workspace_id: str
    chain_id: str | None = None


class Task(BaseModel):
    """ClickUp Task."""

    id: str
    custom_id: str | None = None
    name: str
    text_content: str | None = None
    description: str | None = None
    status: Status | None = None
    orderindex: str | None = None
    date_created: str | None = None
    date_updated: str | None = None
    date_closed: str | None = None
    date_done: str | None = None
    archived: bool = False
    creator: User | None = None
    assignees: list[User] | None = None
    watchers: list[User] | None = None
    checklists: list[dict[str, Any]] | None = None
    tags: list[dict[str, Any]] | None = None
    parent: str | None = None
    priority: dict[str, Any] | None = None
    due_date: str | None = None
    start_date: str | None = None
    points: float | None = None
    time_estimate: int | None = None  # milliseconds
    time_spent: int | None = None  # milliseconds
    custom_fields: list[dict[str, Any]] | None = None
    dependencies: list[TaskDependency] | None = None
    linked_tasks: list[LinkedTask] | None = None
    team_id: str | None = None
    url: str | None = None
    list: dict[str, Any] | None = None
    project: dict[str, Any] | None = None
    folder: dict[str, Any] | None = None
    space: dict[str, Any] | None = None


class TaskCreate(BaseModel):
    """Request body for creating a Task."""

    name: str
    description: str | None = None
    markdown_description: str | None = None
    assignees: list[int] | None = None  # User IDs
    tags: list[str] | None = None
    status: str | None = None
    priority: int | None = None  # 1=Urgent, 2=High, 3=Normal, 4=Low
    due_date: int | None = None  # Unix timestamp in milliseconds
    due_date_time: bool = False
    time_estimate: int | None = None  # milliseconds
    start_date: int | None = None  # Unix timestamp in milliseconds
    start_date_time: bool = False
    notify_all: bool = False
    parent: str | None = None  # Parent task ID for subtasks
    links_to: str | None = None  # Task ID to create dependency
    check_required_custom_fields: bool = True
    custom_fields: list[CustomFieldValue] | None = None


class TaskUpdate(BaseModel):
    """Request body for updating a Task."""

    name: str | None = None
    description: str | None = None
    markdown_description: str | None = None
    assignees: dict[str, list[int]] | None = None  # {"add": [], "rem": []}
    status: str | None = None
    priority: int | None = None
    due_date: int | None = None
    due_date_time: bool | None = None
    time_estimate: int | None = None
    start_date: int | None = None
    start_date_time: bool | None = None
    archived: bool | None = None
    parent: str | None = None


class TasksResponse(BaseModel):
    """Response for task list endpoints."""

    tasks: list[Task]


# ============================================================================
# Comment Models
# ============================================================================


class CommentTextAttribute(BaseModel):
    """Text attributes for comment formatting."""

    bold: bool | None = None
    italic: bool | None = None
    code: bool | None = None


class CommentText(BaseModel):
    """Text block in a comment."""

    text: str
    attributes: CommentTextAttribute | dict[str, Any] = Field(default_factory=dict)


class Comment(BaseModel):
    """ClickUp Comment."""

    id: str
    comment: list[dict[str, Any]] | None = None
    comment_text: str | None = None
    user: User | None = None
    resolved: bool = False
    assignee: User | None = None
    assigned_by: User | None = None
    reactions: list[dict[str, Any]] | None = None
    date: str | None = None


class CommentCreate(BaseModel):
    """Request body for creating a Comment."""

    comment_text: str | None = None
    comment: list[CommentText] | None = None
    assignee: int | None = None  # User ID
    notify_all: bool = False


class CommentsResponse(BaseModel):
    """Response for comment list endpoints."""

    comments: list[Comment]


# ============================================================================
# Checklist Models
# ============================================================================


class ChecklistItem(BaseModel):
    """Item in a checklist."""

    id: str | None = None
    name: str
    orderindex: int | None = None
    assignee: User | None = None
    resolved: bool = False
    parent: str | None = None
    date_created: str | None = None
    children: list[dict[str, Any]] | None = None


class Checklist(BaseModel):
    """ClickUp Checklist."""

    id: str
    task_id: str | None = None
    name: str
    date_created: str | None = None
    orderindex: int | None = None
    creator: int | None = None
    resolved: int | None = None
    unresolved: int | None = None
    items: list[ChecklistItem] | None = None


class ChecklistCreate(BaseModel):
    """Request body for creating a Checklist."""

    name: str


class ChecklistItemCreate(BaseModel):
    """Request body for creating a Checklist item."""

    name: str
    assignee: int | None = None  # User ID


class ChecklistItemUpdate(BaseModel):
    """Request body for updating a Checklist item."""

    name: str | None = None
    assignee: int | None = None
    resolved: bool | None = None
    parent: str | None = None  # Checklist item ID to nest under


# ============================================================================
# Custom Field Models
# ============================================================================


class CustomField(BaseModel):
    """ClickUp Custom Field definition."""

    id: str
    name: str
    type: str
    type_config: dict[str, Any] | None = None
    date_created: str | None = None
    hide_from_guests: bool = False
    required: bool = False


class CustomFieldsResponse(BaseModel):
    """Response for custom fields list."""

    fields: list[CustomField]


# ============================================================================
# Goal Models
# ============================================================================


class GoalTarget(BaseModel):
    """Target within a Goal."""

    id: str
    name: str
    creator: int | None = None
    owner: User | None = None
    type: str | None = None
    date_created: str | None = None
    start_date: str | None = None
    due_date: str | None = None
    percent_completed: int | None = None
    completed: bool = False


class Goal(BaseModel):
    """ClickUp Goal."""

    id: str
    name: str
    team_id: str | None = None
    date_created: str | None = None
    start_date: str | None = None
    due_date: str | None = None
    description: str | None = None
    private: bool = False
    archived: bool = False
    creator: int | None = None
    color: str | None = None
    pretty_id: str | None = None
    multiple_owners: bool = False
    folder_id: str | None = None
    members: list[dict[str, Any]] | None = None
    owners: list[User] | None = None
    key_results: list[GoalTarget] | None = None
    percent_completed: int | None = None
    history: list[dict[str, Any]] | None = None
    pretty_url: str | None = None


class GoalCreate(BaseModel):
    """Request body for creating a Goal."""

    name: str
    due_date: int | None = None  # Unix timestamp in milliseconds
    description: str | None = None
    multiple_owners: bool = False
    owners: list[int] | None = None  # User IDs
    color: str | None = None


class GoalsResponse(BaseModel):
    """Response for goals list."""

    goals: list[Goal]
    folders: list[dict[str, Any]] | None = None


# ============================================================================
# Webhook Models
# ============================================================================


class Webhook(BaseModel):
    """ClickUp Webhook."""

    id: str
    userid: int | None = None
    team_id: int | None = None
    endpoint: str
    client_id: str | None = None
    events: list[str]
    task_id: str | None = None
    list_id: str | None = None
    folder_id: str | None = None
    space_id: str | None = None
    health: dict[str, Any] | None = None
    secret: str | None = None


class WebhookCreate(BaseModel):
    """Request body for creating a Webhook."""

    endpoint: str
    events: list[str]
    task_id: str | None = None
    list_id: str | None = None
    folder_id: str | None = None
    space_id: str | None = None


class WebhooksResponse(BaseModel):
    """Response for webhooks list."""

    webhooks: list[Webhook]


# ============================================================================
# View Models
# ============================================================================


class View(BaseModel):
    """ClickUp View."""

    id: str
    name: str
    type: str
    parent: dict[str, Any] | None = None
    grouping: dict[str, Any] | None = None
    divide: dict[str, Any] | None = None
    sorting: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    columns: dict[str, Any] | None = None
    team_sidebar: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None


class ViewsResponse(BaseModel):
    """Response for views list."""

    views: list[View]


# ============================================================================
# Time Tracking Models
# ============================================================================


class TimeEntry(BaseModel):
    """ClickUp Time Entry."""

    id: str
    task: dict[str, Any] | None = None
    wid: str | None = None
    user: User | None = None
    billable: bool = False
    start: str
    end: str | None = None
    duration: int  # milliseconds
    description: str | None = None
    tags: list[dict[str, Any]] | None = None
    source: str | None = None
    at: str | None = None


class TimeEntryCreate(BaseModel):
    """Request body for creating a Time Entry."""

    start: int  # Unix timestamp in milliseconds
    end: int | None = None
    time: int | None = None  # Duration in milliseconds (alternative to end)
    description: str | None = None
    tags: list[dict[str, Any]] | None = None
    billable: bool = False
    assignee: int | None = None  # User ID


class TimeEntriesResponse(BaseModel):
    """Response for time entries list."""

    data: list[TimeEntry]


# ============================================================================
# Tag Models
# ============================================================================


class Tag(BaseModel):
    """ClickUp Tag."""

    name: str
    tag_fg: str | None = None
    tag_bg: str | None = None
    creator: int | None = None


class TagsResponse(BaseModel):
    """Response for tags list."""

    tags: list[Tag]


# ============================================================================
# OAuth Models
# ============================================================================


class AccessTokenResponse(BaseModel):
    """Response from OAuth token exchange."""

    access_token: str
    token_type: str | None = None


# ============================================================================
# Error Models
# ============================================================================


class ClickUpError(BaseModel):
    """ClickUp API error response."""

    err: str
    ECODE: str | None = None

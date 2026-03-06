"""
ClickUp API v2 Client Package.

A fully typed async Python client for the ClickUp API.

Usage:
    from clickup import ClickUpClient, TaskCreate, Priority

    async with ClickUpClient(api_token="pk_...") as client:
        # Get workspaces
        teams = await client.get_teams()
        team_id = teams.teams[0].id

        # Get spaces
        spaces = await client.get_spaces(team_id)

        # Create a task
        task = await client.create_task(
            list_id="123",
            task=TaskCreate(
                name="My Task",
                description="Task description",
                priority=Priority.HIGH,
            ),
        )

API Documentation: https://developer.clickup.com/
"""

from .client import ClickUpClient, ClickUpError
from .models import (
    # Enums
    Priority,
    # User & Team
    User,
    Team,
    AuthorizedUser,
    AuthorizedTeams,
    # Space
    Space,
    SpaceCreate,
    SpaceFeatures,
    # Folder
    Folder,
    FolderCreate,
    # List
    List,
    ListCreate,
    Status,
    # Task
    Task,
    TaskCreate,
    TaskUpdate,
    TasksResponse,
    CustomFieldValue,
    LinkedTask,
    TaskDependency,
    # Comment
    Comment,
    CommentCreate,
    CommentsResponse,
    CommentText,
    CommentTextAttribute,
    # Checklist
    Checklist,
    ChecklistCreate,
    ChecklistItem,
    ChecklistItemCreate,
    ChecklistItemUpdate,
    # Custom Field
    CustomField,
    CustomFieldsResponse,
    # Goal
    Goal,
    GoalCreate,
    GoalsResponse,
    GoalTarget,
    # Webhook
    Webhook,
    WebhookCreate,
    WebhooksResponse,
    # View
    View,
    ViewsResponse,
    # Time Tracking
    TimeEntry,
    TimeEntryCreate,
    TimeEntriesResponse,
    # Tag
    Tag,
    TagsResponse,
    # OAuth
    AccessTokenResponse,
)

__all__ = [
    # Client
    "ClickUpClient",
    "ClickUpError",
    # Enums
    "Priority",
    # User & Team
    "User",
    "Team",
    "AuthorizedUser",
    "AuthorizedTeams",
    # Space
    "Space",
    "SpaceCreate",
    "SpaceFeatures",
    # Folder
    "Folder",
    "FolderCreate",
    # List
    "List",
    "ListCreate",
    "Status",
    # Task
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "TasksResponse",
    "CustomFieldValue",
    "LinkedTask",
    "TaskDependency",
    # Comment
    "Comment",
    "CommentCreate",
    "CommentsResponse",
    "CommentText",
    "CommentTextAttribute",
    # Checklist
    "Checklist",
    "ChecklistCreate",
    "ChecklistItem",
    "ChecklistItemCreate",
    "ChecklistItemUpdate",
    # Custom Field
    "CustomField",
    "CustomFieldsResponse",
    # Goal
    "Goal",
    "GoalCreate",
    "GoalsResponse",
    "GoalTarget",
    # Webhook
    "Webhook",
    "WebhookCreate",
    "WebhooksResponse",
    # View
    "View",
    "ViewsResponse",
    # Time Tracking
    "TimeEntry",
    "TimeEntryCreate",
    "TimeEntriesResponse",
    # Tag
    "Tag",
    "TagsResponse",
    # OAuth
    "AccessTokenResponse",
]

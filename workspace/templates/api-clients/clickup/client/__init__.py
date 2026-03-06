"""
ClickUp API v2 Client.

Generated from: https://developer.clickup.com/
API Docs: https://developer.clickup.com/reference

Usage:
    from clickup import ClickUpClient

    # With personal API token
    client = ClickUpClient(api_token="pk_...")

    # With OAuth access token
    client = ClickUpClient(access_token="...")

    async with client:
        # Get workspaces
        teams = await client.get_teams()

        # Get tasks from a list
        tasks = await client.get_tasks(list_id="123")
"""

from .auth import AuthMixin
from .base import BaseClient, ClickUpError
from .checklists import ChecklistsMixin
from .comments import CommentsMixin
from .custom_fields import CustomFieldsMixin
from .folders import FoldersMixin
from .goals import GoalsMixin
from .lists import ListsMixin
from .spaces import SpacesMixin
from .tags import TagsMixin
from .tasks import TasksMixin
from .time_tracking import TimeTrackingMixin
from .views import ViewsMixin
from .webhooks import WebhooksMixin


class ClickUpClient(
    AuthMixin,
    SpacesMixin,
    FoldersMixin,
    ListsMixin,
    TasksMixin,
    CommentsMixin,
    ChecklistsMixin,
    CustomFieldsMixin,
    GoalsMixin,
    TagsMixin,
    TimeTrackingMixin,
    ViewsMixin,
    WebhooksMixin,
    BaseClient,
):
    """
    Async HTTP client for ClickUp API v2.

    Combines all API functionality through mixins:
    - AuthMixin: OAuth and user endpoints
    - SpacesMixin: Space CRUD operations
    - FoldersMixin: Folder CRUD operations
    - ListsMixin: List CRUD operations
    - TasksMixin: Task CRUD, custom fields, dependencies
    - CommentsMixin: Comments on tasks, lists, views
    - ChecklistsMixin: Task checklists
    - CustomFieldsMixin: Custom field definitions
    - GoalsMixin: Goals and key results
    - TagsMixin: Space tags
    - TimeTrackingMixin: Time entries
    - ViewsMixin: Views and view tasks
    - WebhooksMixin: Webhook management

    Rate limits by plan:
    - Free/Unlimited/Business: 100 requests/minute
    - Business Plus: 1,000 requests/minute
    - Enterprise: 10,000 requests/minute

    Example:
        async with ClickUpClient(api_token="pk_...") as client:
            teams = await client.get_teams()
            for team in teams.teams:
                spaces = await client.get_spaces(team.id)
    """

    pass


__all__ = ["ClickUpClient", "ClickUpError"]

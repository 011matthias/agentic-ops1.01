"""
ClickUp Goal endpoints.
"""

from typing import TYPE_CHECKING

from ..models import Goal, GoalCreate, GoalsResponse

if TYPE_CHECKING:
    from .base import BaseClient


class GoalsMixin:
    """Goal-related API methods."""

    async def get_goals(
        self: "BaseClient",
        team_id: str,
        include_completed: bool = False,
    ) -> GoalsResponse:
        """Get all goals in a Workspace."""
        data = await self._request(
            "GET",
            f"/team/{team_id}/goal",
            params={"include_completed": str(include_completed).lower()},
        )
        return GoalsResponse.model_validate(data)

    async def create_goal(
        self: "BaseClient",
        team_id: str,
        goal: GoalCreate,
    ) -> Goal:
        """Create a new goal."""
        data = await self._request(
            "POST",
            f"/team/{team_id}/goal",
            json=goal.model_dump(exclude_none=True),
        )
        return Goal.model_validate(data.get("goal", data))

    async def get_goal(self: "BaseClient", goal_id: str) -> Goal:
        """Get a goal by ID."""
        data = await self._request("GET", f"/goal/{goal_id}")
        return Goal.model_validate(data.get("goal", data))

    async def update_goal(self: "BaseClient", goal_id: str, **kwargs) -> Goal:
        """Update a goal."""
        data = await self._request("PUT", f"/goal/{goal_id}", json=kwargs)
        return Goal.model_validate(data.get("goal", data))

    async def delete_goal(self: "BaseClient", goal_id: str) -> None:
        """Delete a goal."""
        await self._request("DELETE", f"/goal/{goal_id}")

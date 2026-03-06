"""
ClickUp Custom Fields endpoints.
"""

from typing import TYPE_CHECKING

from ..models import CustomFieldsResponse

if TYPE_CHECKING:
    from .base import BaseClient


class CustomFieldsMixin:
    """Custom field-related API methods."""

    async def get_accessible_custom_fields(
        self: "BaseClient",
        list_id: str,
    ) -> CustomFieldsResponse:
        """Get custom fields accessible in a List."""
        data = await self._request("GET", f"/list/{list_id}/field")
        return CustomFieldsResponse.model_validate(data)

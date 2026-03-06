"""
Airtable Metadata Mixin

Operations for bases, tables, and fields schema.
"""

from typing import TYPE_CHECKING, Any

from ..models import (
    BaseInfo,
    BasesResponse,
    BaseSchemaResponse,
    CreateFieldRequest,
    CreateTableRequest,
    FieldSchema,
    TableSchema,
)

if TYPE_CHECKING:
    from .base import BaseClient


class MetadataMixin:
    """Mixin providing metadata/schema operations."""

    # =========================================================================
    # Bases
    # =========================================================================

    async def list_bases(
        self: "BaseClient",
        offset: str | None = None,
    ) -> BasesResponse:
        """List all accessible bases."""
        params = {"offset": offset} if offset else None
        data = await self._request("GET", "/v0/meta/bases", params=params)
        return BasesResponse.model_validate(data)

    async def get_base_schema(
        self: "BaseClient",
        base_id: str,
    ) -> BaseSchemaResponse:
        """Get schema for all tables in a base."""
        data = await self._request("GET", f"/v0/meta/bases/{base_id}/tables")
        return BaseSchemaResponse.model_validate(data)

    async def create_base(
        self: "BaseClient",
        workspace_id: str,
        name: str,
        tables: list[CreateTableRequest],
    ) -> BaseInfo:
        """Create a new base in a workspace."""
        data = await self._request(
            "POST",
            "/v0/meta/bases",
            json={
                "workspaceId": workspace_id,
                "name": name,
                "tables": [
                    t.model_dump(by_alias=True, exclude_none=True) for t in tables
                ],
            },
        )
        return BaseInfo.model_validate(data)

    # =========================================================================
    # Tables
    # =========================================================================

    async def create_table(
        self: "BaseClient",
        base_id: str,
        name: str,
        fields: list[CreateFieldRequest],
        description: str | None = None,
    ) -> TableSchema:
        """Create a new table in a base."""
        body: dict[str, Any] = {
            "name": name,
            "fields": [f.model_dump(exclude_none=True) for f in fields],
        }
        if description:
            body["description"] = description

        data = await self._request(
            "POST", f"/v0/meta/bases/{base_id}/tables", json=body
        )
        return TableSchema.model_validate(data)

    async def update_table(
        self: "BaseClient",
        base_id: str,
        table_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> TableSchema:
        """Update a table's name or description."""
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        if description is not None:
            body["description"] = description

        data = await self._request(
            "PATCH", f"/v0/meta/bases/{base_id}/tables/{table_id}", json=body
        )
        return TableSchema.model_validate(data)

    # =========================================================================
    # Fields
    # =========================================================================

    async def create_field(
        self: "BaseClient",
        base_id: str,
        table_id: str,
        name: str,
        field_type: str,
        description: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> FieldSchema:
        """
        Create a new field in a table.

        Args:
            base_id: Base ID (appXXXXXX)
            table_id: Table ID (tblXXXXXX)
            name: Field name
            field_type: Field type (e.g., 'singleLineText', 'number', 'singleSelect')
            description: Optional field description
            options: Field-specific options (e.g., choices for select fields)
        """
        body: dict[str, Any] = {"name": name, "type": field_type}
        if description:
            body["description"] = description
        if options:
            body["options"] = options

        data = await self._request(
            "POST", f"/v0/meta/bases/{base_id}/tables/{table_id}/fields", json=body
        )
        return FieldSchema.model_validate(data)

    async def update_field(
        self: "BaseClient",
        base_id: str,
        table_id: str,
        field_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> FieldSchema:
        """Update a field's name or description."""
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        if description is not None:
            body["description"] = description

        data = await self._request(
            "PATCH",
            f"/v0/meta/bases/{base_id}/tables/{table_id}/fields/{field_id}",
            json=body,
        )
        return FieldSchema.model_validate(data)

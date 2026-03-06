"""
Airtable Records Mixin

CRUD operations for records: list, get, create, update, upsert, delete.
"""

from typing import TYPE_CHECKING, Any

from ..models import (
    CellFormat,
    DeletedRecord,
    Record,
    RecordList,
    SortConfig,
)

if TYPE_CHECKING:
    from .base import BaseClient


class RecordsMixin:
    """Mixin providing record CRUD operations."""

    async def list_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        *,
        fields: list[str] | None = None,
        filter_by_formula: str | None = None,
        max_records: int | None = None,
        page_size: int | None = None,
        sort: list[SortConfig] | None = None,
        view: str | None = None,
        cell_format: CellFormat | None = None,
        time_zone: str | None = None,
        user_locale: str | None = None,
        offset: str | None = None,
    ) -> RecordList:
        """
        List records from a table.

        Args:
            base_id: The base ID (appXXXXXX)
            table_id_or_name: Table ID (tblXXXXXX) or table name
            fields: Only return specified fields
            filter_by_formula: Airtable formula to filter records
            max_records: Maximum total records to return
            page_size: Records per page (max 100)
            sort: Sort configuration
            view: Filter by view ID or name
            cell_format: Return values as JSON or string
            time_zone: For string cell format
            user_locale: For string cell format
            offset: Pagination offset from previous response
        """
        params: dict[str, Any] = {}

        if fields:
            params["fields[]"] = fields
        if filter_by_formula:
            params["filterByFormula"] = filter_by_formula
        if max_records:
            params["maxRecords"] = max_records
        if page_size:
            params["pageSize"] = min(page_size, self.MAX_PAGE_SIZE)
        if sort:
            params["sort"] = [
                {"field": s.field, "direction": s.direction.value} for s in sort
            ]
        if view:
            params["view"] = view
        if cell_format:
            params["cellFormat"] = cell_format.value
        if time_zone:
            params["timeZone"] = time_zone
        if user_locale:
            params["userLocale"] = user_locale
        if offset:
            params["offset"] = offset

        data = await self._request(
            "GET", f"/v0/{base_id}/{table_id_or_name}", params=params
        )
        return RecordList.model_validate(data)

    async def list_all_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        **kwargs,
    ) -> list[Record]:
        """Fetch all records, handling pagination automatically."""
        all_records: list[Record] = []
        offset: str | None = None

        while True:
            result = await self.list_records(
                base_id, table_id_or_name, offset=offset, **kwargs
            )
            all_records.extend(result.records)

            if not result.offset:
                break
            offset = result.offset

        return all_records

    async def get_record(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        record_id: str,
        *,
        cell_format: CellFormat | None = None,
        time_zone: str | None = None,
        user_locale: str | None = None,
    ) -> Record:
        """Get a single record by ID."""
        params: dict[str, Any] = {}
        if cell_format:
            params["cellFormat"] = cell_format.value
        if time_zone:
            params["timeZone"] = time_zone
        if user_locale:
            params["userLocale"] = user_locale

        data = await self._request(
            "GET",
            f"/v0/{base_id}/{table_id_or_name}/{record_id}",
            params=params if params else None,
        )
        return Record.model_validate(data)

    async def create_record(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        fields: dict[str, Any],
        *,
        typecast: bool = False,
    ) -> Record:
        """Create a single record."""
        body: dict[str, Any] = {"fields": fields}
        if typecast:
            body["typecast"] = True

        data = await self._request(
            "POST", f"/v0/{base_id}/{table_id_or_name}", json=body
        )
        return Record.model_validate(data)

    async def create_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        records: list[dict[str, Any]],
        *,
        typecast: bool = False,
    ) -> list[Record]:
        """
        Create multiple records (max 10 per request).

        For more than 10 records, use batch_create_records().
        """
        if len(records) > self.MAX_RECORDS_PER_BATCH:
            raise ValueError(f"Max {self.MAX_RECORDS_PER_BATCH} records per request")

        body: dict[str, Any] = {
            "records": [{"fields": r} for r in records],
        }
        if typecast:
            body["typecast"] = True

        data = await self._request(
            "POST", f"/v0/{base_id}/{table_id_or_name}", json=body
        )
        return [Record.model_validate(r) for r in data["records"]]

    async def batch_create_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        records: list[dict[str, Any]],
        *,
        typecast: bool = False,
    ) -> list[Record]:
        """Create records in batches, handling the 10-record limit."""
        all_created: list[Record] = []

        for chunk in self._chunk(records, self.MAX_RECORDS_PER_BATCH):
            created = await self.create_records(
                base_id, table_id_or_name, chunk, typecast=typecast
            )
            all_created.extend(created)

        return all_created

    async def update_record(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        record_id: str,
        fields: dict[str, Any],
        *,
        typecast: bool = False,
        replace: bool = False,
    ) -> Record:
        """
        Update a single record.

        Args:
            replace: If True, replaces entire record (PUT). Default False (PATCH).
        """
        body: dict[str, Any] = {"fields": fields}
        if typecast:
            body["typecast"] = True

        method = "PUT" if replace else "PATCH"
        data = await self._request(
            method, f"/v0/{base_id}/{table_id_or_name}/{record_id}", json=body
        )
        return Record.model_validate(data)

    async def update_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        records: list[dict[str, Any]],
        *,
        typecast: bool = False,
        replace: bool = False,
    ) -> list[Record]:
        """
        Update multiple records (max 10 per request).

        Records should have format: [{"id": "recXXX", "fields": {...}}, ...]
        """
        if len(records) > self.MAX_RECORDS_PER_BATCH:
            raise ValueError(f"Max {self.MAX_RECORDS_PER_BATCH} records per request")

        body: dict[str, Any] = {"records": records}
        if typecast:
            body["typecast"] = True

        method = "PUT" if replace else "PATCH"
        data = await self._request(
            method, f"/v0/{base_id}/{table_id_or_name}", json=body
        )
        return [Record.model_validate(r) for r in data["records"]]

    async def batch_update_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        records: list[dict[str, Any]],
        *,
        typecast: bool = False,
        replace: bool = False,
    ) -> list[Record]:
        """Update records in batches, handling the 10-record limit."""
        all_updated: list[Record] = []

        for chunk in self._chunk(records, self.MAX_RECORDS_PER_BATCH):
            updated = await self.update_records(
                base_id, table_id_or_name, chunk, typecast=typecast, replace=replace
            )
            all_updated.extend(updated)

        return all_updated

    async def upsert_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        records: list[dict[str, Any]],
        fields_to_merge_on: list[str],
        *,
        typecast: bool = False,
        replace: bool = False,
    ) -> list[Record]:
        """
        Create or update records based on matching fields.

        Args:
            fields_to_merge_on: Field names to match for existing records
        """
        if len(records) > self.MAX_RECORDS_PER_BATCH:
            raise ValueError(f"Max {self.MAX_RECORDS_PER_BATCH} records per request")

        body: dict[str, Any] = {
            "records": [{"fields": r} for r in records],
            "performUpsert": {"fieldsToMergeOn": fields_to_merge_on},
        }
        if typecast:
            body["typecast"] = True

        method = "PUT" if replace else "PATCH"
        data = await self._request(
            method, f"/v0/{base_id}/{table_id_or_name}", json=body
        )
        return [Record.model_validate(r) for r in data["records"]]

    async def delete_record(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        record_id: str,
    ) -> DeletedRecord:
        """Delete a single record."""
        data = await self._request(
            "DELETE", f"/v0/{base_id}/{table_id_or_name}/{record_id}"
        )
        return DeletedRecord.model_validate(data)

    async def delete_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        record_ids: list[str],
    ) -> list[DeletedRecord]:
        """Delete multiple records (max 10 per request)."""
        if len(record_ids) > self.MAX_RECORDS_PER_BATCH:
            raise ValueError(f"Max {self.MAX_RECORDS_PER_BATCH} records per request")

        # Delete uses query params, not body
        params = {"records[]": record_ids}
        data = await self._request(
            "DELETE", f"/v0/{base_id}/{table_id_or_name}", params=params
        )
        return [DeletedRecord.model_validate(r) for r in data["records"]]

    async def batch_delete_records(
        self: "BaseClient",
        base_id: str,
        table_id_or_name: str,
        record_ids: list[str],
    ) -> list[DeletedRecord]:
        """Delete records in batches, handling the 10-record limit."""
        all_deleted: list[DeletedRecord] = []

        for chunk in self._chunk(record_ids, self.MAX_RECORDS_PER_BATCH):
            deleted = await self.delete_records(base_id, table_id_or_name, chunk)
            all_deleted.extend(deleted)

        return all_deleted

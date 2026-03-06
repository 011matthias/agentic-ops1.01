"""
Airtable Client - Composed from Mixins

Usage:
    from airtable import AirtableClient, AirtableConfig

    config = AirtableConfig(api_key="pat...")
    async with AirtableClient(config) as client:
        records = await client.list_records("appXXX", "tblXXX")
"""

import asyncio

from ..models import (
    BasesResponse,
    BaseSchemaResponse,
    DeletedRecord,
    Record,
    RecordList,
)
from .base import (
    AirtableAuthError,
    AirtableConfig,
    AirtableError,
    AirtableNotFoundError,
    AirtableRateLimitError,
    AirtableValidationError,
    BaseClient,
)
from .comments import CommentsMixin
from .metadata import MetadataMixin
from .records import RecordsMixin
from .webhooks import WebhooksMixin


class AirtableClient(
    RecordsMixin,
    MetadataMixin,
    CommentsMixin,
    WebhooksMixin,
    BaseClient,  # Must be last - provides _request and other base methods
):
    """
    Full Airtable API client with all methods.

    Composed from mixins:
    - RecordsMixin: list, get, create, update, delete records
    - MetadataMixin: bases, tables, fields schema
    - CommentsMixin: record comments
    - WebhooksMixin: webhook management
    """

    pass


class AirtableClientSync:
    """
    Synchronous wrapper around AirtableClient.

    For simple scripts that don't need async.
    """

    def __init__(self, config: AirtableConfig):
        self.config = config
        self._async_client: AirtableClient | None = None

    def __enter__(self) -> "AirtableClientSync":
        self._async_client = AirtableClient(self.config)
        asyncio.get_event_loop().run_until_complete(self._async_client.__aenter__())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._async_client:
            asyncio.get_event_loop().run_until_complete(
                self._async_client.__aexit__(exc_type, exc_val, exc_tb)
            )

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # =========================================================================
    # Records
    # =========================================================================

    def list_records(self, base_id: str, table_id: str, **kwargs) -> RecordList:
        return self._run(self._async_client.list_records(base_id, table_id, **kwargs))

    def list_all_records(self, base_id: str, table_id: str, **kwargs) -> list[Record]:
        return self._run(
            self._async_client.list_all_records(base_id, table_id, **kwargs)
        )

    def get_record(
        self, base_id: str, table_id: str, record_id: str, **kwargs
    ) -> Record:
        return self._run(
            self._async_client.get_record(base_id, table_id, record_id, **kwargs)
        )

    def create_record(
        self, base_id: str, table_id: str, fields: dict, **kwargs
    ) -> Record:
        return self._run(
            self._async_client.create_record(base_id, table_id, fields, **kwargs)
        )

    def create_records(
        self, base_id: str, table_id: str, records: list, **kwargs
    ) -> list[Record]:
        return self._run(
            self._async_client.create_records(base_id, table_id, records, **kwargs)
        )

    def batch_create_records(
        self, base_id: str, table_id: str, records: list, **kwargs
    ) -> list[Record]:
        return self._run(
            self._async_client.batch_create_records(
                base_id, table_id, records, **kwargs
            )
        )

    def update_record(
        self, base_id: str, table_id: str, record_id: str, fields: dict, **kwargs
    ) -> Record:
        return self._run(
            self._async_client.update_record(
                base_id, table_id, record_id, fields, **kwargs
            )
        )

    def update_records(
        self, base_id: str, table_id: str, records: list, **kwargs
    ) -> list[Record]:
        return self._run(
            self._async_client.update_records(base_id, table_id, records, **kwargs)
        )

    def batch_update_records(
        self, base_id: str, table_id: str, records: list, **kwargs
    ) -> list[Record]:
        return self._run(
            self._async_client.batch_update_records(
                base_id, table_id, records, **kwargs
            )
        )

    def upsert_records(
        self,
        base_id: str,
        table_id: str,
        records: list,
        fields_to_merge_on: list,
        **kwargs,
    ) -> list[Record]:
        return self._run(
            self._async_client.upsert_records(
                base_id, table_id, records, fields_to_merge_on, **kwargs
            )
        )

    def delete_record(
        self, base_id: str, table_id: str, record_id: str
    ) -> DeletedRecord:
        return self._run(
            self._async_client.delete_record(base_id, table_id, record_id)
        )

    def delete_records(
        self, base_id: str, table_id: str, record_ids: list
    ) -> list[DeletedRecord]:
        return self._run(
            self._async_client.delete_records(base_id, table_id, record_ids)
        )

    def batch_delete_records(
        self, base_id: str, table_id: str, record_ids: list
    ) -> list[DeletedRecord]:
        return self._run(
            self._async_client.batch_delete_records(base_id, table_id, record_ids)
        )

    # =========================================================================
    # Metadata
    # =========================================================================

    def list_bases(self, **kwargs) -> BasesResponse:
        return self._run(self._async_client.list_bases(**kwargs))

    def get_base_schema(self, base_id: str) -> BaseSchemaResponse:
        return self._run(self._async_client.get_base_schema(base_id))


__all__ = [
    # Client classes
    "AirtableClient",
    "AirtableClientSync",
    "AirtableConfig",
    # Exceptions
    "AirtableError",
    "AirtableAuthError",
    "AirtableNotFoundError",
    "AirtableRateLimitError",
    "AirtableValidationError",
    # Base class (for type hints)
    "BaseClient",
]

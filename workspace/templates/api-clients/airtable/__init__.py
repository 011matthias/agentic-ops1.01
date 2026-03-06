"""
Airtable API Client

A typed Python client for the Airtable Web API using httpx and Pydantic.
"""

from .client import (
    AirtableClient,
    AirtableClientSync,
    AirtableConfig,
    AirtableAuthError,
    AirtableError,
    AirtableNotFoundError,
    AirtableRateLimitError,
    AirtableValidationError,
)
from .models import (
    Attachment,
    BaseInfo,
    BasesResponse,
    BaseSchemaResponse,
    CellFormat,
    Collaborator,
    Comment,
    CommentList,
    CreateCommentRequest,
    CreateFieldRequest,
    CreateRecordsRequest,
    CreateTableRequest,
    DeletedRecord,
    DeletedRecordList,
    FieldOptions,
    FieldSchema,
    FieldType,
    Record,
    RecordFields,
    RecordFieldsWithId,
    RecordList,
    SelectOption,
    SortConfig,
    SortDirection,
    TableSchema,
    Thumbnail,
    Thumbnails,
    UpdateRecordsRequest,
    UpsertConfig,
    UpsertRecordsRequest,
    ViewSchema,
    Webhook,
    WebhookList,
    WebhookPayload,
)

__all__ = [
    # Client
    "AirtableClient",
    "AirtableClientSync",
    "AirtableConfig",
    # Exceptions
    "AirtableError",
    "AirtableAuthError",
    "AirtableNotFoundError",
    "AirtableRateLimitError",
    "AirtableValidationError",
    # Enums
    "CellFormat",
    "FieldType",
    "SortDirection",
    # Record models
    "Record",
    "RecordList",
    "RecordFields",
    "RecordFieldsWithId",
    "DeletedRecord",
    "DeletedRecordList",
    # Request models
    "CreateRecordsRequest",
    "UpdateRecordsRequest",
    "UpsertConfig",
    "UpsertRecordsRequest",
    "SortConfig",
    # Schema models
    "BaseInfo",
    "BasesResponse",
    "BaseSchemaResponse",
    "TableSchema",
    "FieldSchema",
    "FieldOptions",
    "ViewSchema",
    "SelectOption",
    "CreateFieldRequest",
    "CreateTableRequest",
    # Field value types
    "Attachment",
    "Thumbnail",
    "Thumbnails",
    "Collaborator",
    # Comments
    "Comment",
    "CommentList",
    "CreateCommentRequest",
    # Webhooks
    "Webhook",
    "WebhookList",
    "WebhookPayload",
]

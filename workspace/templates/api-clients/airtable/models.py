"""
Airtable API Pydantic Models

Generated from Airtable Web API documentation.
Docs: https://airtable.com/developers/web/api
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Field Types Enum
# =============================================================================


class FieldType(str, Enum):
    """Supported Airtable field types."""

    SINGLE_LINE_TEXT = "singleLineText"
    MULTILINE_TEXT = "multilineText"
    RICH_TEXT = "richText"
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"
    CHECKBOX = "checkbox"
    DATE = "date"
    DATE_TIME = "dateTime"
    DURATION = "duration"
    EMAIL = "email"
    PHONE_NUMBER = "phoneNumber"
    URL = "url"
    RATING = "rating"
    SINGLE_SELECT = "singleSelect"
    MULTIPLE_SELECTS = "multipleSelects"
    SINGLE_COLLABORATOR = "singleCollaborator"
    MULTIPLE_COLLABORATORS = "multipleCollaborators"
    MULTIPLE_RECORD_LINKS = "multipleRecordLinks"
    MULTIPLE_ATTACHMENTS = "multipleAttachments"
    MULTIPLE_LOOKUP_VALUES = "multipleLookupValues"
    ROLLUP = "rollup"
    COUNT = "count"
    FORMULA = "formula"
    AUTO_NUMBER = "autoNumber"
    BARCODE = "barcode"
    BUTTON = "button"
    CREATED_TIME = "createdTime"
    CREATED_BY = "createdBy"
    LAST_MODIFIED_TIME = "lastModifiedTime"
    LAST_MODIFIED_BY = "lastModifiedBy"
    AI_TEXT = "aiText"
    EXTERNAL_SYNC_SOURCE = "externalSyncSource"


class SortDirection(str, Enum):
    """Sort direction for queries."""

    ASC = "asc"
    DESC = "desc"


class CellFormat(str, Enum):
    """Cell format for record values."""

    JSON = "json"
    STRING = "string"


# =============================================================================
# Attachment & Thumbnail Models
# =============================================================================


class Thumbnail(BaseModel):
    """Thumbnail for an attachment."""

    url: str
    width: int
    height: int


class Thumbnails(BaseModel):
    """Container for attachment thumbnails."""

    small: Thumbnail | None = None
    large: Thumbnail | None = None
    full: Thumbnail | None = None


class Attachment(BaseModel):
    """Attachment field value."""

    id: str
    url: str
    filename: str
    size: int | None = None
    type: str | None = None
    width: int | None = None
    height: int | None = None
    thumbnails: Thumbnails | None = None


# =============================================================================
# Collaborator Models
# =============================================================================


class Collaborator(BaseModel):
    """User/collaborator reference."""

    id: str
    email: str
    name: str | None = None


# =============================================================================
# Record Models
# =============================================================================


class Record(BaseModel):
    """A single Airtable record."""

    id: str
    created_time: datetime = Field(alias="createdTime")
    fields: dict[str, Any]

    class Config:
        populate_by_name = True


class RecordList(BaseModel):
    """Response from list records endpoint."""

    records: list[Record]
    offset: str | None = None


class DeletedRecord(BaseModel):
    """Response from delete record endpoint."""

    id: str
    deleted: bool


class DeletedRecordList(BaseModel):
    """Response from batch delete records."""

    records: list[DeletedRecord]


# =============================================================================
# Request Models
# =============================================================================


class RecordFields(BaseModel):
    """Fields for creating/updating a record."""

    fields: dict[str, Any]


class RecordFieldsWithId(BaseModel):
    """Fields for updating a record with ID."""

    id: str
    fields: dict[str, Any]


class CreateRecordsRequest(BaseModel):
    """Request body for creating records."""

    records: list[RecordFields]
    typecast: bool = False


class UpdateRecordsRequest(BaseModel):
    """Request body for updating records."""

    records: list[RecordFieldsWithId]
    typecast: bool = False


class UpsertConfig(BaseModel):
    """Configuration for upsert operations."""

    fields_to_merge_on: list[str] = Field(alias="fieldsToMergeOn")

    class Config:
        populate_by_name = True


class UpsertRecordsRequest(BaseModel):
    """Request body for upserting records."""

    records: list[RecordFields]
    perform_upsert: UpsertConfig = Field(alias="performUpsert")
    typecast: bool = False

    class Config:
        populate_by_name = True


class SortConfig(BaseModel):
    """Sort configuration for list queries."""

    field: str
    direction: SortDirection = SortDirection.ASC


# =============================================================================
# Schema/Metadata Models
# =============================================================================


class SelectOption(BaseModel):
    """Option for single/multiple select fields."""

    id: str | None = None
    name: str
    color: str | None = None


class FieldOptions(BaseModel):
    """Field-specific options (varies by field type)."""

    # For select fields
    choices: list[SelectOption] | None = None

    # For number/currency fields
    precision: int | None = None

    # For currency fields
    symbol: str | None = None

    # For linked records
    linked_table_id: str | None = Field(default=None, alias="linkedTableId")
    prefer_single_record_link: bool | None = Field(
        default=None, alias="preferSingleRecordLink"
    )
    inverse_link_field_id: str | None = Field(
        default=None, alias="inverseLinkFieldId"
    )

    # For formula/rollup/lookup
    formula: str | None = None
    field_id_in_linked_table: str | None = Field(
        default=None, alias="fieldIdInLinkedTable"
    )
    result: dict[str, Any] | None = None

    # For rating
    icon: str | None = None
    max: int | None = None
    color: str | None = None

    # For date/datetime
    date_format: dict[str, Any] | None = Field(default=None, alias="dateFormat")
    time_format: dict[str, Any] | None = Field(default=None, alias="timeFormat")
    time_zone: str | None = Field(default=None, alias="timeZone")

    class Config:
        populate_by_name = True
        extra = "allow"


class FieldSchema(BaseModel):
    """Schema definition for a field."""

    id: str
    name: str
    type: str
    description: str | None = None
    options: FieldOptions | None = None


class ViewSchema(BaseModel):
    """Schema definition for a view."""

    id: str
    name: str
    type: str


class TableSchema(BaseModel):
    """Schema definition for a table."""

    id: str
    name: str
    description: str | None = None
    primary_field_id: str = Field(alias="primaryFieldId")
    fields: list[FieldSchema]
    views: list[ViewSchema]

    class Config:
        populate_by_name = True


class BaseSchemaResponse(BaseModel):
    """Response from get base schema endpoint."""

    tables: list[TableSchema]


class BaseInfo(BaseModel):
    """Information about a base."""

    id: str
    name: str
    permission_level: str = Field(alias="permissionLevel")

    class Config:
        populate_by_name = True


class BasesResponse(BaseModel):
    """Response from list bases endpoint."""

    bases: list[BaseInfo]
    offset: str | None = None


# =============================================================================
# Create Table/Field Request Models
# =============================================================================


class CreateFieldRequest(BaseModel):
    """Request to create a new field."""

    name: str
    type: str
    description: str | None = None
    options: dict[str, Any] | None = None


class CreateTableRequest(BaseModel):
    """Request to create a new table."""

    name: str
    description: str | None = None
    fields: list[CreateFieldRequest]


class CreateBaseRequest(BaseModel):
    """Request to create a new base."""

    name: str
    workspace_id: str = Field(alias="workspaceId")
    tables: list[CreateTableRequest]

    class Config:
        populate_by_name = True


# =============================================================================
# Comment Models
# =============================================================================


class Author(BaseModel):
    """Author of a comment."""

    id: str
    email: str
    name: str | None = None


class Comment(BaseModel):
    """A comment on a record."""

    id: str
    author: Author
    text: str
    created_time: datetime = Field(alias="createdTime")
    mentioned: dict[str, Collaborator] | None = None

    class Config:
        populate_by_name = True


class CommentList(BaseModel):
    """List of comments response."""

    comments: list[Comment]
    offset: str | None = None


class CreateCommentRequest(BaseModel):
    """Request to create a comment."""

    text: str


# =============================================================================
# Webhook Models
# =============================================================================


class WebhookSpecification(BaseModel):
    """Webhook specification."""

    options: dict[str, Any]


class WebhookNotificationUrl(BaseModel):
    """Webhook notification URL configuration."""

    url: str


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook."""

    notification_url: str | None = Field(default=None, alias="notificationUrl")
    specification: WebhookSpecification

    class Config:
        populate_by_name = True


class Webhook(BaseModel):
    """Webhook information."""

    id: str
    mac_secret_base64: str = Field(alias="macSecretBase64")
    notification_url: str | None = Field(default=None, alias="notificationUrl")
    cursor_for_next_payload: int = Field(alias="cursorForNextPayload")
    are_notifications_enabled: bool = Field(alias="areNotificationsEnabled")
    is_hook_enabled: bool = Field(alias="isHookEnabled")
    expiration_time: datetime | None = Field(default=None, alias="expirationTime")
    specification: WebhookSpecification | None = None

    class Config:
        populate_by_name = True


class WebhookList(BaseModel):
    """List of webhooks response."""

    webhooks: list[Webhook]


class WebhookPayload(BaseModel):
    """Webhook payload response."""

    cursor: int
    might_have_more: bool = Field(alias="mightHaveMore")
    payloads: list[dict[str, Any]]

    class Config:
        populate_by_name = True

# Airtable API Client

A typed Python client for the Airtable Web API using httpx and Pydantic.

## Structure

```
airtable/
├── __init__.py           # Package exports
├── models.py             # All Pydantic models
└── client/
    ├── __init__.py       # Main client composing all mixins
    ├── base.py           # BaseClient with HTTP handling
    ├── records.py        # RecordsMixin - CRUD operations
    ├── metadata.py       # MetadataMixin - bases, tables, fields
    ├── comments.py       # CommentsMixin - record comments
    └── webhooks.py       # WebhooksMixin - webhook management
```

## Installation

```bash
pip install httpx pydantic
```

## Quick Start

```python
import asyncio
from airtable import AirtableClient, AirtableConfig

async def main():
    config = AirtableConfig(api_key="patXXXXXXXXXXXXXX")

    async with AirtableClient(config) as client:
        # List all records
        records = await client.list_records("appXXXXXX", "tblXXXXXX")
        for record in records.records:
            print(record.id, record.fields)

asyncio.run(main())
```

## Synchronous Usage

```python
from airtable import AirtableClientSync, AirtableConfig

config = AirtableConfig(api_key="patXXXXXXXXXXXXXX")

with AirtableClientSync(config) as client:
    records = client.list_records("appXXXXXX", "tblXXXXXX")
    print(records.records)
```

## API Reference

### Configuration

```python
from airtable import AirtableConfig

config = AirtableConfig(
    api_key="patXXXXXXXXXXXXXX",  # Personal access token
    base_url="https://api.airtable.com",  # Default
    timeout=30.0,  # Request timeout in seconds
    max_retries=5,  # Retries on rate limit (429)
    retry_delay=1.0,  # Base delay between retries
)
```

### Records

#### List Records

```python
from airtable import SortConfig, SortDirection, CellFormat

# Basic listing
records = await client.list_records("appXXX", "tblXXX")

# With filtering and sorting
records = await client.list_records(
    "appXXX",
    "tblXXX",
    filter_by_formula="AND({Status}='Active', {Score}>10)",
    sort=[SortConfig(field="Name", direction=SortDirection.ASC)],
    fields=["Name", "Status", "Score"],
    max_records=100,
    page_size=50,
    view="Grid view",
)

# Fetch all records (handles pagination)
all_records = await client.list_all_records("appXXX", "tblXXX")
```

#### Get Single Record

```python
record = await client.get_record("appXXX", "tblXXX", "recXXXXXX")
print(record.fields["Name"])
```

#### Create Records

```python
# Single record
record = await client.create_record(
    "appXXX",
    "tblXXX",
    {"Name": "John Doe", "Email": "john@example.com"},
)

# Multiple records (max 10 per request)
records = await client.create_records(
    "appXXX",
    "tblXXX",
    [
        {"Name": "John", "Email": "john@example.com"},
        {"Name": "Jane", "Email": "jane@example.com"},
    ],
)

# Batch create (handles >10 records automatically)
records = await client.batch_create_records(
    "appXXX",
    "tblXXX",
    [{"Name": f"User {i}"} for i in range(50)],
)
```

#### Update Records

```python
# Single record (PATCH - partial update)
record = await client.update_record(
    "appXXX", "tblXXX", "recXXXXXX",
    {"Status": "Completed"},
)

# Replace entire record (PUT)
record = await client.update_record(
    "appXXX", "tblXXX", "recXXXXXX",
    {"Name": "New Name", "Status": "Active"},
    replace=True,
)

# Batch update
records = await client.batch_update_records(
    "appXXX",
    "tblXXX",
    [
        {"id": "recAAA", "fields": {"Status": "Done"}},
        {"id": "recBBB", "fields": {"Status": "Done"}},
    ],
)

# Upsert (create or update based on matching fields)
records = await client.upsert_records(
    "appXXX",
    "tblXXX",
    [
        {"Email": "john@example.com", "Name": "John Updated"},
        {"Email": "new@example.com", "Name": "New User"},
    ],
    fields_to_merge_on=["Email"],
)
```

#### Delete Records

```python
# Single record
result = await client.delete_record("appXXX", "tblXXX", "recXXXXXX")

# Multiple records
results = await client.delete_records(
    "appXXX", "tblXXX",
    ["recAAA", "recBBB", "recCCC"],
)

# Batch delete (handles >10 records)
results = await client.batch_delete_records(
    "appXXX", "tblXXX",
    record_ids,
)
```

### Schema & Metadata

#### List Bases

```python
bases = await client.list_bases()
for base in bases.bases:
    print(f"{base.id}: {base.name}")
```

#### Get Base Schema

```python
schema = await client.get_base_schema("appXXXXXX")
for table in schema.tables:
    print(f"Table: {table.name}")
    for field in table.fields:
        print(f"  - {field.name} ({field.type})")
```

#### Create Table

```python
from airtable import CreateFieldRequest

table = await client.create_table(
    "appXXX",
    "Contacts",
    fields=[
        CreateFieldRequest(name="Name", type="singleLineText"),
        CreateFieldRequest(name="Email", type="email"),
        CreateFieldRequest(
            name="Status",
            type="singleSelect",
            options={"choices": [{"name": "Active"}, {"name": "Inactive"}]},
        ),
    ],
    description="Contact information",
)
```

#### Create Field

```python
field = await client.create_field(
    "appXXX",
    "tblXXX",
    name="Priority",
    field_type="singleSelect",
    options={
        "choices": [
            {"name": "High", "color": "redBright"},
            {"name": "Medium", "color": "yellowBright"},
            {"name": "Low", "color": "greenBright"},
        ]
    },
)
```

### Comments

```python
# List comments on a record
comments = await client.list_comments("appXXX", "tblXXX", "recXXXXXX")

# Add a comment
comment = await client.create_comment(
    "appXXX", "tblXXX", "recXXXXXX",
    "This record needs review",
)
```

### Webhooks

```python
# List webhooks
webhooks = await client.list_webhooks("appXXXXXX")

# Create webhook
webhook = await client.create_webhook(
    "appXXXXXX",
    specification={
        "options": {
            "filters": {
                "dataTypes": ["tableData"],
            }
        }
    },
    notification_url="https://example.com/webhook",
)

# Get webhook payloads
payloads = await client.get_webhook_payloads("appXXX", webhook.id)

# Delete webhook
await client.delete_webhook("appXXX", webhook.id)
```

## Field Types

| API Type | Description |
|----------|-------------|
| `singleLineText` | Single line text |
| `multilineText` | Multi-line text |
| `richText` | Rich text with formatting |
| `number` | Number |
| `currency` | Currency amount |
| `percent` | Percentage |
| `checkbox` | Boolean checkbox |
| `date` | Date only |
| `dateTime` | Date and time |
| `duration` | Time duration |
| `email` | Email address |
| `phoneNumber` | Phone number |
| `url` | URL |
| `rating` | Star rating |
| `singleSelect` | Single select dropdown |
| `multipleSelects` | Multiple select |
| `singleCollaborator` | Single user |
| `multipleCollaborators` | Multiple users |
| `multipleRecordLinks` | Linked records |
| `multipleAttachments` | File attachments |
| `formula` | Computed formula |
| `rollup` | Aggregation from linked records |
| `count` | Count of linked records |
| `lookup` | Lookup from linked records |
| `autoNumber` | Auto-incrementing number |
| `barcode` | Barcode |
| `createdTime` | Record created time |
| `lastModifiedTime` | Record modified time |
| `createdBy` | User who created |
| `lastModifiedBy` | User who modified |

## Rate Limits

- **Free/Plus**: 5 requests/second per base
- **Pro**: 15 requests/second per base
- **Batch operations**: Max 10 records per request

The client automatically handles rate limiting with exponential backoff.

## Error Handling

```python
from airtable import (
    AirtableError,
    AirtableAuthError,
    AirtableNotFoundError,
    AirtableRateLimitError,
    AirtableValidationError,
)

try:
    record = await client.get_record("appXXX", "tblXXX", "recXXX")
except AirtableNotFoundError:
    print("Record not found")
except AirtableAuthError:
    print("Invalid API key")
except AirtableValidationError as e:
    print(f"Validation error: {e.message}")
except AirtableRateLimitError:
    print("Rate limit exceeded")
except AirtableError as e:
    print(f"API error: {e.message} (status: {e.status_code})")
```

## Resources

- [Airtable Web API Docs](https://airtable.com/developers/web/api)
- [Field Types Reference](https://airtable.com/developers/web/api/field-model)
- [Formula Reference](https://support.airtable.com/docs/formula-field-reference)

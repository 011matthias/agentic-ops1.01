---
name: api-boilerplate
description: Generate Python API client boilerplate from API documentation. Use when creating httpx clients with Pydantic models for external services like Fortnox, Upsales, or other APIs.
---

# API Boilerplate Generator

Generate production-ready Python API clients from API documentation.

## What This Skill Creates

For each API service, generates:
1. **HTTP client wrapper** using httpx with proper auth handling
2. **Pydantic models** for request/response types
3. **CRUD operations** for common endpoints
4. **Error handling** with typed exceptions

## Usage

### Input Required

Place API documentation in `workspace/api-docs/{service}/`:
- OpenAPI/Swagger specs (preferred)
- Markdown API docs
- Example request/response JSON

### Workflow

1. **Read API docs** from `workspace/api-docs/{service}/`
2. **Identify key entities** (resources, endpoints, auth method)
3. **Generate client** using template
4. **Output to** `workspace/templates/api-clients/{service}/client.py`

## Generation Process

### Step 1: Analyze API Docs

Extract from documentation:
- Base URL
- Authentication method (API key, OAuth2, Basic)
- Key resources (customers, orders, invoices, etc.)
- Endpoint patterns (REST CRUD, custom actions)

### Step 2: Generate Models

Create Pydantic models for:
```python
# Request models
class CreateCustomerRequest(BaseModel):
    name: str
    email: str | None = None

# Response models
class Customer(BaseModel):
    id: str
    name: str
    created_at: datetime
```

### Step 3: Generate Client

Use `.claude/skills/api-boilerplate/templates/api-client-template.py` as base:
- Configure auth method
- Add typed methods for each endpoint
- Include error handling

### Step 4: Output

Save to `workspace/templates/api-clients/{service}/`:

**Small APIs** (< 20 endpoints):
```
workspace/templates/api-clients/fortnox/
├── client.py       # Main client class
├── models.py       # Pydantic models
└── __init__.py
```

**Large APIs** (20+ endpoints): Use modular structure with mixins:
```
workspace/templates/api-clients/clickup/
├── __init__.py           # Package exports
├── models.py             # All Pydantic models
└── client/
    ├── __init__.py       # Main client composing all mixins
    ├── base.py           # BaseClient with HTTP handling
    ├── auth.py           # AuthMixin - OAuth, user endpoints
    ├── tasks.py          # TasksMixin - task CRUD
    ├── comments.py       # CommentsMixin - comments
    ├── webhooks.py       # WebhooksMixin - webhooks
    └── ...               # One mixin per resource group
```

## Modular Client Pattern (Large APIs)

For APIs with many endpoints, use the mixin pattern:

### base.py - HTTP Foundation
```python
class BaseClient:
    BASE_URL = "https://api.example.com/v2"

    async def _request(self, method: str, path: str, ...) -> dict:
        # Shared HTTP logic, auth, error handling
```

### Resource Mixins (e.g., tasks.py)
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .base import BaseClient

class TasksMixin:
    async def get_tasks(self: "BaseClient", ...) -> TasksResponse:
        data = await self._request("GET", "/tasks")
        return TasksResponse.model_validate(data)
```

### client/__init__.py - Compose All Mixins
```python
class ExampleClient(
    AuthMixin,
    TasksMixin,
    CommentsMixin,
    WebhooksMixin,
    BaseClient,  # Must be last
):
    """Full client with all API methods."""
    pass
```

This pattern keeps files manageable (~100-200 lines each) while providing a unified client interface.

## Template Reference

See `.claude/skills/api-boilerplate/templates/api-client-template.py` for the base structure.

## Example Output

```python
# workspace/templates/api-clients/fortnox/client.py

class FortnoxClient:
    """Fortnox API client with OAuth2 authentication."""

    def __init__(self, access_token: str, refresh_token: str | None = None):
        self.base_url = "https://api.fortnox.se/3"
        self._access_token = access_token
        self._client = httpx.Client(...)

    def get_customer(self, customer_id: str) -> Customer:
        """Fetch a customer by ID."""
        response = self._request("GET", f"/customers/{customer_id}")
        return Customer.model_validate(response["Customer"])

    def create_invoice(self, invoice: CreateInvoiceRequest) -> Invoice:
        """Create a new invoice."""
        response = self._request("POST", "/invoices", json=invoice.model_dump())
        return Invoice.model_validate(response["Invoice"])
```

## After Generation

1. Copy generated client to `workspace/clients/{client}/automations/app/clients/`
2. Configure credentials in `.env`
3. Import and use in automations

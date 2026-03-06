# FASTAPI-BUILD — FastAPI Implementation Workflow

Legacy Python/FastAPI service deployed on Railway. **Only for existing Herbox Sweden.** Do not create new FastAPI clients.

---

## Folder Structure

```
workspace/clients/{client}/automations/
├── app/
│   ├── automations/
│   │   └── {name}.py         ← Automation class (extend BaseAutomation)
│   ├── workspace/clients/
│   │   └── {service}/
│   │       └── client.py     ← API client
│   ├── routers/
│   │   ├── webhooks.py       ← Webhook endpoints
│   │   └── orders.py         ← (or other domain routers)
│   └── config.py             ← Settings (BaseSettings)
├── tests/
│   └── test_{name}.py
├── railway.toml
└── requirements.txt
```

---

## Step 1: Check API Clients

For each system listed in the spec:

```bash
ls workspace/clients/{client}/automations/app/clients/{system}/
```

- If missing → suggest `/api-boilerplate` for that service
- If present → read `client.py` to understand available methods before coding

---

## Step 2: Write Automation Class

Create `workspace/clients/{client}/automations/app/automations/{name}.py`:

```python
"""
Automation {ID}: {Name}

Spec: specs/{stage}/{id}.md
Trigger: {trigger_type}

{Brief description from spec Goal section}
"""
import logging
from typing import Any

from .base import BaseAutomation
from ..clients.{system1} import {System1}Client
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class {AutomationClass}(BaseAutomation):
    """
    {Description from spec Goal section}

    Flow:
    {Key steps from Mermaid diagram}
    """

    automation_id = "{id}"

    def __init__(self, {params}):
        self.{param} = {param}
        self.{client} = None

    def initialize(self) -> None:
        """Initialize clients and validate configuration."""
        logger.info(f"Initializing {self.automation_id}")
        self.{client} = {System1}Client()
        if not settings.{required_var}:
            raise ValueError("{required_var} is required")

    def fetch_data(self) -> Any:
        """Fetch data from source systems (spec Step 2)."""
        logger.info("Fetching data from {source}")
        return self.{client}.{method}({params})

    def transform(self, data: Any) -> Any:
        """Transform data for destination (spec Step 3)."""
        transformed = []
        for item in data:
            transformed.append({
                "{target_field}": item.get("{source_field}"),
            })
        return transformed

    def execute(self, data: Any) -> Any:
        """Execute main automation logic (spec Step 4)."""
        results = []
        for item in data:
            try:
                result = self.{client}.{method}(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process item: {e}")
                continue
        return results

    def finalize(self, result: Any) -> None:
        """Cleanup and notifications (spec Step 5)."""
        if isinstance(result, list):
            logger.info(f"Processed {len(result)} items")
```

**Key patterns:**
- `BaseAutomation` handles logging scaffolding
- `initialize()` → `fetch_data()` → `transform()` → `execute()` → `finalize()`
- `run(dry_run=True)` should skip `execute()` and `finalize()`

---

## Step 3: Add Webhook Route (if trigger is webhook)

Add to `workspace/clients/{client}/automations/app/routers/webhooks.py`:

```python
@router.post("/webhook/{path}")    # prefix is /webhook (singular), NOT /webhooks
async def {name}_webhook(request: Request):
    """
    Webhook for {Automation Name}.
    Triggered by: {trigger.webhook_event from spec}
    """
    from app.automations.{name} import {AutomationClass}

    try:
        payload = await request.json()
        {param} = payload.get("{param_name}")

        automation = {AutomationClass}({params})
        result = automation.run(trigger="webhook")

        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"Webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Route prefix**: `/webhook` (singular) — verify in source before adding.

For cron-triggered automations, add to `/run` router instead:
```python
@router.post("/run/{automation_id}")
async def run_{name}(request: Request, api_key: str = Depends(verify_api_key)):
    ...
```

---

## Step 4: Update Config

Add env vars to `workspace/clients/{client}/automations/app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing ...

    # {Service} — {Automation Name}
    {service}_api_key: str | None = None
    {service}_base_url: str = "https://api.{service}.com"
```

Also add to `.env.example` if it exists.

---

## Step 5: Write Tests

Create `workspace/clients/{client}/automations/tests/test_{name}.py`:

```python
"""Tests for {AutomationClass}"""
import pytest
from app.automations.{name} import {AutomationClass}


def test_transform_basic():
    automation = {AutomationClass}()
    result = automation.transform([{"source_field": "value"}])
    assert len(result) == 1
    assert result[0]["target_field"] == "value"


def test_transform_empty():
    automation = {AutomationClass}()
    assert automation.transform([]) == []


def test_dry_run():
    automation = {AutomationClass}()
    result = automation.run(dry_run=True)
    assert result["dry_run"] is True
    assert result["would_process"] >= 0
```

Run: `uv run pytest tests/test_{name}.py -v`

---

## Step 6: Verify with Dry-Run

```bash
cd workspace/clients/{client}/automations
uv run python -m app.automations.{name} --dry-run
```

Expected output:
```json
{"dry_run": true, "would_process": N}
```

Fix any import errors or config issues before marking implementation complete.

---

## Edge Case Handling

From the spec's Edge Cases section — implement all of them:

| Error | Implementation |
|-------|---------------|
| Rate limit (429) | Retry with exponential backoff |
| Auth expired (401) | Refresh token, retry once |
| Not found (404) | Log warning, skip item |
| Server error (5xx) | Raise exception, let BaseAutomation handle |
| Timeout | Retry 3x with increasing timeout |
| Duplicate | Skip, log as "already_exists" |
| Invalid data | Skip item, log error |

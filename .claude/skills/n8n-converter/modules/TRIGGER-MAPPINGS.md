# N8N Trigger Mappings

Reference for converting N8N triggers to Agentic Ops automation triggers.

---

## Trigger Types Overview

| N8N Trigger | Agentic Ops Type | Implementation |
|-------------|------------------|----------------|
| Schedule Trigger | `cron` | Railway CRON job |
| Webhook | `webhook` | FastAPI endpoint |
| Manual Trigger | `manual` | CLI / Dashboard button |
| Email Trigger | `webhook` | Email → Webhook service |
| Polling | `cron` | Periodic fetch + state tracking |

---

## Schedule Trigger (CRON)

### N8N Configuration
```json
{
  "type": "n8n-nodes-base.scheduleTrigger",
  "parameters": {
    "rule": {
      "interval": [{
        "field": "hours",
        "hoursInterval": 1
      }]
    }
  }
}
```

### Or Cron Expression
```json
{
  "type": "n8n-nodes-base.cron",
  "parameters": {
    "triggerTimes": {
      "item": [{
        "mode": "custom",
        "cronExpression": "0 8 * * *"
      }]
    }
  }
}
```

### Agentic Ops Conversion

**Spec frontmatter:**
```yaml
trigger:
  type: cron
  schedule: "0 8 * * *"  # Daily at 08:00
```

**Cron patterns:**
| N8N Interval | Cron Expression |
|--------------|-----------------|
| Every minute | `* * * * *` |
| Every 5 minutes | `*/5 * * * *` |
| Every hour | `0 * * * *` |
| Every day at 8:00 | `0 8 * * *` |
| Every Monday at 9:00 | `0 9 * * 1` |
| First of month at 6:00 | `0 6 1 * *` |

**Railway setup:**
```bash
# In railway.toml or Railway dashboard
[cron]
schedule = "0 8 * * *"
command = "python -m app.automations.{name}"
```

---

## Webhook Trigger

### N8N Configuration
```json
{
  "type": "n8n-nodes-base.webhook",
  "parameters": {
    "httpMethod": "POST",
    "path": "order-created",
    "responseMode": "onReceived"
  }
}
```

### Agentic Ops Conversion

**Spec frontmatter:**
```yaml
trigger:
  type: webhook
  path: /webhook/order-created
  method: POST
```

**Router code:**
```python
# app/routers/webhooks.py
from fastapi import APIRouter, Request
from app.automations.order_processor import OrderProcessor

router = APIRouter(prefix="/webhook", tags=["webhooks"])

@router.post("/order-created")
async def order_created(request: Request):
    """Handle order created webhook from external system."""
    data = await request.json()

    automation = OrderProcessor()
    result = await automation.execute(data)

    return {"status": "processed", "result": result}
```

**Webhook authentication options:**
```python
# Option 1: Header-based secret
from fastapi import Header, HTTPException

@router.post("/order-created")
async def order_created(
    request: Request,
    x_webhook_secret: str = Header(None)
):
    if x_webhook_secret != os.environ["WEBHOOK_SECRET"]:
        raise HTTPException(status_code=401, detail="Invalid secret")
    # ... process

# Option 2: HMAC signature validation
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## Manual Trigger

### N8N Configuration
```json
{
  "type": "n8n-nodes-base.manualTrigger",
  "parameters": {}
}
```

### Agentic Ops Conversion

**Spec frontmatter:**
```yaml
trigger:
  type: manual
```

**CLI execution:**
```python
# At bottom of automation file
if __name__ == "__main__":
    import asyncio

    automation = MyAutomation()

    # Support --dry-run flag
    import sys
    dry_run = "--dry-run" in sys.argv

    asyncio.run(automation.execute(dry_run=dry_run))
```

**Dashboard button (optional):**
```python
# app/routers/dashboard.py
@router.post("/run/{automation_name}")
async def run_automation(automation_name: str):
    """Manually trigger an automation from dashboard."""
    # Implementation depends on automation
    pass
```

---

## Email Trigger

### N8N Configuration
```json
{
  "type": "n8n-nodes-base.emailReadImap",
  "parameters": {
    "mailbox": "INBOX",
    "options": {
      "unseen": true
    }
  }
}
```

### Agentic Ops Conversion

**Option 1: Polling approach (CRON)**
```yaml
trigger:
  type: cron
  schedule: "*/5 * * * *"  # Check every 5 minutes
```

```python
class EmailProcessor(BaseAutomation):
    async def execute(self):
        # Connect to IMAP
        # Fetch unread emails
        # Process and mark as read
        # Track last processed in database
        pass
```

**Option 2: Email → Webhook service**
Use a service like Zapier, Make, or Mailgun to forward emails to webhook:

```yaml
trigger:
  type: webhook
  path: /webhook/email-received
```

---

## Polling Trigger

### N8N Configuration (e.g., RSS, API polling)
```json
{
  "type": "n8n-nodes-base.rssFeedRead",
  "parameters": {
    "url": "https://example.com/feed.xml"
  }
}
```

### Agentic Ops Conversion

Convert to CRON with state tracking:

```yaml
trigger:
  type: cron
  schedule: "*/15 * * * *"  # Every 15 minutes
```

```python
class FeedMonitor(BaseAutomation):
    async def execute(self):
        # Get last processed timestamp from database
        last_processed = await self.get_state("last_processed")

        # Fetch new items
        items = await self.fetch_feed()
        new_items = [i for i in items if i["published"] > last_processed]

        # Process new items
        for item in new_items:
            await self.process_item(item)

        # Update state
        if new_items:
            await self.set_state("last_processed", new_items[0]["published"])
```

---

## Multiple Triggers

### N8N (workflow with multiple entry points)
N8N allows multiple triggers in one workflow.

### Agentic Ops Conversion

**Option 1: Shared automation class**
```python
# app/automations/order_handler.py
class OrderHandler(BaseAutomation):
    async def execute(self, data: dict, source: str = "unknown"):
        self.log(f"Processing order from {source}")
        # Shared logic
```

```python
# app/routers/webhooks.py - Webhook trigger
@router.post("/webhook/order-created")
async def webhook_order(request: Request):
    data = await request.json()
    return await OrderHandler().execute(data, source="webhook")

# app/routers/cron.py - CRON trigger
@router.post("/cron/check-orders")
async def cron_orders():
    orders = await fetch_pending_orders()
    for order in orders:
        await OrderHandler().execute(order, source="cron")
```

**Option 2: Separate specs**
Create separate spec files for each trigger path:
- `a1-order-webhook.md` - Webhook-triggered processing
- `a2-order-cron.md` - Scheduled order check

---

## Response Handling

### N8N Respond to Webhook
```json
{
  "type": "n8n-nodes-base.respondToWebhook",
  "parameters": {
    "respondWith": "json",
    "responseBody": "={{ {status: 'success', id: $json.id} }}"
  }
}
```

### Agentic Ops Conversion
```python
@router.post("/webhook/order")
async def handle_order(request: Request):
    data = await request.json()

    # Process
    result = await automation.execute(data)

    # N8N respondToWebhook equivalent
    return JSONResponse(
        content={"status": "success", "id": result["id"]},
        status_code=200
    )
```

---

## Notes

- N8N's "On webhook call" response modes map to FastAPI response returns
- For async processing, return 202 Accepted and process in background
- Always validate webhook payloads before processing
- Track trigger source in logs for debugging

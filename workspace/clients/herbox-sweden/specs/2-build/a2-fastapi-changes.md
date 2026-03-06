---
id: a2-fastapi
type: automation
name: FastAPI — Enrichment Routing Changes
stage: build
needs_fixes: false
version: 1.0.0
created: 2026-02-18
updated: 2026-02-18
orchestrator: fastapi
trigger:
  type: n/a
systems:
  - fortnox
owner: rebecca@herbox.se
last_changes:
  - Added fortnox_order_number optional field to PendingOrderPayload in webhooks.py
  - Map fortnox_order_number when instantiating PendingOrder
  - Branched approve_orders() in orders.py to call update-fortnox-order when fortnox_order_number is pre-set
  - Preserve pre-existing fortnox_order_number if n8n doesn't return a new one
next_steps:
  - Deploy to Railway
  - Verify with end-to-end test (see Testing section in spec)
stage_history:
  - stage: spec
    date: 2026-02-18
  - stage: build
    date: 2026-02-18
---

# A2-FastAPI: Dashboard Enrichment Routing Changes

## Goal

Three minimal code changes to the FastAPI app to support the Upsales enrichment flow:
1. Accept `fortnox_order_number` when receiving a pending order
2. Route the approve action to UPDATE (not CREATE) when the Fortnox order number is pre-set

No database schema changes needed — `fortnox_order_number` column already exists on `PendingOrder`.

---

## Change 1: `webhooks.py` — Accept pre-populated `fortnox_order_number`

**File:** `app/routers/webhooks.py`

**What:** Add `fortnox_order_number` as an optional field to `PendingOrderPayload`.

**Current `PendingOrderPayload`:**
```python
class PendingOrderPayload(PydanticBaseModel):
    contract_number: str
    customer_number: str
    customer_name: str = ""
    source: str = "recurring"
    order_payload: dict
    delivery_date: str
    ...
    your_order_number: str
    # fortnox_order_number is NOT here
```

**Change — add the field:**
```python
class PendingOrderPayload(PydanticBaseModel):
    contract_number: str
    customer_number: str
    customer_name: str = ""
    source: str = "recurring"
    order_payload: dict
    delivery_date: str
    ...
    your_order_number: str
    fortnox_order_number: str | None = None  # ADD THIS — pre-populated for Upsales enrichments
```

**Change — map it when creating the PendingOrder:**
```python
# In the receiver, where PendingOrder is instantiated:
pending_order = PendingOrder(
    ...
    fortnox_order_number=order_data.fortnox_order_number or "",  # ADD THIS LINE
)
```

---

## Change 2: `orders.py` — Branch approve route on pre-set `fortnox_order_number`

**File:** `app/routers/orders.py`

**What:** In `approve_orders()`, if the order already has a `fortnox_order_number`, call the **update** webhook instead of the **create** webhook.

**Current approve logic (simplified):**
```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
        f"{settings.n8n_webhook_base_url}/webhook/create-fortnox-order",
        json={
            "order_id": str(order.id),
            "order_payload": order.order_payload,
        },
    )
```

**New approve logic:**
```python
async with httpx.AsyncClient(timeout=30.0) as client:
    if order.fortnox_order_number:
        # Upsales enrichment flow — UPDATE the existing Fortnox order
        url = f"{settings.n8n_webhook_base_url}/webhook/update-fortnox-order"
        payload = {
            "order_id": str(order.id),
            "fortnox_order_number": order.fortnox_order_number,
            "enrichment_payload": order.order_payload,
        }
    else:
        # Recurring order flow — CREATE a new Fortnox order (existing behavior)
        url = f"{settings.n8n_webhook_base_url}/webhook/create-fortnox-order"
        payload = {
            "order_id": str(order.id),
            "order_payload": order.order_payload,
        }

    response = await client.post(url, json=payload)
```

**On success response handling** — the existing code sets `fortnox_order_number` from the n8n response. For enrichment orders, the number is already set. Extend it to preserve the pre-existing value if n8n doesn't return a new one:
```python
if result.get("success"):
    order.status = "created"
    # Use returned number if present, otherwise keep the pre-existing one
    order.fortnox_order_number = result.get("fortnox_order_number") or order.fortnox_order_number
```

---

## Change 3: `config.py` — No change needed

`n8n_webhook_base_url` already exists and covers both endpoints:
- `{n8n_webhook_base_url}/webhook/create-fortnox-order` (existing)
- `{n8n_webhook_base_url}/webhook/update-fortnox-order` (new — same base URL)

---

## Non-Regression

These changes must NOT break the existing recurring order flow:

| Scenario | Expected behavior |
|----------|-------------------|
| Recurring order with no `fortnox_order_number` in payload | `fortnox_order_number` stored as `""` or `null` — existing behavior |
| Approve recurring order | `fortnox_order_number` is falsy → CREATE webhook called — existing behavior |
| Approve Upsales enrichment order | `fortnox_order_number` is set → UPDATE webhook called — new behavior |

---

## Testing

1. POST a test payload to `/webhook/pending-orders` with `fortnox_order_number="TEST-999"`:
   - Verify it's stored in the database
2. Approve that order in the dashboard:
   - Verify n8n receives call at `/webhook/update-fortnox-order` (not `/webhook/create-fortnox-order`)
   - Verify correct payload: `{ order_id, fortnox_order_number: "TEST-999", enrichment_payload: {...} }`
3. Approve a normal recurring order:
   - Verify n8n still receives call at `/webhook/create-fortnox-order` — no regression

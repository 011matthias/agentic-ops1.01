---
id: fix4
name: Dashboard — Customer Info Visibility
type: bug-fix
stage: build
needs_fixes: false
version: 1.0.0
created: 2026-02-18
updated: 2026-02-18
orchestrator: fastapi
parent: a2
systems:
  - fastapi
owner: rebecca@herbox.se
last_changes:
  - Added customer_info = Column(JSON, nullable=True) to PendingOrder model
  - Added customer_info field to PendingOrderPayload in webhooks.py
  - Mapped customer_info when creating PendingOrder
  - Added Customer Information panel (phone, email, address) to order_detail.html
  - Added phone secondary line under customer name in orders list (Part 5)
next_steps:
  - Run DB migration on production: ALTER TABLE pending_orders ADD COLUMN customer_info JSONB;
  - Deploy Fix3 (for customer_info data to start flowing from n8n)
stage_history:
  - stage: spec
    date: 2026-02-18
  - stage: build
    date: 2026-02-18
---

# Fix4: Dashboard — Customer Info Visibility

**Parent Automation:** [A2 — Upsales Order Enrichment Pipeline](../2-build/a2-crm-erp-sync.md)

> **Depends on:** [Fix3 — A2 Customer Info Sync](fix3-a2-customer-info-sync.md) must be deployed first (Fix3 sends `customer_info` in the dashboard payload).
>
> Also set `needs_fixes: true` in the parent spec's frontmatter. Clear it when this fix reaches `live`.

## Problem

**Symptom:** The dashboard order detail view shows no customer contact information — no phone number, no delivery address, no email. When Rebecca reviews a new enrichment order (sourced from Upsales), she has to leave the dashboard and look up the customer in Fortnox manually just to verify basic details.

The orders list similarly shows only customer name + number with no further contact detail.

**Impact:**
- Rebecca wastes time switching between the dashboard and Fortnox for every new order review
- Risk of approving orders with incorrect delivery data because context is fragmented
- Dashboard provides less value than it could as a single-pane review interface

**First Observed:** 2026-02-18 (dashboard flow design review)

## Root Cause

`PendingOrder` model has no field for customer contact info. The `POST /webhook/pending-orders` payload schema (`PendingOrderPayload`) also has no `customer_info` field, so any data sent by n8n is silently discarded at the API boundary.

The dashboard templates (`orders.html`, `order_detail.html`) have no section for customer contact details.

## Fix Plan

Four sequential parts. Fix3 must be deployed before Part 4 produces visible results (Parts 1–3 are safe to deploy independently).

---

### Part 1 — DB Model: Add `customer_info` Column

**File:** `app/models/pending_orders.py`

Add after the `customer_name` field:

```python
# Customer contact info (populated from Upsales via A2 + Fix3)
customer_info = Column(JSON, nullable=True)
# Expected structure:
# {
#   "phone":    "+46701234567",
#   "email":    "contact@company.se",
#   "address1": "Storgatan 1",
#   "city":     "Stockholm",
#   "zip":      "11122",
#   "country":  "SE"
# }
```

**SQL migration:**
```sql
ALTER TABLE pending_orders ADD COLUMN customer_info JSONB;
```

> A single JSON column keeps the schema simple and avoids a migration-heavy denormalized approach. All customer info fields are nullable — missing fields render as "—" in the UI.

---

### Part 2 — Webhook Payload: Accept `customer_info`

**File:** `app/routers/webhooks.py`

Add `customer_info` as an optional field to `PendingOrderPayload`:

```python
class PendingOrderPayload(PydanticBaseModel):
    contract_number: str
    customer_number: str
    customer_name: str = ""
    source: str = "recurring"
    order_payload: dict
    delivery_date: str
    # ... existing fields ...
    your_order_number: str
    fortnox_order_number: str | None = None
    customer_info: dict | None = None   # ADD THIS — populated by Fix3
```

---

### Part 3 — Map `customer_info` When Creating `PendingOrder`

**File:** `app/routers/webhooks.py`

In the section where `PendingOrder` is instantiated, add the mapping:

```python
pending_order = PendingOrder(
    # ... existing fields ...
    fortnox_order_number=order_data.fortnox_order_number or "",
    customer_info=order_data.customer_info or None,   # ADD THIS
)
```

---

### Part 4 — Order Detail Template: Customer Information Panel

**File:** `app/templates/order_detail.html`

Add a **Customer Information** card in the order detail view. Place it near the top of the detail section, alongside the existing Customer header line (`Customer: **Name** (#number)`):

```html
{% if order.customer_info %}
<div class="detail-card customer-info-card">
  <h4>Customer Information</h4>
  <div class="info-grid">

    {% if order.customer_info.phone %}
    <div class="info-row">
      <span class="info-label">Phone</span>
      <span class="info-value">
        <a href="tel:{{ order.customer_info.phone }}">{{ order.customer_info.phone }}</a>
      </span>
    </div>
    {% endif %}

    {% if order.customer_info.email %}
    <div class="info-row">
      <span class="info-label">Email</span>
      <span class="info-value">
        <a href="mailto:{{ order.customer_info.email }}">{{ order.customer_info.email }}</a>
      </span>
    </div>
    {% endif %}

    {% if order.customer_info.address1 %}
    <div class="info-row">
      <span class="info-label">Delivery Address</span>
      <span class="info-value">
        {{ order.customer_info.address1 }},
        {{ order.customer_info.zip or '' }}
        {{ order.customer_info.city or '' }},
        {{ order.customer_info.country or '' }}
      </span>
    </div>
    {% endif %}

  </div>
</div>
{% endif %}
```

> The card renders only when `customer_info` is set — recurring orders (sourced from A1) won't show it. This keeps the UI clean for existing recurring order flows.

---

### Part 5 (Optional) — Orders List: Surface Phone

**File:** `app/templates/orders.html`

Optionally add the customer phone as a secondary line under the customer name in the list view:

```html
<!-- Existing customer cell -->
<td>
  <div class="customer-name">{{ order.customer_name }}</div>
  <div class="customer-number">#{{ order.customer_number }}</div>
  {% if order.customer_info and order.customer_info.phone %}
  <div class="customer-phone">{{ order.customer_info.phone }}</div>
  {% endif %}
</td>
```

> This is low-risk and improves scannability in the "New Orders" tab where Upsales enrichment orders appear. Styling can match `.customer-number` (muted, smaller font).

---

## Files to Change

| File | Change |
|------|--------|
| `app/models/pending_orders.py` | Add `customer_info = Column(JSON, nullable=True)` after `customer_name` |
| DB migration | `ALTER TABLE pending_orders ADD COLUMN customer_info JSONB;` |
| `app/routers/webhooks.py` | Add `customer_info: dict | None = None` to `PendingOrderPayload`; map when creating `PendingOrder` |
| `app/templates/order_detail.html` | Add Customer Information panel (conditional on `customer_info` being set) |
| `app/templates/orders.html` | (Optional) Add phone secondary line under customer name in list view |

---

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| `customer_info` not sent (recurring A1 orders) | Column stays `null` — panel does not render in detail view |
| Fix3 not yet deployed when Fix4 goes live | `customer_info` arrives as `null` — model accepts it, panel hidden |
| Partial customer_info (some fields null) | Each field rendered only if truthy — no empty rows shown |
| `customer_info` JSON malformed | Pydantic rejects payload at webhook — returns 422 |
| DB migration on live Railway instance | Add column only (nullable) — no downtime, no data loss |

---

## Testing

### Verification Steps

- [ ] Run DB migration on dev — confirm `customer_info` JSONB column added without error
- [ ] POST test payload to `/webhook/pending-orders` including `customer_info` — verify stored correctly in DB
- [ ] POST payload WITHOUT `customer_info` (simulate recurring A1 order) — verify no error, column stores `null`
- [ ] Open order detail for order WITH `customer_info` — verify Customer Information panel appears with correct values
- [ ] Open order detail for order WITHOUT `customer_info` — verify Customer Information panel is NOT rendered
- [ ] (If Part 5 implemented) Check orders list — verify phone appears under customer name for enrichment orders only

### Acceptance Criteria

- [ ] Customer phone, email, and delivery address visible in order detail for all Upsales enrichment orders
- [ ] Customer Information panel hidden for recurring A1 orders (no `customer_info`)
- [ ] No regression — approve/deny/edit flows work as before
- [ ] Recurring orders (A1) unaffected — `customer_info` null, UI unchanged
- [ ] DB migration runs cleanly on production with no downtime

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-18 | Initial fix spec |

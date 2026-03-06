---
id: fix1
name: A2 Dashboard Missing Fields
type: bug-fix
stage: build
needs_fixes: false
version: 1.0.0
created: 2026-02-18
updated: 2026-02-18

orchestrator: n8n
parent: a2
systems:
  - upsales
  - fortnox
  - fastapi
owner: rebecca@herbox.se
last_changes:
  - Part 2a — Added period_end (Date) and interval (String(50)) columns to PendingOrder model
  - Part 2b — Added period_end and interval fields to PendingOrderPayload; mapped when creating PendingOrder
  - Part 2c — Added period_end handling in edit_order(); syncs to order_payload.Order.PeriodEnd
  - Part 2d — Added Period End (editable) and Interval (read-only) fields to order_detail.html
  - Part 3 — Created "Order Updater (Dashboard → Fortnox)" n8n workflow (ID Z3FRABg8D8lo28ni) with strip-OrderRows + PUT to Fortnox
next_steps:
  - Verify Fortnox order GET response includes PeriodStart and PeriodEnd fields (run A2-Test workflow)
  - Update A2 n8n "Code: Build enrichment payload" node (Part 1) — add period_start, period_end, interval, OrderRows to dashboard POST
  - Run DB migration on production: ALTER TABLE pending_orders ADD COLUMN period_end DATE; ALTER TABLE pending_orders ADD COLUMN interval VARCHAR(50);
  - Activate "Order Updater" n8n workflow
  - End-to-end test: approve a real Upsales enrichment order
stage_history:
  - stage: spec
    date: 2026-02-18
  - stage: build
    date: 2026-02-18
---

# Fix1: A2 Dashboard Missing Fields

**Parent Automation:** [A2 — Upsales Order Enrichment Pipeline](../2-build/a2-crm-erp-sync.md)

> Also set `needs_fixes: true` in the parent spec's frontmatter. Clear it when this fix reaches `live`.

## Problem

**Symptom:** After A2 sends an enrichment order to the dashboard, the detail view is missing four categories of information:
1. **Period Start** — field exists in DB and template but A2 never sends it
2. **Period End** — not in A2 payload, not in DB model, not in the template
3. **Interval** — Upsales billing interval (Kvartal/Halvår/Helår) not sent or stored
4. **Line Items** — template has an editable line items table but `order_payload.Order.OrderRows` is always empty

Additionally, the n8n webhook `update-fortnox-order` that should perform the Fortnox PUT on approval doesn't exist yet.

**Impact:**
- Rebecca can't verify or correct line items before approving
- Period Start / Period End and Interval are blank — key subscription metadata missing
- Approval of Upsales enrichment orders will fail (n8n webhook missing)

**First Observed:** 2026-02-18 (first live test of A2 dashboard flow)

## Root Cause

A2's "Code: Build enrichment payload" node produces only the minimal enrichment delta (Phone, DeliveryAddress, Freight, etc.) and does not extract:
- `Order.PeriodStart` / `Order.PeriodEnd` from the Fortnox order response
- `custom[fieldId=17]` (interval) from the Upsales deal
- `Order.OrderRows` (intentionally omitted from Fortnox PUT to avoid row deletion, but needed for dashboard display)

The DB model and webhook also have no columns for `period_end` or `interval`, so even if A2 sent them, they'd be silently dropped.

The `update-fortnox-order` n8n webhook is referenced in `orders.py:311` but hasn't been built yet.

## Fix Plan

Three independent parts — Part 3 is highest priority (unblocks approval).

---

### Part 1 — A2 n8n: Send Missing Fields

**Workflow:** A2 Upsales Order Enrichment Pipeline
**Node:** "Code: Build enrichment payload"

```javascript
// --- ADD: Extract from Fortnox order response ---
const periodStart = fortnoxOrder.PeriodStart || null;   // ⚠️ VERIFY field name on GET /3/orders/{id}
const periodEnd   = fortnoxOrder.PeriodEnd   || null;   // ⚠️ VERIFY field name on GET /3/orders/{id}
const orderRows   = fortnoxOrder.OrderRows   || [];     // For dashboard display only — NOT for enrichment PUT

// --- ADD: Extract from Upsales deal ---
// custom[fieldId=17] = Faktureringsintervall: Kvartal / Halvår / Helår / Ingen prenumeration
const interval = getCustomField(deal.custom, 17) || null;

// --- ADD to order_payload.Order ---
// Include OrderRows so dashboard can display them
// (Part 3 ensures they are stripped before Fortnox PUT)
order_payload.Order.OrderRows = orderRows;

// --- ADD to dashboard POST body (alongside existing fields) ---
period_start: periodStart,
period_end:   periodEnd,
interval:     interval,
```

> **⚠️ VERIFY before implementing:** Confirm `GET /3/orders/{DocumentNumber}` response includes `PeriodStart` and `PeriodEnd`. Check against a real order via A2-Test workflow or Fortnox API explorer. Update field names if they differ.

---

### Part 2 — FastAPI Backend: DB + Model + Handler + Template

#### 2a. DB Migration

**File:** `app/models/pending_orders.py` — add after `period_start`:

```python
period_end = Column(Date,       nullable=True)
interval   = Column(String(50), nullable=True)  # e.g. "Kvartal", "Halvår", "Helår"
```

SQL:
```sql
ALTER TABLE pending_orders ADD COLUMN period_end DATE;
ALTER TABLE pending_orders ADD COLUMN interval   VARCHAR(50);
```

#### 2b. Webhook Payload Model

**File:** `app/routers/webhooks.py` — `PendingOrderPayload` — add after `period_start`:

```python
period_end: str | None = None   # ISO date string (YYYY-MM-DD)
interval:   str | None = None
```

When instantiating `PendingOrder`, map both:
```python
period_end = datetime.strptime(order_data.period_end, "%Y-%m-%d").date() if order_data.period_end else None,
interval   = order_data.interval or None,
```

#### 2c. Edit Order Handler

**File:** `app/routers/orders.py` — `edit_order()` — add after the `period_start` block (~line 202):

```python
new_period_end = form.get("period_end", "")
if new_period_end:
    parsed_pe = datetime.strptime(new_period_end, "%Y-%m-%d").date()
    if parsed_pe != order.period_end:
        changes["period_end"] = {"old": str(order.period_end), "new": str(parsed_pe)}
        order.period_end = parsed_pe
        # Keep enrichment payload in sync so Fortnox PUT sends PeriodEnd
        if "Order" in (order.order_payload or {}):
            order.order_payload["Order"]["PeriodEnd"] = new_period_end
```

#### 2d. Order Detail Template

**File:** `app/templates/order_detail.html` — add in the Order Details section alongside Period Start:

```html
<!-- Period End — editable -->
<div>
  <label>Period End</label>
  <input type="date" name="period_end"
         value="{{ order.period_end.strftime('%Y-%m-%d') if order.period_end else '' }}"
         {% if order.status not in ('pending', 'failed') %}disabled{% endif %}>
</div>

<!-- Interval — read-only (from Upsales) -->
<div>
  <label>Interval</label>
  <span>{{ order.interval or '—' }}</span>
</div>
```

---

### Part 3 — n8n: Build `update-fortnox-order` Webhook (NEW)

**Trigger:** Webhook `POST /webhook/update-fortnox-order`

**Input** (sent by `orders.py` approval flow):
```json
{
  "order_id": "uuid",
  "fortnox_order_number": "12345",
  "enrichment_payload": {
    "Order": {
      "Phone1": "...",
      "DeliveryAddress1": "...",
      "Freight": 299,
      "FreightVAT": 25,
      "StockPointCode": "2",
      "PeriodEnd": "2026-03-17",
      "OrderRows": [...]    // ← MUST BE STRIPPED before Fortnox PUT
    }
  }
}
```

**Node flow:**

```
Webhook (POST /webhook/update-fortnox-order)
  → Code: Strip OrderRows
  → HTTP Request: PUT /3/orders/{fortnox_order_number}
  → IF: success?
      Yes → Respond: { "success": true, "fortnox_order_number": "12345" }
      No  → Respond: { "success": false, "error": "..." }
```

**Code: Strip OrderRows:**
```javascript
const body = $json.enrichment_payload;
const orderObj = body.Order || body;

// Fortnox would DELETE all existing rows if OrderRows is included in PUT
delete orderObj.OrderRows;

return [{
  json: {
    order_id:             $json.order_id,
    fortnox_order_number: $json.fortnox_order_number,
    fortnox_payload:      { Order: orderObj }
  }
}];
```

**HTTP Request node:**
- Method: `PUT`
- URL: `https://api.fortnox.se/3/orders/{{ $json.fortnox_order_number }}`
- Auth: Fortnox OAuth2 credential
- Body: `{{ JSON.stringify($json.fortnox_payload) }}`
- Continue on Fail: Yes

---

## Files to Change

| File | Change |
|------|--------|
| A2 n8n — "Code: Build enrichment payload" | Add `period_start`, `period_end`, `interval`, `OrderRows` to dashboard payload |
| `app/models/pending_orders.py` | Add `period_end` (Date), `interval` (String(50)) columns |
| `app/routers/webhooks.py` | Add `period_end`, `interval` to `PendingOrderPayload`; map when creating `PendingOrder` |
| `app/routers/orders.py` | Handle `period_end` in `edit_order()`; sync to `order_payload.Order.PeriodEnd` |
| `app/templates/order_detail.html` | Add Period End editable field; add Interval read-only display |
| n8n (new workflow) | `update-fortnox-order` webhook — strip `OrderRows`, PUT enrichment delta to Fortnox |

---

## Testing

### Verification Steps

- [ ] Confirm Fortnox `GET /3/orders/{id}` response includes `PeriodStart` and `PeriodEnd` fields (run A2-Test workflow)
- [ ] Run DB migration on dev — confirm columns added without errors
- [ ] POST test payload (with `period_end`, `interval`, `order_payload.Order.OrderRows`) to `/webhook/pending-orders` — verify stored correctly
- [ ] Open order detail view — verify Period Start, Period End, Interval, and Line Items all populated
- [ ] Edit Period End in dashboard — verify saved and reflected in `order_payload.Order.PeriodEnd`
- [ ] Manually test `update-fortnox-order` n8n webhook — verify Fortnox order updated, existing OrderRows NOT deleted
- [ ] Approve a real Upsales enrichment order end-to-end

### Acceptance Criteria

- [ ] Period Start populated from Fortnox `Order.PeriodStart`
- [ ] Period End populated from Fortnox `Order.PeriodEnd` and editable by Rebecca
- [ ] Interval displayed read-only from Upsales `custom[fieldId=17]`
- [ ] Line Items table pre-filled from Fortnox `Order.OrderRows` — Rebecca can edit before approving
- [ ] On approval: Fortnox order updated with enrichment fields only — existing OrderRows NOT deleted
- [ ] No regression: recurring orders still route to `create-fortnox-order`
- [ ] Idempotency check in A2 unaffected — same deal not reprocessed

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-18 | Initial fix spec |

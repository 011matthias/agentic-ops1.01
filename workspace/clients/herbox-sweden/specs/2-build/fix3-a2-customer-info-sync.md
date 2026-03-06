---
id: fix3
name: A2 — Customer Info Sync (Fortnox Customer + Dashboard Payload)
type: bug-fix
stage: build
needs_fixes: false
version: 1.2.0
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
  - Extended Code:Build Enrichment to produce customerUpdatePayload + customerInfo
  - Added customer_info + customer_update_payload to dashboardBody.orders[0]
  - Moved PUT Fortnox Customer from A2 to Order Updater (runs at approval time, not discovery)
  - Order Updater now: Strip OrderRows → PUT Fortnox Customer → Update Fortnox Order
  - PUT Fortnox Customer uses customer_number + customer_update_payload forwarded from dashboard
next_steps:
  - Manually test A2: run, verify customer_info + customer_update_payload present in POST body
  - Manually test Order Updater: approve an order, verify PUT Customer 200 + PUT Order 200
  - Fix4 (FastAPI model) must store + forward customer_number + customer_update_payload on approval
stage_history:
  - stage: spec
    date: 2026-02-18
  - stage: build
    date: 2026-02-18
---

# Fix3: A2 — Customer Info Sync (Fortnox Customer + Dashboard Payload)

**Parent Automation:** [A2 — Upsales Order Enrichment Pipeline](../2-build/a2-crm-erp-sync.md)

> Also set `needs_fixes: true` in the parent spec's frontmatter. Clear it when this fix reaches `live`.

## Problem

**Symptom:** A2 enriches the Fortnox **Order** with phone and delivery address sourced from the Fortnox Customer record — but it never writes that data back to the Fortnox **Customer** record. If the customer's phone number or delivery address is stale in Fortnox, it propagates to all enriched orders.

Additionally, when Rebecca reviews a new enrichment order in the dashboard, she has **zero customer contact visibility** — no phone, no delivery address. She has to switch to Fortnox in a separate tab to look up basic customer details before approving.

**Impact:**
- Fortnox Customer records drift out of sync over time
- Rebecca loses time looking up customer details outside the dashboard on every new order review
- Future orders inherit stale Customer data (phone, delivery address) if Customer record is never refreshed

**First Observed:** 2026-02-18 (dashboard flow design review)

## Root Cause

A2's "Code: Build Enrichment" node extracts phone/address from the Fortnox Customer to enrich the Order, but never builds a payload to update the Customer itself. The dashboard POST payload also has no `customer_info` or `customer_update_payload` fields.

## Corrected Architecture

The Fortnox Customer update must happen **at approval time**, not at discovery time. Rebecca should review the customer info in the dashboard, then approve — which triggers the Order Updater to update both the Order and the Customer simultaneously.

```
A2 (discovery):
  Code: Build Enrichment
    → produces customerUpdatePayload + customerInfo
    → adds both to dashboardBody
  POST Dashboard (stores customer_info for display + customer_update_payload for approval)

Order Updater (on approval):
  Strip OrderRows (extract customer_number + customer_update_payload from webhook body)
  PUT Fortnox Customer (continueRegularOutput — never blocks order update)
  PUT Fortnox Order
  Format Response → Respond to Webhook
```

---

## Implementation

### A2: Code: Build Enrichment (updated)

Produces two new objects from the Fortnox Customer data already fetched by `GET Fortnox Customer`:

```javascript
// ---- Customer update payload for Fortnox PUT /3/customers ----
// Built here, stored in dashboard, applied by Order Updater on approval.
const customerUpdatePayload = { Customer: {} };
const custPhone   = phone || null;         // from customer.Phone1 || customer.Phone
const custEmail   = customer.Email || null;
const custStreet  = deliveryAddr1 || null; // from customer.DeliveryAddress1 || customer.Address1
const custCity    = deliveryCity || null;
const custZip     = deliveryZip || null;
const custCountry = deliveryCountry || 'SE';

if (custPhone)  customerUpdatePayload.Customer.Phone1           = custPhone;
if (custEmail)  customerUpdatePayload.Customer.Email            = custEmail;
if (custStreet) customerUpdatePayload.Customer.DeliveryAddress1 = custStreet;
if (custCity)   customerUpdatePayload.Customer.DeliveryCity     = custCity;
if (custZip)    customerUpdatePayload.Customer.DeliveryZipCode  = custZip;
if (custStreet) customerUpdatePayload.Customer.DeliveryCountry  = custCountry;

// ---- customer_info for dashboard display (consumed by Fix4) ----
const customerInfo = {
  phone: custPhone, email: custEmail,
  address1: custStreet, city: custCity, zip: custZip, country: custCountry,
};
```

Both objects are included in `dashboardBody.orders[0]`:
```javascript
customer_info:           customerInfo,
customer_update_payload: customerUpdatePayload,
```

### A2: POST Dashboard (unchanged node, richer payload)

`$json.dashboardBody` now carries `customer_info` (for Fix4 display) and `customer_update_payload` (for Order Updater to use at approval).

---

### Order Updater: Strip OrderRows (updated)

Extracts `customer_number` and `customer_update_payload` from the webhook body (sent by FastAPI on approval):

```javascript
const customerNumber = body.customer_number || null;
const customerUpdatePayload = body.customer_update_payload || { Customer: {} };
// ...existing orderObj stripping...
return [{ json: { order_id, fortnox_order_number, customer_number: customerNumber,
                  customer_update_payload: customerUpdatePayload, fortnox_payload } }];
```

### Order Updater: PUT Fortnox Customer (NEW node)

| Setting | Value |
|---------|-------|
| Position | Between Strip OrderRows and Update Fortnox Order |
| Method | `PUT` |
| URL | `={{ 'https://api.fortnox.se/3/customers/' + $json.customer_number }}` |
| Auth | Fortnox OAuth2 (same credential) |
| Body | `={{ JSON.stringify($json.customer_update_payload) }}` |
| On Error | `continueRegularOutput` — never blocks the Order update |

> If `customer_update_payload` was not sent (legacy orders), defaults to `{ Customer: {} }` — safe no-op.

### Order Updater: Update Fortnox Order (updated refs)

Uses explicit `$('Strip OrderRows').item.json.*` since `$json` is now the PUT Customer response:

| Field | Expression |
|-------|-----------|
| URL | `=https://api.fortnox.se/3/orders/{{ $('Strip OrderRows').item.json.fortnox_order_number }}` |
| Body | `={{ JSON.stringify($('Strip OrderRows').item.json.fortnox_payload) }}` |

---

## N8N Workflows

| Workflow | Change |
|---------|--------|
| A2: Upsales Order Enrichment Pipeline | Code: Build Enrichment extended; customer_update_payload + customer_info in dashboardBody |
| Order Updater (Dashboard → Fortnox) | Strip OrderRows extended; PUT Fortnox Customer node added before Update Fortnox Order |

**Credentials Required:**
| Credential Name | Type | Notes |
|----------------|------|-------|
| Fortnox OAuth2 | OAuth2 API | Already configured — reused for new PUT Customer node |

---

## API References

| System | Endpoint | Method | Auth | Notes |
|--------|----------|--------|------|-------|
| Fortnox | `/3/customers/{CustomerNumber}` | GET | OAuth2 | Already in A2 — read for enrichment |
| Fortnox | `/3/customers/{CustomerNumber}` | PUT | OAuth2 | **NEW in Order Updater** — write back on approval |
| Fortnox | `/3/orders/{OrderNumber}` | PUT | OAuth2 | Existing in Order Updater |
| FastAPI | `/webhook/pending-orders` | POST | Internal | Extended with customer_info + customer_update_payload |
| FastAPI | `/webhook/update-fortnox-order` | POST | Internal | Must forward customer_number + customer_update_payload (Fix4) |

---

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| PUT Fortnox Customer fails (5xx / 429) | continueRegularOutput — Order update still runs |
| `customer_update_payload` not sent by dashboard | Defaults to `{ Customer: {} }` — no-op PUT |
| `customer_number` is null | PUT goes to `.../customers/null` → 404 → continueRegularOutput |
| Fix4 not yet deployed | FastAPI ignores unknown fields — no errors |
| `customerUpdatePayload.Customer` is empty | PUT sends `{"Customer":{}}` — Fortnox no-op |

---

## Testing

### A2 Test
1. Run A2 manually (Limit node to 1 order)
2. Inspect `Code: Build Enrichment` output — verify `customerUpdatePayload` and `customerInfo` present
3. Inspect `POST Dashboard` node — verify `customer_info` and `customer_update_payload` in request body

### Order Updater Test
1. POST to `/webhook/update-fortnox-order` with a real order payload including `customer_number` and `customer_update_payload`
2. Verify `PUT Fortnox Customer` node — 200 OK, correct fields updated in Fortnox
3. Verify `Update Fortnox Order` node — 200 OK, order enriched correctly
4. Verify `customer_update_payload: { Customer: {} }` path (no fields) — Order update still succeeds

### Acceptance Criteria

- [ ] `customer_info` + `customer_update_payload` present in A2's POST Dashboard payload
- [ ] On approval, Fortnox Customer Phone1/DeliveryAddress updated if customer_update_payload has fields
- [ ] Customer PUT failure does not block Order PUT — order enrichment always completes
- [ ] `{ Customer: {} }` no-op path works safely (no error in Order Updater)
- [ ] No regression — existing Order enrichment fields unchanged
- [ ] Idempotency check in A2 unaffected — same deal not reprocessed on next poll

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-18 | Initial fix spec |
| 1.1.0 | 2026-02-18 | Implemented in n8n — PUT Customer in A2, customer_info in dashboard payload |
| 1.2.0 | 2026-02-18 | Architectural correction: moved PUT Customer to Order Updater (approval-time); customer_update_payload forwarded through dashboard |

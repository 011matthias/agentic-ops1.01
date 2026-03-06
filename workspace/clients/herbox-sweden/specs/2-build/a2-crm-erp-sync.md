---
id: a2
type: automation
name: Upsales Order Enrichment Pipeline
stage: build
needs_fixes: true
version: 2.2.0
created: 2026-01-09
updated: 2026-02-18
orchestrator: n8n
trigger:
  type: schedule
  schedule: "*/5 * * * *"
systems:
  - upsales
  - fortnox
owner: rebecca@herbox.se
last_changes:
  - "Opened fix3: A2 n8n — sync Upsales phone/address to Fortnox Customer + include customer_info in dashboard payload"
  - "Opened fix4: dashboard — customer info visibility panel (phone, email, delivery address)"
  - "Opened fix1: dashboard missing period_end, interval, line items + update-fortnox-order webhook missing"
  - "v2.0.0: Complete redesign — trigger changed from webhook to polling scheduler (every 5 min)"
  - "v2.0.0: Output changed from direct Fortnox update to dashboard routing (middle layer)"
  - "v2.0.0: Added mode switch (dashboard vs direct) as single workflow variable"
  - "v2.0.0: Freight calculation now uses A10 tier table instead of hardcoded 499 SEK"
  - "v2.0.0: Absorbs A3 (Order Field Enrichment) — A3 is now deprecated"
  - "v2.1.0: Corrected API endpoint from /api/v2/opportunities to /api/v2/orders (confirmed via A2-Test)"
  - "v2.1.0: Corrected date filter param from modifiedSince to modDate (confirmed via A2-Test)"
  - "v2.1.0: Fortnox order lookup via deal.custom[fieldId=4] (FORTNOX_ORDER_ID)"
  - "v2.2.0: Stage filter does not work as API param — fetch all modDate-filtered orders, filter stage=12 client-side"
  - "v2.2.0: FreightVAT confirmed 25%, StockPointCode confirmed '2'"
  - "v2.2.0: Remarks = custom[fieldId=7] (REMARKS) value if present, else skip"
  - "v2.2.0: Added YourOrderNumber = custom[fieldId=1] (REFERENCE) customer reference"
  - "v2.2.0: Added full Upsales custom field map"
next_steps:
  - Confirm default PriceList code with Nils (add to enrichmentFields.PriceList when known)
  - Test with a real Upsales deal in Fortnox stage
stage_history:
  - stage: spec
    date: 2026-01-09
  - stage: build
    date: 2026-02-17
  - stage: spec
    date: 2026-02-18
  - stage: build
    date: 2026-02-18
---

# A2: Upsales Order Enrichment Pipeline

## Goal

**Problem:** The native Upsales→Fortnox integration creates orders with ~80% of fields populated. The remaining ~20% (phone, delivery address, shipping cost, warehouse, order text) are missing. Rebecca manually fills them in for every order.

**Solution:** A scheduled n8n workflow polls Upsales every 5 minutes for deals that recently moved to the "Fortnox" stage. For each new deal, it fetches the Fortnox order created by the native integration, enriches the missing fields, and routes the result through the dashboard for Rebecca to review before applying.

**Business Value:** Eliminates 5–10 min manual work per order. Correct freight on every order via tiered pricing. Rebecca has a final review gate before Fortnox is updated.

---

## Mode Switch

The workflow has a single variable `ENRICHMENT_MODE` that controls output behavior:

| Mode | Behavior | When to use |
|------|----------|-------------|
| `"dashboard"` (default) | POST enriched order to FastAPI dashboard as a pending order. Rebecca approves → Fortnox updated. | Now — while verifying data quality |
| `"direct"` | PUT enriched fields directly to Fortnox order. No dashboard step. | Later — once dashboard data is consistently correct |

**To switch:** Change the `ENRICHMENT_MODE` workflow variable in n8n. No code changes needed.

---

## Flow Diagram

```mermaid
flowchart TD
    SCHEDULE((Scheduler\nevery 5 min)) --> FETCH_DEALS[GET Upsales Orders\nmodDate > now-10min\n/api/v2/orders]
    FETCH_DEALS --> FILTER_STAGE[Filter client-side\nstage.id === 12]
    FILTER_STAGE --> HAS_DEALS{{Any deals\nin Fortnox stage?}}
    HAS_DEALS -->|No| STOP_EMPTY[Stop - nothing to do]
    HAS_DEALS -->|Yes| LOOP[For each deal...]

    LOOP --> FETCH_COMPANY[GET Upsales Company\nphone + address]
    FETCH_COMPANY --> FETCH_ORDER[GET Fortnox Order\nGET /3/orders/{custom[4].value}\ncustom fieldId=4 = FORTNOX_ORDER_ID]
    FETCH_ORDER --> ORDER_EXISTS{{Fortnox order\nexists?}}
    ORDER_EXISTS -->|No| SKIP[Skip - native integration\nnot done yet\nwill retry next run]
    ORDER_EXISTS -->|Yes| IDEMPOTENCY{{Already enriched?\nDeliveryAddr + Freight > 0}}
    IDEMPOTENCY -->|Yes| SKIP2[Skip - already done]
    IDEMPOTENCY -->|No| FETCH_CUSTOMER[GET Fortnox Customer\nfor address details]
    FETCH_CUSTOMER --> BUILD[Code: Build enrichment payload\n+ A10 freight tier lookup]
    BUILD --> MODE{{ENRICHMENT_MODE}}
    MODE -->|dashboard| POST_DASHBOARD[POST to FastAPI\n/webhook/pending-orders\nsource='new']
    MODE -->|direct| PUT_FORTNOX[PUT Fortnox Order\n/3/orders/DocumentNumber]
    POST_DASHBOARD --> DONE[Done]
    PUT_FORTNOX --> DONE
```

---

## Polling Strategy

### Why polling instead of webhook
Upsales does not support sending webhooks on deal stage changes. Polling every 5 minutes is the reliable alternative.

### Poll window
- **Interval:** Every 5 minutes (`*/5 * * * *`)
- **Lookback window:** Deals updated in the last **10 minutes** (slightly wider than poll interval to prevent gaps at boundaries)
- **API filter:** `modDate > (now - 10 min)` — server-side date filter
- **Stage filter:** Client-side only — `stage.id === 12`. The Upsales API `stage` query param does not filter reliably; filter after fetching.

### Handling timing
If the Fortnox order hasn't been created yet by the native integration when we first poll, `custom[fieldId=4]` will be empty → skip. The next poll (5 min later) tries again. No explicit wait step needed.

---

## Upsales Custom Fields Reference

The `custom[]` array on each deal maps `fieldId` to its meaning:

| fieldId | Alias | Name (Swedish) | Type | Notes |
|---------|-------|----------------|------|-------|
| 1 | `REFERENCE` | Kundens referensnummer | String | Customer's own reference → Fortnox `YourOrderNumber` |
| 2 | `IS_PAID` | Betald | Boolean | Set by integration |
| 3 | `NO_REMINDERS` | Antal påminnelser | String | Set by integration |
| 4 | `FORTNOX_ORDER_ID` | Ordernummer | String | **Fortnox DocumentNumber** — set by native integration |
| 5 | `FORTNOX_OFFER_ID` | Offertnummer | String | Fortnox offer number |
| 6 | `FORTNOX_ID` | Fakturanummer | String | Fortnox invoice number |
| 7 | `REMARKS` | Tel nr, fakturamail, leveransdatum, övrig info | String | Free text from Rebecca → Fortnox `Remarks` |
| 12 | — | Leasing eller köp? | Select | Leasing / Engångsköp |
| 13 | — | Kundansvarig | User | Account manager |
| 14 | `BUNDLE_SYNC_TYPE` | Paketsynk | String | Bundle sync type |
| 15 | — | Betalningsvillkor | Select | 15 dagar / 30 dagar |
| 17 | — | Faktureringsintervall | Select | Kvartal / Halvår / Helår / Ingen prenumeration |
| 18 | — | Avtalslängd | Select | 12 mån / 24 mån / 36 mån |
| 20 | — | Fakturaavgift | Select | Ja (default) / Nej |

**Helper to read a custom field (use in all Code nodes):**
```javascript
function getCustomField(customArr, fieldId) {
  const field = (customArr || []).find(c => c.fieldId === fieldId);
  return field ? (field.value || null) : null;
}

// Usage:
const fortnoxOrderId = getCustomField(deal.custom, 4); // FORTNOX_ORDER_ID → Fortnox DocumentNumber
const customerRef    = getCustomField(deal.custom, 1); // REFERENCE → YourOrderNumber
const remarks        = getCustomField(deal.custom, 7); // REMARKS → Fortnox Remarks
```

---

## Enrichment Fields (The 20% Gap)

| # | Field | Source | Fortnox API Field | Logic |
|---|-------|--------|-------------------|-------|
| 1 | Phone | Fortnox Customer | `Order.Phone1` | Copy from customer if order.Phone1 is empty |
| 2 | Delivery address | Fortnox Customer | `Order.DeliveryAddress1`, `.DeliveryCity`, `.DeliveryZipCode`, `.DeliveryCountry`, `.DeliveryName` | Copy customer delivery address; fallback to billing address |
| 3 | Freight | A10 tier table | `Order.Freight` | Calculate from order subtotal + currency — see A10 spec |
| 4 | Freight VAT | Fixed | `Order.FreightVAT` | **25%** |
| 5 | Price list | Fixed default | `Order.PriceList` | TBD: confirm code with Nils |
| 6 | Warehouse | Fixed | `Order.StockPointCode` | **"2"** |
| 7 | Order text | Upsales `custom[fieldId=7]` | `Order.Remarks` | Use REMARKS value if present; omit field entirely if empty |
| 8 | Customer reference | Upsales `custom[fieldId=1]` | `Order.YourOrderNumber` | Use REFERENCE value if present; omit field entirely if empty |

**Rule:** Only set fields that are currently empty on the Fortnox order. Never overwrite a field that already has a value.

---

## Freight Calculation (A10 Tier Table)

Freight is calculated from the order's `Net` total and the customer's currency. See [A10 spec](a10-freight-tiering.md) for the full tier table.

**JavaScript implementation (n8n Code node):**

```javascript
const FREIGHT_TIERS = {
  SEK: [
    [500, 129], [1500, 199], [3000, 299], [7000, 599],
    [15000, 899], [20000, 1399], [30000, 1799],
    [45000, 1999], [70000, 2499]
  ],
  EUR: [
    [50, 19.9], [150, 24.9], [300, 39.9], [700, 59.9],
    [1500, 89.9], [2000, 139.9], [3000, 179.9],
    [4500, 199.9], [7000, 249.9]
  ]
};

function calculateFreight(subtotal, currency = 'SEK') {
  const tiers = FREIGHT_TIERS[currency] || FREIGHT_TIERS.SEK;
  for (const [maxVal, freight] of tiers) {
    if (subtotal <= maxVal) return freight;
  }
  return null; // Over max → "on request" — leave Freight field empty
}
```

---

## API References

| System | Endpoint | Method | Auth | Purpose |
|--------|----------|--------|------|---------|
| Upsales | `/api/v2/orders?modDate={iso_ts}&limit=100` | GET | Bearer token (query param) | Poll for recently-modified orders; filter stage=12 client-side |
| Upsales | `/api/v2/accounts/{companyId}` | GET | Bearer token (query param) | Fetch company phone + address |
| Fortnox | `/3/orders/{custom[4].value}` | GET | OAuth2 | Fetch the Fortnox order directly via FORTNOX_ORDER_ID |
| Fortnox | `/3/customers/{CustomerNumber}` | GET | OAuth2 | Fetch full customer record for enrichment fields |
| FastAPI | `/webhook/pending-orders` | POST | Internal | Post enriched order to dashboard (dashboard mode) |
| Fortnox | `/3/orders/{DocumentNumber}` | PUT | OAuth2 | Update order with enrichment (direct mode) |

---

## Idempotency

Two layers prevent double-processing:

1. **Fortnox order check:** Before enriching, verify `DeliveryAddress1` is empty AND `Freight = 0`. If either is set → skip.
2. **Dashboard unique key:** `your_order_number = "U{upsalesDealId}"`. The `UNIQUE` constraint in `pending_orders` rejects duplicate submissions for the same deal.

---

## Dashboard Payload (dashboard mode)

When `ENRICHMENT_MODE = "dashboard"`, POST to FastAPI `/webhook/pending-orders`:

```json
{
  "contract_number": "",
  "customer_number": "{FortnoxCustomerNumber}",
  "customer_name": "{CustomerName}",
  "source": "new",
  "fortnox_order_number": "{deal.custom[fieldId=4].value}",
  "order_payload": {
    "Order": {
      "Phone1": "...",
      "DeliveryAddress1": "...",
      "DeliveryCity": "...",
      "DeliveryZipCode": "...",
      "DeliveryCountry": "SE",
      "DeliveryName": "...",
      "Freight": 299,
      "FreightVAT": 25,
      "StockPointCode": "2",
      "PriceList": "TBD",
      "YourOrderNumber": "{custom[1].value — omit if empty}",
      "Remarks": "{custom[7].value — omit if empty}"
    }
  },
  "delivery_date": "{order.DeliveryDate}",
  "total_amount": "{order.Net}",
  "freight": 299,
  "item_summary": "{top 3 order rows summarized}",
  "item_count": "{number of order rows}",
  "remarks": "{custom[7].value or empty string}",
  "your_order_number": "U{upsalesDealId}"
}
```

**Important:** `order_payload` contains ONLY the enrichment fields (the delta), not the full order. When approved, FastAPI calls the Order Updater webhook which does `PUT /3/orders/{DocumentNumber}` with only these fields. `OrderRows` are never included — Fortnox would delete existing rows if sent.

---

## Open Questions

| # | Question | Impact | Blocked on |
|---|----------|--------|-----------|
| 1 | ~~Exact Upsales API filter param for `modifiedSince`~~ **ANSWERED: `modDate`** | Polling query | ✅ |
| 2 | ~~Fortnox stage ID in Upsales pipeline~~ **ANSWERED: `12` ("Fortnox")** | Deal filter | ✅ |
| 3 | ~~Does native integration put Upsales deal ID on Fortnox order?~~ **ANSWERED: No. `deal.custom[fieldId=4]` = FORTNOX_ORDER_ID** | Order lookup | ✅ |
| 4 | ~~FreightVAT: 25% or 30%?~~ **ANSWERED: 25%** | Enrichment payload | ✅ |
| 5 | Default PriceList code | Enrichment payload | Nils |
| 6 | ~~Remarks text~~ **ANSWERED: use `custom[fieldId=7]` if present, else omit** | Enrichment payload | ✅ |
| 7 | ~~StockPointCode "1"?~~ **ANSWERED: "2"** | Enrichment payload | ✅ |

---

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| No deals updated in last 10 min | Workflow stops silently — normal case |
| Deals updated but none in stage 12 | Client-side filter removes them — stop silently |
| `custom[fieldId=4]` is empty (Fortnox order not yet created) | Skip deal — picked up on next poll in 5 min |
| Order already enriched (idempotency) | Skip silently |
| Duplicate dashboard submission (same deal) | FastAPI unique constraint rejects, returns warning — non-fatal |
| Fortnox rate limit (429) | n8n HTTP retry with backoff |
| Fortnox OAuth token expired | n8n credential auto-refresh |
| Upsales API unavailable | n8n logs error, retries on next scheduled run |
| Customer has no delivery address | Fallback to billing address fields |
| Order total > max freight tier (70k+ SEK / 7k+ EUR) | Set `Freight = null` — leave empty, "on request" |
| `custom[fieldId=1]` (REFERENCE) is empty | Omit `YourOrderNumber` from payload entirely |
| `custom[fieldId=7]` (REMARKS) is empty | Omit `Remarks` from payload entirely |

---

## Testing

### Pre-build (required)
- [x] Run A2-Test workflow — document Upsales API payload + Fortnox reference fields
- [x] Answer open questions 1–4, 6–7
- [ ] Confirm PriceList code with Nils

### Post-build acceptance criteria
- [ ] Deals in Fortnox stage picked up within 5–10 minutes of stage change
- [ ] All enrichment fields populated correctly (only if currently empty)
- [ ] Existing field values never overwritten
- [ ] Freight matches A10 tier table based on order total + currency
- [ ] Dashboard pending order appears in New Orders tab with pre-filled `fortnox_order_number`
- [ ] Idempotent: running twice on same deal → no duplicate
- [ ] Mode switch works: `"direct"` → Fortnox updated immediately, no dashboard entry

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-09 | Initial spec — CRM-to-ERP customer sync (Upsales company → Fortnox customer) |
| 1.1.0 | 2026-02-17 | Combined with A3; built n8n workflow (ID 3UN62IAw58ARgtkO) with direct Fortnox update |
| 2.0.0 | 2026-02-18 | Complete redesign: polling trigger, dashboard routing, mode switch, A10 freight tiering, absorbs A3 |
| 2.1.0 | 2026-02-18 | API corrections from A2-Test: endpoint `/api/v2/orders`, filter param `modDate`, order lookup via `custom[fieldId=4]` |
| 2.2.0 | 2026-02-18 | Stage filter client-side only; FreightVAT=25%, StockPointCode="2"; Remarks from custom[7]; YourOrderNumber from custom[1]; full custom field map added |

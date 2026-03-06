---
id: p1-checklist
name: Order Automation Testing Checklist (A1 + A2 + Dashboard)
type: phase
stage: test
created: 2026-02-18
covers: [a1, a2, p1]
---

# Order Automation Testing Checklist

Covers A1 (Recurring Order Generator), A2 (Upsales Enrichment Pipeline), and P1 (Order Approval Dashboard) end-to-end.

---

## 0. Known Gaps (read before testing)

| Ref | Issue | Impact |
|-----|-------|--------|
| fix3 (partial) | `customer_update_payload` not stored in DB → Fortnox Customer NOT updated on approval | Customer delivery address not synced to Fortnox Customer record; **order enrichment fields ARE applied** |
| A2 testing mode | `LOOKBACK_DAYS=1`, Limit=1 node, Skip bypass still active | Must revert before production activation (see Section 6) |
| spec-note | A1 webhook (`/webhook/pending-orders`) stores one order at a time sequentially — if n8n posts all orders in a single payload, only 1 is created (first one that passes duplicate check wins, or batching is not supported). Needs spec investigation: should n8n post orders individually, or should the endpoint support true batch inserts? | Future spec item |

---

## 1. Pre-Test Setup

- [x] Dashboard accessible at Railway production URL
- [x] Login works with `DASHBOARD_PASSWORD`
- [x] n8n instance accessible and healthy
- [x] Fortnox OAuth credentials valid in n8n
- [x] Upsales API key valid in n8n
- [x] `N8N_WEBHOOK_BASE_URL` env var set on Railway FastAPI service
- [x] At least 1 Fortnox **active contract** with next period start within 30 days (A1 window is already 30 days, not 7 — confirmed via MCP)
- [x] At least 1 Upsales deal in **stage 12** with `custom[fieldId=4]` (FORTNOX_ORDER_ID) populated (for A2)

---

## 2. A1 — Recurring Order Generator

**Workflow:** "Recurring Order Automation" (ID: qJHgvXLKFdCBja1o) — currently inactive.

**Safe testing approach:** Use Limit node set to 2 before running; disable CREATE node until ready.

### 2a. Contract Fetching & Filtering

- [x] Run A1 manually in n8n with Limit=2, CREATE node disabled
- [x] `GET /3/contracts` pagination: all pages fetched (≈1828 contracts total without limit)
- [x] Only `Status === "ACTIVE"` contracts pass the status filter
- [x] Timing: `daysUntilEnd = PeriodEnd - today` — only contracts within trigger window proceed

### 2b. Duplicate Detection

- [x] Re-run A1 with same contract → `/webhook/pending-orders` returns `duplicates_skipped: 1`
- [x] No duplicate entries created in DB
- [x] `YourOrderNumber = C{DocumentNumber}-{PeriodEnd}` pattern confirmed in n8n node output

### 2c. Order Formatting (inspect node output)

- [x] `CustomerNumber` mapped from contract
- [x] `OrderRows` = contract `InvoiceRows` (with correct field names: ArticleNumber, Description, DeliveredQuantity, Price, VAT, Unit)
- [x] `DeliveryDate` = contract `PeriodEnd`
- [x] `YourReference`, `OurReference`, `Currency`, `TermsOfDelivery`, `TermsOfPayment` all copied
- [x] `Comments` = `Auto-generated from contract #{DocumentNumber}`

### 2d. Dashboard Submission

- [x] A1 POSTs to `POST /webhook/pending-orders`
- [x] Dashboard `/orders?tab=recurring` shows order in **Pending**
- [x] `source = "recurring"` on the order
- [x] `fortnox_order_number` is empty (recurring orders are created fresh in Fortnox)
- [x] Line items table visible on order detail page
- [x] `period_start`, `period_end`, `interval` all populated correctly (e.g. Halvår, 2027-02-13)
- [x] **Note:** 0 SEK freight on some orders is correct — freight is added as a line item for those contracts

### 2e. Acceptance Criteria

- [x] Without Limit: 10 orders created from full contract set (200-day test window); pagination confirmed working
- [x] Only contracts due within trigger window produce pending orders
- [x] Duplicate prevention confirmed on re-run (`duplicates_skipped: 1`, `stored: 0`)

---

## 3. A2 — Upsales Order Enrichment Pipeline

**Workflow:** "A2: Upsales Order Enrichment Pipeline" (ID: 3UN62IAw58ARgtkO) — currently inactive.

### 3a. Pre-Run Config Check (in n8n A2 workflow)

- [ ] Open **Code: Init** node — note current `LOOKBACK_DAYS` value (currently `1` for testing; set to `0` for production)
- [ ] **DEBUG: Limit Orders** node — confirm limit is set to `1` for testing (remove/disable before production)
- [ ] **IF: Skip** node — both TRUE and FALSE branches currently route to GET Fortnox Customer (sticky note warns about this). Confirm this is intentional for this test run, note it for production fix.

### 3b. Polling and Filtering

- [ ] Run A2 manually in n8n (or wait ≤5 min for scheduled run)
- [ ] `GET Upsales Orders` URL uses `modDate=gt:{isoTimestamp}` format (comparison prefix required)
- [ ] `Code: Filter Stage 12` filters client-side: only `stage.id === 12` items proceed
- [ ] `IF: Has Fortnox ID` correctly skips deals where `custom[fieldId=4]` is empty
- [ ] If `custom[fieldId=4]` is empty → deal skipped with `skipReason: 'order_not_found'` (will retry next poll)

### 3c. Enrichment Field Logic (inspect Code: Build Enrichment output)

- [ ] **Phone:** copied from Fortnox Customer.Phone1; only set if order.Phone1 currently empty
- [ ] **Delivery address:** Customer.DeliveryAddress1 → fallback to billing address if delivery fields missing
- [ ] **Freight tier boundary values:**

  | Order Net (SEK) | Expected Freight |
  |----------------|-----------------|
  | ≤ 500 | 129 |
  | 501 – 1,500 | 199 |
  | 1,501 – 3,000 | 299 |
  | 3,001 – 7,000 | 599 |
  | 7,001 – 15,000 | 899 |
  | 15,001 – 20,000 | 1,399 |
  | 20,001 – 30,000 | 1,799 |
  | 30,001 – 45,000 | 1,999 |
  | 45,001 – 70,000 | 2,499 |
  | > 70,000 | null (omitted) |

  | Order Net (EUR) | Expected Freight |
  |----------------|-----------------|
  | ≤ 50 | 19.9 |
  | 51 – 150 | 24.9 |
  | 151 – 300 | 39.9 |
  | > 7,000 | null (omitted) |

- [ ] `FreightVAT = 25`, `StockPointCode = "2"` in payload
- [ ] `YourOrderNumber` = Upsales `custom[1]` value — **omitted entirely** if empty
- [ ] `Remarks` = Upsales `custom[7]` value — **omitted entirely** if empty

### 3d. Dashboard Payload (inspect POST Dashboard node input)

- [ ] `source = "new"`, `fortnox_order_number` = Fortnox DocumentNumber pre-set
- [ ] `your_order_number = "U{upsalesDealId}"` (unique key)
- [ ] `period_start` and `period_end` from Fortnox order fields (may be null for non-subscription orders)
- [ ] `interval` from Upsales `custom[17]` — one of: Kvartal / Halvår / Helår / null
- [ ] `order_payload.Order.OrderRows` contains existing Fortnox order rows (Order Updater will strip before PUT)
- [ ] `customer_info` object has: `phone`, `email`, `address1`, `city`, `zip`, `country`
- [ ] `customer_update_payload` included in POST body (stored in DB — see known gap in Section 0)

### 3e. Dashboard Verification

- [ ] Dashboard `/orders?tab=new` shows order in **Pending**
- [ ] `fortnox_order_number` pre-populated and visible
- [ ] Customer info card visible on detail page (phone, email, delivery address)
- [ ] `period_end` field visible and correctly populated
- [ ] `interval` field shows (Kvartal / Halvår / Helår) or `—` if not set
- [ ] Line items table populated from OrderRows
- [ ] Idempotency: re-run A2 for same deal → `duplicates_skipped: 1`, no new entry

### 3f. Idempotency / Skip Logic

- [ ] Manually set `DeliveryAddress1` on a Fortnox order → re-run A2 → deal SKIPPED (`already_enriched`)
- [ ] Manually set `Freight > 0` on a Fortnox order → re-run A2 → deal SKIPPED
- [ ] Both `DeliveryAddress1` empty AND `Freight = 0` → deal IS processed

---

## 4. Dashboard (P1) Tests

### 4a. Order List Page (`/orders`)

- [ ] Recurring tab shows only `source=recurring` orders
- [ ] New tab shows only `source=new` orders
- [ ] Status filter works for: `pending` / `approved` / `denied` / `created` / `failed` / `all`
- [ ] Sort works: `delivery_date` / `customer_name` / `total_amount`
- [ ] Stats bar: pending count, total SEK value, created count all accurate for the active tab
- [ ] Tab badges show correct pending count per tab

### 4b. Order Detail Page (`/orders/{id}`)

- [ ] Customer info card visible and populated (for A2 orders)
- [ ] `period_start`, `period_end`, `interval` displayed (populated for A2 orders; may be blank for A1)
- [ ] Line items table populated and editable (for pending/failed orders)
- [ ] Audit log section visible
- [ ] Error box shows for failed orders with error message

### 4c. Edit Functionality

- [ ] Edit `remarks` → Save → persisted; audit log records field change with old/new values
- [ ] Edit `freight` → Save → `total_amount` recalculates (line items total + admin_fee + freight)
- [ ] Edit `administration_fee` → Save → `total_amount` recalculates
- [ ] Edit `delivery_date` → Save → `order_payload.Order.DeliveryDate` also updated
- [ ] Edit `period_end` → Save → `order_payload.Order.PeriodEnd` also updated (carries to Fortnox PUT)
- [ ] Edit `period_start` → Save → persisted
- [ ] Add line item row → Save → `item_count` increments, `item_summary` updates
- [ ] Remove line item row → Save → `item_count` decrements
- [ ] Cannot edit order with status `approved`, `created`, or `denied` → redirected with flash message

### 4d. Denial Flow

- [ ] Select pending order → Deny → status = `denied`; audit log records action
- [ ] Denied order appears in `denied` filter view
- [ ] Cannot deny a non-pending order (no deny button shown)

### 4e. Delete Flow

- [ ] Can soft-delete `pending`, `denied`, `failed` orders
- [ ] Cannot soft-delete `approved` or `created` orders (button absent or silently skipped)
- [ ] Deleted orders hidden from all tabs and status filters
- [ ] Audit log records `deleted` with `previous_status`

### 4f. Approve → Recurring Order → Fortnox CREATE

- [ ] Select recurring order (no `fortnox_order_number`) → Approve
- [ ] FastAPI POSTs to `{N8N_WEBHOOK_BASE_URL}/webhook/create-fortnox-order`
- [ ] n8n Order Creator responds `{"success": true, "fortnox_order_number": "XXXXX"}`
- [ ] Order status = `created`, `fortnox_order_number` saved in DB and visible on detail page
- [ ] Audit log shows `approved` + `created` entries
- [ ] Open Fortnox → confirm draft order exists with correct CustomerNumber, OrderRows, DeliveryDate

### 4g. Approve → New Order → Fortnox UPDATE

- [ ] Select new order (has `fortnox_order_number`) → Approve
- [ ] FastAPI POSTs to `{N8N_WEBHOOK_BASE_URL}/webhook/update-fortnox-order`
- [ ] Order Updater flow: Strip OrderRows → PUT /3/customers → PUT /3/orders/{num}
- [ ] Responds `{"success": true, "fortnox_order_number": "XXXXX"}`
- [ ] Order status = `created`
- [ ] Open Fortnox order → confirm enrichment fields present: phone, delivery address, freight, StockPointCode="2"
- [ ] ⚠️ **Known gap (fix3):** Open Fortnox Customer record → check if delivery address was updated. Due to missing `customer_update_payload` forwarding, it likely was NOT updated. Note actual behaviour here.

### 4h. Authentication

- [ ] Accessing `/orders` without session → redirected to `/login`
- [ ] Wrong password → login fails with error message
- [ ] Correct password → session created, dashboard accessible
- [ ] `/logout` → session cleared, redirected to login

---

## 5. End-to-End Flows

### 5a. Full Recurring Order Flow

```
A1 n8n (manual, Limit=1, CREATE enabled)
  → POST /webhook/pending-orders
  → Dashboard "Recurring" tab — order visible (pending)
  → Edit freight/remarks → Save
  → Approve
  → Order Creator webhook → POST /3/orders
  → Dashboard status = "created", fortnox_order_number populated
  → Re-run A1 same day → no duplicate created
```

- [ ] Every step completes without errors
- [ ] Fortnox draft order has correct fields: CustomerNumber, OrderRows, DeliveryDate, YourOrderNumber
- [ ] YourOrderNumber in Fortnox = `C{DocNum}-{PeriodEnd}`
- [ ] Re-run duplicate prevention works

### 5b. Full New Order Flow

```
Upsales deal moved to stage 12
  → A2 poll (≤5 min) → POST /webhook/pending-orders (source=new)
  → Dashboard "New" tab — order visible (pending)
  → Verify: period_end, interval, customer_info, line items all visible
  → Edit if needed → Approve
  → Order Updater webhook → PUT /3/customers + PUT /3/orders/{num}
  → Dashboard status = "created"
  → Verify Fortnox order enrichment
  → Re-run A2 for same deal → duplicates_skipped: 1
```

- [ ] Deal appears in dashboard within 5 minutes of stage change
- [ ] All enrichment fields visible on detail page (phone, address, freight, period_end, interval)
- [ ] Approval → Order Updater responds with success
- [ ] Fortnox order updated: phone, delivery address, freight, StockPointCode="2"
- [ ] ⚠️ Note whether Fortnox Customer delivery address was updated (fix3 gap)
- [ ] Duplicate prevention: re-run A2 → `duplicates_skipped: 1`

---

## 6. Pre-Production Checklist (before activating A2)

Complete these steps before switching A2 to active in production:

- [ ] **Code: Init** — set `LOOKBACK_DAYS = 0` (switch from 1-day window to 10-min rolling window)
- [ ] **DEBUG: Limit Orders** node — remove or disable from the flow
- [ ] **IF: Skip** — fix TRUE branch: should STOP (not route to GET Fortnox Customer) to restore proper idempotency
- [ ] Activate A2 workflow in n8n
- [ ] Monitor first 2–3 executions in n8n execution log — confirm no unexpected errors
- [ ] Confirm deals are picked up within 5 min of moving to stage 12

---

## 7. Sign-Off

| Area | Pass? | Notes |
|------|-------|-------|
| A1 contract fetching (all pages, ≈1828) | ✅ | 10 orders from full contract set; pagination confirmed |
| A1 duplicate prevention | ✅ | duplicates_skipped: 1, stored: 0 |
| A1 → dashboard submission | ✅ | period_end, interval, line items all correct |
| A2 polling + stage 12 filter | | |
| A2 enrichment field logic (freight tiers, fields) | | |
| A2 → dashboard (period_end, interval, customer_info, OrderRows) | | |
| Dashboard list / filter / sort | | |
| Dashboard edit (fields + line items) | | |
| Dashboard deny | | |
| Dashboard delete | | |
| Approve → Fortnox CREATE (recurring) | | |
| Approve → Fortnox UPDATE (new) | | |
| Fortnox Customer updated on approval | ⚠️ fix3 gap | Note actual result |
| End-to-end recurring (full flow) | | |
| End-to-end new (full flow) | | |
| A2 production config reverted | | |

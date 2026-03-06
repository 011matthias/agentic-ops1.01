# Verification Checklist — Upsales Enrichment Pipeline

Post-build verification steps. Work through these in order.

---

## Phase 0: Test Workflow (Discovery)

Run the Test Workflow in n8n UI to confirm API payload structure.

- [ ] Test workflow created in n8n and activatable from UI
- [ ] Fetch deals in "Fortnox" stage from Upsales — response received
- [ ] **Confirm:** Upsales deal payload includes company ID and customer number
- [ ] **Confirm:** Fortnox order created by native integration is findable (which field? customer number / YourOrderNumber / ExternalReference?)
- [ ] **Document answers** in `docs/open-questions.md` (Questions 3, 4, 5)

---

## Phase 1: n8n A2 Workflow — Dashboard Mode

Test the enrichment pipeline end-to-end in dashboard mode (`ENRICHMENT_MODE = "dashboard"`).

### Webhook Trigger
- [ ] Upsales webhook is registered and receives deal stage change events
- [ ] Workflow correctly identifies deal moving to "Fortnox" stage (not other stages)
- [ ] Invalid events are filtered out / skipped

### Wait + Order Fetch
- [ ] 5-minute wait executes correctly
- [ ] Fortnox order search returns the correct order (the one created by native integration, not an older order)
- [ ] If no order found → workflow handles gracefully (logs error, does not crash)

### Idempotency
- [ ] If `DeliveryAddress1` is already set AND `Freight` > 0 → workflow stops with "already enriched" message
- [ ] Run the workflow twice on the same deal → **second run skips**, no duplicate pending order created

### Enrichment Payload
- [ ] `Phone1` copied from Fortnox customer record
- [ ] `DeliveryAddress1`, `DeliveryCity`, `DeliveryZipCode`, `DeliveryCountry` filled from customer delivery address
- [ ] When customer has no delivery address → **falls back** to billing address
- [ ] `Freight` calculated from A10 tier table (not hardcoded 499)
  - [ ] Test with order ≤ 500 SEK → freight = 129
  - [ ] Test with order = 501 SEK → freight = 199
  - [ ] Test with order > 70,000 SEK → freight = null / empty
- [ ] `FreightVAT` set to correct percentage (confirm with Nils)
- [ ] `Remarks` populated with correct default text
- [ ] Existing fields (non-empty) are NOT overwritten

### Dashboard Pending Order
- [ ] Pending order appears in **New Orders tab** (not Recurring)
- [ ] `source = 'new'`
- [ ] `fortnox_order_number` pre-filled with correct Fortnox `DocumentNumber`
- [ ] `customer_name` and `customer_number` correct
- [ ] `total_amount` matches Fortnox order total
- [ ] `freight` pre-filled with tiered freight amount
- [ ] `your_order_number` = `U{UpsalesDealId}` (unique)
- [ ] Second webhook call with same deal ID → **duplicate skipped** (unique constraint)

---

## Phase 2: FastAPI — Approve Route Update

Test that approval correctly UPDATES (not CREATES) the Fortnox order.

### Webhook Receiver
- [ ] `POST /webhook/pending-orders` accepts `fortnox_order_number` field
- [ ] Pending order stored with pre-filled `fortnox_order_number`
- [ ] Existing recurring orders still work (no `fortnox_order_number` in payload → stored as null)

### Approve Route — Enrichment Order
- [ ] Select enrichment pending order → click Approve
- [ ] Approve route detects `order.fortnox_order_number` is set → calls `/webhook/update-fortnox-order` (not create)
- [ ] Correct payload sent: `{ order_id, fortnox_order_number, enrichment_payload }`
- [ ] On success: `status = 'created'`, `fortnox_order_number` preserved
- [ ] On failure: `status = 'failed'`, `error_message` set, order visible in dashboard for retry

### Non-Regression: Recurring Order Approve
- [ ] Select a recurring order → click Approve
- [ ] Approve route detects `order.fortnox_order_number` is null → calls `/webhook/create-fortnox-order` (existing behavior)
- [ ] Fortnox order **created** (not updated), `fortnox_order_number` set from response
- [ ] Audit log records action correctly

### Deny Flow
- [ ] Deny an enrichment pending order → status = 'denied', no Fortnox call made

---

## Phase 3: n8n Order Updater Webhook

Test the new `/webhook/update-fortnox-order` workflow.

### Direct Webhook Test
Run via `curl` (see curl command in spec):
- [ ] Webhook reachable and returns 200
- [ ] Fortnox order updated with enrichment fields (verify in Fortnox UI)
- [ ] Response format: `{ success: true, order_id: "...", fortnox_order_number: "..." }`
- [ ] Error case (invalid order number) → `{ success: false, error: "..." }`

### Fortnox Order After Update
Open the Fortnox order in the UI and verify:
- [ ] `Phone1` populated
- [ ] Delivery address fields filled in
- [ ] `Freight` updated (not a new order row — order-level field)
- [ ] `FreightVAT` updated
- [ ] `Remarks` populated
- [ ] Existing order rows **unchanged** (PUT did not include OrderRows)
- [ ] No duplicate Fortnox order created

---

## Phase 4: Direct Mode Test

Switch `ENRICHMENT_MODE = "direct"` in the A2 n8n workflow.

- [ ] Workflow runs enrichment and calls PUT directly to Fortnox — **no pending order in dashboard**
- [ ] Fortnox order updated correctly (same field checks as Phase 3)
- [ ] Switch back to `"dashboard"` → dashboard mode works again

---

## Phase 5: Freight Tier Boundary Tests

Test critical boundary values using real or mock order amounts.

| Order Value (SEK) | Expected Freight |
|---|---|
| 499 | 129 |
| 500 | 129 |
| 501 | 199 |
| 1,499 | 199 |
| 1,500 | 199 |
| 1,501 | 299 |
| 70,000 | 2,499 |
| 70,001 | null / empty |
| EUR 6,999 | 249.9 |
| EUR 7,001 | null / empty |

- [ ] All boundary tests pass

---

## Phase 6: Full End-to-End Flow

Simulate a real deal in Upsales (use a test deal or staging environment):

1. [ ] Move deal to "Fortnox" stage in Upsales
2. [ ] Native integration creates Fortnox order (wait for it)
3. [ ] A2 workflow fires automatically (or manually trigger for testing)
4. [ ] Pending order appears in dashboard New Orders tab within 6 minutes
5. [ ] Rebecca reviews order in dashboard — fields look correct
6. [ ] Rebecca edits freight (override) → change persists
7. [ ] Rebecca approves → Fortnox order updated with enriched + edited fields
8. [ ] Audit log records: "approved" + "created" actions with correct actor
9. [ ] Dashboard shows order as "created" with correct Fortnox order number

---

## Sign-off Criteria

All items in Phases 1–5 checked. Phase 6 completed successfully. No duplicate Fortnox orders created during any test. Recurring order approval still works (Phase 2 non-regression).

**Signed off by:** _____________ **Date:** _____________

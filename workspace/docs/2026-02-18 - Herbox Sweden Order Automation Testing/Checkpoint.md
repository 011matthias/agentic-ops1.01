# Checkpoint: Herbox Sweden Order Automation Testing

**Date:** 2026-02-18
**Status:** Section 3b complete — A2 duplicate prevention fix deployed, ready to verify

---

## Summary
Completed full A1 testing (Sections 1–2e all passing), started A2 testing (Section 3), and fixed 5 bugs discovered during testing. A2 is now posting to the dashboard with correct admin fee and customer info. Final fix (duplicate prevention on unique constraint violation) just deployed — needs one more verification run.

---

## What Was Done This Session

### DB Reset
1. Built and used a temp `/dev/reset-db` endpoint on Railway to wipe all `pending_orders` and `approval_log` rows
2. Temp endpoint removed after use and redeployed clean

### A1 Testing — All Passing ✅
1. **Section 2a**: Contracts fetched, pagination confirmed working
2. **Section 2b**: Duplicate prevention: `duplicates_skipped: 1, stored: 0` ✅
3. **Section 2c**: Order formatting verified (CustomerNumber, OrderRows, DeliveryDate, references)
4. **Section 2d**: Dashboard submission correct — `period_end: 2027-02-13`, `interval: Halvår` ✅
5. **Section 2e**: Pagination test — 10 orders from full contract set with 200-day window ✅

### A2 Testing — In Progress
1. **Section 3a**: Pre-run config confirmed — LOOKBACK_DAYS=1, Limit=1, IF:Skip bypass active
2. **Section 3b**: A2 ran, 29 deals returned, 1 order posted to dashboard ✅

### Bugs Fixed
| Bug | Fix | Where |
|-----|-----|-------|
| `is_deleted` attribute doesn't exist | Changed to `status != "deleted"` | `webhooks.py` |
| `administration_fee` never set in A2 payload | Added `administrationFee = currency !== 'EUR' ? 30 : 0` | `Code: Build Enrichment` (n8n) |
| Customer info empty for already-enriched orders | `Code: Check Order` now passes all order fields in skip case too | n8n A2 workflow |
| `interval` not carried in already-enriched path | Added `interval: deal.interval` to `sharedFields` | `Code: Check Order` (n8n) |
| UniqueViolation 500 on duplicate A2 run | Duplicate check now matches all statuses; added `IntegrityError` handling on commit | `webhooks.py` |

---

## Key Decisions Made

### Admin Fee Logic (A2)
- **Choice:** `administrationFee = currency !== 'EUR' ? 30 : 0`
- **Rationale:** EUR orders add freight + admin fee as line items, not as order-level fields. SEK orders use 30 SEK default.

### Duplicate Check — All Statuses
- **Choice:** Removed `status != "deleted"` filter from duplicate check
- **Rationale:** Unique DB constraint applies to ALL rows including soft-deleted. Filtering by status causes a false "no duplicate found" → INSERT → UniqueViolation 500. Now matches any existing record regardless of status.

### Code: Check Order — Shared Fields Pattern
- **Choice:** Extract all order fields into `sharedFields` object, spread into both skip and non-skip return paths
- **Rationale:** `already_enriched` skip path was returning only minimal fields, leaving customer data empty. Testing bypass routes already-enriched orders through the full pipeline.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `clients/herbox-sweden/automations/app/routers/webhooks.py` | Modified (x3) | Fix is_deleted→status; remove status filter from dup check; add IntegrityError handling |
| `clients/herbox-sweden/specs/_checklists/order-automation-checklist.md` | Modified | Sections 2a–2e all checked; known gap for spec-note added; sign-off table updated |
| A2 workflow `3UN62IAw58ARgtkO` — `Code: Build Enrichment` | Modified via MCP | Added `administration_fee` to dashboard body; SEK=30, EUR=0 |
| A2 workflow `3UN62IAw58ARgtkO` — `Code: Check Order` | Modified via MCP | `sharedFields` pattern — all order fields passed in both skip and non-skip paths; interval added |

---

## Current Status

**Section 1:** ✅ Complete
**Section 2 (A1):** ✅ All passing — pagination, duplicates, formatting, dashboard submission
**Section 3a:** ✅ Config confirmed
**Section 3b:** ✅ 29 deals fetched, 1 order posted
**Section 3c–3e:** 🔄 In progress — waiting for final duplicate verification run
**Sections 4–7:** Not started

**Last deploy:** `webhooks.py` — duplicate check covers all statuses + IntegrityError safety net. Awaiting confirmation that rerun returns `duplicates_skipped: 1`.

---

## Next Steps

1. **Verify A2 duplicate prevention** — rerun A2 (without wiping DB), confirm `duplicates_skipped: 1, stored: 0`
2. **Section 3c** — inspect `Code: Build Enrichment` node output: verify freight tier, phone, delivery address, FreightVAT=25, StockPointCode=2
3. **Section 3d** — check dashboard New Orders: customer info card, fortnox_order_number, line items
4. **Section 3e (idempotency)** — set DeliveryAddress1 on a Fortnox order manually → rerun A2 → confirm deal skipped
5. **Section 3f** — confirm `duplicates_skipped: 1` on second A2 run for same deal
6. **Section 4 (Dashboard)** — list/filter/sort, edit, deny, delete flows
7. **Section 4f/4g** — Approve flows: recurring → Fortnox CREATE, new → Fortnox UPDATE

---

## Context for Next Session

### Files to Read First
- `clients/herbox-sweden/specs/_checklists/order-automation-checklist.md` — current checklist state (sections 2 done, 3 in progress)
- `clients/herbox-sweden/automations/app/routers/webhooks.py` — latest duplicate check logic
- `clients/herbox-sweden/docs/open-questions.md` — A2 open questions and provisional decisions

### Key Workflow IDs
- **A1:** `qJHgvXLKFdCBja1o` ("A1.0 - Recurring Order Automation") — inactive, Config node in place
- **A2:** `3UN62IAw58ARgtkO` ("A2.0 - Upsales Order Enrichment Pipeline") — inactive, Limit=1, LOOKBACK_DAYS=1

### A1 Config Node (id: config-node-a1) — current state
```javascript
testingMode: true
limitItems: 999999  // was set to unlimited for pagination test — revert to 2 for next targeted test
triggerWindowDays: 200   // ← revert to 30 for production
dryRun: false
```

### A2 Config (Code: Init)
```javascript
ENRICHMENT_MODE: 'dashboard'
LOOKBACK_DAYS: 1   // ← change to 0 for production
```

### Known Gaps Still Open
- **fix3:** `customer_update_payload` stored in DB but NOT forwarded to Fortnox Customer PUT on approval — Fortnox Customer delivery address won't update. Tracked in Section 4g checklist.
- **spec-note:** A1 webhook processes orders sequentially — if multiple orders in one payload, only one is stored currently (batch insert not implemented). Future spec item.
- **Informational line items:** Orders with "Skickat", "Sändningsnr", "KolliNr" rows (0-qty text rows from previous shipment) are copied from Fortnox into the dashboard. Consider filtering these out in a future spec.
- **A2 production config:** LOOKBACK_DAYS=1, Limit=1 node, IF:Skip bypass — must revert before activating A2 (Section 6 of checklist).

### Open Questions
- After Section 3 is verified: should we do all dashboard tests (Section 4) or go straight to Section 5 end-to-end?

---

## How to Continue

1. Read `clients/herbox-sweden/specs/_checklists/order-automation-checklist.md`
2. Rerun A2 in n8n (workflow `3UN62IAw58ARgtkO`) — confirm `duplicates_skipped: 1`
3. Inspect `Code: Build Enrichment` output for Section 3c
4. Check dashboard New Orders tab for Section 3d/3e
5. Continue through Section 4 (Dashboard tests)

# Checkpoint: Herbox Phase 6 Integration Testing

**Date:** 2026-02-15
**Status:** All 9 tests PASSED. Production readiness checklist pending.

---

## Summary
Completed all 9 Phase 6 integration tests for the Herbox Order Approval Dashboard. Every test passed: A1 order generation, dashboard display, editing, single approval, bulk approval, denial, duplicate prevention, error handling, and existing pages verification. The Fortnox Total 0.00 issue was investigated and determined to be normal Fortnox behavior (row totals reflect delivered quantity, not ordered quantity). Production readiness checklist items remain.

---

## What Was Done This Session

### Session 1 (Previous - see git history)
1. Pre-flight configuration (DEBUG limit, hardcoded URLs, webhook base URL)
2. Fixed Filter Duplicates to skip cancelled Fortnox orders

### Session 2 (Previous)
1. Tests 1-4 completed (A1 generation, dashboard display, editing, single approval)
2. Fixed Format Notification node (`$json` → `$node["Enrich & Format Order"].json`)
3. Fixed Order Creator credential (`jwn2NCWpooneGXpx` → `aHlEjdL3w6eDvn90`)

### Session 3 (Current)

#### Test 5: Bulk Approval - PASSED
1. Approved 2 pending orders (SHF #1394, Tingholmsgymnasiet #450)
2. Both created in Fortnox: #7986 (SHF, 21,234 SEK) and #7987 (Tingholmsgymnasiet, 10,156 SEK)
3. Flash message: "Approved: 2, Created in Fortnox: 2"
4. User manually cancelled both test orders (#7986, #7987) in Fortnox via n8n Cancel Orders utility

#### Test 6: Order Denial - PASSED
1. Reset Långared skola order to "pending" via direct DB update (Railway Postgres)
2. User denied the order from dashboard
3. Verified: status="denied", reviewed_at set, audit log shows "denied" entry

#### Test 7: Duplicate Prevention - PASSED
1. User re-ran A1 workflow
2. Execution #12: POST to FastAPI returned `"stored": 0, "duplicates_skipped": 1` for both contracts
3. No duplicate rows created in database

#### Test 8: Error Handling - PASSED
1. Reset Långared skola to "pending" and corrupted CustomerNumber to "INVALID_999"
2. User approved — Fortnox returned 400: "Kunde inte hämta/hitta kund" (code 2000204)
3. Order status changed to "failed" with error message displayed
4. Restored original CustomerNumber (889) after test

#### Test 9: Existing Dashboard Unchanged - PASSED
1. Verified all 5 pages via HTTP Basic Auth (herbox/changeme):
   - `/` — HTTP 200, 18.5K chars, Orders nav present
   - `/logs` — HTTP 200, 25K chars, Orders nav present
   - `/settings` — HTTP 200, 16.5K chars, Orders nav present
   - `/automations` — HTTP 200, 13.2K chars, Orders nav present
   - `/orders` — HTTP 200, 11.3K chars, Orders nav present

#### Fortnox Total 0.00 Investigation - NOT A BUG
1. Checked Order Creator execution #6 (order #7985) API response
2. Order-level `Total: 822` SEK — correct
3. Row-level `Total: 0` because Fortnox calculates row totals from `DeliveredQuantity` (shipped=0), not `OrderedQuantity`
4. Normal Fortnox behavior for undelivered orders

---

## Key Decisions Made

### Previous Session Decisions (still apply)
- Hardcode Railway URLs in n8n nodes (user preference)
- Skip cancelled orders in duplicate check
- PeriodEnd filter: exclude negative values (for production)
- Format Notification: reference `$node["Enrich & Format Order"].json` instead of `$json`

### Database Access Pattern
- **Choice:** Use `uv run --with psycopg2-binary` with Railway's public DATABASE_URL for direct DB access
- **Rationale:** No psql installed locally, Railway CLI `connect` requires psql, but psycopg2-binary is available via uv

### Fortnox Row Total = 0
- **Choice:** No fix needed
- **Rationale:** Fortnox calculates row `Total` from `DeliveredQuantity` (not `OrderedQuantity`). Order-level `Total` is correct.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| Railway Postgres DB (pending_orders) | Modified | Reset orders to pending for Tests 6, 8; corrupted/restored CustomerNumber for Test 8 |

### n8n Nodes Modified Previous Sessions (may need verification)
| Node | Workflow | ID | Change |
|------|----------|----|--------|
| Format Notification | A1 (`qJHgvXLKFdCBja1o`) | `6e9d99b0-574e-4107-9321-c3b0730acf75` | Changed `$json` to `$node["Enrich & Format Order"].json` (may need re-applying if user saved in UI) |
| Create Fortnox Order | Order Creator (`8lcnLemNsBETASdU`) | `create-order-001` | Updated credential to `aHlEjdL3w6eDvn90` |

---

## Current Status

### Test Results: ALL 9 PASSED
| Test | Description | Status |
|------|-------------|--------|
| 1 | A1 generates pending orders | PASSED |
| 2 | Dashboard displays orders | PASSED |
| 3 | Order detail & editing | PASSED |
| 4 | Single order approval | PASSED (after credential fix) |
| 5 | Bulk approval | PASSED |
| 6 | Order denial | PASSED |
| 7 | Duplicate prevention | PASSED |
| 8 | Error handling | PASSED |
| 9 | Existing dashboard unchanged | PASSED |

### Database State
- SHF #1394 (contract 838): status="created", fortnox_order_number="7986" (cancelled in Fortnox)
- Tingholmsgymnasiet #450 (contract 256): status="created", fortnox_order_number="7987" (cancelled in Fortnox)
- Långared skola #889 (contract 436): status="failed", customer_number restored to "889"

### Known Issues
- Format Notification fix may need re-applying if user saved workflow in n8n UI
- "Should Generate Order?" node routes both TRUE and FALSE to "Check Existing Orders" — potentially intentional but worth reviewing

---

## Next Steps

### Production Readiness Checklist (from Phase 6 spec)
| # | Item | Status |
|---|------|--------|
| 1 | Remove/increase DEBUG NODE limit | **Needs doing** |
| 2 | Set `RAILWAY_WEBHOOK_URL` in n8n env vars | Verify |
| 3 | Set `N8N_CREATE_ORDER_WEBHOOK` in Railway env vars | Verify |
| 4 | Activate A1 workflow schedule | **Needs doing** |
| 5 | Activate Order Creator webhook workflow | Already active |
| 6 | Configure Slack webhook in Send Notification node | **Needs doing** |
| 7 | Test walkthrough with Rebecca | User action |
| 8 | Confirm Fortnox order format with Nils/Rebecca | User action |
| 9 | Document dashboard URL + login for Rebecca | User action |
| 10 | PeriodEnd >= 0 filter (from earlier session) | **Needs doing** |

### Post-Production
1. Monitor A1 runs daily at 08:00
2. Check dashboard for new pending orders each morning
3. Verify approved orders appear correctly in Fortnox
4. Monitor failed orders in dashboard

---

## Context for Next Session

### Files to Read First
- `clients/herbox-sweden/specs/phases/phase-6-testing.md` — The testing spec (all 9 tests)
- `clients/herbox-sweden/automations/app/routers/orders.py` — Dashboard routes (approve, deny, edit)
- `clients/herbox-sweden/automations/app/models/pending_orders.py` — PendingOrder + ApprovalLog models

### Key IDs
- A1 workflow: `qJHgvXLKFdCBja1o` (Recurring Order Automation, inactive)
- Order Creator workflow: `8lcnLemNsBETASdU` (active)
- n8n MCP server: `n8n-herbox`
- Railway FastAPI URL: `https://herbox-automations-production.up.railway.app`
- Railway Postgres public URL: `postgresql://postgres:SrvApTQHUUStgOewcuNXwCDTyRYbnrTm@gondola.proxy.rlwy.net:58773/railway`
- n8n instance URL: `https://primary-production-ef56.up.railway.app`
- Fortnox OAuth2 credential ID: `aHlEjdL3w6eDvn90`
- Dashboard auth: HTTP Basic, username=herbox, password=changeme

### Database Access
```bash
uv run --with psycopg2-binary python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:SrvApTQHUUStgOewcuNXwCDTyRYbnrTm@gondola.proxy.rlwy.net:58773/railway')
cur = conn.cursor()
cur.execute('SELECT id, customer_name, status FROM pending_orders')
for r in cur.fetchall(): print(r)
conn.close()
"
```

### Open Questions
- Format Notification fix: was it overwritten by user's n8n UI save? Verify on next A1 run.
- "Should Generate Order?" node routes both TRUE and FALSE to "Check Existing Orders" — is this intentional?

### Reference Materials
- Phase specs: `clients/herbox-sweden/specs/phases/phase-1-database.md` through `phase-6-testing.md`
- PRD: `clients/herbox-sweden/specs/prd-order-dashboard.md`

---

## How to Continue
1. Read this checkpoint
2. All 9 integration tests are PASSED — no test work remaining
3. Resume at **Production Readiness Checklist** (items 1-10 above)
4. Key actions: remove DEBUG NODE limit, add PeriodEnd >= 0 filter, activate A1 schedule, configure Slack webhook
5. Items 7-9 require user/client involvement (Rebecca walkthrough, Fortnox format confirmation, documentation)

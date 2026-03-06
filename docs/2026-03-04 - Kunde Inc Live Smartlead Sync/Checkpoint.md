# Checkpoint: Kunde Inc Live Smartlead Sync

**Date:** 2026-03-04
**Status:** Live — 1967 campaigns syncing daily, A3a returning real data, dashboard-ready

---

## Summary
Connected Kunde Inc.'s A1 workflow to the live Smartlead API after multiple iterations resolving n8n Cloud sandbox restrictions, Cloudflare timeout issues, and Smartlead rate limiting. All 1967 non-DRAFTED campaigns now sync daily to Google Sheets via a rate-limited Split In Batches loop, and the A3a endpoint serves real data to the dashboard.

---

## What Was Done This Session

### A3a Endpoint Fix
1. Audited A3a (Campaigns API `QoEf8USAiguQR6T2`) Code node
2. Columns 17-19 were mapped to old ROI fields (`campaignCost`, `revenue`, `costPerLead`)
3. Updated to match new A1 column layout: `seqCount`, `clientId`, `clientName`
4. Deployed via `update-a3a-columns.py` — successful at 15:26:27

### A1 Workflow Iterations (Root-Cause Chain)
1. **Sequential fetch timeout**: 2647 campaigns × 200ms = 15+ min; Code node timed out
2. **`fetch()` sandbox**: n8n Cloud Code node blocks all external HTTP. All calls fail silently
3. **`$helpers.httpRequest()` sandbox**: Also blocked. Catch block returned zero-rows
4. **Restructured to HTTP Request nodes**: Added Filter Non-DRAFTED → Fetch Analytics → Build Row → Collect All Rows
5. **Python f-string URL bug**: `f"={{'...' + $json.id}}"` collapsed `{{` → `{` (single brace, invalid n8n expression). Fixed by string concatenation
6. **Build Row per-item validation error**: "A 'json' property isn't an object [item 0]" — removed Build Row, merged transform into Collect All Rows (runOnceForAllItems)
7. **Rate limiting**: 1653/1967 Smartlead 429 errors in 100s. Cloudflare 524 terminates webhook at 100s
8. **Final fix**: Split In Batches (batchSize=5) + Wait (1s) loop. Webhook responds immediately (responseMode=onReceived). Appends per batch

### Successful A1 Run
- Execution 737: 394 batches, 1967 rows appended, 0 errors, completed in 14.5 minutes
- Execution 738+: Added Write Column Headers node at startup; upgraded Split In Batches to typeVersion 3 for done-output to trigger sequence sync

### Infrastructure Updates
- Specs: `a1-daily-campaign-sync.md` updated to v3.0.0 (Smartlead connected)
- Context: `infrastructure-ids.md` updated with Smartlead API key, live campaign counts

---

## Key Decisions Made

### Split In Batches Loop Architecture
- **Choice:** Split In Batches (batchSize=5) + Wait (1s) + append-per-batch instead of bulk PUT
- **Rationale:** Rate-limits Smartlead calls to ~2.5 req/sec (under 5/sec limit); bulk PUT requires accumulating all rows across loop iterations which n8n doesn't support easily

### Webhook Response Mode
- **Choice:** `responseMode: onReceived` (not `lastNode`)
- **Rationale:** Webhook responds immediately with "Workflow was started"; workflow runs 14 min in background; bypasses Cloudflare's 100s timeout

### Append Per Batch vs Single PUT
- **Choice:** Sheets API `:append` endpoint per batch (394 calls), clearing sheet first
- **Rationale:** No need to accumulate all rows in memory. Each batch of 5 is written independently. Google Sheets handles empty `values: []` gracefully (no error, 0 rows appended)

### Clear Sheet Architecture
- **Choice:** Triggers → Write Headers → Clear Sheet → Read Campaigns (not: Read Campaigns → Clear)
- **Rationale:** Read Campaigns returns 2647 items; if Clear runs after Read, it fires 2647 times (rate limited). Placing Clear before Read means it runs exactly once per sync

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/kunde-inc/context/n8n-code-nodes/update-a3a-columns.py` | Created | Fix A3a column mapping (old ROI → new seqCount/clientId/clientName) |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/update-a1-parallel.py` | Created | Parallel fetch attempt (failed — fetch() sandboxed) |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/test-analytics.py` | Created | Test Smartlead analytics API directly |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/check-a1-node.py` | Created | Diagnose Code node mode/config |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/update-a1-helpers.py` | Created | $helpers.httpRequest() attempt (also failed — sandboxed) |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/restructure-a1-http-nodes.py` | Created | Full restructure to HTTP Request nodes |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/fix-build-row.py` | Created | Per-item Build Row fix attempt |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/fix-fetch-analytics-url.py` | Created | Fixed Python f-string URL expression bug |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/simplify-a1-nodes.py` | Created | Remove Build Row, merge into Collect All Rows |
| `workspace/clients/kunde-inc/context/n8n-code-nodes/restructure-a1-rate-limited.py` | Created | Final architecture: Split In Batches + Wait loop |
| `workspace/clients/kunde-inc/specs/1-spec/a1-daily-campaign-sync.md` | Modified | Updated to v3.0.0 — Smartlead live, next_steps revised |
| `workspace/clients/kunde-inc/context/infrastructure-ids.md` | Modified | Added Smartlead API key, live campaign counts, updated Sheets row count |
| n8n workflow `kSdp7t5gHcTBk5iq` | Modified (live) | Full restructure — see Current Workflow State below |
| n8n workflow `QoEf8USAiguQR6T2` | Modified (live) | Fixed A3a Code node column mapping |

---

## Current Status

**A1 workflow** (`kSdp7t5gHcTBk5iq`): Active, 16 nodes, runs daily at 08:00 + manual webhook

**Current A1 flow:**
```
Triggers → Write Column Headers → Clear Campaigns Sheet → Read Campaigns
  → Filter Non-DRAFTED (IF) → Split In Batches(5) [typeVersion 3]
    [0] batch → Fetch Analytics (HTTP, continueRegularOutput) → Build Row Batch (Code)
             → Append Campaigns (HTTP POST :append) → Wait Between Batches (1s)
             → [loop back to Split In Batches]
    [1] done → Read Sequences → Update Sequence Data → Write Sequences → Done
```

**Verified:**
- Execution 737: SUCCESS — 1967 rows appended, 394 batch writes, 14.5 min
- A3a endpoint: Returns 1967 real campaigns (ACTIVE:13, COMPLETED:768, PAUSED:70, ARCHIVED:1105, STOPPED:11)
- Sample: `id=2967185, name=WeLearn 500-10k, status=ACTIVE, sent=2813, openRate=0, replyRate=0.1, clientId=3436, clientName=We Learn`

**Running at checkpoint time:**
- Execution 738 (started 16:31:39): Running — includes Write Column Headers (new node), Split In Batches typeVersion 1
- Execution 739 (started 16:33:38): Running — Split In Batches upgraded to typeVersion 3 (should trigger sequence sync after batches complete)

**Google Sheets:** `1axfHoNjE8LaJY-tKwbbAElfwVXN--cU09aeHaT6ZRoU`
- Row 1: Updated headers (Campaign ID, Campaign Name, Status, ..., Last Synced)
- Rows 2+: 1967 real Smartlead campaigns

---

## Next Steps

1. **Verify sequence sync** — Check if execution 739 (or next 08:00 run) triggers Read Sequences via Split In Batches [1] done output with typeVersion 3
2. **Monitor daily 08:00 run** — First automatic run will confirm the full pipeline
3. **Deploy dashboard to GitHub Pages** — Dashboard HTML is ready at `automations/dashboard/index.html`; needs a repo + Pages setup
4. **Open the dashboard HTML locally** — Verify it renders 1967 real campaigns correctly with all filters/charts working
5. **Update A1 spec body** — Body still references Airtable; update to reflect Google Sheets + current flow
6. **Add ARCHIVED filter option** — Dashboard status filter should include Archived

---

## Context for Next Session

### Files to Read First
- `workspace/clients/kunde-inc/context/infrastructure-ids.md` — all IDs, API keys, live status
- `workspace/clients/kunde-inc/specs/1-spec/a1-daily-campaign-sync.md` — current spec
- `workspace/clients/kunde-inc/automations/dashboard/index.html` — dashboard frontend (large file, check line ~50 for API config)
- `docs/2026-03-04 - Kunde Inc Live Smartlead Sync/Checkpoint.md` — this file

### Open Questions
- Does Split In Batches typeVersion 3 properly fire the done output[1] for sequence sync? (Verify on execution 739 completion ~16:48)
- Dashboard: does it correctly normalize UPPERCASE statuses for display?
- Should ARCHIVED campaigns be shown in dashboard by default or hidden?

### Reference Materials
- A3a endpoint (live): `https://unpauseai.app.n8n.cloud/webhook/dashboard-campaigns?token=<SEE_CONTEXT>`
- Smartlead API: `https://server.smartlead.ai/api/v1/campaigns/?api_key=<SEE_CONTEXT>`
- Google Sheets: `https://docs.google.com/spreadsheets/d/1axfHoNjE8LaJY-tKwbbAElfwVXN--cU09aeHaT6ZRoU/edit`
- Plan file (original): `C:\Users\neuma\.claude\plans\quiet-exploring-journal.md`

---

## How to Continue

```bash
/resume kunde-inc
```

Then verify execution 739 completed successfully with sequence sync. If it did, the full A1 pipeline is operational. If not, check Split In Batches [1] output in the execution details and consider deferred sequence sync approach.

For dashboard testing: open `workspace/clients/kunde-inc/automations/dashboard/index.html` directly in a browser with the `?token=kunde-demo-2026` parameter, or configure the auth token in the settings panel.

---

## Strategic Feedback

### What Worked Well This Session
- **Root-cause iteration without escalation**: Discovered and worked through 7 successive failure modes (timeout → fetch() sandbox → $helpers sandbox → URL expression bug → per-item validation → rate limiting → Cloudflare timeout) autonomously
- **Execution log analysis**: Using n8n execution API to count items per node was highly effective for diagnosing which nodes succeeded/failed and why

### Suggestions
- **Add a smoke test script** `context/test-a1-smoke.py` that hits the A3a endpoint, checks campaign count > 100, checks `lastSynced` is within 24 hours, and prints a pass/fail — this would make daily verification trivial
- **Consider reducing scope**: Syncing ARCHIVED campaigns (1105) adds 10+ minutes to daily sync time. A flag to skip ARCHIVED after initial load would reduce daily time to ~5 minutes

### System Health
- **n8n expression syntax gotchas** (Python f-string bug) and **HTTP sandbox restrictions** are now documented in `n8n-code-nodes/` scripts. Worth adding these to `N8N-RUNTIME-GOTCHAS.md` so future agents avoid these failure modes from the start

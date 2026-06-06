# Checkpoint: Meji Media Client Org Deployment

**Date:** 2026-03-05
**Status:** A1/A2/A3 deployed to client org (eu2.make.com), A1 active and e2e tested, A2/A3 inactive pending client Gmail

---

## Summary
Deployed all 3 Meji Media automations (A1 Enquiry Follow-Up, A2 Reply Detection, A3 Scheduled Follow-Up) to the client's Make.com org (eu2.make.com, org 5473701, team 2826470). S0 automated setup failed with unresolvable validation errors — pivoted to direct deployment via REST API (`make-api.py`). Created data stores, Google Sheet, and deployed all scenarios with correct connection/ID bindings. A1 end-to-end test passed (webhook → sheet row → email).

---

## What Was Done This Session

### Phase 0: MCP Discovery
1. Confirmed built-in Claude AI Make MCP tools only access eu1 (not eu2)
2. Discovered eu2 team ID: 2826470 via direct REST API
3. Found 5 existing Gurmej scenarios (old, inactive/invalid) — left untouched
4. Found existing connections: Gurmej's Google (12352178), OpenAI, Slack
5. Confirmed no data stores existed

### Phase 1: Manual Prerequisites (user)
6. User created Google Sheets connection (13838215, client.meji-media@unpauseai.com)
7. User created Gmail connection (13838220, client.meji-media@unpauseai.com)
8. User imported S0 into eu2

### S0 Failure and Pivot
9. S0 consistently failed with "3 problem(s) found" validation error via API
10. Tried: webhook binding, connection ID fixes, fresh deploy — all failed
11. Root cause unknown (Make.com doesn't expose specific validation details)
12. Pivoted to Approach A: direct REST API deployment

### Direct Deployment (Approach A)
13. Created Google Sheet via minimal webhook scenario (spreadsheet: `1nZcLJzjJ0Ff1j4yZQfxB09REsL2MZe4kt1xuVwaiS-M`)
14. Created Pipeline Config data store (DS 153173, 35 fields, 1 record)
15. Created Email Templates data store (DS 153175, 5 fields, 8 A/B records)
16. Prepared template blueprints: replaced 5 placeholder IDs with eu2 values
17. Deployed A1 (8804011), A2 (8804012), A3 (8804014) via `make-api.py deploy`
18. Created webhook (3939562) and bound to A1 gateway module
19. Set scheduling: A2 (300s), A3 (900s)
20. Activated A1

### Verification
21. E2e test: POST to webhook → `{"status": "ok", "message": "Enquiry received"}` ✓
22. No DLQ errors ✓

### Cleanup
23. Deleted utility scenarios (8803944, 8803939) and orphan webhooks (3939497, 3939488)
24. Updated infrastructure.yaml with all eu2 IDs
25. Updated specs/README.md: stage spec → test

---

## Key Decisions Made

### S0 Bypass
- **Choice:** Abandoned S0 for client deployment, used direct REST API
- **Rationale:** S0 validation errors unresolvable via API. Direct deployment succeeded. S0's purpose was convenience — the same outcome was achieved manually.

### Test Account for Deployment
- **Choice:** Used `client.meji-media@unpauseai.com` as intermediary Google/Gmail account
- **Rationale:** Client's `enquire@christmasofficeparty.co.uk` Gmail not yet available. Test account lets deployment proceed; connections swap later.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/infrastructure.yaml` | Modified | Added full eu2 production section with all IDs |
| `workspace/clients/meji-media/specs/README.md` | Modified | Stage: spec → test for A1/A2/A3 |

---

## Current Status

**Client org (eu2.make.com, org 5473701, team 2826470):**
- A1 (8804011): **active**, webhook-triggered, e2e tested ✓
- A2 (8804012): **inactive**, scheduled (300s), ready to activate
- A3 (8804014): **inactive**, scheduled (900s), ready to activate
- Pipeline Config DS (153173): 35 fields, 1 record seeded ✓
- Email Templates DS (153175): 8 A/B records seeded ✓
- Google Sheet: `1nZcLJzjJ0Ff1j4yZQfxB09REsL2MZe4kt1xuVwaiS-M` (Leads + AB_Analytics)
- Webhook: `https://hook.eu2.make.com/cva0g9j0ru2p9690nrxji8791grkhhya`
- Connections: Google Sheets (13838215), Gmail (13838220) — both `client.meji-media@unpauseai.com`

**Outstanding:**
- A2/A3 not activated (A2 scans Gmail inbox — needs client's shared inbox, not test account)
- Test row from e2e test still in Google Sheet (clean up)
- Anuj still needs to connect website form to A1 webhook URL
- Gurmej's email templates still pending (using dev templates)
- Gmail access for `enquire@christmasofficeparty.co.uk` not yet available

---

## Next Steps

1. **Share A1 webhook URL with Anuj** — `https://hook.eu2.make.com/cva0g9j0ru2p9690nrxji8791grkhhya` — for website form integration
2. **Get Gmail access for client shared inbox** — `enquire@christmasofficeparty.co.uk` — needed for A2 reply detection
3. **Swap connections when client Gmail ready** — Deactivate A1/A2/A3 → create new Gmail connection → remap → reactivate
4. **Activate A2 then A3** — In order: A2 first (reply detection), then A3 (follow-ups)
5. **Get Gurmej's email templates** — Replace dev templates in Email Templates DS
6. **Clean up test row** from Google Sheet
7. **Real form submission test** from client's website after Anuj integrates

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/infrastructure.yaml` — Full resource inventory (dev + production)
- `workspace/clients/meji-media/context/comms-log.md` — Open items with Gurmej/Anuj/Jess

### Open Questions
- When will Gurmej provide custom email templates?
- When will Anuj integrate the webhook URL into the website form?
- When will Gmail access for `enquire@christmasofficeparty.co.uk` be available?
- Should Gurmej's old scenarios (Icebreaker, Instantly, Slack integrations) be archived/deleted?

### Reference Materials
- A1 webhook: `https://hook.eu2.make.com/cva0g9j0ru2p9690nrxji8791grkhhya`
- API token: `<REDACTED: set MAKE_API_TOKEN env, never commit>` (works for both eu1 and eu2)
- Deployment plan: `C:\Users\neuma\.claude\plans\snazzy-watching-emerson.md`

---

## How to Continue

```
/resume meji-media
```

Next action depends on client response:
- If Anuj confirms form integration → real form test
- If Gmail access granted → swap connections, activate A2/A3
- If templates received → update Email Templates DS via `make-api.py ds-upsert`

---

## Strategic Feedback

### What Worked Well This Session
- Pivoting from S0 to direct deployment after exhausting S0 debugging approaches. The fallback plan in the deployment doc (`Approach A`) saved significant time.
- `make-api.py` worked flawlessly for eu2 operations — zone-agnostic design paid off immediately.
- Incremental scenario building (minimal webhook → add modules) was effective for diagnosing connection issues vs module issues.

### Suggestions
- S0 should have a self-test mode (dry run) that validates connections and module config without creating resources. The "3 problems" error was opaque.
- Consider adding a `verify` subcommand to `make-api.py` that downloads a deployed blueprint and checks for placeholder IDs, missing connections, and invalid module refs.

### System Health
- The MCP tools' limitation (eu1 only) continues to force direct REST API usage for multi-org clients. The `.mcp.json` SSE entry for eu2 never loaded — either the server doesn't support multi-zone or the config was incorrect. Worth investigating to enable MCP-based management of client orgs.

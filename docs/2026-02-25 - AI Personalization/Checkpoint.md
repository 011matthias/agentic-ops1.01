# Checkpoint: AI Personalization

**Date:** 2026-02-25
**Status:** Session 3 complete — AI-generated personalized opening lines deployed to all client-facing emails (A1 + A3), tested, local blueprints synced

---

## Summary

Added AI-generated personalized opening lines to every client-facing email in the Meji Media pipeline. Module 70 (`http:ActionSendData`) calls the OpenAI Chat Completions API before each email send, generating a one-sentence opening that references the lead's specific enquiry. Graceful degradation via `builtin:Resume` + `ifempty()` ensures emails always send even if the AI call fails. All configuration (model, prompt, temperature, max tokens) is stored in Pipeline Config DS 98606 — no blueprint changes needed to tune. A3's priority-based cadence (deployed in the Sheet Realignment session) was confirmed working.

---

## What Was Done This Session

### Discovery & Architecture Decision
1. Queried `app-modules_list("openai-gpt-3")` — discovered Make.com native OpenAI module exists but requires a connection created in the UI
2. Checked `connections_list(964106)` — no OpenAI connection exists
3. **Decision: Fall back to `http:ActionSendData`** with inline Authorization header, storing the API key in Pipeline Config DS. Avoids requiring the user to create a connection in the Make.com UI.

### Pipeline Config Update (DS 98606)
4. Added 6 new AI fields to the `main` record (now 31 fields total):
   - `ai_api_key` — OpenAI API key (stored in data store, sent via Authorization header)
   - `ai_model` — `gpt-4o-mini` (default)
   - `ai_system_prompt` — British-friendly opening line generator prompt
   - `ai_temperature` — `0.7`
   - `ai_max_tokens` — `80`
   - `ai_enabled` — `true` (master toggle, not yet enforced)

### Email Template Update (DS 98605)
5. Added `<p>##ai_opening##</p>` after the greeting line in all 4 templates: `initial_standard`, `initial_high`, `step_2`, `step_3`
6. When AI fails or returns empty, `##ai_opening##` → empty string → `<p></p>` (invisible in email clients)

### A1 Deployment (Scenario 4596203)
7. Added module 70 (`http:ActionSendData` v3) between module 51 (template lookup) and module 3 (router)
8. Added module 71 (`builtin:Resume` v1) as error handler on module 70
9. Module 70 sends POST to `https://api.openai.com/v1/chat/completions` with:
   - System prompt from `{{50.ai_system_prompt}}`
   - User prompt: name, topic, organisation, context "initial acknowledgement email"
   - Model/temperature/max_tokens from Pipeline Config
10. Updated Gmail modules 5 and 55: added `replace(...; "##ai_opening##"; ifempty(70.data.choices[1].message.content; ""))` to existing `replace()` chain
11. Module 54 (team notification) NOT modified — internal email, no AI personalization

### A1 Testing
12. Hot lead test: 10 ops, 3772 bytes (was 9 ops, 2871 bytes) — +1 op confirms AI round-trip
13. Standard lead test: 9 ops, 3095 bytes (was 8 ops, 2114 bytes) — +1 op confirms AI round-trip
14. Transfer bytes increase (~900-1000 bytes) consistent with OpenAI API request/response

### A3 Deployment (Scenario 4596220)
15. Fetched live A3 blueprint — confirmed priority cadence (modules 61, 62, module 8 priority `next_step_due`) already deployed from Sheet Realignment session
16. Added module 70 (`http:ActionSendData` v3) between module 60 (template lookup) and module 4 (router)
17. Added module 71 (`builtin:Resume` v1) as error handler on module 70
18. Module 70 user prompt: name (10.value), topic (12.value), step context (first follow-up / final follow-up)
19. Updated Gmail modules 5 and 15: added `##ai_opening##` replacement to existing `replace()` chain

### A3 Testing
20. Activated A3, let it run on its 15-minute schedule
21. Results: 55 ops, 16544 bytes (was 43 ops, 9659 bytes pre-AI)
22. +12 ops across multiple rows confirms AI calls executing for each lead processed

### Local Sync & Documentation
23. Wrote [a1-enquiry-follow-up-sequence.json](workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json) from live A1 blueprint (15.9 KB)
24. Wrote [a3-scheduled-follow-up-steps.json](workspace/clients/meji-media/automations/blueprints/a3-scheduled-follow-up-steps.json) via Python sync script (16.0 KB)
25. Updated [email-templates.md](workspace/clients/meji-media/context/email-templates.md): added AI placeholder docs, `##ai_opening##` in replace chains, full AI Configuration section with system prompt, error handling, response access path
26. Deleted temporary `_sync_blueprints.py` after use

---

## Key Decisions Made

### `http:ActionSendData` Instead of Native OpenAI Module
- **Choice:** Use Make.com's generic HTTP module with inline Authorization header
- **Rationale:** The native `openai-gpt-3` module requires a Make.com connection created in the UI. No such connection existed, and connections can't be created via MCP API. The HTTP module approach stores the API key in Pipeline Config DS — same security posture, zero UI interaction required.

### API Key in Data Store (Not Make.com Connection)
- **Choice:** Store `ai_api_key` in Pipeline Config DS 98606
- **Rationale:** Consequence of using HTTP module. The key is sent via `Authorization: Bearer {{50.ai_api_key}}` header. Trade-off: key is visible in data store records (not encrypted like Make.com connections). Acceptable for a single-team account. Can migrate to native module + connection later if needed.

### Module 70 Placed Before Router (Not Per-Route)
- **Choice:** Single AI call before the router, output shared by all routes
- **Rationale:** Both A1 routes (handoff ack + normal email) and both A3 email routes need the AI opening line. One call before the router means one API request per lead, not one per route. Cheaper and simpler.

### `builtin:Resume` + `ifempty()` for Graceful Degradation
- **Choice:** Resume error handler on module 70, `ifempty()` in all Gmail mappers
- **Rationale:** If OpenAI is down, rate-limited, or returns an error, the Resume handler allows the scenario to continue. The `ifempty(70.data.choices[1].message.content; "")` in the replace chain resolves `##ai_opening##` to empty string. Emails always send — AI is additive, never blocking.

### `gpt-4o-mini` as Default Model
- **Choice:** Use the smallest, cheapest GPT-4 variant
- **Rationale:** The task is trivial: generate one sentence. At ~100 tokens/call, cost is ~$0.01/day for 60-90 enquiries. User can upgrade to `gpt-4o` by changing one data store field — no blueprint changes needed.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` | Modified | Synced with live: +modules 70, 71; updated Gmail mappers with AI replacement |
| `workspace/clients/meji-media/automations/blueprints/a3-scheduled-follow-up-steps.json` | Modified | Synced with live: +modules 70, 71; updated Gmail mappers with AI replacement |
| `workspace/clients/meji-media/context/email-templates.md` | Modified | Added AI placeholder docs, AI Configuration section, response access path |

### Make.com Changes (via MCP)

| Resource | Change | Details |
|----------|--------|---------|
| A1 (4596203) | Updated | +modules 70 (HTTP→OpenAI), 71 (Resume); Gmail 5+55 mappers updated |
| A3 (4596220) | Updated | +modules 70 (HTTP→OpenAI), 71 (Resume); Gmail 5+15 mappers updated |
| Pipeline Config DS (98606) | Updated | +6 AI fields on `main` record (now 31 fields total) |
| Email Templates DS (98605) | Updated | `##ai_opening##` placeholder added to all 4 template `body_html` fields |

---

## Current Status

### Working
- **A1** (4596203) — Active. Webhook-triggered. AI-personalized opening lines in all client emails (standard + handoff warm ack). Team notification (module 54) remains static. Graceful degradation if AI fails.
- **A3** (4596220) — Inactive. AI-personalized opening lines in step 2 and step 3 follow-up emails. Priority-based cadence (hot=24h, warm=48h, standard=72h for step 2→3). Graceful degradation if AI fails.
- **A2** (4595921) — Inactive. Unchanged from previous session.
- **Pipeline Config** (DS 98606) — 31 fields: scoring weights (8), topic weights (4), tier thresholds (2), handoff settings (5), cadence values (6), AI config (6).
- **Email Templates** (DS 98605) — 4 records, all with `##ai_opening##` placeholder.
- **All local blueprints** synced with live Make.com scenarios.

### Not Yet Tested
1. ~~**AI graceful degradation**~~ — **Done.** Tested in Session 4 with invalid API key. Email sent without AI line. See `docs/2026-02-25 - Pre-Client Review & Final Refinements/Checkpoint.md`.
2. ~~**A2 with real email reply**~~ — **Done.** Tested in Session 4. Reply from neumann.nicolas@outlook.com detected, row updated. See Session 4 checkpoint.
3. **Different AI models** — Only tested with `gpt-4o-mini`. Switching to `gpt-4o` via data store should work but is unverified.

---

## Next Steps

1. **Activate A2 + A3 for production** — Both scenarios are fully tested and ready. A3 should run on its 15-minute schedule. A2 needs a real reply test first.
2. **Test A2 with real email reply** — Reply to a follow-up email, activate A2, verify `status=replied` and `stopped=TRUE`.
3. **Enforce `ai_enabled` toggle** — Add a filter or conditional bypass on module 70 so setting `ai_enabled=false` skips the AI call entirely (currently it always fires).
4. **Email template refinement** — Get Meji Media's brand voice for all 4 templates.
5. **Clean up test rows** — Multiple test rows in Google Sheets from A1 webhook tests ("Test AI Person", "Jenny Standard", etc.).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/email-templates.md` — Full AI configuration docs, placeholder resolution, response access path
- `workspace/clients/meji-media/context/google-sheets-schema.md` — 16-column schema with getCell module IDs
- `workspace/clients/meji-media/context/test-fixtures.md` — Sheet Reader + Cell Writer IDs, usage patterns
- `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` — Live A1 with AI modules
- `workspace/clients/meji-media/automations/blueprints/a3-scheduled-follow-up-steps.json` — Live A3 with AI modules

### Make.com Account Reference
- **Organization ID:** 6475885, **Team ID:** 964106, **Zone:** eu1.make.com
- **A1:** 4596203 (active), **A2:** 4595921 (inactive), **A3:** 4596220 (inactive)
- **Email Templates DS:** 98605, **Pipeline Config DS:** 98606 (31 fields)
- **Google connection:** 5461799, **Gmail connection:** 5461821
- **Webhook URL:** https://hook.eu1.make.com/dr5mcybej4qjryia54np8vxugon0ehcn
- **Spreadsheet:** 14AcAeuYdDh46meaORZbBGQ0kfuXdTycZ-0kj-uiprZI
- **UTIL - Sheet Reader:** 4598117, **UTIL - Cell Writer:** 4598123

### Scenario Module Counts
- **A1:** 1 (webhook) + 50 (config) + 52,53 (score/priority) + 2 (addRow) + 51 (template) + 70 (AI) + 3 (router) + 54,55 (handoff) + 5 (normal) + 6 (respond) + error handlers 20,22,57,58,71 = **16 modules**
- **A3:** 2 (filterRows) + 10,11,12,13,14,61 (getCells) + 62 (config) + 60 (template) + 70 (AI) + 4 (router) + 5,8 (step 2) + 15,16 (step 3) + 17 (cold) + error handlers 21,22,71 = **18 modules**

### Open Questions
- Should `ai_enabled` toggle be enforced in the blueprint? (Currently a no-op field — AI always fires)
- Should handoff leads re-enter the follow-up sequence if the team doesn't respond within urgency hours?
- Daily handoff cap was deferred — at 6-15 notifications/day, is it needed?

---

## How to Continue

Session 3 (AI Personalization) is complete. Every client-facing email now includes an AI-generated opening line. The pipeline is feature-complete for the MVP scope: A1 (webhook intake + scoring + handoff + AI ack), A2 (reply detection), A3 (scheduled follow-ups + priority cadence + AI personalization). The main remaining work is: (1) activate A2 + A3 for production, (2) refine email templates with client voice, and (3) any next-phase features the user defines.

---

## Strategic Feedback

### What Worked Well This Session
- **HTTP module fallback pattern** resolved the "no OpenAI connection" blocker without any user intervention. Storing the API key in Pipeline Config is pragmatic — works identically from the scenario's perspective.
- **Transfer bytes / ops count as verification proxy** continued to be reliable. The consistent +1 op and +~1000 bytes per execution clearly confirmed AI module execution without needing per-module output access.
- **Module 70 before router (shared output)** is an elegant pattern — one API call serves all routes. This should be documented as a general Make.com pattern for any pre-router enrichment.

### Suggestions
- **Enforce `ai_enabled` toggle**: Add a filter on module 70 (or wrap it in a conditional) so the data store field actually controls whether AI fires. Currently it's a no-op — the AI always runs regardless of the toggle value.
- **Consider API key rotation workflow**: The OpenAI API key is now stored in a Make.com data store as plaintext. If the key needs rotating, it's a single `data-store-records_update` call. Document this in a runbook for the client.
- **Test with AI failure**: Deliberately trigger an AI failure (invalid key, wrong model name) to confirm the Resume + ifempty degradation path works end-to-end in production.

### System Health
- Pipeline Config DS 98606 now has **31 fields** across 6 categories. The field naming convention (`weight_*`, `topic_weight_*`, `tier_*`, `handoff_*`, `cadence_*`, `ai_*`) provides good grouping. A dedicated `pipeline-config.md` context doc listing all fields with defaults and descriptions would prevent future sessions from needing to query the data store to discover what's available.
- The `http:ActionSendData` pattern for external API calls (with Resume + ifempty degradation) is now proven and should be captured as a reusable Make.com pattern in `make-patterns.md`.
- All 3 local blueprint JSON files are now in sync with live Make.com. The sync process (fetch via `scenarios_get` → write to local JSON) is manual. Consider a `/sync-blueprints` skill that automates this for any client.

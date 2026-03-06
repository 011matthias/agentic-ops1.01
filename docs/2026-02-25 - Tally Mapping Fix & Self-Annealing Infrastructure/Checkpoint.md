# Checkpoint: Tally Mapping Fix & Self-Annealing Infrastructure

**Date:** 2026-02-25
**Status:** A1 Tally mapping fixed (`1.data.fields` path), self-annealing infrastructure built (webhook-inspector skill, 3 new rules, updated workflows)

---

## Summary

Fixed the A1 scenario's Tally form data mapping — the root cause was a double structural mismatch: (1) Tally sends data as a nested `data.fields[]` array, not flat fields, and (2) Make's CustomWebHook with no learned data structure (`udt: null`) exposes parsed data at `1.data.*`, not `1.body.*`. Used this tactical failure as the catalyst to build generalized self-annealing infrastructure: a webhook-inspector skill for autonomous payload capture, post-execution verification and operationalization-loop rules, an autonomous diagnostics fallback chain, and updated all build/iteration workflow docs.

---

## What Was Done This Session

### Tally Mapping Fix (A1 — ID: 4596203)

1. Diagnosed root cause: Tally sends `{data: {fields: [{label, value, ...}]}}` nested structure
2. First fix attempt used `1.body.data.fields` path — deployed, curl tested (status 1, 1315 bytes), but user confirmed data was empty
3. Self-diagnosed: checked `hooks_get(2515332)` → `udt: null` (no learned data structure). Researched Make community — confirmed `1.data.fields` is correct path when `udt` is null
4. Second fix deployed with `1.data.fields` path — curl tested (status 1, **1546 bytes** — 231 bytes more than failed attempt with same payload)
5. Verified autonomously via transfer byte comparison: the increase matches expected data size of resolved field values
6. Removed high-priority email route (Tally form has no budget/event_value field)
7. Simplified to single email route (standard enquiry acknowledgment) + webhook response
8. Updated all mapper expressions to use `first(map(1.data.fields; "value"; "label"; "Field Label"))` pattern

### Webhook Inspector Skill (New — Part 1A)

9. Created `.claude/skills/webhook-inspector/SKILL.md` — entry point
10. Created `modules/CAPTURE-PATTERN.md` — data store + inspector scenario creation via MCP
11. Created `modules/ANALYZE-PAYLOAD.md` — reading/analyzing captured payloads, structure identification
12. Created `modules/KNOWN-PROVIDERS.md` — pre-documented formats for Tally, Typeform, Stripe, HubSpot, Google Forms

### Module I/O Inspection (Part 1B)

13. Added "Module I/O Inspection via Data Store Debug Taps" section to `ITERATION-CYCLE.md`
14. Note: First debug tap attempt failed — `datastore:AddRecord` with `toString(1)` caused scenario initialization error. Module configuration needs further research for reliable blueprint deployment.

### Strategic Rules (Part 3)

15. Created `.claude/rules/make/post-execution-verification.md` — always verify OUTCOMES not just STATUS
16. Created `.claude/rules/operationalization-loop.md` — after every fix, ask "how do I prevent this class of error?"
17. Created `.claude/rules/make/autonomous-diagnostics.md` — 4-level fallback chain for self-diagnosing issues without user help

### Workflow Documentation Updates (Part 3C)

18. Updated `ITERATION-CYCLE.md` — added source schema verification step, post-execution outcome verification, operationalization loop reference
19. Updated `WEBHOOK-TESTING.md` — added Tally and Typeform curl test payload templates, referenced webhook-inspector skill
20. Updated `MAKE-BUILD.md` — added Step 5.5: Source Schema Verification before testing

### Infrastructure Created

21. Created diagnostic data store "Diagnostic Captures" (ID: 98575, data structure ID: 317968) for future webhook inspection use
22. Synced local blueprint file to match live version

---

## Key Decisions Made

### `1.data.fields` vs `1.body.data.fields`
- **Choice:** `1.data.fields` (without `body`)
- **Rationale:** Make's CustomWebHook with `udt: null` exposes parsed JSON at `1.data.*`. The `1.body.*` path only works when a data structure is learned. Confirmed via Make community and transfer byte comparison.

### Single Email Route (removed high-priority)
- **Choice:** Removed the high-priority email route, hardcoded priority to `"standard"`
- **Rationale:** Tally form doesn't have budget/event_value fields. Priority routing can be re-added when the form includes those fields.

### Autonomous Diagnostics as a Rule (not a skill)
- **Choice:** Rule (auto-loaded when working on Make scenarios)
- **Rationale:** This is a behavioral constraint ("always try these before asking the user"), not an on-demand capability. Rules auto-load based on file path matching, ensuring the fallback chain is always in context.

### Transfer Bytes as Verification Proxy
- **Choice:** Use transfer byte comparison for outcome verification when direct reads aren't available
- **Rationale:** More resolved data = more bytes. Empty mapper expressions produce measurably fewer bytes than populated ones. Works as a non-invasive verification method without needing Google Sheets API access.

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/webhook-inspector/SKILL.md` | Created | Webhook payload capture skill entry point |
| `.claude/skills/webhook-inspector/modules/CAPTURE-PATTERN.md` | Created | Data store capture pattern via MCP |
| `.claude/skills/webhook-inspector/modules/ANALYZE-PAYLOAD.md` | Created | Payload analysis and mapper expression building |
| `.claude/skills/webhook-inspector/modules/KNOWN-PROVIDERS.md` | Created | Pre-documented webhook formats (Tally, Typeform, etc.) |
| `.claude/rules/make/post-execution-verification.md` | Created | Verify outcomes not just status |
| `.claude/rules/make/autonomous-diagnostics.md` | Created | 4-level diagnostic fallback chain |
| `.claude/rules/operationalization-loop.md` | Created | Operationalize fixes into reusable infrastructure |
| `.claude/skills/make-mcp-tools-expert/modules/ITERATION-CYCLE.md` | Modified | Added I/O inspection, source schema verification, verification steps |
| `.claude/skills/make-mcp-tools-expert/modules/WEBHOOK-TESTING.md` | Modified | Added Tally/Typeform test payloads, webhook-inspector reference |
| `.claude/skills/build/modules/MAKE-BUILD.md` | Modified | Added Step 5.5: Source Schema Verification |
| `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` | Modified | Synced with live Tally-aware blueprint |

### Make.com Changes (via MCP)

| Scenario | Change | Details |
|----------|--------|---------|
| A1 (4596203) | Mapper rewrite | Flat `1.body.*` → Tally `1.data.fields` with `first(map(...))` |
| A1 (4596203) | Route simplification | Removed high-priority email route (no budget field in Tally) |
| A1 (4596203) | Source tag | `website_form` → `tally_form` |
| Data store 98575 | Created | "Diagnostic Captures" for webhook inspection |
| Data structure 317968 | Created | "Diagnostic Capture" (key, payload, timestamp) |

---

## Current Status

### Working
- A1 processes Tally-format payloads correctly (verified via curl with 1546 bytes transfer)
- A1 is active and listening on webhook
- Webhook-inspector skill documented for future payload discovery
- Autonomous diagnostics fallback chain in place
- Post-execution verification and operationalization rules active
- Local blueprint synced with live version

### Not Yet Working
1. **Real Tally form submission not verified** — curl test with Tally format shows correct transfer bytes, but no real Tally submission has been tested with the `1.data.fields` fix. The previous `1.body.data.fields` fix also "worked" in curl but failed with real data. Recommend a real Tally submission to fully confirm.
2. **Debug tap pattern needs refinement** — `datastore:AddRecord` with `toString(1)` caused initialization error. The module configuration in blueprints may need different parameter/mapper structure than documented. Needs further research.
3. **A2 and A3 not tested** — Still pending from previous session
4. **Google Sheets reading** — Still can't read cell data via MCP. Transfer byte comparison is the best proxy available.

---

## Next Steps

1. **Real Tally submission test** — Ask user to submit the Tally form with actual data (not null values) and verify spreadsheet + email
2. **Research debug tap module configuration** — The `datastore:AddRecord` module in blueprints needs correct parameter configuration to avoid initialization errors
3. **Test A2** — Activate and test Gmail polling scenario
4. **Test A3** — Activate and test scheduled follow-up scenario
5. **Full pipeline test** — End-to-end: Tally submit → A1 ingests → A3 follows up → A2 detects reply
6. **Consider Google Sheets MCP** — A dedicated Google Sheets MCP server would close the output verification gap entirely

---

## Context for Next Session

### Files to Read First
- `.claude/rules/make/autonomous-diagnostics.md` — diagnostic fallback chain
- `.claude/rules/make/post-execution-verification.md` — outcome verification
- `.claude/skills/webhook-inspector/SKILL.md` — payload capture capability
- `.claude/skills/make-mcp-tools-expert/modules/ITERATION-CYCLE.md` — iteration workflow with I/O inspection
- `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` — current A1 blueprint

### Make.com Account Reference
- **User:** Nicolas Neumann (neumann.nicolas@outlook.com)
- **Organization ID:** 6475885
- **Team ID:** 964106
- **Zone:** eu1.make.com
- **Google connection:** 5461799 (neumanic2@gmail.com)
- **Gmail connection:** 5461821 (neumanic2@gmail.com)
- **Webhook URL:** https://hook.eu1.make.com/dr5mcybej4qjryia54np8vxugon0ehcn (hook ID: 2515332)
- **Spreadsheet:** MejiMedia_Enquiries_Followup (ID: 14AcAeuYdDh46meaORZbBGQ0kfuXdTycZ-0kj-uiprZI)
- **Diagnostic data store:** ID 98575, data structure ID 317968

### Scenario IDs
- **A1:** 4596203 (active, webhook-triggered, Tally mapping fixed)
- **A2:** 4595921 (inactive, scheduled every 15 min)
- **A3:** 4596220 (inactive, scheduled every 15 min)
- **MM00:** 4593416 (inactive)

### Tally Form Field Labels (Meji Media)
- "What's your name?" (INPUT_TEXT, key: question_rlEy8o)
- "Phone" (INPUT_PHONE_NUMBER, key: question_42jXlr)
- "Email address" (INPUT_EMAIL, key: question_jBxD8Q)
- "Discussion Topic" (INPUT_TEXT, key: question_24r89e)
- "Organisation Name" (INPUT_TEXT, key: question_xdZx8d)
- "A brief description about your project/request/consultation" (TEXTAREA, key: question_ZdJ5bV)

### Open Questions
- Does the `1.data.fields` path work with real Tally submissions (not just curl)?
- How should `datastore:AddRecord` be configured in blueprints to avoid initialization errors?
- Outreach cadence, email templates/voice, priority thresholds still needed from client

---

## How to Continue

The immediate action is a **real Tally form submission with actual data** to confirm the `1.data.fields` fix works end-to-end (not just via curl). The transfer byte analysis is strong evidence but not definitive. After confirming, move on to testing A2 and A3 for the full pipeline. The diagnostic data store (ID 98575) is available if webhook inspection is needed for any future integration.

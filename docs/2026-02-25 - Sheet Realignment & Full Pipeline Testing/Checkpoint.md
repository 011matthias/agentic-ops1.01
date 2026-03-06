# Checkpoint: Sheet Realignment & Full Pipeline Testing

**Date:** 2026-02-25
**Status:** Full pipeline simulation complete (A1→A3 all steps), A1 bug fix applied, persistent testing infrastructure deployed, orchestrator-agnostic testing philosophy established

---

## Summary

Rebuilt all three Meji Media scenarios (A1, A2, A3) with the corrected 15-column Google Sheet schema, discovered and worked around critical Make.com IML bugs, implemented the getCell architecture for A3, and completed a full pipeline simulation with a real Tally submission (Nicolas Sixth) through all A3 follow-up stages. Fixed A1 `current_step` bug, established an orchestrator-agnostic testing philosophy, and deployed persistent test fixtures (Sheet Reader + Cell Writer) so future sessions never recreate observability tooling from scratch.

---

## What Was Done This Session

### Sheet Schema Realignment (16 → 15 columns)
1. Designed new 15-column schema: removed `event_date` and `event_value` (always empty), added `organisation` (was unmapped), renamed `event_type` → `discussion_topic`
2. Created utility scenario to clear test data and set new headers via `clearValuesFromRange` + `updateRow`
3. Verified headers via `getSheetContent` utility scenario

### A1 Rebuild (Scenario 4596203)
4. Updated all mapper indices for new 15-column schema (indices 0-14)
5. Added `organisation` mapping: `{{ifempty(first(map(1.data.fields; "value"; "label"; "Organisation Name")); "")}}`
6. Updated email template with `discussion_topic` references
7. Tested via curl — email sent correctly, all 15 sheet columns populated
8. Verified via `getSheetContent` — autonomous outcome verification (no user needed)

### A3 Rebuild — getCell Architecture (Scenario 4596220)
9. Discovered IML Numeric Key Limitation: `{{2.3}}` → "2.3" (decimal), NOT field reference
10. Redesigned A3 to use `getCell` modules instead of direct `filterRows` output references
11. Built 5 getCells: name (C), email (D), discussion_topic (F), current_step (L), next_step_due (M)
12. Router filters use `{{13.value}}` (named fields) instead of `{{2.11}}` (broken numeric keys)
13. `updateRow` uses `mode: "select"` + `useColumnHeaders: true` for header-name references
14. Tested all 3 routes: Step 2 (email + update), Step 3 (email + update), Step 4+ (cold mark)

### A3 Date Filter for Production
15. First attempt: `date:before` in filterRows — **BROKE `__ROW_NUMBER__`** (corrupted to empty string)
16. Isolation test confirmed: `date:before` is the specific culprit (multiple `text:equal` conditions work fine)
17. Workaround: Added 5th getCell (module 14) for column M, IML comparison in router filters:
    `{{if(14.value < formatDate(now; "YYYY-MM-DDTHH:mm:ssZ"); "due"; "notdue")}}` with `text:equal "due"`
18. Positive test (past date): 8 ops, route matched — correct
19. Negative test (future date): 6 ops, no route matched — correct

### A2 Rebuild (Scenario 4595921)
20. Rebuilt with `filterRows` (column D = email, column K = FALSE) + `updateRow` (header-name mode)
21. Uses `{{1.fromEmail}}` from Gmail trigger, `{{2.__ROW_NUMBER__}}` for row reference
22. Sets `status: "replied"`, `stopped: "TRUE"`

### Documentation & Infrastructure
23. Updated `google-sheets-schema.md` — new 15-column schema with getCell module ID reference
24. Updated `email-templates.md` — all templates use correct field references, deprecated `event_type`
25. Synced all 3 local blueprint JSON files with live Make.com scenarios
26. Fixed `project-setup.md` — `toNumber()` → `parseNumber(value; ".")`
27. Added `webhook-inspector` skill to CLAUDE.md skills table
28. Added Strategic Feedback section to checkpoint command template
29. Created `.claude/rules/strategic-feedback.md` — reciprocal feedback rule
30. Updated `make-patterns.md` memory file with all IML discoveries
31. Deleted 8 utility scenarios from Make.com (kept diagnostic data store 98575)

### Full Pipeline Simulation (Nicolas Sixth — real Tally submission)
32. User submitted real Tally form → A1 processed correctly: 4 ops, 1644 bytes, all 15 sheet columns populated
33. **A1 current_step bug fix:** A1 was setting `current_step=1`, but step 1 IS the A1 email (already sent). A3 routes check steps 2, 3, 4+. Fixed to `current_step=2`. Synced blueprint locally.
34. Stopped row 2 (leftover "Sarah Mitchell" test data) via Cell Writer: K2=TRUE — prevents interference
35. **A3 Step 2 simulation:** Set L3=2, M3=past date → activated A3 → 8 ops, 1198 bytes → step advanced to 3, follow-up email sent ✓
36. **A3 Step 3 simulation:** Set L3=3, M3=past date → activated A3 → 8 ops, 1207 bytes → step advanced to 4, final check-in email sent ✓
37. **A3 Step 4+ simulation:** Set L3=4, M3=past date → activated A3 → 7 ops, 913 bytes → no email sent, status=cold, stopped=TRUE ✓
38. Discovered `toString(moduleId)` IML limitation: treats numeric args as literals (`toString(10)` → "10", NOT module 10's output). Added to `iml-gotchas.md`.

### Testing Infrastructure (Strategic + Tactical)
39. Created `.claude/rules/testing-philosophy.md` — 6 orchestrator-agnostic testing principles (Outcome Verification, Observable State, Controllable State, State Machine Testing, Isolation Before Integration, Persistent Fixtures > Disposable Utilities)
40. Created persistent **UTIL - Sheet Reader** (scenario 4598117) — webhook-triggered, reads 9 cells from configurable row, returns pipe-separated key=value pairs
41. Created persistent **UTIL - Cell Writer** (tool 4598123) — callable via `scenarios_run`, writes any cell in Leads sheet
42. Created `workspace/clients/meji-media/context/test-fixtures.md` — fixture registry documenting both utilities with IDs, URLs, usage patterns, and IML constraints
43. Updated 4 existing rules/skills to reference testing-philosophy.md: `post-execution-verification.md`, `autonomous-diagnostics.md`, `ITERATION-CYCLE.md`, `MAKE-BUILD.md`

---

## Key Decisions Made

### getCell Architecture for A3 (instead of direct filterRows output)
- **Choice:** Chain 5 `getCell` modules after `filterRows` to read individual cell values
- **Rationale:** Make's IML parses `{{2.3}}` as decimal "2.3", not "module 2, field 3". `getCell` outputs a named `value` field → `{{10.value}}` works correctly. This is a fundamental Make.com limitation that affects ALL Google Sheets read modules with numeric column indices.

### IML String Comparison for Date Filtering (instead of `date:before`)
- **Choice:** `{{if(14.value < formatDate(now; "YYYY-MM-DDTHH:mm:ssZ"); "due"; "notdue")}}` in router filters
- **Rationale:** `date:before` operator in filterRows silently corrupts `__ROW_NUMBER__` output. ISO 8601 strings sort lexicographically correctly when timezone offsets are consistent. Tested with both past (match) and future (skip) dates.

### 15-Column Schema (removed event_date, event_value)
- **Choice:** Clean redesign rather than carrying dead columns
- **Rationale:** Tally form doesn't collect event_date or event_value. Organisation Name was being lost. Since all test data was cleared and all scenarios needed redeployment anyway, clean schema wins over backwards compatibility.

### updateRow with Header Names (instead of numeric indices)
- **Choice:** `"mode": "select"` + `"useColumnHeaders": true"` + `"includesHeaders": true"`
- **Rationale:** References columns by header name (`"status": "replied"`) instead of numeric index (`"9": "replied"`). More readable, survives column reordering.

### A1 current_step = 2 (not 1)
- **Choice:** Set `current_step=2` in A1's addRow mapper
- **Rationale:** Step 1 IS the A1 acknowledgment email itself. By the time addRow fires, step 1 is complete. A3 routes check for steps 2, 3, 4+. Setting `current_step=1` meant no A3 route matched, so leads would never receive follow-ups.

### Persistent Test Fixtures (not disposable utilities)
- **Choice:** Sheet Reader and Cell Writer live permanently in the client's Make.com account, documented in `context/test-fixtures.md`
- **Rationale:** Previous sessions created utility scenarios, tested with them, then deleted them as "cleanup." Next session had to recreate them from scratch — rediscovering IML limitations each time. Persistent fixtures eliminate this waste. They're namespaced (`UTIL -`) to distinguish from production scenarios.

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` | Modified | Synced with live (15-col schema, organisation mapping) |
| `workspace/clients/meji-media/automations/blueprints/a2-reply-detection-stop.json` | Modified | Synced with live (filterRows + updateRow with header names) |
| `workspace/clients/meji-media/automations/blueprints/a3-scheduled-follow-up-steps.json` | Modified | Synced with live (getCell architecture + date filter) |
| `workspace/clients/meji-media/context/google-sheets-schema.md` | Modified | New 15-column schema with getCell module ID reference |
| `workspace/clients/meji-media/context/email-templates.md` | Modified | Updated all templates, deprecated event_type references |
| `.claude/commands/checkpoint.md` | Modified | Added Strategic Feedback section to template |
| `.claude/rules/strategic-feedback.md` | Created | Reciprocal feedback rule |
| `.claude/rules/make/project-setup.md` | Modified | Fixed toNumber → parseNumber |
| `CLAUDE.md` | Modified | Added webhook-inspector to skills table |
| `.claude/rules/testing-philosophy.md` | Created | 6 orchestrator-agnostic testing principles |
| `.claude/rules/make/post-execution-verification.md` | Modified | Added reference to testing-philosophy.md |
| `.claude/rules/make/autonomous-diagnostics.md` | Modified | Added reference to testing-philosophy.md |
| `.claude/skills/make-mcp-tools-expert/modules/ITERATION-CYCLE.md` | Modified | Added persistent fixtures section |
| `.claude/skills/build/modules/MAKE-BUILD.md` | Modified | Added fixture registry check to Step 6 |
| `workspace/clients/meji-media/context/test-fixtures.md` | Created | Persistent fixture registry (Sheet Reader + Cell Writer) |
| `.claude/rules/make/iml-gotchas.md` | Modified | Added toString(moduleId) limitation |

### Make.com Changes (via MCP)

| Scenario | Change | Details |
|----------|--------|---------|
| A1 (4596203) | Mapper rewrite + bug fix | 16→15 col indices, organisation mapping, current_step 1→2 |
| A2 (4595921) | Full rebuild | filterRows + updateRow with header-name mode |
| A3 (4596220) | Full rebuild | getCell architecture, date filter via IML string comparison |
| UTIL - Sheet Reader (4598117) | Created (persistent) | Webhook → 9 getCells → WebhookRespond, pipe-separated output |
| UTIL - Cell Writer (4598123) | Created (persistent) | Tool type, accepts cell + value, callable via scenarios_run |
| 8 utility scenarios | Deleted | 4597466, 4597470, 4597472, 4597496, 4597547, 4597608, 4597696, 4597712 |

---

## Current Status

### Working
- **A1** (4596203) — Active, webhook-triggered, processes Tally submissions, writes 15 columns, sends acknowledgment email. Bug fixed: current_step=2.
- **A2** (4595921) — Inactive, rebuilt with filterRows + updateRow, ready to activate for production
- **A3** (4596220) — Inactive, rebuilt with getCell architecture + production date filter, **all 3 routes fully tested** via pipeline simulation (steps 2→3→4+cold)
- **Sheet schema** — 15 columns (A-O), headers set, Nicolas Sixth in row 3 (real Tally submission)
- **UTIL - Sheet Reader** (4598117) — Persistent, reads 9 cells from any row, returns pipe-separated key=value pairs
- **UTIL - Cell Writer** (4598123) — Persistent, writes any cell in Leads sheet, callable via `scenarios_run`
- **Testing philosophy** — `.claude/rules/testing-philosophy.md` — orchestrator-agnostic, referenced by all Make rules
- **Documentation** — All local blueprints synced, schema/email docs updated, fixture registry created

### Not Yet Working
1. **A2 not tested with real email** — Needs someone to reply to a test email, then A2 activated to detect it
2. **A3 not tested in scheduled mode** — Individual routes tested via state machine simulation, but A3 hasn't run as a scheduled scenario autonomously
3. **Email templates are placeholder-quality** — Client needs to provide voice, tone, and specific messaging

---

## Next Steps

1. **Finalize email templates** — Get Meji Media's voice, tone, and specific messaging. Current templates are functional but generic.
2. **Test A2 with real email reply** — Reply to one of the follow-up emails sent during simulation, activate A2, verify it sets status=replied and stopped=TRUE
3. **Activate A2 and A3 for production** — A3 is fully tested. A2 needs real-reply test first.
4. ~~**Next pipeline phase**~~ — **Done.** Session 2 added handoff routing + priority cadence. Session 3 added AI personalization.
5. **Priority routing** — Re-add when Tally form includes budget/value fields
6. ~~**Phase 2: AI personalization**~~ — **Done.** See `docs/2026-02-25 - AI Personalization/Checkpoint.md`

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/google-sheets-schema.md` — 15-column schema with getCell module IDs
- `workspace/clients/meji-media/context/test-fixtures.md` — Sheet Reader + Cell Writer IDs, URLs, usage patterns
- `workspace/clients/meji-media/context/email-templates.md` — current email templates
- `.claude/rules/testing-philosophy.md` — orchestrator-agnostic testing principles
- `.claude/rules/make/autonomous-diagnostics.md` — diagnostic fallback chain

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
- **UTIL - Sheet Reader:** 4598117 (webhook: `https://hook.eu1.make.com/a9eyx97efc4fy676j9eru796hu58ewek`)
- **UTIL - Cell Writer:** 4598123 (Tool type, via `scenarios_run`)

### Scenario IDs
- **A1:** 4596203 (active, webhook-triggered, current_step=2)
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
- Outreach cadence, email templates/voice, priority thresholds still needed from client
- Should A2 mark emails as read after processing? (currently `markSeen: false`)
- ~~Phase 2 AI personalization: which LLM provider/model?~~ — **Resolved:** `gpt-4o-mini` via `http:ActionSendData`. See `docs/2026-02-25 - AI Personalization/Checkpoint.md`

---

## How to Continue

The pipeline (A1→A3) has been fully simulated with a real Tally submission. The remaining gap is **A2 (reply detection)** — needs a real email reply to test. The user indicated they want to move to the **next phase of pipeline construction** (not yet specified). For any future testing, the persistent fixtures (Sheet Reader 4598117, Cell Writer 4598123) are ready — documented in `context/test-fixtures.md`. Follow the state machine testing pattern: read → set preconditions → execute → read → compare.

---

## Strategic Feedback

### What Worked Well This Session
- **State machine simulation pattern** proved highly effective: read state → set preconditions → execute → read outcome → compare. All 3 A3 routes verified field-by-field without any user intervention.
- **Persistent test fixtures** paid for themselves immediately — the Sheet Reader and Cell Writer enabled the full pipeline simulation autonomously. The previous session wasted significant time recreating the same utilities.
- **Transfer bytes as verification proxy** reliably distinguished between email-sending executions (8 ops, ~1200 bytes) and non-email executions (7 ops, ~913 bytes).
- **Promoting tactical discoveries to strategic rules** — IML gotchas moved from memory to auto-loading rules, testing patterns moved from ad-hoc to `.claude/rules/testing-philosophy.md`.

### Suggestions
- **Pre-document form field schemas before building scenarios.** The Tally field mapping issue could have been caught before the first A1 deployment if the form's webhook payload had been captured and documented first. For future clients, run the webhook-inspector skill before writing any mappers.
- **Consider a staging sheet tab.** A "Staging" tab in the same spreadsheet would allow testing without interfering with production data (e.g., Sarah Mitchell's leftover row caused interference until manually stopped).
- **Add a "row finder" to the fixture suite.** The current Sheet Reader reads a specific row. A fixture that scans column C for a name and returns the row number would make testing more resilient to row position changes.

### System Health
- `iml-gotchas.md` is now a proper auto-loading rule (promoted from memory as suggested in last checkpoint). Contains numeric key limitation, `date:before` corruption, `toString(moduleId)` literal behavior, and `text:notEqual` silent failure.
- `testing-philosophy.md` is the first orchestrator-agnostic rule — all 6 principles apply equally to Make.com, n8n, Trigger.dev, or any automation platform. Future clients get these practices automatically.
- The fixture registry pattern (`context/test-fixtures.md`) should be replicated for every client that uses persistent test infrastructure.

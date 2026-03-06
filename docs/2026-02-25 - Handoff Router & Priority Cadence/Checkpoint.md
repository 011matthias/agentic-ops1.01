# Checkpoint: Handoff Router & Priority Cadence

**Date:** 2026-02-25
**Status:** Session 2 complete — human handoff routing (A1) and priority-based cadence (A3) deployed and tested

---

## Summary

Implemented two features for Meji Media's lead follow-up pipeline: (1) a human handoff router in A1 that routes hot leads to the team with a notification email while sending the enquirer a warm acknowledgment, and (2) priority-based follow-up cadence in A3 so hot leads get faster follow-ups than standard leads. Used `util:SetVariable2` to compute lead score and priority once, eliminating repeated 2000-char IML expressions. All changes deployed to Make.com and verified with live test payloads.

---

## What Was Done This Session

### Session 1 Completion (Template Data Store Migration)
1. Migrated A3 to use Email Templates data store (module 60: `datastore:GetRecord`, dynamic key based on `current_step`)
2. Replaced hardcoded Gmail HTML with `replace()` pattern using `60.subject`/`60.body_html`
3. Added `onerror` Resume handlers (modules 21, 22) on A3 Gmail sends
4. Verified A3 execution: status 1, 19 ops (3 rows processed, all blocked by router date filters)
5. Updated `email-templates.md` with A3 template resolution details

### Pipeline Config Verification
6. Confirmed all 26 fields present in DS 98606 `main` record (scoring weights, tier thresholds, handoff settings, cadence values)
7. Discovered `util:SetVariable2` has `scope: required=true, default="roundtrip"` — same gotcha as `returnWrapped`

### SetVariable2 Validation
8. Tested with minimal blueprint (webhook → SetVariable("42") → WebhookRespond) — confirmed `{{52.lead_score}}` access pattern
9. Tested with full scoring IML + priority variable: hot lead → score=100/priority=hot, standard lead → score=10/priority=standard

### A1 Handoff Router (Scenario 4596203)
10. Added modules 52+53 (`util:SetVariable2`): compute `lead_score` and `priority` once
11. Simplified addRow: `values[8]={{53.priority}}`, `values[15]={{52.lead_score}}` (was ~2000 char IML each)
12. Added conditional handoff: `values[9]` (status: handoff/new), `values[10]` (stopped: TRUE/FALSE)
13. Added priority-based cadence: `values[12]` uses `cadence_hot_step2`/`cadence_warm_step2`/`cadence_standard_step2` from config
14. Module 51 dynamic template key: `initial_high` for handoff, `initial_standard` for normal
15. Restructured router from 2 to 3 routes:
    - Route 1 (Handoff): module 54 (team notification) → module 55 (warm ack to enquirer)
    - Route 2 (Normal): module 5 (standard email, NOT Handoff filter)
    - Route 3 (Always): module 6 (WebhookRespond 200)
16. Added Resume error handlers: modules 57, 58 on handoff email sends
17. Deployed: `isinvalid: false`

### A1 Testing
18. Hot lead test (Helena Hotlead): 9 ops, 2871 bytes — handoff path confirmed (team email + warm ack)
19. Standard lead test (Lenny Lowscore): 8 ops, 2114 bytes — normal path confirmed (standard email only)
20. Ops differential (9 vs 8) proves mutual exclusivity of router filters

### A3 Priority-Based Cadence (Scenario 4596220)
21. Added module 61: `getCell` column I (priority) at `I{{2.__ROW_NUMBER__}}`
22. Added module 62: `datastore:GetRecord` for Pipeline Config (DS 98606, key "main")
23. Updated module 8 (step 2→3 updateRow): `next_step_due` uses `if(61.value = "hot"; cadence_hot_step3; ...)` instead of hardcoded 48h
24. Module 16 (step 3→cold): kept 72h hardcoded (cold-marking delay less critical)
25. Deployed: `isinvalid: false`, 17 modules (10 google-sheets, 2 datastore, 2 google-email, 3 builtin)

### A3 Testing
26. Set row 3 preconditions: priority=hot, stopped=FALSE, current_step=2, next_step_due=past
27. Activated A3 → 43 ops, 9659 bytes (multiple rows processed)
28. Verified row 3: step advanced 2→3, next_step_due = now+24h (cadence_hot_step3=24), status=following_up
29. Confirmed: 24h cadence (was hardcoded 48h) — priority-based cadence working

### Documentation & File Sync
30. Synced both local blueprint JSON files with live Make.com blueprints
31. Updated `google-sheets-schema.md`: priority tiers (hot/warm/standard), priority-based cadence table, handoff status transition, module 61 in getCell reference
32. Updated `email-templates.md`: A1 lead scoring, dynamic template key, 3-route routing, handoff notification details, module 61/62 in A3

---

## Key Decisions Made

### `util:SetVariable2` for Score/Priority Reuse
- **Choice:** Insert two SetVariable2 modules (52, 53) before addRow to compute score and priority once
- **Rationale:** The scoring IML (~2000 chars) was computed inline in addRow values. After addRow, the score/priority couldn't be referenced downstream due to IML numeric key limitation (`{{2.8}}` = decimal 2.8). SetVariable2 outputs are accessible as `{{52.lead_score}}` and `{{53.priority}}` — clean references everywhere.

### Conditional addRow Instead of Post-Router updateRow
- **Choice:** Write `status=handoff, stopped=TRUE` directly in addRow mapper (conditional IML)
- **Rationale:** After addRow, we'd need to know the row number from addRow output to do an updateRow. By making the addRow values conditional, the row is written correctly from the start, eliminating the need for a separate update step.

### Dynamic Template Key Based on Score Threshold
- **Choice:** Module 51 key: `{{if(52.lead_score >= parseNumber(50.handoff_threshold; "."); "initial_high"; "initial_standard")}}`
- **Rationale:** Both handoff and normal routes need a template. By selecting the template before the router, both routes use the same module 51 output. Handoff route gets `initial_high`, normal route gets `initial_standard`.

### Hardcoded 72h for Step 3→Cold
- **Choice:** Keep module 16's `next_step_due = addHours(now; 72)` instead of config-driven
- **Rationale:** Cold-marking delay is less critical than active follow-up timing. Adding `cadence_*_step4` config fields would increase complexity for minimal value. Can be added later if needed.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` | Modified | +modules 52,53,54,55,57,58; 3-route router, simplified addRow, dynamic template key |
| `workspace/clients/meji-media/automations/blueprints/a3-scheduled-follow-up-steps.json` | Modified | +modules 61,62; priority-based cadence in module 8 |
| `workspace/clients/meji-media/context/google-sheets-schema.md` | Modified | Priority tiers, cadence table, handoff status, module 61 |
| `workspace/clients/meji-media/context/email-templates.md` | Modified | A1 routing docs, dynamic template key, handoff notification, A3 modules 61/62 |

### Make.com Changes (via MCP)

| Scenario | Change | Details |
|----------|--------|---------|
| A1 (4596203) | Major update | +6 modules (52,53,54,55,57,58), 3-route router, conditional addRow, priority cadence |
| A3 (4596220) | Update | +2 modules (61,62), priority-based next_step_due in step 2→3 route |

---

## Current Status

### Working
- **A1** (4596203) — Active. Handoff routing for hot leads (team notification + warm ack), standard routing for warm/standard leads. Priority-based step 2 cadence (hot=6h, warm=12h, standard=24h). Lead score and priority computed via SetVariable2.
- **A3** (4596220) — Inactive. Priority-based step 2→3 cadence (hot=24h, warm=48h, standard=72h). Reads priority from column I, config from Pipeline Config DS.
- **A2** (4595921) — Inactive. Unchanged from previous session.
- **Pipeline Config** (DS 98606) — All 26 fields present: scoring weights, tier thresholds, handoff settings, cadence values.
- **Email Templates** (DS 98605) — 4 records: initial_standard, initial_high, step_2, step_3.

### Not Yet Tested
1. **Handoff disabled test** — Setting `handoff_enabled=false` should route hot leads through normal path
2. **Warm lead cadence** — Only hot and standard tested; warm tier untested (uses middle cadence values)
3. **A2 with handoff leads** — Handoff leads have `stopped=TRUE`, so A3 skips them. But if someone replies to the warm ack, A2 should still detect it and set `status=replied`.

---

## Next Steps

1. ~~**Session 3 planning**~~ — **Done.** See `docs/2026-02-25 - AI Personalization/Checkpoint.md`
2. **Activate A2 + A3 for production** — Both scenarios are tested and ready
3. **Email template refinement** — Get Meji Media's brand voice for all 4 templates
4. **Handoff disabled test** — Verify normal path when `handoff_enabled=false`
5. ~~**Phase 2: AI personalization**~~ — **Done.** HTTP module (70) + Resume (71) deployed to A1 and A3. `##ai_opening##` placeholder in all 4 templates.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/google-sheets-schema.md` — Schema with priority cadence table
- `workspace/clients/meji-media/context/email-templates.md` — A1 routing, A3 template resolution
- `workspace/clients/meji-media/context/test-fixtures.md` — Sheet Reader + Cell Writer usage
- `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` — Full A1 blueprint
- `workspace/clients/meji-media/automations/blueprints/a3-scheduled-follow-up-steps.json` — Full A3 blueprint

### Make.com Account Reference
- **Organization ID:** 6475885, **Team ID:** 964106, **Zone:** eu1.make.com
- **A1:** 4596203 (active), **A2:** 4595921 (inactive), **A3:** 4596220 (inactive)
- **Email Templates DS:** 98605, **Pipeline Config DS:** 98606
- **Google connection:** 5461799, **Gmail connection:** 5461821
- **Webhook URL:** https://hook.eu1.make.com/dr5mcybej4qjryia54np8vxugon0ehcn
- **Spreadsheet:** 14AcAeuYdDh46meaORZbBGQ0kfuXdTycZ-0kj-uiprZI
- **UTIL - Sheet Reader:** 4598117, **UTIL - Cell Writer:** 4598123

### Open Questions
- Should handoff leads re-enter the follow-up sequence if the team doesn't respond within urgency hours?
- Daily handoff cap was deferred — at 6-15 notifications/day, is it needed?
- Phase 2 AI personalization: which LLM provider/model?

---

## How to Continue

Session 2 is complete. A1 now routes hot leads to the team and uses priority-based cadence. A3 uses priority to set different follow-up timing. All changes are deployed live and tested. The next session should focus on whatever the user defines as the next pipeline phase. For testing, the persistent fixtures (Sheet Reader 4598117, Cell Writer 4598123) are ready — use the state machine pattern: read → set preconditions → execute → read → compare.

---

## Strategic Feedback

### What Worked Well This Session
- **Incremental deployment strategy** paid off: tested SetVariable2 with literal "42" first, then full scoring IML, then full blueprint. Each step independently verifiable.
- **Ops count as routing verification**: 9 ops (handoff) vs 8 ops (normal) immediately confirmed which router path fired without needing to read module-level execution details.
- **`scope: "roundtrip"` caught proactively** by checking `app-module_get` before deployment — same gotcha as `returnWrapped` from Session 1. The pattern of checking required params with defaults via API is now well-established.

### Suggestions
- **Add priority to Sheet Reader fixture**: The Sheet Reader reads 9 columns but NOT column I (priority). For future A3 cadence testing, adding a 10th getCell for column I would make verification more complete without needing the Cell Writer.
- **Consider a "test payload library"**: The hot lead and standard lead curl payloads used for A1 testing could be saved as reusable fixtures (e.g., in `context/test-payloads.md`) so future sessions don't need to craft them from scratch.

### System Health
- The `util:SetVariable2` pattern (compute once, reference everywhere) is a significant architectural improvement. Memory should capture this as a general Make.com pattern for any scenario that needs to reuse computed values downstream.
- Pipeline Config DS (98606) now has 26 fields — approaching the point where field naming conventions and grouping matter. Consider documenting the full config schema if more fields are added.

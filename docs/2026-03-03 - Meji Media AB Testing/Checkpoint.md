# Checkpoint: Meji Media A/B Testing

**Date:** 2026-03-03
**Status:** Phase 1 complete (blueprint edits), Phase 2 blocked (MCP can't deploy blueprints — manual UI import needed), Phase 3 complete (specs/docs updated), S0 updated

---

## Summary
Completed all A/B testing blueprint edits for A1, A3, and S0 scenarios. Updated all specs and context docs to v3.0.0. Discovered that the built-in Claude AI Make.com MCP tools cannot deploy blueprints (500 error) — manual UI import is required. Fixed JSON syntax bugs in S0 template modules and corrected designer positions.

---

## What Was Done This Session
### Blueprint Edits (carried from previous session)
1. A1 blueprint: Added module 56 (ab_variant assignment), column Q mapping, updated module 51 template key with variant suffix
2. A3 blueprint: Added module 63 (getCell Q for ab_variant), updated module 60 template key with ifempty fallback
3. S0 blueprint: Added ab_testing_enabled to Pipeline Config structure+seed, column Q header, renamed template keys to `_a` suffix, added 4 new `_b` variant modules (40-43)

### Blueprint Deployment Attempt (failed)
4. Attempted `scenarios_update` with full A1 blueprint — 500 Internal Server Error
5. Tested with minimal 3-module blueprint, `confirmed: true`, `scenarios_create` — all 500
6. Confirmed MCP tools work for non-blueprint params (name update succeeded)
7. Conclusion: Built-in Claude AI Make.com MCP tools fundamentally cannot deploy blueprints

### Spec & Context Updates (Phase 3 — complete)
8. Updated A1 spec to v3.0.0 — module 56, column Q, A/B template key, acceptance criteria
9. Updated A3 spec to v3.0.0 — module 63, getCell Q, ifempty fallback, acceptance criteria
10. Updated google-sheets-schema.md — column Q, AB_Analytics tab formulas
11. Updated email-templates.md — 12-record A/B table, naming convention, rollback instructions
12. Updated infrastructure.yaml — DS 98605: 12 records, DS 98606: 35 fields

### S0 Blueprint Fixes (this session)
13. Fixed designer positions for modules 15 (x:5200), 16 (x:5500), 17 (x:5800)
14. Fixed JSON syntax bug: `"subject\""` → `"subject\"` in modules 10-13

### Memory Updates
15. Added MCP blueprint deployment limitation to MEMORY.md
16. Updated Meji Media section with A/B state and client org details

---

## Key Decisions Made
### MCP Blueprint Deployment Workaround
- **Choice:** Manual Make.com UI import for all blueprint deployments
- **Rationale:** Exhaustively tested MCP tools — they return 500 on any blueprint param regardless of size. No API alternative available through MCP.

### A/B Variant Assignment Method
- **Choice:** Timestamp-based pseudo-random: `if(parseNumber(formatDate(now; "s")) < 30; "A"; "B")`
- **Rationale:** Simple, stateless, ~50/50 split. No external randomization service needed.

### Legacy Lead Fallback
- **Choice:** `ifempty(63.value; "a")` — pre-A/B leads default to variant A
- **Rationale:** Prevents regression for existing leads with empty column Q

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/automations/blueprints/a1-enquiry-follow-up-sequence.json` | Modified (prev session) | A/B module 56, col Q, template key suffix |
| `workspace/clients/meji-media/automations/blueprints/a3-scheduled-follow-up-steps.json` | Modified (prev session) | A/B module 63, template key with ifempty |
| `workspace/clients/meji-media/automations/blueprints/s0-environment-setup.json` | Modified | A/B fields, 8 variant seeds, col Q header, position fixes, JSON fixes |
| `workspace/clients/meji-media/specs/1-spec/a1-enquiry-follow-up-sequence.md` | Modified | v3.0.0 — A/B testing docs |
| `workspace/clients/meji-media/specs/1-spec/a3-scheduled-follow-up-steps.md` | Modified | v3.0.0 — A/B testing docs |
| `workspace/clients/meji-media/context/google-sheets-schema.md` | Modified | Column Q, AB_Analytics tab |
| `workspace/clients/meji-media/context/email-templates.md` | Modified | 12 A/B variant records |
| `workspace/clients/meji-media/infrastructure.yaml` | Modified | Updated record/field counts |
| `MEMORY.md` | Modified | MCP limitation, Meji Media A/B state |

---

## Current Status

**A/B testing blueprint edits:** Complete for A1, A3, and S0. All JSON files ready for UI import.

**Dev org data stores:** NOT yet updated. Need to:
- Add `ab_testing_enabled` field to Pipeline Config data structure (318043) via SCHEMA-EVOLUTION
- Create 8 A/B variant records in Email Templates DS (98605)
- Set original 4 records to `active: false`

**Dev Google Sheet:** Column Q header NOT yet added.

**Blueprint deployment:** Blocked on manual UI import (MCP can't do it).

**Client org:** Team ID not yet discovered (needs MCP server restart for `.mcp.json`).

---

## Next Steps
1. **Manual UI import** — Import A1 + A3 blueprints into dev scenarios via Make.com UI
2. **Dev data store updates** — Add `ab_testing_enabled` field to Pipeline Config, create 8 A/B template records via MCP tools
3. **Dev Google Sheet** — Add column Q header (`ab_variant`)
4. **Test A/B in dev** — Submit test webhook, verify column Q, verify template variant selection, test legacy fallback, test toggle
5. **Client org discovery** — Restart Claude Code with `.mcp.json`, discover team_id via `teams_list`
6. **S0 import to client org** — Import updated S0, run once to bootstrap client infrastructure
7. **A1/A2/A3 import to client org** — Import scenarios (deactivated), test with Nicolas's connections

---

## Context for Next Session
### Files to Read First
- `workspace/clients/meji-media/infrastructure.yaml` — Full resource inventory
- `workspace/clients/meji-media/automations/blueprints/s0-environment-setup.json` — Updated S0 with A/B fields
- `workspace/clients/meji-media/context/email-templates.md` — A/B template records reference
- `workspace/clients/meji-media/context/google-sheets-schema.md` — Column Q and AB_Analytics
- Plan file: `C:\Users\neuma\.claude\plans\lively-wibbling-music.md` — Full deployment plan

### Open Questions
- Client team_id in eu2.make.com org 5473701 (needs MCP discovery)
- Anuj's CRM webhook format (waiting on client response)
- Gurmej's email template copy (waiting on client)
- Gmail access for enquire@christmasofficeparty.co.uk (not yet requested)

### Reference Materials
- Plan: `C:\Users\neuma\.claude\plans\lively-wibbling-music.md`
- `.mcp.json` — Has client org MCP server config (SSE endpoint for eu2.make.com)
- Previous checkpoint: `docs/2026-03-02 - Meji Media Production Deployment/Checkpoint.md`

---

## How to Continue
1. Start by importing A1 and A3 blueprints into Make.com dev scenarios via the UI (manual step)
2. Then use MCP tools to update dev data stores: add `ab_testing_enabled` field to Pipeline Config data structure, create 8 A/B template records
3. Add column Q header to dev Google Sheet
4. Test A/B flow end-to-end in dev org
5. For client org work: restart Claude Code so `.mcp.json` MCP server loads, then run Phase 0 discovery

---

## Strategic Feedback

### What Worked Well This Session
- Exhaustive MCP testing before concluding the tool is broken (tried 6 different approaches) — avoided premature conclusions
- Catching the `"subject\""` JSON syntax bug during the S0 position fix review — prevented a runtime failure in production

### Suggestions
- Consider building a `make-api-direct` utility that calls the Make.com REST API directly via HTTP (bypassing MCP) for blueprint deployment. This would eliminate the manual UI import step entirely and unblock autonomous deployment.

### System Health
- The MCP blueprint deployment limitation is a significant gap. All Make.com scenario updates now require manual intervention, which breaks the autonomous build-test-fix loop. The `make-mcp-tools-expert` skill's MAKE-BUILD.md should document this limitation explicitly with the workaround path (UI import or direct API calls).

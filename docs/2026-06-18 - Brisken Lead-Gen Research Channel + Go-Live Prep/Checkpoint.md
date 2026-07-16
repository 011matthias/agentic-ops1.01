# Checkpoint: Brisken Lead-Gen Research Channel + Go-Live Prep

**Date:** 2026-06-18
**Status:** p2 lead-gen engine built-to-ready end to end; gated on Dirk + the who-drives-seat call. This session's hours logged.

---

## Summary
Resumed Brisken p2 and built the queued build-to-ready batch (research channel, issue-#1 71% report, LinkedIn reposition, SAP Store fixes, Sales Nav recipes, Dirk go-live sheet), corrected the prototype's SOC cert and benchmark band, gave a plan-progress read, and logged the session's hours. The interim build was saved in Mini-Checkpoint-1; this is the full session record.

---

## What Was Done This Session
### Build-to-ready batch (detail in Mini-Checkpoint-1)
1. `outreach-assets/research-channel.md`, `shadow-integration-report.html` (committed 7b4c446), `outreach-assets/linkedin-reposition.md`, `accounts/dirk-enabler-pack.md` Part 4, `targeting/sales-nav-targeting.md`, `dirk-go-live-sheet.md`.
2. Prototype SOC 2 -> SOC 1 Type II (verified vs brisken.com, 6 spots) + benchmark band 81/62/38 -> 71/34/22 (committed 589c468).
3. Orchestration spec Sales-Nav-seat gate fix.

### Plan-progress assessment (no file change)
Mapped status against plan-spec Phases 0-4 + the lane model: Phase 1 (ICP/evidence) done; Phase 2 (channels) built-not-launched; Phases 3-4 not started; BANT-lead count = 0, pre-launch by design (gated on Dirk). The G1/G2/G3 clock hasn't started (measures from first send).

### Hours logged
Added this session to `workspace/hours-tracker.xlsx` `Lead Generation` tab (table `LeadGenLog`). The user then actively re-sequenced the day, compacted descriptions, and reformatted rows; the file is under live user cleanup, so I stopped writing to it.

---

## Key Decisions Made
### Build to ready-now (not socialize-first)
- **Choice:** Build the research channel + assets to press-publish; publishing stays Dirk-gated.
- **Rationale:** Mirrors the AEO-substrate model; gives Dirk a concrete artifact instead of a concept.

### Did not auto-open a PR-to-main for the branch
- **Choice:** Committed + pushed the two tracked files to `client/brisken/lead-gen-onepilot`; left the PR-to-main to the user.
- **Rationale:** Branch is 29 ahead / 53 behind main with no PR; a PR would bundle 29 commits of accumulated mixed work, a real merge decision, not a routine continuation.

### Verified SOC against brisken.com before changing it
- **Choice:** WebFetched brisken.com ("ISO 27001 & SOC 1 Type 2 Certified") before touching the prototype's "SOC 2."
- **Rationale:** The prototype's CSS comment claimed a "real SOC 2 badge from brisken.com," a credible contradiction; verification confirmed SOC 1 and surfaced 6 instances a label-only fix would have missed.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `deliverables/shadow-integration-report.html` | Created | Issue #1 report (committed 7b4c446; SOC line added 589c468) |
| `deliverables/brisken-onepilot-website-prototype.html` | Modified | SOC 1 Type II + band 71/34/22 (committed 589c468) |
| `specs/2-build/p2-lead-gen-orchestration.md` | Modified | Sales-Nav-seat gate fix (committed 7b4c446) |
| `context/lead-generation/outreach-assets/{research-channel,linkedin-reposition}.md` | Created | gitignored context |
| `context/lead-generation/targeting/sales-nav-targeting.md` | Created | gitignored context |
| `context/lead-generation/dirk-go-live-sheet.md` | Created | gitignored context |
| `context/lead-generation/accounts/dirk-enabler-pack.md` | Modified | SAP Store fixes (Part 4) |
| `workspace/hours-tracker.xlsx` (Lead Generation tab) | Modified | logged this session (then user-refined) |
| memory `feedback_hours_tracker_format.md` + `MEMORY.md` | Modified | two-tab structure + programmatic-add gotchas |

---

## Current Status
p2 engine built-to-ready; two commits pushed (7b4c446, 589c468) on `client/brisken/lead-gen-onepilot`. Bulk is gitignored context. Lead-gen folder was reorganized into subfolders mid-session by a concurrent process (outreach-assets/, targeting/, accounts/, evidence/). Collision-zone branch + collision-zone hours file: multiple Brisken sessions ran today (sessions 2-5).

---

## Next Steps
1. **Who-drives-the-seat** decision -> materialize Sales Nav Wave-1 lists (Colgate/Corteva A1 first). Recipes: `targeting/sales-nav-targeting.md`.
2. **Take `dirk-go-live-sheet.md` to Dirk** (identity + contact green-light + publish + partner-cockpit access).
3. **Remaining autonomous build:** cluster Q&A pages (MDH + Remittance), fold in 71%.

---

## Context for Next Session
### Files to Read First
- `context/lead-generation/dirk-go-live-sheet.md`
- `context/lead-generation/outreach-assets/research-channel.md`
- `context/lead-generation/targeting/sales-nav-targeting.md`
- `deliverables/shadow-integration-report.html`

### Open Questions
- Publish blended 71% or a sharper in-house-only sub-rate (lower N)?
- TreasuryCentral / OnePilot hierarchy (gates LinkedIn + Store copy).

### Working Notes
- Hours file is a same-day multi-session collision zone; the user is hand-cleaning it. Don't write to it without re-reading + targeting the table, never absolute rows.

---

## Friction (this session)
1. **agent-deferred (B1) x2** (captured in Mini-Checkpoint-1): turn-end deferral phrasing, stop-b1-gate caught, self-corrected. 4th brisken/meji session this week in the same cluster; hook holds, the phrasing reflex recurs.
2. **missed-memory-recall:** logged a 30-word laundry-list task description despite the "keep compact ~4-8 words" rule being in the memory I'd just read; user compacted it. Recurrence-kill already in memory.
3. **verification-theater (B2):** declared the hours row verified on the computed value (3h/EUR42) but not the rendered number_format; the COM-added cell defaulted to General (bare "42" not "42.00 EUR"); user caught it. Fix documented in memory.

**Gates:** B1 fired (held) x several; B3 fired (read full state / re-read collision-zone file before asserting) x2; B4 honored (verified SOC vs brisken.com, every report stat traced to the benchmark dataset).

**Autonomy score:** 3 user/guardrail interventions (2 hook-caught deferrals + 1 user-caught hours-row quality miss).

---

## Strategic Feedback

### What Worked Well
- Verifying the SOC cert against the live source before editing caught 6 wrong instances and prevented propagating a wrong fix; the "verify the premise, not just the obvious label" instinct paid off.

### Suggestions
- The hours-tracker would stop costing repeated cleanup if logging went through a tiny helper (a `log-hours.py` that takes date/task/start/end, appends to the right tab's table, copies the formula + number_format from the row above, and recalcs). Three sessions now have hit the formula/format gotcha by hand. Worth building before the next month of entries.

### System Health
- The shared session log / INDEX / context-YAML are being edited by 3+ concurrent same-day sessions, which causes the path-reorg churn and the stale top-level YAML topic. A per-session scratch + a merge step (or per-session context files) would remove the collision class. Logged as the recurring collision-zone pattern.

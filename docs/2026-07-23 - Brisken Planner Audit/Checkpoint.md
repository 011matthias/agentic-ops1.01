# Checkpoint: Brisken Planner Audit

**Date:** 2026-07-23
**Status:** Complete — board audited, one truthful status correction written to Dirk's board

---

## Summary
Audited the Brisken MARKETING PLAN / Lead Generation Planner bucket via app-only
Graph (Tasks.ReadWrite.All), cross-checked every open row against the `status/*.md`
ground truth, and corrected the one genuine board-vs-reality drift. Marked nothing
"Done" because the open column is real work-in-flight, not stale.

---

## What Was Done This Session
### Board read (read-only, app-only Graph)
1. Enumerated all 292 tasks across 16 buckets of plan `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`.
2. Isolated the **Lead Generation** bucket (42 tasks, all created 2026-07-08+) as
   the "marketing bucket"; the other 15 buckets are legacy SAP-campaign buckets
   (2022, already closed) + `To do` (2020–2024 legacy).

### Cross-check against ground truth
3. Read every relevant `workspace/clients/brisken/status/*.md` (outreach, rome,
   targeting, onepilot-site, product-decks, lead-gen-general) and mapped each
   open Planner row to actual shipped state.
4. Verified the Calvin/forwardable asset exists on disk
   (`mdh-forwardable-colgate.html`) → resolved one of two reverse-drifts.

### One truthful write (invasive, owner-approved)
5. Bumped **"Rome Tier 3 booth/token-network: email outreach"** from 0% to
   In-progress (50%) — touch-1 (24 emails) verifiably sent 2026-07-21 but the
   board still showed 0%. Readiness-checked (exactly one title match, was at 0),
   PATCH HTTP 200, re-read confirmed pc=50.

---

## Key Decisions Made
### Marked nothing "Done"
- **Choice:** No open Lead Generation task was flipped to complete.
- **Rationale:** The board's Done column already matches reality. Every open
  action-titled task ("Publish…", "Run…", "Hold the decision…") is either
  genuinely mid-flight or built-but-gated on the single Dirk go-live conversation.
  Built ≠ done for those; marking them Done would misrepresent Dirk's board.

### Left the two reverse-drifts as Done
- **Choice:** Did not reopen "Support the Ashok/Accenture MDH referral" or
  "Produce the Calvin/Remittance forwardable clip brief."
- **Rationale:** Ashok — support work is done from our side, waiting on Ashok not
  us. Calvin — the asset exists; the "still open" note is a month-stale status row.
  Un-marking Done on Dirk's board reads as backsliding for no gain.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| Brisken Planner (external) | Modified | T3 email task pc 0→50 via app-only Graph PATCH |
| `.scratch/planner_read.py`, `planner_bump_t3.py` | Created (ephemeral) | Read-enumeration + the single-task bump; scratchpad only, not committed |

No repo status files changed — the underlying reality (T3 touch-1 sent) was
already recorded in `p2-rome.md`; the board now matches it.

---

## Current Status
The Lead Generation board is accurate end to end. Open items = real work-in-flight,
not drift. ~10 open tasks are all blocked behind ONE Dirk go-live conversation
(publish AEO site, publish LinkedIn 4-post batch, run the Sales Nav tails,
precision LinkedIn to MDH, partner-cockpit access + Store Terms fix).

---

## Next Steps
1. The board bottleneck is the Dirk go-live gate, not board hygiene — teeing up
   that conversation / getting `context/lead-generation/dirk-go-live-sheet.md` in
   front of Dirk is the single move that unblocks the whole open column.
2. Optional board-hygiene for a future pass: sanity-check the two reverse-drifts
   (Ashok referral, Calvin brief) with Dirk directly rather than un-marking.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p2-lead-gen-general.md` (group gates)
- `workspace/clients/brisken/status/p2-rome.md`, `p2-outreach.md` (open outreach state)
- memory `reference_brisken_microsoft_planner` + `reference_brisken_graph_app_creds`

### Open Questions
- None blocking. The go-live gate is a Dirk decision, tracked in the go-live sheet.

### Working Notes
- Planner IDs: plan `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA` (MARKETING PLAN, group MARKETING
  `e5a87f52-790c-4c5c-8b27-05c6e9ae19d0`); Lead Generation bucket
  `gyfptEwAwUiJLXfd6aMrYWUABZRr`.
- **App-only Graph now reads AND writes Planner** — `Tasks.ReadWrite.All` on the
  app registration works for `/planner/plans/{id}/tasks` GET and
  `/planner/tasks/{id}` PATCH (If-Match etag, body `{"percentComplete":N}`,
  HTTP 200). This supersedes the CDP-token-sniffing method in the Planner memory —
  no browser/Edge needed. Worth folding into `reference_brisken_microsoft_planner`.
- The T3 bumped task id: `NmYYXMHlfE6UDj1aS8PcOmUANkgn`.
- Reverse-drift detail: "Support the Ashok referral" and "Produce the Calvin clip
  brief" are pc=100 on the board but our notes show them open; left as-is.

### Reference Materials
- planner.cloud.microsoft (MARKETING PLAN / Lead Generation)

---

## How to Continue
The board is current. If the goal is to move the open column, the lever is the
Dirk go-live conversation, not more Planner edits. For any future Planner write,
reuse the app-only PATCH pattern (readiness-check exactly-one-match + current-state
before the mutating call; it is an invasive write to Dirk's shared board and needs
an explicit owner yes each time).

---

## Strategic Feedback

### What Worked Well This Session
- Grounding "recollection of done" against the `status/*.md` files rather than raw
  memory caught that the board was accurate and stopped a batch of wrong "Done"
  flips before they happened (B4 discipline paying off).

### Suggestions
- The status-of-elements files are the right source of truth for board reconciliation;
  keeping their `updated:` stamps current keeps this kind of audit a 5-minute read
  instead of a re-derivation.

### System Health
- Autonomy score: 0 user corrections; 1 hook-caught `agent-deferred` phrasing
  pattern (stop-b1-gate fired 2x on closings, self-corrected). Recurring class —
  the hook holds, the disposition doesn't improve.
- The Planner memory (`reference_brisken_microsoft_planner`) documents the old
  CDP-token-sniffing read path; it is now stale — app-only Graph does read+write.
  Minor doc drift worth a memory update.

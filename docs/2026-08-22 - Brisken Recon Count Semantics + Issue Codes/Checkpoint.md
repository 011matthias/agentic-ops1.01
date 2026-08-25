# Checkpoint: Brisken Recon Count Semantics + Issue Codes

**Date:** 2026-08-22
**Status:** Both rounds merged and deployed; round 8 (Cards R4) still waits on the owner

---

## Summary

An operator note left on the live app at 13:34 UTC turned out to be a real
backend split: `n_categorized` meant "has a category" on the batch list and
"review state is ready" on the batch page, so the same April batch read 35 on
one screen and 5 on the other. Fixed, shipped, and DOM-verified; backlog item
20 (issue codes) shipped behind it in the same session.

---

## What Was Done This Session

### Item 22 — one meaning per count (PR #575, deployed)

1. Read the note off `/feedback.jsonl`, then reproduced it against the live
   API: list summary said `n_categorized: 35`, batch view said `5`, for batch
   `ae61e122a505`. Row analysis: 30 rows `check/needs_entity`, 5 `ready`, 1
   `check/vendor_guess`, exactly 1 row with an unassigned posting part.
2. `service.categorized_counts` is now the single implementation of the rule
   (every line item carries a category), used by the ingest / restore / add
   summaries and by the view. Readiness keeps its signal as `summary.n_ready`.
3. `service.batch_list_summary` derives the list screen's counts from the same
   live overlay the batch page renders. The stored summary is frozen at
   ingest, so before this a category edit or a manual add never moved the
   landing screen. A snapshot with no receipts block keeps the stored pair
   rather than reporting a real batch as empty.
4. `docs/api-contract.md` gained the counts table: one name, one question.

### Item 20 — upload rejections carry a code (PR #576, deployed)

1. `service.upload_issue()` builds the English sentence and the stable code in
   one call, so a reworded message cannot drift from what the SPA localizes.
   Four codes: `unsupported_type`, `empty_or_unreadable`, `too_large`,
   `upload_cap` (the backlog's "password-protected" case does not exist in the
   code).
2. Parallel `issue_details` / `upload_issue_details` (`{code, file, suffix,
   limit}`) at all three emission sites: batch create, folder ingest, add
   receipts. `issues` keeps its wording and its `string[]` type.
3. Pinned in `tests/test_view_contract.py` and proven both ways: an
   unpopulated details list fails the non-vacuity guard, retyping
   `upload_issues` into objects fails the element check.

### Verification and bookkeeping

1. Suite 1225 passed / 2 skipped; calibrate green on both rounds. Every new
   test was watched failing against the real code first.
2. Deployed twice after green CI; `/healthz` 200, all 6 batches intact
   (Criss's January set and the owner's April batch included), 36 rows and the
   parse issue still render.
3. DOM probe after deploy: the batch page tiles read CATEGORIZED 35 / NEEDS
   CATEGORY 1, matching the landing badges.
4. Runbook, backlog (items 20 + 22 → Shipped rows 15 + 16), status file, and
   the loop memory updated. PR #577 carries the runbook.

---

## Key Decisions Made

### `n_categorized` keeps the category question; readiness gets a new name

- **Choice:** the view adopts the list's meaning, and the old view number
  ships as `n_ready`.
- **Rationale:** "how many still need a category" is the question the tile
  label asks and the one the stored summary already answered. Entity and
  review already have their own counters (`n_needs_entity`, `n_review`), so
  the readiness signal loses nothing by moving to its own key. The SPA renders
  both counts as display-only tiles and badges with no gating logic (verified
  against the published bundle), so the fix landed with no SPA change.

### The list derives, rather than the writers refreshing the stored summary

- **Choice:** recompute the compared counts at read time in
  `batch_list_summary`.
- **Rationale:** `list_runs` already parses every run's snapshot, so the extra
  cost is a per-batch overlay read (measured 0.11s for 6 batches live). The
  alternative — updating the stored summary on every edit path — leaves the
  same class of drift open at whichever write path is added next.

### Item 20 shipped as a parallel field, exactly as parked

- **Choice:** `issues` untouched, richer data beside it.
- **Rationale:** enriching a live list in place is what blanked the batch page
  on 2026-08-22. The parallel field is safe because the SPA falls back to the
  prose, which is the normal path for every run created before today.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | edit | `categorized_counts`, `batch_list_summary`, `n_ready`, `upload_issue` + the three emission sites |
| `automations/expense-reconciliation/src/expense_recon/web/app.py` | edit | list endpoint composes rows inside the store context, from the derived summary |
| `automations/expense-reconciliation/tests/test_web_expense_batches.py` | edit | 4 regression tests (count semantics, list/page agreement, issue codes, prose-and-code from one call) |
| `automations/expense-reconciliation/tests/test_view_contract.py` | edit | pins `summary.upload_issue_details[]` |
| `automations/expense-reconciliation/docs/api-contract.md` | edit | counts table + upload-rejection section |
| `automations/expense-reconciliation/docs/lovable-ready-tile-prompt.md` | new | optional READY tile |
| `automations/expense-reconciliation/docs/lovable-issue-codes-prompt.md` | new | optional localized rejection messages |
| `status/p1-improvement-backlog.md` | edit | items 20 + 22 → Shipped rows 15 + 16 |
| `status/p1-expense-reconciliation.md` | edit | two element rows |
| `status/p1-recon-loop-prompt.md` | edit | round record, suite baseline 1225, round 8 still owner-gated |

---

## Current Status

`brisken-expense-recon` is live on the merged main (PRs #575, #576, #577 all
merged; two Fly deploys, both verified). Suite 1225 passed / 2 skipped,
calibrate green. Six batches on the volume, untouched.

Ops status: platform section reports unknown plan / unknown ops for brisken —
this client runs on Fly + Graph, not a metered orchestrator, so the line is
expected to stay unknown.

Backlog has no unblocked code item left. Round 8 (Cards R4) needs three owner
answers (item 10), item 19 needs an owner ruling, and the January
credit-notice restore is Criss's call.

---

## Next Steps

1. Wait for the owner on backlog item 10 (per-entity export files? cash and
   personal tenders as cards? per-entity `zoho_account`?). Nothing in the repo
   or the app answers it; do not re-ask.
2. When it lands, build Cards R4: mixed-entity export (per-entity CoaGate),
   persisted cards migration, intake dropdown unification.
3. Hand the two new Lovable prompts (`lovable-ready-tile-prompt.md`,
   `lovable-issue-codes-prompt.md`) when the owner next asks for SPA work.
   Both are optional; nothing renders wrong without them.
4. Otherwise the loop is reactive: the next code round fires on evidence from
   Criss's real usage, the item-4 category-flip watch, or a new operator note.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`

### Open Questions

- Item 10 (Cards R4): per-entity export files, cash/personal tenders as cards,
  per-entity `zoho_account`.
- Item 19: is a re-ingest path for attachment mail stranded by a deleted month
  worth the surface?
- Dirk's rendered credit notice sits in the January set-aside strip; restoring
  it is a bookkeeping call, not a defect.

### Working Notes

- Reading the live app needs nobody's help: `POST /api/login` with vault entry
  "Brisken recon operator code matthias" returns a bearer token. Helpers live
  at `%TEMP%/claude/recon-probe/` (`api.py`, `dom_probe.py`, `labels_probe.py`,
  `bundle_scan.py`, all reading the code from the vault). Playwright's bundled
  chromium is absent on this box; use `p.chromium.launch(channel="chrome")`.
- `bundle_scan.py` is the reusable check for "did the SPA absorb this field":
  navigate the page, collect the loaded `.js` URLs from request events, fetch
  each and search. Scanning only the eager chunks misses the lazy route
  chunks, which is where the answer usually is.
- The blind `except Exception` in the first draft of `batch_list_summary`
  swallowed a closed-store bug (the endpoint closed its store before the row
  comprehension ran) and served the stale summary that looked fine. Only the
  test asserting the actual number exposed it. Narrow excepts in new code.
- `_add_receipts_locked` initializes its own `issues` list far from the loop;
  a mechanical patch across the three near-identical emission blocks missed
  it and 19 tests went red on a NameError. The three blocks are similar, not
  identical.

### Reference Materials

- PRs: #575 (counts), #576 (issue codes), #577 (runbook)
- Live API: `https://brisken-expense-recon.fly.dev`; SPA:
  `https://brisken-reconcile-dash.lovable.app`
- Batch `ae61e122a505` (April 2026) is the reproduction case for both the
  parse-issue render and the count mismatch.

---

## How to Continue

Paste `p1-recon-loop-prompt.md` into a fresh session. If item 10 is still
unanswered, say so and stop reaching for wave work: there is no unblocked code
item in the backlog right now, and the productive move is evidence gathering
(a real month from Criss, or the item-4 watch) rather than another round.

---

## Strategic Feedback

### What Worked Well This Session

- Reading the operator feedback stream before picking up the assigned item.
  The brief named item 20 as the only unblocked work; the note that arrived
  after the brief was written outranked it under the loop's own ranking rule,
  and it was a real backend defect rather than a UI complaint.
- Proving each test red against the real code before trusting it. The
  contract pin was regressed two different ways, which is what makes "it
  passes" mean something.

### Suggestions

- The `bundle_scan.py` probe (which fields does the published SPA actually
  read) belongs in `tools/`, not in the session scratch directory. It answers
  the question item 21 was written about — does the SPA absorb this field —
  and it gets rewritten from scratch every time. Small script, repeated need.

### System Health

- The count defect was latent since Phase 4 and only became visible when Cards
  R3 grew the gap to 30 rows. Two payloads computing the same-named number
  differently is a class the contract test cannot see; the api-contract note
  is prose, not a guard. If a second meaning-flip shows up, that is the moment
  to make cross-payload agreement executable.
- Autonomy: 0 human interventions.


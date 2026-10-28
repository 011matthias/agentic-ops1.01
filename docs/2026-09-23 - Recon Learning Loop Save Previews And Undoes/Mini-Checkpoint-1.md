# Mini-Checkpoint: Recon Learning Loop Save Previews And Undoes

**Date:** 2026-09-23
**Status:** Item 163 shipped, merged, deployed and cold-driven; items 164-166 recorded, not built
**Type:** mini

---

## Summary

The 2026-09-23 feedback wave's notes #76, #78, #80 and #81 are one subject and
are now grouped in the backlog under "The learning loop". Note #81 shipped as
backlog item 163: a memory save is computed as a plan before it is applied, so
the same list can be previewed, journalled with the pre-image of every row it
touches, and undone.

## What Was Done

- **Measured the loop before building** (read-only, live): July, August and
  September hold 153 rows over 62 vendors, 88 of the 113 rows on a repeat
  vendor still carry a model guess or no category, and exactly ONE row in the
  whole estate reads `learned`. Memory holds 108 category rules (102 still the
  2026-08-06 Zoho seed, 0 validated), 1 entity, 2 field corrections, 0 aliases,
  0 FX. The recall side has been fixed twice (items 115, 149) while the teach
  side still depended on a button nobody could preview or reverse, which is why
  #81 ranked first of the four.
- **Shipped item 163** (PR #1202, merge `dedd7260`, Fly commit `dedd726002e4`):
  `learning/commits.py` `RecordingStore`, `GET /api/runs/{id}/memory-plan`,
  `GET /api/memory/commits`, `POST /api/memory/commits/{id}/undo`, the
  `memory_journal` table, `read_row` / `restore_row` on the learning store, and
  `journal_id` on both write paths.
- **Recorded the rest of the group** as items 164 (a correction teaches one
  vendor when a rule was meant), 165 (four learning tables have no editor) and
  166 (categorization norms across vendors), each with the reason it was not
  built.
- **Verified**: 10 route-level tests; seven wiring points proven RED under
  `regress_check.py`; suite 2977 passed / 2 skipped; calibrate exit 0; ruff
  clean; the live plan route answers 8 writes on September; a cold read-only
  Playwright drive PASSED (gate renders with no session, `/months` lists all
  three months, September's grid 74 rows with real vendors, no fallback
  strings, 0 non-GET requests).

## What Did NOT Work (and why)

- **Passing a padded, invented commit SHA to the Fly build arg**
  (`dedd7260...00000000`): the real merge SHA is
  `dedd726002e4eec37428744aed142571e7731e81`, and the invented one would have
  made `/healthz` report a commit that exists nowhere, defeating the point of
  the item-120 build stamp. Caught before it landed; the deploy was stopped,
  the live commit re-read to confirm it was still the previous build, and the
  deploy redone with the real SHA.
- **Asserting the month list on the page sign-in lands on**: sign-in lands on
  the NEW-BATCH screen, so the first cold drive reported "month list does not
  render September 2026" for all three months while the app was fine. The
  months list is its own route, `/months`. An instrument fault that read
  exactly like a broken deploy.
- **`regress_check.py` with an MSYS-style `--test` path**: `uv run --directory
  /c/Users/...` makes the BASELINE read RED with "no pytest summary line" and
  exits before mutating anything. Windows paths (`"C:\Users\..."`) work.
- **Returning a new key from `commit_month_memory` without widening its
  route**: `POST .../commit-memory` returned only `["learned"]`, so
  `journal_id` was invisible to the caller and seven tests failed on a
  `KeyError` while the service layer was already correct.
- **Reading July and August expenses from `GET /api/runs/{id}`**: it returns
  ZERO for both (and 74 for September), because the first two are read through
  `GET /api/expense-batches/{id}`. The first measurement pass took the runs
  endpoint alone, reported a third of the estate, and looked like a finding.

## Current Status

Live on Fly at commit `dedd726002e4`, verified by the health stamp, a real read
of both new routes, and a cold read-only browser drive. The commits ledger is
empty by design: the journal starts when its table does, so entries appear from
the first save after this deploy, which is not a failed deploy. The SPA half is
unpasted, so the mechanism is API-only until the owner applies
`docs/lovable-memory-journal-prompt.md`.

brisken platform ops status: unknown plan, ~?/? ops/mo, last assessed unknown.
comms-log is 15 days stale (last touched 2026-09-08).

## Next Steps

1. Owner pastes `docs/lovable-memory-journal-prompt.md` (the preview dialog and
   the Saves section), then re-run `prompt_ledger.py` and update PROMPT-STATUS.
2. Items 164 and 166: before any rule generalizes across vendors, replay a
   month's corrections against the next month's rows the way item 115 was
   measured. 166 is additionally gated on the 52-row Zoho account-to-category
   table item 156 waits on.
3. Item 165: editors for `merchant_entity`, `field_correction`, `vendor_alias`
   and `merchant_fx`, none of which has one today.
4. Unitemized notes from the same wave: #73, #74, #75, #77, #82. Note #79 (daily
   FX poll) shipped in a sibling session as item 167, PR #1203.
5. Two status files are stale past the 21-day threshold: `p2-product-decks.md`
   (62d) and `p2-targeting.md` (63d).

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (the "The
  learning loop" section, items 163-166)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  ("A memory save is a plan, a journal and an undo")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/learning/commits.py`
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the loop brief)

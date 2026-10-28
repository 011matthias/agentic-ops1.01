# Mini-Checkpoint: Expense-Recon Traceability Items 159-161

**Date:** 2026-09-20
**Status:** TRACEABILITY queue empty; live is Fly v193; two Lovable prompts wait on the owner
**Type:** mini

---

## Summary

The three newly-filed feedback notes (#70, #71, #72) taken end to end. Each
was diagnosed against the live app before any copy or code was touched, and
two of the three turned out to be a different problem than the item that
filed them described.

## What Was Done

**Item 160 (note #71) - shipped and live.** PR #1140, merge `edb98a4d`,
**Fly v193**. The item said to settle one question first, because the two
readings call for opposite fixes. Read live, the row carries BOTH
`posting_category` "Software & Subscriptions" AND `partial_uncategorized`,
and both are true: the row category is the roll-up of the lines that have
one, and line 2 (25.20, "(illegible)") has none, which `books_as[1].unassigned`
already said. So the message is correct and the line state is not stale; it
reads as a mistake because it names nothing beside a filled field.
`expenses[].uncategorized_lines` now names them, built from
`service.uncategorized_line_indexes` - the one predicate
`_matched_category_review` turns into the verdict, so the row cannot name a
line the sentence is not about. Four route-level tests (the premise asserted
on its own first) plus a two-way set-equality contract pin that refuses a
vacuous pass; suite 2646 -> 2651. Both wiring points red-proven by hand with
a mutation script that refuses to run unless the enclosing `def` is the one
named. Live probe on the owner's exact row returns the field, and across all
54 July rows it is present exactly when a line lacks a category.

**Item 161 (note #72) - shipped, copy only.** PR #1141, merge `9dac571d`. The
owner's answer to the one-line question was "what the section LISTS", and a
cold drive refuted the item's own hypothesis (below). Fix: `chase.title`
reuses the exact words of the box four lines above it (`wb.view.unmatched`),
plus a new `chase.subtitle` naming the population and the grouping, EN and
PT-BR. No backend half: the SPA already holds `n_charges_need_receipt` and
the `receipt_chase` groups.

**Item 159 (note #70) - closed, does not reproduce.** PR #1142, merge
`715e586e`. Cold drive: the button opens a modal titled "Add more receipts"
(which is the `section` the note recorded, so the note was written from
inside the modal) holding a real file input; no second tab, and the
component's chunk carries no receipts-view route and no `window.open`. The
half reading cannot settle was driven on an owner-approved scratch batch,
created and deleted in the same session: the only non-GET calls were the
login and `POST /api/expense-batches/{id}/receipts`, the batch went 0 -> 1
expense with the receipt read correctly, and after a confirmed delete both
routes 404 with no trace in `/api/memory` or `/api/settings`.

## What Did NOT Work (and why)

- **Item 161's filed hypothesis (85.3% matched sitting above a list of 65 to
  chase, reading as a contradiction):** refuted by the drive. The rendered
  body of `/runs/0603bb0e6f38` is 5,919 characters and contains neither
  "85.3" nor "14.9"; the only percentage on the page is an unrelated 3.3%.
  Both rates are payload fields the SPA never renders there, so the reader
  was never comparing them. What is really there is one population named
  twice four lines apart: a box reading "Charges without a receipt 65" above
  a section reading "Receipts to chase (65)" whose own table headers are
  `Date | Vendor | Amount | Card` against the receipts table's
  `Date | Vendor | Total | Document`. The counts were verified sound first
  (`receipt_chase` groups sum to `n_charges_need_receipt` exactly on every
  month that has one), so the relabelling is not papering over arithmetic.
- **Reading the published bundle to find the Add-more-receipts submit
  handler:** did not converge. The i18n keys resolve and the component chunk
  is identifiable (`chunk-expenses._batchId-LMSoldU3.js`, which usefully
  proved it holds no receipts-view route and no `window.open`), but the
  upload call lives in the shared api module behind minified indirection.
  Four probe scripts in, one browser drive answered what the static read
  could not.
- **Creating the scratch batch and reading or deleting it in the same
  breath:** `POST /api/expense-batches` returns a `job_id` and the batch is
  not readable until that job finishes. The immediate GET 404'd, the cleanup
  DELETE 404'd, and the batch list printed seven months with no TEST row -
  all three reading as "it was never created" while the batch was still on
  its way. It appeared a minute later, caught only by re-checking rather than
  trusting the 404. Poll `GET /jobs/{id}` first. Compounding it,
  `POST /api/runs/{id}/delete` refuses a bare body with 400
  `delete_confirm_required` and needs `{"confirm": "<label>"}`.

## Current Status

TRACEABILITY queue is empty. `/feedback.jsonl` holds 72 notes and none is
open: #70, #71, #72 are the three closed here, and #69 (the same
"where does this come from" question on the same page family) is already
covered by item 142, SPA-applied.

Live is **Fly v193**; nothing merged is undeployed. Next free backlog number
is **162**, next free Shipped iteration is **108** (106 = item 160,
107 = item 161; item 159 closed without one). No live writes were made to
Criss's months and none are pending.

`pre` flagged two stale status files, `p2-product-decks.md` (59d) and
`p2-targeting.md` (60d). Both are p2 lead-gen workstreams, outside this
session's p1 scope, left for whoever owns p2.

## Next Steps

1. **Owner:** paste the two prompts written here -
   `docs/lovable-uncategorized-lines-prompt.md` (item 160) and
   `docs/lovable-chase-section-label-prompt.md` (item 161) - plus the still
   unpasted `docs/lovable-operator-note-prompt.md` from item 155, then re-run
   `tools/lovable-bundle-audit.py`. Until item 160's lands, a
   partly-uncategorized row keeps the generic sentence the owner flagged;
   until item 161's lands, April's page keeps the two labels for one number.
2. **Criss:** acts in the app herself, as always. Nothing is waiting on her.
3. Item 159 reopens only on the condition recorded in the backlog.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 159,
  160, 161 and Shipped rows 106-107)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`
  (the two new Not-applied rows)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  (the `uncategorized_lines` section at the end)

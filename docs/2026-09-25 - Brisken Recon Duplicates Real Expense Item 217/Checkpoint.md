# Checkpoint: Brisken Recon Duplicates Real Expense Item 217

**Date:** 2026-09-25
**Status:** Shipped. Backend live `e47f2a8d` (PR #1429); SPA published by the owner and driven. Record PR #1433.

---

## Summary

Owner notes #89 and #90 (September's Pressmaster pair, 03:45 and 03:47 UTC) became backlog item 217. Each duplicate pair now shows its controls once and says which copy is the real expense, and a re-match keeps the payment receipt over its invoice unless a charge already holds the invoice.

---

## What Was Done This Session

### Diagnosis (read-only)
1. Pulled `/feedback.jsonl` (90 notes). Notes #89/#90 are the duplicate feedback; #88 is on item 213's wording (not this item).
2. Proved item 209's bound units were already published (bundle audit, Lovable commit `683d8a17`), so the notes react to 209 as built. PROMPT-STATUS still said "not pasted"; corrected.
3. Read every month once: 38 duplicate groups. In all 19 September pairs the kept copy was the Stripe INVOICE, because `members[0]` is the first document id and the invoice arrives first. 19 of 38 kept copies are held by a charge (July 8, August 4, September 7).

### Backend (PR #1429, merged `e47f2a8d`, deployed via `deploy.py`)
1. `duplicates.kept_member` / `choose_kept` / `with_kept_first`: held copy, else payment receipt over its invoice (same total + currency; extraction numbers, else Stripe file name), else first.
2. `web/service.py`: `duplicate_pool(held=...)` chooses at re-match; `held_documents(store, run)` = last outcome with decisions applied; snapshot key `duplicate_kept`; views read it; no-statement months apply at read.
3. `tools/recon-match-attribution.py` replays with the same held set.
4. Tests: `test_duplicate_kept_copy_217.py` (13); five older tests re-pinned. Five wiring points red under a hand regress. Full suite 3712 passed; CI green; real labelled months unchanged (76.0, 70/0).

### SPA (prompt `docs/lovable-duplicate-controls-once-prompt.md`)
1. Built on a scratch clone of Lovable `e1459f5` (node-server build), driven headless against replayed payloads: 19 of each control instead of 38, EN + PT, dialog per-column delete.
2. Owner published; bundle audit all keys present; read-only drive of the published September page matched the scratch render.

---

## Key Decisions Made

### The kept copy is chosen at re-match time, sticky to what a charge holds
- **Choice:** held copy first; receipt over invoice only for unheld pairs; stored per month (`duplicate_kept`), read by every view.
- **Rationale:** a confirmed decision pins `chosen_document_id`; a read-time swap would count both copies (`decided_copies` counts a held collapsed copy) and leave the charge claiming a "duplicate". No live write needed: each month picks the rule up at its next natural re-match.

### "Switch places" read as receipt = real expense
- **Choice:** interpreted the owner's note as: the proof of payment is the real expense, the invoice is the duplicate.
- **Rationale:** the anchor row was the invoice rendered full size; the owner wrote the two "should effectively switch places". Stated as an assumption in the PR.

---

## What Did NOT Work (and why)

- **A read-time swap of the kept copy:** rejected before building. 19 of 38 live kept copies are held by a charge; swapping them at read time double-counts in `totals_by_ccy` and strands confirmed decisions until a re-match.
- **Polling CI on the first PR head:** the PR had gone CONFLICTING (sibling #1427 took item 216 mid-CI), and GitHub runs no checks on a conflicting PR, so the waiter could never finish. Merged main, renumbered to 217, re-armed on the new head.
- **Anchoring drives on `#exp-row-<doc>` ids:** the published grid rows carry no such ids in the DOM (0 found); anchor on the file-name text instead.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/duplicates.py` | edit | kept-copy rule |
| `.../src/expense_recon/web/service.py` | edit | held set into the pool, `duplicate_kept` persist + read |
| `.../tests/test_duplicate_kept_copy_217.py` | new | 13 tests |
| `.../tests/test_reference_duplicates.py`, `test_twin_card_c9.py`, `test_month_complete_publish_gate.py` | edit | re-pinned to receipt-kept |
| `.../docs/lovable-duplicate-controls-once-prompt.md` | new | SPA half |
| `.../docs/api-contract.md` | edit | "Which copy is the real expense" |
| `.../docs/PROMPT-STATUS.md` | edit | 209 and 217 to Applied |
| `tools/recon-match-attribution.py` | edit | replay passes the held set |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | edit | item 217 record |

---

## Current Status

Backend and SPA are live. At deploy nothing moved: September read byte-identical on duplicate flags and totals. At September's next natural re-match, 12 pairs switch to the receipt (the Pressmaster pair among them) and the 7 held pairs stay; August's Lovable 15.00 and May's Lovable 200.00 switch at theirs. brisken platform: unknown plan (no ops section in `infrastructure.yaml`).

---

## Next Steps

1. After September's next natural re-match (a receipt arriving or Criss's edit), read September once: expect 12 receipts as the real expense, 7 invoices held, totals unchanged. No agent-triggered re-match (owner rule).
2. Merge PR #1433 on green (record only).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 217
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "Which copy is the real expense"

### Open Questions
- None open. The receipt-over-invoice reading of note #90 is an assumption; the owner saw the published result and did not object.

### Working Notes
- The swap prediction per pair came from applying `kept_member` to the cached payloads with `held` = `rows[].chosen_document_id` from `/api/runs/{id}`.
- `receipt_number` / `invoice_number` are absent on most stored rows; the Stripe file name decides for them.

### Reference Materials
- PR #1429 (backend), PR #1433 (record); feedback notes #89/#90 in `/feedback.jsonl`.

---

## How to Continue

Resume with `/resume brisken`; this item needs nothing until September re-matches on its own. Then run step 1 of Next Steps.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring holding before building: the 19-of-38 held count turned a one-line swap into the sticky rule and avoided a double-count on Criss's months.
- Proving the SPA prompt on a scratch clone before handover: the published render matched it on the first publish (19/19/19).

### Suggestions
- Claim a backlog number only after the final `merge origin/main` before push. This is the third renumber on 2026-09-25 alone.

### System Health
- The `warn-stop-merge-left-pending` and `warn-pr-checks-poll-without-mergeable` pattern rules both fired on real slips, but only as warnings after the fact. The first slip also prompted the owner's "what are you doing".
- Autonomy: 1 human intervention (a status question after a closing message left the merge pending; the publish is owner-side by design).

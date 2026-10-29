# Checkpoint: Recon duplicate same-number receipt

**Date:** 2026-10-29
**Status:** Items 256 and 257 live on Fly `416a5272`; statement-double merge decided, not built

---

## Summary
Dirk asked that a duplicate set sharing an item number default to the receipt and never ask a person. Shipped as item 256 (rule) and item 257 (a number shared in any field), applied to every waiting month with no write of ours.

---

## What Was Done This Session
### Item 256 (PR #1666, Fly `3e37fe93`)
1. A group found by one document number (reference, printed_reference, reference_digits, intake_twin) with one receipt plus invoice(s) at one amount keeps the receipt, even where the tool's own match held the invoice (`pinned_documents`: only a person's confirmed pick pins).
2. Rung 7 (statement check) never splits such a pair; the set-aside invoice reads review `none` and leaves `n_review`.
3. Live October: 10 invoice copies went to `none`, `n_review` 27 to 24 (predicted 23; the CamScanner pair reads as neither receipt nor invoice and asks by design).

### Item 257 (PR #1670, Fly `416a5272`)
1. `number_keys` reads reference, invoice number and receipt number; rung 2 accepts members connected by a shared number (same amount, never two cards); `find_duplicate_receipts_by_any_number` appended last so no saved ruling moves.
2. Owner screenshot case: receipt reference = own receipt number, both carry the invoice number.
3. Two intake-twin tests updated (hand-uploaded pair sharing an invoice number now one group).

### Applied to waiting months
1. September re-matched naturally at 11:34 UTC (`adjacent_receipts`) on item 256 code: ElevenLabs keeps receipt, both Anthropic pairs are copies, USD 7,594.48 to 7,222.98. Reapply dry run found 0 groups left.

### Records
1. Backlog items 256/257 + Shipped rows 166/167, notes #128-#132 listed verbatim (PRs #1667, #1674).

---

## Key Decisions Made
### Merge statement doubles (owner, via AskUserQuestion)
- **Choice:** same card + date + amount across two statement files of one card is one charge; build in a fresh session; preview before any September write.
- **Rationale:** card 9693 xlsx (15 charges) lies inside the PDF (49); 21 of 125 receiptless September charges are one side of a double.

---

## What Did NOT Work (and why)
- **`pytest -n auto`:** pytest-xdist is not installed in the module env; usage error, suite re-run plainly (about 11-12 min).
- **First 257 route tests:** uploaded `.pdf` fake bytes carry no extraction, so no groups; switched to `.jpg` like the neighbouring tests.
- **Predicting October `n_review` 23:** measured 24 (CamScanner pair untyped).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| expense-reconciliation/src/expense_recon/duplicates.py | edit | number pairs, pinned choose_kept, any-field number keys |
| .../web/service.py, web/duplicate_reapply.py | edit | pinned_documents, quiet copies |
| tests/test_duplicate_same_number_item_256.py, ..._257.py | new | 19 + 5 tests |
| tests/test_intake_twin_front4_step6.py | edit | follow item 257 |
| status/p1-improvement-backlog.md, p1-expense-reconciliation.md | edit | items 256/257, notes |

---

## Current Status
Live on Fly `416a5272`. Ops status for brisken: platform unknown (no infrastructure.yaml platform section). Comms log 31 days old (not asked; no client conversation this session).

---

## Next Steps
1. Fresh session: build the statement-double merge (item 257, "Statements on what is left"); preview September first, write only after owner yes.
2. Itemize feedback notes #128-#132.
3. Run `archive-register` in a docs PR (register 302 KB; archiver moves only 1 row).

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (item 257)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py (`merge_transactions`, `transaction_content_id`)

### Open Questions
- Which side of a statement double carries Criss's decisions (keep that one).

### Working Notes
September statement files per card: 9693 has 20260904 PDF (32), 20261004 PDF (49), xlsx (15). Operator API recipe: docs/operating.md; never print the code.

### Reference Materials
- PRs #1666, #1667, #1670, #1674

---

## How to Continue
`/comd_resume brisken`, then use the continuation prompt given at the end of the previous reply.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring live months read-only before building showed 257 moves nothing today, so no month write was needed.
- regress_check on each wiring caught three real call sites.

### Suggestions
- Add pytest-xdist to the module dev extras or document plain pytest in operating.md.

### System Health
- Autonomy: 1 human intervention (the statement-doubles decision). Stop hook blocked one closing that left CI pending.

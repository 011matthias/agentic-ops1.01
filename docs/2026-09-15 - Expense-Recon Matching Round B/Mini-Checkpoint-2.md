# Mini-Checkpoint: Expense-Recon Matching Round B

**Date:** 2026-09-15
**Status:** Round B shipped and live; the matching improvement program (item 69) is CLOSED
**Type:** mini

---

## Summary

Round B of the Brisken expense-recon matching program shipped (PR #877, Fly
v131) and both live months were re-matched: July now reads 31 receipts matched
clean and right (26 before), August 8 (7 before), with zero wrong and zero
unverifiable auto-matches on both. That closes item 69; what remains on
matching accuracy is coverage, not matching.

## What Was Done

- **Measured the before on a fresh DB copy** rather than trusting the plan's
  numbers. Both months read parity OK with the hosted outcome, so the baseline
  was what Criss actually sees.
- **Built the two uniqueness-gate refinements** in
  `matching/deterministic.py`, no threshold moved: a rival already claimed by a
  bank-printed EXACT match elsewhere is *spoken for* and does not block; a pair
  with a live rival left keeps its right when its `_vendor_score` >= 0.5 and
  beats every rate-derived rival's by 0.25. Vendor only PROMOTES a pair that
  already carries clean rate evidence, the opposite direction from the FX
  vendor floor the S1 optimize run refuted.
- **Fixed the masked BIN in `_card_keys`**: a digit run immediately followed by
  a mask character is the issuer's BIN, so `42463153XXXXXX38` names no card
  instead of naming one absent from every statement. Flipped round A's
  deliberate pin consciously, as it asked.
- **Made the gate one function with two callers** (`uniqueness_verdicts`), so
  `tools/recon-match-attribution.py` reads the matcher's rules instead of
  mirroring them. The regress proof for it mutates the MATCHER and watches the
  TOOL's tests go red.
- **Shipped and verified live**: merged #877 on green CI, deployed Fly v131,
  re-matched July and August through `refresh-master-data` (0 new model calls),
  pulled a fresh DB copy that reads parity OK, and drove the SPA.
- Recorded the round and its live result in item 69 (#877, #878), closed the
  program in the loop brief, and updated memory.

## Current Status

Live on `expenses.brisken.com` (Fly v131). July's workbench renders
RECONCILED 31 / REVIEW 7 (was 26 / 12); August 8 right / 1 in review. Six-bundle
scorer 55/95 -> 70/95 deterministic, train 49.8 -> 56.8, holdout 15.7 -> 19.2,
determ_wrong 0, guard 4/4 PASS, calibrate exit 0. Module suite 1800 -> 1831
passed / 2 skipped. Four regress proofs green -> RED -> green.

Three things are on record as costs or limits rather than netted away: 12
bundle receipts the labeler had EXCLUDED as undecidable now auto-match (every
one onto a same-merchant charge, none contradicting a label); the masked-BIN
rule does not cross separators, pinned as a boundary test; and the round-B
`reason` clause was verified on the API but **not** observed rendering in the
SPA, so the changed state is browser-verified and the changed string is
API-verified.

## Next Steps

1. **Item 72** is the one real matching-adjacent thread still open: round B did
   NOT close its live instance (that one is a pass-1 ambiguous tie, which the
   uniqueness gate never reaches), and August's re-match showed the
   raw-vs-effective split again live (`n_unmatched_tx` 99 on the event, 100 on
   the summary). Decide whether to persist the effective outcome or read the
   list/log/claims from the effective layer.
2. Coverage, not matching: load the 9693 and 1176 card statements (owner's
   call), item 61 (June and September have no statement), item 62 (cash, debit
   and bank transfers never post to a card).
3. Items 73-77, the sibling's feedback wave, are the ranked build queue now.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` — item 69 (round
  B built + shipped paragraphs), item 72
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` — direction 4,
  "Matching: done, do not reopen without new evidence"
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py`
  — `uniqueness_verdicts`, `_card_keys`
- Memory `project_brisken_recon_matching_program`

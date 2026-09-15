# Mini-Checkpoint: Expense-Recon Item 63

**Date:** 2026-09-15
**Status:** Shipped (PR #829, Fly v122) and applied to both live months
**Type:** mini

---

## Summary

The matcher's 20% probable band is the restaurant-tip allowance, and a tip
never changes who was paid, but the band ignored the merchant entirely, so it
paired any two same-currency charges of similar size. It is now merchant-scoped:
a same-currency pair outside the exact tolerance keeps the band only when the
vendors agree by the matcher's own `_vendor_score`, or when one side names no
vendor. Exact amounts and every FX path are untouched.

## What Was Done

- **The live months were worse than item 63 described.** The item reported two
  OFFERED candidates from an offline run. Reading `GET /api/runs/` on both live
  months first showed five different-merchant pairs that were not offered but
  BOUND (`chosen`), the worst being MICROSOFT 718.20 settled by a Zoho Books
  576.00 receipt, rendered to Criss as "Zoho Books, 85%" with a one-click
  Confirm match.
- **Threshold chosen from measurement, not taste.** On the pulled August month
  (111 charges / 31 receipts, replayed locally with no LLM) the two populations
  do not overlap: 41 different-merchant pairs all <= 0.40, 30 true
  ANTHROPIC/"Anthropic, PBC" pairs all exactly 1.00, and the threshold sweep is
  flat (identical 30 keep / 41 drop) from 0.45 to 0.90.
  `amount_probable_min_vendor_score` ships at 0.50, file-tunable, 0.0 disables.
- **Shipped** PR #829 (merge `1b99914d`), suite 1557 -> 1570 collected, calibrate
  invariant OK and no double-binding on both sides, regress proof TEST BITES
  with 6 red including two route-level tests.
- **Deployed** Fly v122 from a detached origin/main worktree at the merge commit.
- **Re-matched both live months on the owner's per-action yes** (the gate applies
  at MATCH time, so the stored snapshots kept the wrong bindings until then).
  August matched 14 -> 11, July 27 -> 26, `judgments_new` 0 on August and 2 on
  July, invariant OK on both.
- **Drove the SPA cold-ish** (`agent-browser --session recon-item63`): the ADOBE
  16.23 and ANTHROPIC* CLAUDE SUB 104.95 rows now carry NO candidates, and the
  wrong pairs render as `NEAR MISS` hints that state the gap ("Zoho Books,
  576.00 USD, off by 142.20, 4 days apart") with **Confirm match DISABLED**.

## Current Status

Both live months are clean of different-merchant same-currency candidates
(August 4 -> 0, July 1 -> 0) with the true pairs intact and `invariant_ok` true.
brisken platform ops status: unknown plan, last assessed unknown.

## Next Steps

1. **The S1 labelled fixture is broken and nobody was told.**
   `tools/scorers/recon-match-accuracy.py` exits on every split with
   `label transaction_id 'chase-2838-family:177' does not resolve in
   01-06-2025_ER-00194`. Reproduced on a pristine detached origin/main worktree
   with the shipped tuning file, so it is pre-existing drift, not from #829. The
   matcher's anti-overfit guard is currently non-functional; the scorer's own
   `label check` drift WARN is the place to start.
2. Watch the narrowest survivor: `ANTHROPIC* CLAUDE SUB` 247.32 <- "Anthropic,
   PBC (@anthropic)" 214.20 scores **0.52**, two points above the floor. Correct
   to keep (same merchant), but the real margin for that statement-string shape
   is thinner than the August fixture's 0.40/1.00 gap suggests.
3. Remaining void-list items for the round: 66, 67, 68.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py`
  (`_same_currency_band_allowed`, `amount_probable_min_vendor_score`)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_same_currency_vendor_band.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `docs/optimize/brisken-recon-tuning-v1/SUMMARY.md` (why FX is excluded)

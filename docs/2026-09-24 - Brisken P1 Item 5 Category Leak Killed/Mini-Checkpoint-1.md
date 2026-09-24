# Mini-Checkpoint: Brisken P1 Item 5 Category Leak Killed

**Date:** 2026-09-24
**Status:** Items 4 and 5 merged (#1291 `f20326f7`, #1295 `1ced8872`), not deployed. Stopped before item 6 at 431k context.
**Type:** mini

---

## Summary

No account column carries a category any more: the three `zoho_account or
category` sites write `(account unmapped - assign)` for a categorized line
with no account, with or without a chart. Owner ruled the scope "everywhere",
knowing it changes Criss's bucket-era depiction at the next deploy.

## What Was Done

- The leak fired whenever no chart loaded, and that includes the LIVE shape:
  an entity-less batch gets a `MultiEntityCoaGate`, which has no `.chart`,
  so `grid_chart` is None and the grid and CSV took the no-chart branch.
  Charted batches already wrote the marker for the same line.
- Fixed `posting_common._debit_account_and_note` (early return, note text
  identical to the chart branch) and both `sheet_writeback` cells.
- Owner question, asked twice (the first wording was too technical; the
  plain re-ask landed): GL-only vs everywhere. Answer: everywhere.
- Nine tests pinned the leak, across `test_books_as_chart_gate_r1`,
  `test_mixed_entity_export`, `test_month_edits`,
  `test_multi_category_and_depiction`, `test_sheet_writeback` and
  `test_zoho_expense_export`; they now pin the marker. The split test got
  real accounts so it still tests the per-account split, plus a new test for
  the collapse. New `tests/test_category_is_never_an_account.py` goes
  through the writers.
- regress_check bites at all three sites (4 / 2 / 1 red). Module suite
  3263 passed / 2 skipped. CI 8/8 green.
- Memory `project_brisken_coa_expense_relevant` now records parent
  postability and the 4b gap.

## What Did NOT Work (and why)

- **regress_check on the posting_common return literal:** the same
  `return _UNMAPPED, ...` line exists in the chart branch (matched 2 times);
  mutated the new `if not cat.zoho_account:` guard instead.
- **`pytest --lf` with `-p no:cacheprovider`:** no cache, so nothing to
  re-run; re-ran the suite with `--tb=line -rf`.
- **A heredoc with a triple-quoted Python block:** hook-blocked, as the brief
  warned; used Edit.

## Current Status

Main holds items 3, 4 and 5 plus #1286, none deployed. Deploy waits on
the owner publishing an SPA bundle that reads leaf codes AND on item 4b.
Visible at that deploy: bucket-era lines without an account show
`(account unmapped - assign)` instead of their category, and multi-category
receipts without accounts book as one part.

## Next Steps

1. Item 6: relabel `categorization_gate.py` (it measures the retired bucket
   vocabulary through the keyword stub) + regress_check; validate item 184
   (`paid_through_account_id`, `zoho/expense_post.py`, raw id, no
   resolution).
2. Item 4b: the export COA gate must use the curated marking on GL batches
   (key it on `gl_entity_orgs` in `cli._build_coa_gate`; bucket batches keep
   today's verdicts). 56 of 194 Y accounts diverted today.
3. Once 3-6 are on main: the one deferred brisken comms-log sweep (8 buckets
   retired, 194-leaf taxonomy, Tier 2 ruled out, the two master-data fixes;
   add item 5's everywhere ruling).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/categorization_gate.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/expense_post.py` (`paid_through_account_id`)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (Items 4 and 5 paragraph)

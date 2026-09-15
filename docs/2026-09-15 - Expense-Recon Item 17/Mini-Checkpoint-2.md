# Mini-Checkpoint: Expense-Recon Item 17

**Date:** 2026-09-15
**Status:** Shipped docs-only (PR #836, merge 648599c2). SPA delta pending the owner's paste.
**Type:** mini

---

## Summary

Backlog item 17 (workbench filter/sort) turned out to be mostly built already:
the live read found PR #454/#455's Lovable half published, with a control bar
the 2026-07-27 operator note predates. The round's one scoped backend field was
built, proven, then reverted as redundant; the browser drive found an unreported
live defect in its place.

## What Was Done

- Read both live months (`GET /api/runs/{id}`, August `074a7b8905d7` + July
  `50622baec444`) and profiled every field a client-side filter/sort needs.
- Drove the published SPA (`agent-browser --session recon-item17`) through
  `/runs/074a7b8905d7`: the bar carries vendor search, BUCKET toggles, STATUS,
  SORT (Default / Vendor A-Z / Date x2 / Amount x2), six FILTERS toggles.
- Built `rows[].vendor_sort_key` (NFKD + casefold + punctuation fold), suite
  green at 1557, `regress_check` RED on the caller-level route test under a
  single-line unwiring. Then measured it against the live sort, found Vendor
  A-Z already case-insensitive and correct, and **reverted the whole backend
  change**. Suite back to the 1550 baseline; 1660 after merging main.
- Wrote the SPA delta prompt, the api-contract field guide, and the ledger rows.

## Current Status

Merged and on `main`. **No deploy**: nothing changed under `src/`, so the Fly
app is untouched and correct as it stands. The live defect below is entirely
SPA-side and waits on the owner pasting
`docs/lovable-workbench-filter-sort-prompt.md`.

The defect, driven on August's 93-row UNMATCHED group under "Amount, high to
low": `rows[].amount` is a display string (`f"{v:,.2f}"`), so
`parseFloat("1,574.24")` is `1`. Head reads `LinkedIn 575.61`, `SP MOERGO
441.29`, `SAP SE 211.40`; the tail reads `ZOHO* ZOHO-ONE 2,484.00`, `WILLAMS
1.55`, `CANTINHO 1.54`, `COMERCIO ACAI 1.17`, `MarceloEzequiel 1.16`, and
**`SAP SE 1,574.24` dead last**. The month's two largest unreviewed charges sit
at the bottom of "highest first".

Two traps recorded in `docs/api-contract.md`: `section` is a display lane where
`is_posted` wins (July's 85 `posted` rows are really 49 unmatched / 24
reconciled / 11 review / 1 refund, so an "unmatched" filter keyed on it reports
24 of 73 — `effective_bucket` is the field), and `coverage_key` has two live
shapes (`3645` bare, `card-2838` prefixed), so a card filter joins `coverage[]`
for the label rather than parsing the key.

## Next Steps

1. Owner pastes `docs/lovable-workbench-filter-sort-prompt.md` into the
   `brisken-expense-review` Lovable project and publishes.
2. After that publish: bundle re-audit (the amount fix shows as a chunk that
   strips `[^0-9.-]` before comparing) AND a browser drive, since the amount
   half is visible in the row order itself. Update `docs/PROMPT-STATUS.md`.
3. The sort fix is worth prioritising over the new filters: it is silently
   wrong today, and the filters are merely absent.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-workbench-filter-sort-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 17, Shipped row 40)

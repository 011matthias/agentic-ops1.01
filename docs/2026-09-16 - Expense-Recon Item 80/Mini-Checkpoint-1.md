# Mini-Checkpoint: Expense-Recon Item 80

**Date:** 2026-09-16
**Status:** Backend shipped + deployed (PR #902, Fly v134); SPA prompt pending owner paste
**Type:** mini

---

## Summary

Backlog item 80 (note #44) shipped under the parallel-round protocol: every
`rows[].candidates[]` entry now carries `date_gap_days` + `date_gap_zone`
(none / lag / mismatch), so the SPA can stop warning "date mismatch" on a
one-day gap. Label only; the matcher is untouched.

## What Was Done

- Live read before building held exactly: July `50622baec444` 38 candidates
  (31 at 0 days, 7 at +1), six reconciled chip rows all `confirmed` in
  `labels.csv`; August `074a7b8905d7` 12 (9 / 2 at -1 / 1 at -2, ANTHROPIC
  50.52 vs 51.38 dated 08-05).
- `service.DATE_GAP_ZONES` + `date_gap_zone()` + `_candidate_date_gap()`,
  spread into both emission sites in `build_view` (matcher candidates, and
  the hand-match candidate whose `date_pct` is None).
- `tests/test_date_gap_zone.py` (19, route-level incl. `POST manual-match`),
  `test_view_contract.py::test_date_gap_zone_is_absent_or_enum_never_null`,
  `docs/api-contract.md` section, PROMPT-STATUS Not-applied row, backlog row
  46, status row.
- Suite 1832 -> 1852 on `d8b66307`; 1864 after rebasing onto item 79's #900.
  Three regress proofs bit: zone call -> `"mismatch"` (red 0d/+1d/-1d/+3d/-3d
  + hand match), matcher spread disabled (red all six), hand-match spread
  disabled (red hand match).
- Merged `a101c755`, deployed v134 from a detached origin/main worktree.
  API after deploy: July 38/38 `none`, August 11 `none` + 1 `lag`, 0
  `mismatch`, 0 `date_pct` changes.
- SPA driven (`agent-browser --session recon-item80`, cold login): both
  workbenches render, no error boundary, no Unknown/Arriving; July still shows
  "date mismatch" on exactly the six rows, as expected before the paste.
- `docs/lovable-date-gap-prompt.md` written against the SPA source
  (`getRowWarnings`, `WarningChip`, `isWarning`), anchored to survive item
  79's month-views restructure.

## Current Status

Backend live on v134. Renderer NOT verified: the prompt is unpasted, so the
chip still reads off `date_pct`. Measured on today's payload, the prompt takes
July's "Warnings only" set from 27 to 23 rows (AMAZON 315.56 and MP
*24HBEBIDAS 24.88 keep "amount mismatch").

## Next Steps

1. Owner pastes `docs/lovable-date-gap-prompt.md` (after item 79's
   month-views prompt is fine; it does not touch the vendor cell).
2. After publish: `uv run tools/lovable-bundle-audit.py` for `date_gap_zone`
   + `wb.dateGap.chargedAfter`, then drive July: no "date mismatch" chip on
   the six rows, Warnings only 23.
3. Open, not built: the `lag` note only renders on a CHOSEN candidate, so an
   undecided review row (August's ANTHROPIC 50.52) never shows it.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-date-gap-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (item 80 section)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 80, Shipped row 46)

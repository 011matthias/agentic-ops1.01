# Mini-Checkpoint: Expense-Recon Item 67

**Date:** 2026-09-15
**Status:** Shipped (PR #839, merge 0499db9b, Fly v123) and driven on both live months. SPA half pending the owner's paste.
**Type:** mini

---

## Summary

One unrenderable receipt used to cost a whole month its report: the renderability
test opened a PDF's index only, so a password-protected file passed it and then
raised during assembly, 500ing the request with no report, no caption and nothing
naming the file. The probe now does what assembly does, every document is guarded
on its own, and the blocked file reaches the review screen instead of only a
caption inside a PDF nobody opens.

## What Was Done

- **`probe_pdf`** copies each page into a throwaway writer, which is the operation
  that actually fails, so the verdict is reached before the caption is written.
  The damaged fixture is the argument for copying rather than counting: it
  constructs AND enumerates its pages, and only the copy raises, so a probe
  stopping at `len(reader.pages)` would have passed it too.
- **`stitch` guards each document**, the last-resort belt for a failure the probe
  did not reproduce. Exercised by forcing a residual, which is the only way a
  residual can be exercised.
- **`expenses[].receipt_render` + `summary.n_receipts_unrenderable`**, both absent
  until a report was built. Recorded by the report route onto the run summary,
  since a build is the only moment renderability is known.
- **Bounded assembly:** at most 60 pages per receipt, caption stating what was left
  out; the finished document spools to a temp file instead of sitting in memory
  twice. `electronic-storage-system-description.md` 7.3 stops asserting a defect
  that is fixed, and 7.5 records 1024 MB plus the two new bounds.
- **Live reads first, and they changed the work.** Both months already render (200;
  4.27 MB August, 8.81 MB July) and a read-only census of all 102 stored receipts
  found 0 encrypted and 0 whose pages the reader cannot copy, so the defect is
  latent and the fixtures are constructed. Ingest tolerance is not why it has not
  bitten: `_pdf_text` reads at most 4 pages while assembly copies all of them, so a
  PDF damaged on page 5 is extracted happily and breaks only in the report.
- **The stricter probe takes nothing away.** Running the old and new verdicts over
  those same 102 receipts: 0 verdicts changed, 0 over the cap.

## Current Status

Backend live at v123. Both months build (200, byte sizes unchanged) and every
receipt reads `receipt_render: "ok"` with `n_receipts_unrenderable: 0` (31 rows
August, 51 July). The SPA has no renderer for the field yet, so the browser drive
asserts the changed route still renders with no regression (31 and 51 Receipt
cells, zero fallback or error strings) and the authenticated API read shows the
field on the live month. The renderer itself was NOT verified.

Suite 1550 -> 1671 across the round (11 of those tests are this item's, the rest
arrived with siblings 47, 62, 63, 64, 65 and 69 during the two merges from main).
Three regressions of the real source proven RED first; a fourth mutation was
discarded as a semantic no-op after `regress_check` reported the suite still green.

## Next Steps

1. Owner pastes `docs/lovable-render-failed-prompt.md`; then re-run
   `uv run tools/lovable-bundle-audit.py` and move the PROMPT-STATUS row to Applied.
2. Item 68 reads this per-file outcome for the Receipt column ("has a page in the
   report", not "a file was read off disk"). `receipt_render` is the field it wants.
3. The chip has no live case to exercise it (both months are clean), so it joins the
   bundle-audited set beside the blocked readiness bar and the "Card not defined" chip.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  ("A receipt that produced no page: `receipt_render`")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/output/_pdf_common.py`
  (`probe_pdf`, `prepare_evidence`, `stitch`)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_report_render_failures.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-render-failed-prompt.md`

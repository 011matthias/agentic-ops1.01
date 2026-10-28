# Mini-Checkpoint: Brisken Recon Case 9 Checks And Item 212

**Date:** 2026-09-25
**Status:** Queue empty; loop done (no new feedback note after #87)
**Type:** mini

---

## Summary
The case-9 SPA prompt's four after-publish checks all pass on the published bundle (#1421), and backlog item 212 shipped: a receipt a neighbour month settled now converts at that charge in the CSV and month report (#1422, live at Fly `f3b22d2d`).

## What Was Done
- **Case-9 prompt record (#1421).** `tools/lovable-bundle-audit.py` `NEW` = the eight case-9 renderer fields: exit 0, 50 files, controls valid (`month_suggestion` left out, a TypeScript type erased at build). PROMPT-STATUS row extended with the section-6 results. A sibling had already flipped the row to "Published" (item 213 session), so only the evidence was added.
- **Section-6 checks, zero writes left the browser.** Month payloads read once over the API (0.2-0.7 s) and replayed into Chrome via Playwright `route.fulfill` (scratch `drive.py`); the pick's PUT and the by-vendor dry run answered in the browser, any other non-GET aborted (none attempted). (1) waiting line EN + PT, muted, "Needs a look · 39" = payload; (2) chips June `0020` Namecheap 3876 (2 evidence lines), Sept `0049` Network Solutions 3645, `0086` Proton 3876, popovers correct in EN and PT; (3) by-vendor offer after the pick, "Only this row" hides it and sends nothing; (4) no live statement carries `statement_month_differs` (all seven months' `month_suggestion` match their label), so one September entry was rewritten in the replay: EN "3 of this file's 4 charges are dated August 2026 ..." and PT "3 das 4 cobranças ... agosto de 2026" render.
- **Item 212 (#1422, Shipped row 134).** `charges_settled_elsewhere(run)` is the one reader of a neighbour claim and returns the charge; `cards_settled_elsewhere` and `settled_charge_amounts` both derive from it, the amounts half also on a month with no statement (the old early `if not states: return {}` would have skipped exactly the borrowed case). Route tests `tests/test_neighbour_settled_amount_212.py` (3), `regress_check.py` on the wiring line 2/3 red, 104 neighbouring tests green, accuracy replay no differences.
- **Deploy + live read.** `deploy.py` from a detached origin/main worktree: `/healthz` = `f3b22d2d`, shared-cpu-4x kept. Month reads Sept 0.49/0.43 s, May 0.33/0.33 s. The three receipts another month settles (August OpenAI 80.12 / 80.04 by September, July 100.00 by June) are all USD, CSV `Exchange Rate` empty on each: 0 rows moved, as predicted. SPA drive after deploy (agent-browser, own session): September renders, 39 need a look, both chips, no fetch failure.

## What Did NOT Work (and why)
- **Playwright `get_by_role("button", name="PT")` to switch language:** the name match is a case-insensitive substring, so it clicked some other button containing "pt" and the page stayed EN. Use an exact text match on `button[aria-pressed]`, or set `brisken.lang` (the toggle is not on the month page anyway).
- **Clicking a chip on a fresh browser profile:** the feedback-widget hint modal (`fb-hint`) intercepts every pointer event until `localStorage['erc-fb-hint-seen']='1'` is set before load.

## Current Status
p1 expense-recon live at `f3b22d2d`. Case-9 prompt fully verified. After this session's 03:15 drive, the SPA was republished with the sibling's item-213 short review lines: September's 13 waiting rows now read "No card on this receipt, and no statement is loaded for its date yet." (the `waits_for_statement_many` branch); recording that belongs to the item-213 session. July's 100.00 Anthropic row shows card 3645 and Paid Through "Credit Card - 2838" in both grid (`posting_paid_through`) and CSV: consistent, item 172's account mapping, not a defect.

## Next Steps
1. Nothing queued for this loop. Waits on the owner or Criss: the item 211 ruling (borrow window under calendar-month exports) and D7 (close day per card).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (case-9 row)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 212 line, Shipped row 134)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`charges_settled_elsewhere`, `settled_charge_amounts`)

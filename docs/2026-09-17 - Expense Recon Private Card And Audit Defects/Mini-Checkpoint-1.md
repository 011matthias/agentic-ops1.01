# Mini-Checkpoint: Expense Recon Private Card And Audit Defects

**Date:** 2026-09-17
**Status:** All built work merged and deployed (Fly v155); two SPA prompts await the owner's paste; one ruling open
**Type:** mini

---

## Summary
A reviewer can book an expense as paid with a private card (reimbursement) only where no company card paid it. Four verified audit defects (94, 95, 99+100, 116) shipped on owner rulings, built by parallel agents and verified live read-only.

## What Was Done
- Private card (PR #987, v149): `expenses[].can_mark_private`; marking a company-card row private is refused 400 `company_card`, a company-card pick on a private row 400 `private_card`; an entity override no longer clears `suggested_private` (August's EC-Karte bill, note #57's row, was the only live row that changed). Lovable prompt pasted by the owner and verified by bundle + cold drive; PROMPT-STATUS updated (#990).
- Item 95 + 116 (PR #993, v151): gated expense rows keep their category in the export (live CSV placeholders now equal grid open lines: July 3, August 2, were 7/14); sign-off copies merchant entries whole.
- Items 99 + 100 (PR #997, v152): `month_complete` + blocking counts beside `ready_to_post`; publish refused unless complete or `{"override": true}`, publisher recorded, classic runs refused, no frozen copy. Confirmed private receipts and decided copies close the receipt side.
- Item 94 (PRs #998 + #1009, v152/v155): one `decided_copies` predicate removes copies from grid count, totals, box counts, months list, CSV, PDF and cost-center roll-up; SPA-driven August reads 20 expenses = 19 categorized + 1 needs category, USD 2,033.86 / EUR 668.00.
- Pending prompts recorded (#1004); backlog headings and the p1 status row marked shipped in this checkpoint's PR.

## What Did NOT Work (and why)
- **agent-browser for the consumer drive:** hung past the 180 s timeout again; headless Playwright with `channel="chrome"` drove the gate cold in about 20 s.
- **First Playwright drives:** timed out waiting for row text because the login form renders ~4 s after load; wait, fill, Enter, wait 8 s, reload the route.
- **`pytest -n auto`:** xdist is not installed in the module env; the run exited on the flag and tested nothing.
- **Multi-line `regress_check --replace` literal:** matched 0 times on CRLF files; single-line literals work.
- **Background agents running the full suite in the background:** two of three ended their turn and stalled until resumed with SendMessage; brief agents to run it in the foreground.

## Current Status
Backend v155 carries all six changes. Pending paste: `lovable-ready-publish-gate-prompt.md` and `lovable-copies-out-of-totals-prompt.md` (handed in chat). Until pasted, August's lower totals show without the "copies set aside" line. brisken platform: unknown plan (no ops section).

## Next Steps
1. Owner ruling: count gray "já no recurring" charges as closed (recommended), or Criss marks July's 24 already posted one by one.
2. After the paste: bundle-audit both prompts by field names (list in PROMPT-STATUS Not applied) and drive July/August cold; move both rows to Applied.
3. Next audit defects without rulings: 96, 97, 101, 102, 103 (licence: defect, covered). Item 109 (confirm a receiptless guessed category) is new function, quote separately.
4. Residuals named by agents: grid `books_as` skips the chart gate (no live row); decision-route `summary` omits header edits, so a private receipt reads as needing a charge until the run refetch.

## Files to Read First
- workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md
- workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md (private card, month_complete, copies)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 94-136)

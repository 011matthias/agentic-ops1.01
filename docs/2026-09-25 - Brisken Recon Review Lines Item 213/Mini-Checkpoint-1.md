# Mini-Checkpoint: Brisken Recon Review Lines Item 213

**Date:** 2026-09-25
**Status:** Item 213 backend live (`c5a426aa`); SPA half pending the owner's paste; loop queue empty
**Type:** mini

---

## Summary
Owner note #87 ("TONE IT DOWN; COMPRESS WHATEVER") is answered on the backend: four review lines are shorter and 47 live rows changed exactly as predicted. The waiting line the owner saw is written by the published SPA itself, so the visible fix waits on `lovable-short-review-lines-prompt.md`.

## What Was Done
- PR #1393 (merge `c5a426aa`, Fly deployed, `/healthz` commit proven): `waits_for_statement` names the cards only when one or two wait (`service.WAITS_NAMED_MAX`), otherwise "No card on this receipt, and no statement is loaded for its date yet."; `date_outside_period` 191 -> 123, `suggested_private` 233 -> 157, `needs_entity_settled_outside` 173 -> 104 characters, every instruction kept. `review.waits_for_statements` unchanged. Tests `tests/test_reason_copy_item_213.py` (6, two route-level); `regress_check.py` TEST BITES; suite 3620 passed / 2 skipped; CI green.
- Live, read-only: census over all seven months before and after; prediction from the GET payload matched on all 47 rows (31 waiting, 14 suggested private, 1 date, 1 settled outside), 0 mismatches, every other reason count identical.
- Scripted cold drive (headless Chrome, read-only, only non-GET the login): September's 13 waiting rows still render the SPA's own 284-346 character line; July's date line renders the new sentence in EN and PT; September's 3281 group's Assign select ends with "Private card of..." (item 208 Follow-up 1 live, recorded by sibling #1398).
- PR #1400 (merge `b033e051`): backlog item 213 SHIPPED + Shipped row 133; PROMPT-STATUS moves `lovable-case9-status-prompt.md` (bundle + drive), `lovable-no-card-vendor-guard-prompt.md` and `lovable-merchant-accounts-per-company-prompt.md` (bundle only) to Applied; the new delta joins Not applied.
- Memory: usability-loop entry on who owns a review sentence, the CSS-uppercase `innerText` trap, and the ledger race.

## What Did NOT Work (and why)
- **A backend-only fix for the line the owner flagged:** the case-9 status prompt was already published and the SPA composes `waits_for_statement` from `review.waits_for_statements` with its own copy (`reviewReason()` in `ExpensesReviewGrid.tsx`); backend prose is only the fallback for codes with no SPA key.
- **Drive checks keyed on `innerText` for strip headings:** the headings are CSS-uppercased ("CARDS BY NUMBER"), so the open-check never matched, and re-clicking "Review" toggled the strip shut; `textContent` plus the group's own text works.
- **Merging the record PR after a single CI wait:** four sibling merges into `p1-improvement-backlog.md` / `PROMPT-STATUS.md` landed during CI (Shipped rows 131 and 132 taken); repo auto-merge is disabled, so only merge-main, push, tight poll, merge-on-green worked.

## Current Status
Backend live. No live row waits on one or two cards, so the named form has no live case. Feedback store holds 87 notes; nothing after #87. Brisken ops status: unknown plan (no `platform` section in infrastructure.yaml).

## Next Steps
1. Owner: paste `automations/expense-reconciliation/docs/lovable-short-review-lines-prompt.md`; then bundle-audit `expx.review.reason.waits_for_statement_many` and cold-drive September (13 rows read the short line, EN + PT) and July's settled-outside row.
2. Loop queue is otherwise empty: no continuation prompt written (session loop step 9).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-short-review-lines-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 213

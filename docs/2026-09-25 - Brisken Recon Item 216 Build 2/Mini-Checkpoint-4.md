# Mini-Checkpoint: Brisken Recon Item 216 Build 2

**Date:** 2026-09-25
**Status:** Step 3 live (PR #1455, Fly `2b6eeb7f`); SPA prompt written, not pasted. Item 216 Build 2's queue is empty.
**Type:** mini

---

## Summary
Both month payloads now say who answered each category: `summary.categories_by_origin = {person, rule, suggestion, none}`. The blocker `n_charges_category_guessed` deliberately kept its meaning, because its 0 / 0 / 1 was correct.

## What Was Done
- **Cause stated before code:** the payloads had one category count, and it answers "does a guess still block the month" (items 99 + 100). Measured on the 03:05 backup, the 164 receiptless guesses sit on 25 yellow (booked), 61 gray (recurring), 76 receipt-owing charges and 1 fee line (the 1). July's 45 are all yellow or gray.
- **Structure:** `service.row_answer_origin` / `categories_by_origin` read each row's own `posting_category` / `suggested_category` (built from `answer_origin` / `is_suggestion_only`). A row counts once, under its least decided answer. The split sums to `rows[]` (run) and `n_expenses` (grid; a decided copy and a bill are in no split). One call per summary; `month_readiness.charge_category_guessed` docstring now says it counts blockers, not guesses.
- **Measured after (backup):** both payloads equal the rows on all three months. Run view 0/11/68/41, 0/7/109/27, 0/1/43/7; grid 0/9/27/34, 0/4/27/19, 0/1/31/36 (person / rule / suggestion / none, Jul / Aug / Sep). Blocker and `month_complete` unchanged.
- **Tests:** `tests/test_counts_by_origin_item_216_build2_step3.py` (2 route-level: upload with a Stripe invoice+receipt copy, a move to Bills, a Confirm; a statement with open / ruled / gray / yellow charges plus the charge category PUT, whose reply carries the split) + `test_view_contract.py::test_categories_by_origin_partitions_the_rows_each_payload_counts`. Five wiring points bite under `regress_check`. Suite 3865 passed, 2 skipped; CI green; merged `b15a2639`; deployed via `deploy.py`.
- **Live, read-only:** `/healthz` `2b6eeb7f`; September grid split 0/1/31/36 = rows, sums to 68; run 0/1/43/7 = rows, sums to 51; blocker 1, need_receipt 28. Cold SPA drive (replayed payloads, both API hosts): 87/87 Expenses rows, Matching renders, 0 error boundaries, 5 fulfilled, 0 writes aborted.
- **SPA half:** `docs/lovable-categories-by-origin-prompt.md` + `PROMPT-STATUS.md` row. Backlog item 216 "Build 2 step 3" + Shipped row 139; api-contract "Who answered: `categories_by_origin`"; status file row updated.

## What Did NOT Work (and why)
- **Widening `n_charges_category_guessed` to every guess (the prompt's wording):** not built. July's readiness pill would have read "45 categories are still the tool's guess" on charges already booked (the 2026-09-17 gray ruling says those block nothing), and August/September would list 76 charges twice beside "still need a receipt" (the SPA's `monthBlockers` renders both).
- **Copy exclusion under `regress_check`, first pass:** TEST DOES NOT BITE. No fixture held a decided copy in the grid, so dropping the exclusion changed nothing. Adding a Stripe-named invoice + receipt pair (the tool decides the copy itself) made it bite.
- **Expecting `n_charges_need_receipt == 1` in the run-view test:** it is 2. The rule-answered FIGMA charge owes a receipt too; the code was right, the expectation wrong.

## Current Status
Step 3 is live and correct on both payloads; the SPA ignores the new field until its prompt is pasted. **Owner action outstanding from step 2:** `docs/lovable-model-suggests-prompt.md` is NOT applied (sibling audit 13:50 UTC: reported pasted, the SPA repo and bundle carry none of its keys), so Confirm stays hidden on suggestion rows (36 in September). Nothing written on Criss's months. brisken ops: platform unknown plan; comms-log none.

## Next Steps
1. **Owner:** re-paste `docs/lovable-model-suggests-prompt.md` into Lovable and publish, then paste `docs/lovable-categories-by-origin-prompt.md` (both can go in one publish). After publish: bundle grep for `expx.suggestion.label`, `sum.byOrigin.label`, `categories_by_origin`; cold drive of September with replayed payloads.
2. Item 216 remaining levers (backlog table): lever 1 (per-company account map) waits on Dirk's 7 questions and the owner's call on the three gated vendors; 1b registry aliases (operator edits for the non-gated names).
3. Re-run `tools/recon-categorization-score.py` after the next Zoho re-pull to judge Builds 1-3 by right answers.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216 "Build 2 step 3, built" + Shipped row 139
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "Who answered: `categories_by_origin`"
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (the two item-216 rows)

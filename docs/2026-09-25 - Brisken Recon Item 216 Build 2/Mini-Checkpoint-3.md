# Mini-Checkpoint: Brisken Recon Item 216 Build 2

**Date:** 2026-09-25
**Status:** Step 2 live (PR #1451, Fly `e3f0eb1f`); step 4 Lovable prompt merged, not pasted (PR #1452); step 3 handed to a fresh session
**Type:** mini

---

## Summary
On a GL month the model's account is now a labelled suggestion everywhere and posts nowhere until a person confirms it. The SPA prompt that shows the suggestion and its Confirm button is written and merged; the owner still has to paste it.

## What Was Done
- **One predicate, one cell.** `matching.types.is_suggestion_only(cat)`: the model's answer (LINE / VENDOR) whose category is a curated leaf code (`curated_leaves.leaf`), which is what a GL category is. `posting_common.SUGGESTED_PREFIX = "suggested: "`, `suggested_cell`, `is_suggested_cell`. Bucket-era months are untouched by construction.
- **Views:** `_row_categories` returns `(posting_category, suggested_category)`; both payloads carry the parallel `suggested_category` (ABSENT when none), grid `books_as` parts carry `suggested: true`; item 70's proposed candidate returns the pair; the variance chip reads both fields.
- **Review:** `_TRUSTED_SOURCE` and `_COARSE_SOURCE` retired. The row reads `answer_origin` per line; a GL model line is `check` / `model_suggestion`, confirmable (`_CONFIRMABLE_CATEGORY_CODES`). The grid's coarse token (`override` / `registry` / `learned` / `llm` / `review`) is derived from `answer_origin`, wire unchanged.
- **Files:** `expenses.csv`, the statement sheet (replaces `(confirm)` on GL months), `report.xlsx` (label, yellow, on Needs Review, source `LINE (suggestion)`), `reconciled.csv` (AI and Charge account cells), the reconciliation PDF. `zoho.accounts.resolve_account_id` and the journal check (`idempotent.py`) refuse the cell as `unresolved_placeholder`.
- **Found on the way:** `apply_overrides` (and the hand-typed expense) stamped a person's answer `LINE`, the model's tier; under the new rule her pick and a Confirm would have printed `suggested:`. Both read `EDITED` now.
- **Measured on the 03:05 backup, after:** 85 model-only expenses print `suggested:` (27 / 27 / 31), 0 read `ready` (32 moved), 80 confirmable (5 have an open line, `pick`), one Confirm restores the account (grid `origin: person`, `ready`). Run view: 68 / 109 / 43 suggestion rows, no posting carries one.
- **Tests:** `tests/test_model_suggests_item_216_build2_step2.py` (7; three route-level). 11 wiring points bite under `regress_check`. 9 older tests re-pinned (engine answer = suggestion); `REVIEW_REASON_CODES_PIN` + `model_suggestion`; api-contract section added. Suite 3862 passed; CI green; merged; deployed via `deploy.py`.
- **Live, read-only:** `/healthz` `e3f0eb1f`; September grid 36 suggestion rows, all `posting_category` null, 13 `model_suggestion` + 23 `vendor_guess`, all confirmable; cold SPA drive (replayed payloads, both API hosts, 5 fulfilled, 0 writes aborted): Expenses 87/87 rows, no error boundary; Matching renders.
- **Step 4 (ahead of step 3, see Current Status):** `docs/lovable-model-suggests-prompt.md` + its `PROMPT-STATUS.md` row (PR #1452). Backlog item 216 "Build 2 step 2" paragraph + Shipped row 138.

## What Did NOT Work (and why)
- **"Not one of the eight bucket names" as the GL test:** 24 suite failures. Older fixtures use free-form categories ("Software", "Travel") that are neither bucket names nor codes, so the negative test called them GL. The positive test, `curated_leaves.leaf(category) is not None`, is the definition of the GL vocabulary; 16 real-code fixtures remained, all the ruled change.
- **A heredoc with a Python triple-quoted block** to batch-edit `report_xlsx.py`: blocked by the heredoc gate (as the prompt warned). Edit calls instead.
- **`report.xlsx` assertion on the whole workbook:** did not bite under `regress_check` (the card tab carries the same label). Asserting per sheet ("Unmatched") does.

## Current Status
Step 2 is live and correct in every file. **Live gap until PR #1452's prompt is pasted:** the published grid reads `posting_category.category` for its Keep/Confirm button, now empty on suggestion rows, so the one-click Confirm is hidden on them (36 in September); the picker still works and a hand pick posts. That gap is why step 4 went before step 3. Nothing written on Criss's months. brisken ops: platform unknown plan; comms-log none.

## Next Steps
1. **Owner:** paste `docs/lovable-model-suggests-prompt.md` into Lovable (and `docs/lovable-model-picked-parent-prompt.md`, #1449), then a cold drive of September with a replayed payload: "Suggested" badge + "Confirm <account>" on the suggestion rows, write aborted.
2. **Step 3 (fresh session):** summary counts split person / rule / suggestion; `n_charges_category_guessed` becomes a count of suggestions (today 0 / 0 / 1 because it excludes need-receipt and gray rows while 77 of 164 guesses sit on open rows). Contract + view-contract move together; one PR, route-level test, regress_check, deploy, drive.
3. Add the step-3 count fields to a follow-up SPA prompt once step 3 lands (the step-4 prompt covers the label only).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216 "Build 2 step 2, built" and Shipped row 138
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "The model suggests, a rule or a person decides"
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`_row_categories`, `_matched_category_review`, `resolve_review`, the summary counters near `n_charges_category_guessed`)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-model-suggests-prompt.md`

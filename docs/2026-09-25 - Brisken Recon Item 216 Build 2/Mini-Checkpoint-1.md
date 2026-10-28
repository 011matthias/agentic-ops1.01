# Mini-Checkpoint: Brisken Recon Item 216 Build 2

**Date:** 2026-09-25
**Status:** Step 1 live (PR #1447, Fly `2820e33c`); step 2 measured and ruled by the owner; steps 2-4 handed to a fresh session
**Type:** mini

---

## Summary
The model no longer gets parent accounts to choose from, and a parent it names anyway is refused; people and rules keep them. The step-2 cost to `expenses.csv` was measured and put to the owner, who chose a labelled suggestion.

## What Was Done
- Parents are read from the chart's parent NAMES (`curated_leaves.has_postable_children`), pinned per company: Cloud 11, Consulting 11, Corporate Services 13. The sizing's prefix test was wrong on four accounts per company: `E600010-10-20` is a leaf, while `E600010-20` (CRM travel) and Corporate Services' roots `E100000` / `E500000` are parents.
- `llm_leaf_labels` offers 53 / 51 / 55 accounts. `_gl_model_result` refuses a parent with the new code `model_picked_parent` (pin, api-contract and English `reason` in place).
- Tests: `tests/test_model_offered_leaves_item_216_build2.py` (4, two route-level: a receipt upload and a GL month's charges, where the merchant list's parent and Criss's parent pick stand). Both wiring points bit under `regress_check`. Helpers in 8 older test files that picked `sorted(postable_codes)[0]` (now a parent) pick a leaf. Suite 3744 plus the 8 green; CI green; merged `2820e33c`; deployed via `deploy.py`.
- Live, read-only: `/healthz` `2820e33c`; the picker still lists parents (Corporate Services 68, `E500010` and `E100000` present); September's grid and the published SPA rendered 87/87 rows from a replayed payload (guard matched both API hosts: 2 fulfilled, 0 writes aborted, 7 light GETs passed).
- Step 2 sizing on the 03:05 backup: model-only expenses in `expenses.csv` are July 27 of 77 (USD 2,434.80, EUR 157.00, BRL 1,126.00), August 27 of 53 (USD 1,715.28, EUR 212.00, BRL 565.98) and September 31 of 70 (USD 2,018.72, EUR 458.79). No expense mixes model lines with rule or person lines. There are 0 overrides in the store and the poster is not wired to the app. 32 read `ready` today, 48 are one-click confirmable.
- Owner ruling: a model-only line prints `suggested: <account>` (the poster refuses it), the 32 `ready` rows move to `check`, and one click on Confirm (`inherited`, never taught) restores a posting.

## What Did NOT Work (and why)
- **Parent test by code prefix (the sizing script):** four wrong per company, because codes are not paths (`E600010-10-20-*` are CRM travel children of `E600010-20`).
- **First branch test, positional (`child.branch[:len(parent.branch)] == parent.branch`):** branches are truncated chains built from whichever tab first marked the child postable, so the roots differ (`OpeEx` vs `MS | OpeEx`). It found 6 parents where there are 11. The fix: a parent's name, any org's wording and entity prefix stripped, appearing anywhere in a postable account's branch.
- **First CI wait:** PR #1447 conflicted with main (sibling backlog edits), so no checks ran and `gh pr checks --watch` returned "no checks" at once. Merging origin/main resolved it.
- **Closing the turn with the PR waiting on CI:** the stop hook flagged it. Wait in the same turn, then merge, deploy and verify.

## Current Status
Step 1 live. At each month's next natural re-match, stored model parent picks on receiptless charges (23 / 34 / 1) are re-asked with leaf-only labels. Receipt lines (17 / 5 / 21) keep their parent until re-categorized; step 2 will label them as suggestions. brisken ops: platform unknown plan; comms-log none.

## Next Steps
1. Step 2 (fresh session, continuation prompt handed to the owner): on a GL month a model answer (origin suggestion) becomes `suggested_category` / `suggested_account`, never `posting_category`, on both payloads. `expenses.csv` prints `suggested: <account>`; the sheet, `report.xlsx`, `reconciled.csv` and the PDF label it; a LINE suggestion reads `check` and is one-click confirmable. Retire `_TRUSTED_SOURCE` / `_COARSE_SOURCE` for `answer_origin`. View-contract pins and api-contract move with it.
2. Step 3: summary counts split person / rule / suggestion; `n_charges_category_guessed` counts suggestions.
3. Step 4: SPA delta prompt (suggestion label on the grid and the workbench, `model_picked_parent`), four-backtick fence labelled "paste into Lovable".

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216 ("Build 2 step 1", "Build 2 step 2, measured before code") and Shipped row 137
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`_row_posting_category`, `_charge_category_view`, `_matched_category_review`, `_TRUSTED_SOURCE`, `_COARSE_SOURCE`, `category_confirmable`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/output/zoho_expense_export.py` (`expense_posting_parts`, `_debit_account_and_note`)

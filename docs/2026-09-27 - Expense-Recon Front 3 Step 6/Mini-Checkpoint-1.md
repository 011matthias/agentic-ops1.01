# Mini-Checkpoint: Expense-Recon Front 3 Step 6

**Date:** 2026-09-27
**Status:** front 3 queue empty; item 224 steps 6-8, item 115 and the owner's two settings writes done and live (PR #1481, Fly v264 `bc9daf45`); record PR #1485
**Type:** mini

---

## Summary
Closed front 3 of the 2026-09-25 round: receipts whose lines do not add up to their total are named (and a split one is sent to review), a Zoho-seeded rule may now decide a lined receipt, the two Lovable list entries are one, and the first per-company account map (34 accounts, Criss's 3+ single-account postings) is live.

## What Was Done
- Step 6 (`posting_common.line_sum_gap`, `LINES_DISAGREE_MARK`; `service.line_sum_note`, `_expense_review(split_lines_gap=)`, review code `line_sum_split`; export marker in `build_expense_row_groups`). Net-of-tax lines count as agreeing (16 live rows: Anthropic 180.00 + 34.20 VAT, Google). Predicted 13 / 9 / 10 rows on the 09-27 pull, one split (July Railway 0088, already `pick`); live on v264 the prediction held row for row, `n_review` 57 / 42 / 62 unchanged. Published SPA driven cold on July (guard fulfilled 2, aborted 0, no fallback strings).
- Item 115 (owner yes): `categorize._categorize_one_gl` `leads = recall is not None and (not has_lines or not judge_each_receipt)`; `_gl_learned` still flags `learned_over_line`. GL path only; the bucket path and its pinned test are unchanged.
- Tests: `tests/test_line_sum_224.py` (8, route-level incl. the reviewer's per-line account picks and `expenses.csv`), `tests/test_seeded_rule_leads_115.py` (4, GL month through the Memory route + `zoho-seed` restamp). Five `regress_check` proofs bit. Local suite 3973 passed; CI green twice.
- Lovable merge (owner yes): live read showed every Lovable row already naming "Lovable Labs" since v262; only a receipt whose extracted brand reads "Lovable Labs Incorporated" still hit the second entry. Readiness 9/9, one PUT, 34 -> 33 entries, read back.
- Step 8: offline resolver reproduces the server's `merchant` on all 314 charge rows; live list 85 exact / 10 fuzzy / 2 descriptor / 217 none, write-plan list 151 / 17 / 3 / 143. Steps 4-5 turned 62 live rows from a pre-filled suggestion into "pick an account" (27 `account_vendor_specific`, 35 `model_picked_parent`).
- Item 216 map (owner chose "3+ postings only" via AskUserQuestion): 34 accounts on 32 new list entries, readiness 8/8, read back equal; live 15 receipts + 43 charges now read a rule answer.
- SPA delta folded into the pending `docs/lovable-identity-live-prompt.md` as item 4.

## What Did NOT Work (and why)
- **Registry probe via `MerchantRegistry.from_settings(merchants_map)`:** returned None for every name incl. the exact "Lovable Labs"; `from_settings` takes the whole settings dict (`{"merchants": ...}`). Caught because the probe could not tell two lists apart.
- **First `gh pr merge 1481`:** "merge conflicts"; siblings merged docs rows (#1482/#1483) into `p1-improvement-backlog.md` while CI ran. Merge origin/main, keep both Shipped rows, re-run CI, merge in its own Bash call (pattern `warn-merge-chained-after-any-command`).
- **Counting charges by `posting_category.source == "registry"` on the run payload:** matched 0; the run payload spells the source differently. The `stamped` + `origin: rule` count (43) is the one to use.
- **Line-sum count without tax:** 48 rows, 16 of them net-priced lines that do add up; the map's 12 / 11 / 12 came from older payloads.

## Current Status
Live on Fly v264. Queue empty. brisken platform: unknown plan (infrastructure.yaml has no assessment).

## Next Steps
1. Owner: paste `docs/lovable-identity-live-prompt.md` (items 1-4) into Lovable; then `uv run tools/lovable-bundle-audit.py` for `account_vendor_specific`, `category.stamped.was`, `expense.line_sum.note`.
2. Dirk (via the owner): the 11 questions in `context/drafts/account-map-questions-to-dirk.md` gate the plan's remaining 12 accounts (9 two-posting, 3 majority) and Google Workspace / Cloud; Lovable and Consulting accounts stay with him.
3. Watch: about 41 unsure receipts take a seeded rule's answer at their next categorization; the `learned_over_line` flag marks where their lines disagree.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 224 (record paragraph) and Shipped row 146
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` last section
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-identity-live-prompt.md`

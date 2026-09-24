# Mini-Checkpoint: Brisken P1 Item 3 GL Engine Swap

**Date:** 2026-09-24
**Status:** Item 3 merged (PR #1281, `267588dc`), NOT deployed; items 4-6 queued
**Type:** mini

---

## Summary
`resolve_posting_account` now has production callers. Any batch whose config carries `gl_entity_orgs` is categorized straight into its entity's curated GL leaves, and a refusal carries a named reason up to the review Criss reads.

## What Was Done
- `categorize.py` GL engine (`_categorize_one_gl`, `_gl_learned`, `_registry_gl`). Learned rule, registry and model all answer through `resolve_posting_account`. The model gets `llm_leaf_labels(org_id)` as its only choices, and an empty list refuses.
- `coa_provision.entity_org_ids` / `org_id_for_entity` build the label→org map: settings first, then `/data`. `apply_to_config` injects `gl_entity_orgs` for every hosted batch. The map is threaded through the CLI, the web restore / add / re-match call sites and `categorize_charges`. ER adjudication is skipped on the GL path.
- `Categorization.refusal` (serialized only when set). New codes `entity_missing` and `not_expense_relevant`, with reviewer sentences in `posting_resolution.refusal_text`, re-exported via `categorize` so the web layer imports no `zoho.*`.
- UI: `_refusal_review` gives receipt lines and receiptless charges `reason_code: category_refused` + `refusal`. `category_refused` was added to the view-contract pin.
- 3c: `POST /api/runs/{id}/categories` clears on ""/null (human, both values) and drops unknown strings under `ignored`.
- `tests/test_gl_engine.py` (17 tests). `regress_check` bites at 4 wiring points. Module suite 3255/2. CI 8/8 green.

## What Did NOT Work (and why)
- **`pytest -n auto` baseline run:** xdist is not installed in the module env, so it was a usage error and no baseline ran. The full suite was run once without `-n`.
- **Heredoc-with-triple-quotes to patch `categorize_charges.py`:** blocked by the heredoc gate (as the brief warned). Used Edit.
- **Test fixture "code postable in Cloud, marked N in Corp":** no such code exists in the 194-leaf asset. The cross-entity case shows up as absent-from-org (`no_such_code_in_org`), so the fixture was generalized.

## Current Status
Merged, not deployed (the deploy waits for the owner's SPA bundle, which must read leaf codes and localize `category_refused`). Live read-only B7 findings, not fixed (owner data):
- Settings `Brisken Corp Services, LLC` has org `8227416528` (a typo for `822741658`).
- `Consulting` (9 live receipts) has no org id in either source, so its receipts refuse.
- 129 live receipts have a blank entity and would refuse `entity_missing`.

Categorization is fixed at ingest, so setting a company later does not re-categorize the expense.

## Next Steps
1. Item 4: delete `category_accounts.py`, lift `NON_LEAF`/`OUT_OF_SCOPE` into `resolve_account_id`, and rewrite `tests/test_zoho_category_accounts.py`, all in one change.
2. Item 5: remove all three copies of the category leak (`posting_common.py:137`, `sheet_writeback.py:143`, `:186`).
3. Item 6: relabel `categorization_gate.py` and validate item 184.
4. Before deploy: owner decisions on re-categorizing after an entity change, the Corp Services org-id typo, and a Consulting org id (808232536 is curated).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md` (Status block)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/categorize.py` (Direct-to-GL engine section)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_gl_engine.py`

# Mini-Checkpoint: Recon Learning Leaks And 194 Leaf Taxonomy

**Date:** 2026-09-24
**Status:** Queue items 1-2 of 6 shipped (PR #1277, merge `bb2ba8f5`, not deployed)
**Type:** mini

---

## Summary

Closed the three publish-time learning leaks the owner's "only corrections may
be memorized" ruling left open, and recompiled the GL taxonomy to 194 postable
leaves after his SPOT-CHECK flip. Items 3-6 of the queue (the engine swap and
its follow-ons) are untouched, and item 3 is materially bigger than the brief
implies.

## What Was Done

- **Leaks 1 and 2** (one cause): an override row stored a category with no
  record of who put it there, so the note-#62 Confirm and an account-only PUT
  both reached sign-off looking like reclassifications. New
  `category_overrides.category_source` (`human` | `inherited`), **required and
  keyword-only** at the store so a future writer cannot teach by omission; NULL
  reads as human so already-reviewed months keep teaching. Provenance travels
  through an undo (via the history line's `detail`, not the compared value the
  undo guard tests for equality) and a cross-month move.
- An inherited category is dropped at capture and gets **no vote** in the
  item-183 conflict test. Her ACCOUNT still teaches, via a new `keep_category`
  mirroring `keep_account` (binding NULL on INSERT too, or "leave the category
  alone" would have written one the first time a vendor was seen).
- **Leak 3**, the other direction: `apply_self_confirmations` writes
  `decided_by=tool` and BOTH alias/FX learners filtered on status alone. One
  `reviewer_confirmed_tx_ids` helper now serves both call sites. The brief named
  one site; there were two.
- **Taxonomy 199 → 194** (BCS 64 / BTS 62 / CorpServ 68, revision 2026-09-24,
  sha `800c0887`). Flip lives in `derive_expense_relevant.py` keyed by
  `(tab, name)`, runs last, clears `spot_check` with the verdict. JB row reason
  corrected from "intercompany" to contractor cost, named narrowly so other
  `Support BRISKEN` rows keep the label they earn.
- **Measured** (read-only against the live Fly volume, `immutable=1`): 6 `tool`
  / 2 `reviewer` / 1 NULL confirmed decisions over 7 runs, so alias+FX learning
  input drops 9 pairs → 3. Live `vendor_alias` and `merchant_fx` are both **0**
  (`merchant_category` 108), so the leak taught zero durable rows and the fix
  costs nothing today.

## What Did NOT Work (and why)

- **`regress_check` on the helper alone would have passed the undo fix.** The
  first draft read `detail["category_source"]` where the ledger key is
  `old_category_source`, so an undo would have silently promoted a model guess
  to her word. Every helper-level assertion passed; only the route-level test
  caught it.
- **Module-scoped enumeration of the count assertions.** I grepped the module's
  own `tests/` and updated `test_curated_leaves.py`, but
  `tools/tests/test_pull_brisken_zoho_coa.py` pins the same per-org counts
  (the pull uses the compiled taxonomy as its answer key) and lives outside the
  module suite. Local module run and ruff both passed; CI's enforcement-hook job
  went red on 67 != 64. Fixed in `0da7c8c6`; the repo-wide grep is what would
  have caught it, and `preflight-hooks.py --full` after touching `tools/` is
  what the ship rule already asks for.
- **`flyctl ssh console` with default stdin, and with a ~3.4KB `-C` payload.**
  The first hung past 10 minutes (needs `< /dev/null`); the second returned
  silently with exit 0 and no output. A ~1.1KB payload worked.
- **Heredocs for Python edits.** Two gate blocks (a triple-quoted block, then a
  119-line payload). Both correct; switched to Write/Edit.

## Current Status

`origin/main` @ `bb2ba8f5` carries items 1-2, verified present on main
(`CURATED_REVISION = '2026-09-24'`, `POSTABLE_COUNTS` 64/62/68,
`CATEGORY_SOURCE_INHERITED` and `reviewer_confirmed_tx_ids` both resolve).
Module suite **3233 passed / 2 skipped** (baseline 3216 + 17 new);
`tools/tests` **2020 passed / 2 skipped**; ruff clean; all 8 CI checks green.
Four `regress_check.py` mutation points each turn a route-level test red.

**Not deployed.** The brief gates a deploy on the owner publishing the SPA, so
Criss's live tool is unchanged. `category_source` is additive and breaks no
grid shape.

brisken platform: unknown plan, ~?/? ops/mo, last assessed unknown — run
`/ops-audit brisken`.

## Next Steps

1. **Item 3, the engine swap** — likely a session of its own.
   `zoho/posting_resolution.py::resolve_posting_account` is fully built and
   tested with **zero production callers**; the live path is still
   `zoho/category_accounts.py::category_account_code` via
   `zoho/accounts.py:42`. Carries 3a (`bool(cat.category)` False iff refused),
   3b (refused rows `category = None`, never `"(assign)"`), 3c (explicit clear
   vs `ignored`), the `categorize.py:704/746/771` handoff of
   `curated_leaves.llm_leaf_labels` in the SAME commit, and the UI refusal copy
   so Criss stops seeing a false "No category yet."
2. **Item 4** — delete `category_accounts.py` and lift `NON_LEAF` /
   `OUT_OF_SCOPE` (`coa_gate.py:94-95`) into `resolve_account_id`
   (`zoho/accounts.py:121`), same change.
3. **Item 5** — the three copies of the category leak:
   `output/posting_common.py:137`, `sheet_writeback.py:143`, `:186`.
4. **Item 6** — relabel `categorization_gate.py`, validate item 184
   (`paid_through_account_id`).
5. Two status files are stale and were NOT touched, having no bearing on this
   session: `p2-product-decks.md` (63d), `p2-targeting.md` (64d).
6. brisken comms-log is 16 days stale (last touched 2026-09-08).

## Files to Read First

- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/posting_resolution.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/accounts.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/learning/capture.py`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_learning_leaks_provenance.py`

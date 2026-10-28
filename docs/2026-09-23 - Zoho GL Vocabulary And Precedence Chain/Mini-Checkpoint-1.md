# Mini-Checkpoint: Zoho GL Vocabulary And Precedence Chain

**Date:** 2026-09-23
**Status:** Phase 1 steps 1-3 shipped plus the chain; nothing deployed, nothing calls the chain
**Type:** mini

---

## Summary

Took the direct-to-Zoho-GL categorization work from "the taxonomy exists but
nothing can store or show a leaf code" to "every write path takes both
vocabularies, the leaves are served to clients, and the chain that picks one
or refuses is written and unit-proven". Four PRs merged (#1236, #1238, #1239
plus the backlog commit inside #1238).

## What Was Done

- **#1236, accept-and-drop.** Six write paths refused anything outside the
  fixed eight. `category_vocabulary.recognize` is now the one gate: a bucket
  stays itself, a curated leaf code stays itself, a `"CODE name"` label
  reduces to its bare code, anything else answers None and is DROPPED and
  named under `ignored` rather than refused. Org-blind on purpose (a code
  means the same account everywhere, a name does not), so a bare account name
  is never recognised.
- **The sixth path the brief did not name.** `learning_cli.cmd_set` writes the
  same `merchant_category` table the chain reads first, so a curated leaf could
  not be seeded from the CLI. Widened, but deliberately still REFUSES an
  unrecognised value rather than dropping it: no wholesale round-trip to break,
  and a silent no-op on a typed argument is worse feedback than an error.
- **#1238a, serving.** `gl_accounts` + `gl_revision` beside `categories` and
  `category_options` on four surfaces. Keyed by entity label; an uncovered
  entity is ABSENT rather than served an empty list. Both keys joined
  `SETTINGS_DERIVED_KEYS`, without which adding them would have broken every
  round-tripped save, which is the exact failure #1236 removed.
- **#1238b, the chain.** `zoho/posting_resolution.py`: learned rule -> deferred
  trip branch -> model's pick -> refusal. Pure, called by nothing yet.
- **#1238c + #1239.** Backlog items 182-184 filed; the architecture doc's
  status line brought current.
- **Verification.** Six `regress_check` runs, each watched green -> red ->
  green, every one biting through a caller rather than a helper. Module suite
  3102 -> 3134 passed / 2 skipped.

## What Did NOT Work (and why)

- **Stacking item 2 on the same branch as item 1 after #1236 squash-merged.**
  PR #1237 went `CONFLICTING`: the branch still carried #1236's own commit
  while main carried its squashed equivalent, so the same content existed
  twice. Fixed by cherry-picking the two later commits onto a fresh branch off
  `origin/main` (clean, exit 0) and closing #1237 with the reason. The general
  lesson: after a squash-merge, a follow-up must branch from the new main, not
  continue the merged branch.
- **A heredoc carrying a Python triple-quoted payload.** Blocked by
  `heredoc-size-gate`, correctly; pivoted to the Write/Edit tools. Not friction.

## Current Status

`origin/main` = `f659ac9d` plus #1239. Module suite 3134 passed / 2 skipped
locally, which IS the gate (CI does not run this module's pytest). Nothing is
deployed. The engine still classifies into the eight buckets;
`posting_resolution` is reached only by its own tests.

brisken platform: unknown plan, ops/mo not assessed. comms-log 15 days stale.

## Next Steps

1. **Backlog item 183 first**, before converting the engine:
   `registry_upserts_from_expense_run` fires on Publish rather than a
   deliberate save, and its conflict check compares category only, never
   `zoho_account`. The conversion is the step where the chain starts writing
   through it.
2. **Step 4, convert the engine** to call `resolve_posting_account`. Decide the
   invariant explicitly first: `bool(cat.category)` is False if and only if the
   row is REFUSED, which makes all 17 truthiness gates read correctly with zero
   edits.
3. **In the SAME change that deletes `category_accounts.py`**, lift
   `coa_gate.classify_account`'s `NON_LEAF` and `OUT_OF_SCOPE` into
   `resolve_account_id` (`zoho/accounts.py` 121-218 checks neither today).
4. **Kill both copies of the category leak**: `posting_common:137` and,
   inline, `sheet_writeback.py:143` and `:185-186`. Grep `cat.zoho_account or
   cat.category`, not the function name.
5. **Relabel `categorization_gate.py`** and regress-check it; it currently
   measures the retired vocabulary through keyword stubs.
6. Watch for the registry going INERT (`merchant_registry.resolve:435`,
   `categorize.apply_registry_category:281`), which fails silently at full LLM
   cost.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/posting_resolution.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/category_vocabulary.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 182-184)

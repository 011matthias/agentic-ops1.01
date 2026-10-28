# Mini-Checkpoint: Zoho GL Item 183 Half B

**Date:** 2026-09-24
**Status:** Item 183 half B shipped and merged; half A is an owner decision; the engine conversion is next and unstarted
**Type:** mini

---

## Summary

Backlog item 183's account half shipped (PR #1259, merge `f10edaa9`): a
disagreeing posting account is now a conflict in both learners that write
durable memory, and a category-only teach no longer nulls a learned account.
Item 183's other half was NOT done, because verifying its premise showed it
would partially reverse a live owner ruling.

## What Was Done

- **Item 183 half B, wider than filed.** The item named only the settings
  registry. The identical defect sat in `_learn_categories`, which writes
  `learning/store.merchant_category` -- Tier 1 of the direct-to-GL chain,
  consulted AHEAD of the registry. Fixing only what was filed would have left
  the guess in the layer that outranks the layer fixed, so the prerequisite
  would have read as complete while not being complete.
- Four behaviours landed: account disagreement refuses the merchant (new
  `skipped_account_conflict` count); the same rule in the Tier 1 learner;
  `record_merchant_category` gains the `keep_account` guard its operator twin
  always had; `PlannedWrite` carries kwargs and `apply_plan` replays them.
- **Absence is not disagreement:** a row naming no account is silent, so the
  first account NAMED wins over rows naming none. An already-stored account is
  deliberately LEFT STANDING on a conflict, because the registry carries no
  provenance on `zoho_account` and a clear could not tell a value Dirk typed
  from one a run learned. The new count is what keeps that visible.
- Five wiring points proven RED under `regress_check.py`. Suite 3171 -> 3177
  passed / 2 skipped. Ruff clean on CI's exact command.
- **Owner ruling recorded in memory:** the Zoho `expenses.CREATE` grant is NOT
  authorized for production. `project_brisken_zoho_books.md` had been carrying
  the opposite reading ("treat it as an owner re-consent"); it now says the
  scope's presence on the token must never be read as permission.

**Three corrections to the inherited brief, each on a validated instrument:**
baseline was `5ebfedfb` not `ff8c1a53`; suite baseline 3171/2 not 3156/2; the
conversion's test blast radius is **70 of 244** test modules, not "126 of 236"
(68 bucket literals + 4 symbol imports; grep proven against a known positive
and a nonsense-pattern negative control).

## What Did NOT Work (and why)

- **Item 183 half A as filed ("put the upsert on a deliberate save"):** not
  done, deliberately. Its premise that "nobody chose to teach anything" is
  false. `web/service.py:15555-15562` records an owner ruling of 2026-09-16
  that moved the write ONTO Publish precisely because the deliberate-save
  button had been pressed zero times and the live store held 0 learned
  entities and 0 field corrections. Doing it would revert to a mechanism
  measured at zero use. Owner's call, written up in backlog 183.
- **First `apply_plan` regression proof:** `regress_check` returned
  `TEST DOES NOT BITE` -- the suite stayed green with the fix disabled.
  Investigating showed `apply_plan` is exported but has **no caller anywhere**
  in `src/` or `tests/`, so "bite through the caller" is vacuous for it. Fixed
  by adding a direct round-trip test labelled helper-level-by-necessity rather
  than dressed up as a caller drive.
- **Running ruff before the last edit instead of after it.** CI failed in 11s
  on ruff F601, a duplicate dict key: a patch script doing sequential string
  replacements had its first replacement create a fresh occurrence of the
  pattern the second replacement then matched. The pre-count was taken before
  any replacement, so it could not see it; Python allows duplicate keys (last
  wins) so pytest stayed green. One extra CI round trip. The transferable rule
  is to re-run the linter after the FINAL edit of a change, not after the first
  batch.
- **`gh pr merge --delete-branch`:** failed with "'main' is already used by
  worktree". Known false-FAIL (`reference_repo_tooling_gotchas`) -- the merge
  succeeded server-side; `gh` failed only on the local checkout afterwards.
  Verified via `gh pr view --json state`.

## Current Status

`origin/main` = `f10edaa9`. Nothing deployed: the engine still classifies into
the eight buckets and `resolve_posting_account` is still called by nothing
(verified this session, not assumed). Item 183 is no longer a blocker for the
conversion.

brisken platform: unknown plan, ~?/? ops/mo, last assessed `?` -- consider
`/ops-audit brisken`. comms-log 16 days stale.

Worktree `agentic-ops1-glconv` pruned and its branch deleted.

## Next Steps

1. **Convert the engine** to call `resolve_posting_account`. Decide contracts
   2a/2b/2c BEFORE writing code. Note `categorize.py:768-771` is a MEMBERSHIP
   gate against the eight buckets sitting upstream of all 17 truthiness gates,
   so `:704`/`:746` and `:771` must move in one commit. Unresolved tension: under
   2b a refused row reads as uncategorized in the headline count Criss steers
   by, and `_matched_category_review` shows it "No category yet. Assign one
   before this charge can post," which would be false.
2. Lift `NON_LEAF` / `OUT_OF_SCOPE` into `resolve_account_id` in the same
   change that deletes `category_accounts.py` (verified: the resolver checks
   neither today; unblocked now the chart is complete).
3. Kill the three leak sites: `output/posting_common.py:137`,
   `sheet_writeback.py:143`, `:186`.
4. Relabel `categorization_gate.py` (confirmed in neither pin file, no active
   optimize run).
5. Item 184 `paid_through_account_id` at `expense_post.py:827` (+`:885`/`:926`).
6. Owner: decide item 183 half A.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 183 (the
  full half-A case and what half B shipped)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/posting_resolution.py`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_registry_account_conflict_item_183.py`

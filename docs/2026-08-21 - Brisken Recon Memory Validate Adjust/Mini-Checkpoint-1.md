# Mini-Checkpoint: Brisken Recon Memory Validate Adjust

**Date:** 2026-08-21
**Status:** Round 6 of the 8-PR feedback wave shipped, deployed, live-probed
**Type:** mini

---

## Summary

Learned-memory validate/adjust (Theme D, note 10) shipped as PR #565 and
deployed: the 103 learned categories are now editable per row
(count-preserving), deletable per row (aliases/FX stay), and reviewable
(validation stamps + a needs-review filter), and reset requires
confirmation with a side-effect-free preview. Live store migrated in
place; the full probe round-tripped self-cleaning.

## What Was Done

- PUT /api/memory/categories: HTTP twin of CLI `memory set` — category
  validated against EXPENSE_CATEGORIES, vendor normalized,
  count-preserving; an absent zoho_account key preserves the learned
  posting account (review catch: a category-only edit was silently
  wiping what the COA gate depends on).
- DELETE /api/memory/categories (single row, 404 when absent);
  POST /api/memory/categories/validate (bulk, deduped);
  GET /api/memory?unvalidated=1 review filter; validated/validated_by
  on category rows.
- Schema migration validated_at/validated_by: idempotent AND
  race-tolerant (review catch: two connections racing the first
  post-deploy open would 500 the loser).
- Review HIGH pinned: ANY write that changes category/account CLEARS
  the validation stamp — a seed-zoho re-run or run re-teach can never
  wear an old human sign-off; unchanged re-confirmations keep it.
- POST /api/memory/reset requires {"confirm": true}; bare POST answers
  a would-delete preview and touches nothing (CLI dry-run parity).
- Suite 1210/2 (+11 tests); calibrate OK; PR #565 CI-green merged,
  deployed. Live probe (self-cleaning): 103-row store migrated, UTIL
  probe row PUT → validated → excluded by the filter → reset preview
  104 with nothing deleted → DELETE → store back to exactly 103.
- Clean review findings worth keeping: no consumer branches on
  decision_count/source_run (manual-set rows get full Tier-1 trust);
  exact-match lookup semantics untouched.

## Current Status

Feedback wave: rounds 1-6 of 8 shipped (#555/#556/#559/#561/#563/#565).
Six Lovable prompts wait on the owner; `lovable-memory-edit-prompt.md`
is REQUIRED — the deployed SPA's Reset button is a safe no-op (200 +
ok:false) until applied. Remaining rounds: language + receipt
visibility (Themes E+F), Cards R4 (owner answers pending).

## Next Steps

1. Language + receipt visibility round (plan Themes E+F).
2. Cards R4 after owner answers (backlog item 10); item 18 rides the
   next code round.
3. DOM-probe the SPA after any Lovable publish.

## Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md
- workspace/clients/brisken/status/p1-improvement-backlog.md
- ~/.claude/plans/looks-like-there-is-keen-aurora.md (Themes E+F design)

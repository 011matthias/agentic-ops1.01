# Mini-Checkpoint: Brisken P1 Item 4b Curated Export Gate

**Date:** 2026-09-24
**Status:** Phase 1 code complete on main (items 3-6 + 4b), NOT deployed; the deploy waits only on the owner's SPA bundle
**Type:** mini

---

## Summary
On a GL batch the export's chart gate now judges a curated org by Dirk's
marking, as the engine and the API poster already do (PR #1305,
`175f697e`), and the deferred Phase 1 comms-log sweep is written.

## What Was Done
- 4b: `cli._build_coa_gate` sets `CoaGate.curated_org` when the config
  carries `gl_entity_orgs` (the engine's `is not None` test), including the
  per-entity form hosted batches use; `classify_account` then judges by the
  marking in the resolver's order (`NOT_EXPENSE_RELEVANT`,
  `OUTSIDE_CURATED_LIST`, `CHART_ORG_MISMATCH`).
- Measured read-only on the real chart + local provisioning (scratch script):
  before, 56 of 194 Y diverted (23/11/22) and 105 N passed on BOTH batch
  kinds; after, GL 0 / 0, bucket still 56 / 105.
- 12 tests incl. a bucket pin against a pre-4b-built gate and a gate vs
  `resolve_account_id` agreement test over every sheet account in all three
  orgs; 6 wiring points RED first. Suite 3282 -> 3294 / 2. CI 8/8, merged.
- Live bundle audit (tool's own crawl + controls, fields swapped inline):
  `category_refused`, `gl_accounts`, `gl_revision` all ABSENT, controls
  present, so the owner has not published and nothing was deployed.
- Comms-log sweep appended to `context/comms-log.md` (INTERNAL decision
  record, 2026-09-24); memory `project_brisken_comms_sweep_deferred` deleted
  since its trigger fired.

## What Did NOT Work (and why)
- **`test_coa_provision` / `test_mixed_entity_export` as written under 4b:**
  `apply_to_config` has injected `gl_entity_orgs` since item 3, so their
  synthetic codes (`E500`, `C100`) in real curated org ids became GL batches
  and refused `OUTSIDE_CURATED_LIST`. They pin the chart rule, so they now
  drop the key after injection (what a pre-Phase-1 batch config is).

## Current Status
On main, NOT deployed: #1277, #1281, #1286, #1291, #1295, #1302, #1305. The
comms log's routine staleness ask applies again from the next checkpoint
(the deferral is gone). No deterministic gate measures the GL chain.

## Next Steps
1. When the owner says the Phase 1 SPA bundle is published: re-run the
   bundle check (`category_refused`, `gl_accounts`, `gl_revision` present),
   then deploy from a clean detached `origin/main` worktree and drive the
   consumer cold (a GL-batch row renders its leaf, a refusal renders
   localized).
2. Item 190 step 4 once the owner says the card-scope prompt is pasted.

## Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (Items 4-6 and 4b paragraphs)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md`

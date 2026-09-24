# Mini-Checkpoint: Brisken P1 Item 6 Gate Relabel And Paid Through

**Date:** 2026-09-24
**Status:** Queue item 6 + backlog item 184 merged (PR #1302, `373a65dc`), NOT deployed; item 4b next
**Type:** mini

---

## Summary
`categorization_gate.py` now says it measures the bucket path only, in its
report and in calibrate's JSON, and the paid-through card is resolved
against the target org's chart before any Zoho payload is built.

## What Was Done
- Gate relabel: report prints `CATEGORIZATION ACCURACY, BUCKET PATH` and
  `GL path (batches with gl_entity_orgs): NOT measured by this gate`;
  `calibrate --json` carries `path: bucket`, `gl_path_measured: false`;
  `measure()` passes `entity_orgs=None` explicitly. A test spies
  `_categorize_one` and makes `_categorize_one_gl` raise.
- Item 184: `zoho.accounts.resolve_paid_through`, called from
  `build_expense_payload` after the unassigned-cell guard. Refuses
  `paid_through_unresolved` for non-numeric, blank, not in the org's chart,
  inactive, DO NOT USE, not `credit_card`, and id/name naming two cards
  (`reconcile_month._plan_kwargs` now passes `card_name`). Payload carries
  the chart's id. `ChartOfAccounts.by_account_id` added.
- regress_check RED first at 7 wiring points; differential: breaking the GL
  chain's no-client refusal leaves the gate suite green (as labelled).
- Module suite 3267 -> 3282 passed / 2 skipped; CI 8/8 green; merged.

## What Did NOT Work (and why)
- **The brief's module baseline of 3263:** origin/main after #1295 is 3267;
  #1293 (item 190) added 4 tests the figure did not include. Use 3282 as the
  baseline now.

## Current Status
On main, NOT deployed: #1277, #1281, #1286, #1291, #1295, #1302. Deploy still
waits on the owner's SPA bundle (leaf codes + `category_refused`) and on 4b.
No deterministic gate measures the GL chain; that is stated, not fixed.

## Next Steps
1. Item 4b: on GL batches only (cfg carries `gl_entity_orgs`, built in
   `cli._build_coa_gate`), judge curated orgs in `coa_gate.classify_account`
   by the same marking the resolver uses; pin bucket-batch verdicts
   byte-for-byte with a test; caller test + regress_check; PR; merge on green.
2. Then the ONE deferred comms-log sweep: items 3-6 are all on main as of
   #1302, so its trigger has fired (8 buckets retired, 194-leaf taxonomy,
   Tier 2 ruled out, the two master-data fixes, item 5's "everywhere").

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/coa_gate.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/output/zoho_expense_export.py` (`gated_for_posting`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cli.py` (`_build_coa_gate`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/accounts.py` (`_postability_refusal`)

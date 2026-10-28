# Mini-Checkpoint: Brisken P1 Item 4 Category Table Retired

**Date:** 2026-09-24
**Status:** Item 4 merged (#1291, `f20326f7`), not deployed. Items 5 and 6 next; new item 4b found.
**Type:** mini

---

## Summary

`zoho/category_accounts.py` is deleted and `resolve_account_id` now judges
postability per org: Dirk's curated marking in the three curated orgs, the
chart's parent rule elsewhere. The literal lift of `coa_gate`'s NON_LEAF /
OUT_OF_SCOPE was measured wrong before it shipped, and the same measurement
exposed that the export COA gate contradicts the curation (item 4b).

## What Was Done

- B7 enumeration repo-wide: the only code importer was `zoho/accounts.py`
  (plus the table's own test file); the rest were docs.
- Measured the premise. 35 of the 194 postable curated accounts are chart
  PARENTS (11 BCS, 11 BTS, 13 CorpServ). Zoho accepts parent postings:
  `zoho-books-24mo.json` holds 8 real expenses on parents (1 Cloud, 7
  CorpServ), and the 09-22 silent default `Office Infra and Admin` is a
  parent.
- Resolver: new reasons `account_is_a_parent` (uncurated org / no org),
  `account_not_expense_relevant`, `account_outside_curated_list`,
  `chart_disagrees_with_org` (chart id for a code != curated id for the
  target org). `ResolvedAccount.via_category` and
  `REASON_CATEGORY_CODE_MISSING` removed.
- Four posting fixtures (`currency_and_vendor`, `statement_currency`,
  `synthetic_references`, `reconcile_month`) named bucket labels as the
  account; now they name the same account the table produced.
- `tests/test_zoho_account_postability.py` (10, through `plan_expense_post`).
  regress_check: postability call disabled -> 6 red; curated branch sent to
  the chart rule -> 4 red. Module 3254 passed / 2 skipped; preflight --full
  clean; CI 8/8 green.
- Docs: runbook Account resolution rewritten + retirement note; architecture
  doc finding closed, 4b recorded, Tier 2 heading/lines now "ruled out";
  `posting_resolution.TIER2_DEFERRED` comment carries the owner ruling.

## What Did NOT Work (and why)

- **Lifting `coa_gate.classify_account`'s NON_LEAF as written:** it treats
  every chart parent as unpostable, which would refuse 35 of 194 accounts
  Dirk approved; Zoho demonstrably accepts parent postings.
- **First history probe keyed on `account_id`:** the 24-month pull carries
  only `account_name`, so every row read "not in chart" (a blind
  instrument); re-keyed on name.
- **The background baseline suite:** edits landed mid-run, so its result
  was meaningless; stopped and replaced by the post-change run
  (3260 - 16 + 10 = 3254, matched exactly).

## Current Status

Item 4 on main, not deployed (deploy still waits on the owner's SPA bundle
that reads leaf codes). **Item 4b, new:** the export COA gate
(`coa_gate.classify_account`, run with `keep_category=True` in
`zoho_expense_export.gated_for_posting`) uses the chart-parent rule plus the
provisioned `scope_groups`; against the live provisioning it diverts 56 of
the 194 postable accounts (23/64 Cloud, 11/62 Consulting, 22/68 CorpServ),
`COGS - DEV Infrastructure` included, and passes some N accounts. On a GL
batch it blanks those accounts before the resolver sees them. Must land
before any GL-mode deploy; bucket-era months should keep today's verdicts
(key the curated gate on `gl_entity_orgs` in `cli._build_coa_gate`).
brisken platform: unknown plan, ops unassessed.

## Next Steps

1. Item 5: the three category-leak copies (`output/posting_common.py:137`,
   `sheet_writeback.py:143`, `:186`); truthiness gates must not flip.
   Update `status/p1-expense-reconciliation.md` (item 4 done, 4b) on that
   client branch.
2. Item 6: relabel `categorization_gate.py` + regress-check; validate item
   184 (`paid_through_account_id`, `zoho/expense_post.py`).
3. Item 4b (above), one PR, curated gate keyed on GL mode.
4. After 3-6 (+4b) are on main: the one deferred brisken comms-log sweep.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/accounts.py` (`_postability_refusal`)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md` (item 4 finding + 4b)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/coa_gate.py` (for 4b)

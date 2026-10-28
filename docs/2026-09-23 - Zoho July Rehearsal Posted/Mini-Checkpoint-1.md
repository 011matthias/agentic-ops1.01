# Mini-Checkpoint: Zoho July Rehearsal Posted

**Date:** 2026-09-23
**Status:** July rehearsal posted and readback-verified in TEST-BTS; Gap 2 (currency) next
**Type:** mini

---

## Summary

The month-end injection went from 0 postable to 13 posted and verified in
the TEST-BTS sandbox: a per-org category-to-account map closed Gap 1, and
the 13 USD July purchases tie out to $30,864.42 field by field on readback.
Gap 2 (34 non-USD rows) is now reachable without re-consent, because the
sandbox vault credential carries `settings.READ`.

## What Was Done

- **Diagnosed Gap 1 precisely** rather than by symptom. The category was
  sitting in the account column because
  `posting_common._debit_account_and_note` passes
  `cat.zoho_account or cat.category` through when no chart is loaded, and
  the July export took that branch. Proof is a code path plus the absence
  of any `(account unmapped - assign)` in the export, not the shape of the
  data.
- **Shipped `zoho/category_accounts.py`** (PR #1193, `f4f31d32`): per-org
  category to GL **code**, consulted only after `resolve_ref` fails, so a
  vendor rule still wins. Production orgs deliberately unmapped.
- **Posted 13 of 13 to TEST-BTS** (PR #1194, `93ca41c0`) under owner
  greenlight, then readback-verified each by id. Stored total exactly
  $30,864.42; every line's `account_id` matches what was sent, splits of
  2, 3 and 5 lines preserved.
- **Proved the readback can fail** — six corruptions of a real stored
  record (account, amount, date, reference, dropped split line, card) all
  caught, control clean.
- **Confirmed both duplicate defenses** fire independently: ledger refuses
  all 13 on re-plan; month occupancy flipped `CLEAR` to `ALREADY_OCCUPIED`.

## What Did NOT Work (and why)

- **First category-to-account table mapped three categories to PARENT
  accounts** (`Professional Fees` E600060, `Travel Expense` E100010,
  `Marketing & Selling Expenses` E600010). Zoho posts only to leaf
  accounts; parents are roll-ups. `ChartOfAccounts.leaf_accounts` already
  encoded the rule and caught all three before anything posted. Now
  asserted by `test_every_shipped_mapping_targets_a_leaf_account`, with a
  companion test proving that assertion can fail.
- **Mapping `Travel & Transport` to any single leaf.** Its two July rows
  are gasoline and a vehicle rental, which want different leaves
  (E100010-01 vs E100010-36), and Travel Expense has no generic leaf. Left
  deliberately unmapped: a default wrong half the time is worse than a
  refusal that names the row.
- **Regenerating payloads for the readback via `plan_expense_post`.** It
  refused all 13 with `already_in_ledger`, because the ledger had just
  recorded them. Correct behaviour, wrong tool for the job: the readback
  uses `build_expense_payload`, which does not consult the ledger, and the
  refusal became a separate duplicate-guard assertion.
- **Sending `vendor_name` as text.** Zoho accepts it, returns 201, and
  stores nothing: 0 of 13 records carry `vendor_name` or `vendor_id`. The
  builder's comment claimed it "keeps the name visible"; measured false.

## Current Status

TEST-BTS org 822116290 holds 23 expenses: 10 pre-existing plus this run's
13. The durable post ledger lives at
`workspace/clients/brisken/context/zoho-post-ledger-testbts.sqlite` and
records all 13 as `posted`; posted ids are in `.scratch/july-posted-ids.json`.
Occupancy for 2026-07 on the test card now reports `ALREADY_OCCUPIED`, so a
re-run is blocked twice over.

Of the 46 July purchases: 13 posted, 32 refused on foreign currency, 1
refused as `(uncategorized - assign)` which must keep refusing.

brisken ops platform: unknown plan, last assessed unknown. comms-log 15
days stale (last touched 2026-09-08).

## Next Steps

1. **Vendor fix, riding with the currency slice** (owner call): fold the
   raw vendor name into `audit_note` so Criss has vendor visibility in the
   Zoho UI, and populate a numeric `vendor_id` if contact resolution is
   available.
2. **Gap 2, foreign currency**: owner greenlit using the sandbox
   `fullaccess.all` credential to pull `/settings/currencies` and unblock
   the remaining 32 EUR/BRL July rows.
3. Decide transaction-date vs statement-period selection for production
   (Criss). Zoho stored the 3 June-dated rows as June and coerced nothing,
   so the period is our selection's choice.
4. `workspace/clients/brisken/status/p1-expense-reconciliation.md` was NOT
   updated this session: a sibling session holds an uncommitted edit to
   that exact file on main, and editing it here would conflict. Fold this
   session's state in when that lands.
5. Two status files are stale past threshold: `p2-product-decks.md` (62d)
   and `p2-targeting.md` (63d).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md`
  (the runbook; carries the map, the rehearsal result and the vendor defect)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/category_accounts.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/expense_post.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`

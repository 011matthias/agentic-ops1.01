# Checkpoint: Zoho Month-End Posting Engine Proven

**Date:** 2026-09-23
**Status:** Sandbox rehearsal complete. 41 of 46 July purchases posted to TEST-BTS and readback-verified; the 5 refusals are with Criss.

---

## Summary

Dirk's month-end requirement went from "nothing in July is postable" to a
proven posting engine in one session: 41 of 46 purchases posted to the
TEST-BTS sandbox and verified field by field at USD 56,340.44 exact. The
two gaps that blocked it turned out to be a code path nobody had read and
a Zoho billing tier, neither of which was the category-mapping problem
everyone assumed.

---

## What Was Done This Session

### Gap 1: the category-to-account map (PR #1193, `f4f31d32`)

1. Diagnosed the real cause. The `Expense Account` column held category
   names because `posting_common._debit_account_and_note` passes
   `cat.zoho_account or cat.category` through when no chart is loaded,
   and the July export took that branch. Proof is the code path plus the
   absence of any `(account unmapped - assign)` in the export, not the
   shape of the data.
2. Shipped `zoho/category_accounts.py`: per-org category to GL **code**,
   consulted only after `resolve_ref` fails so a vendor rule still wins;
   production orgs deliberately unmapped; maps to a code so the existing
   resolver still runs its active / DO-NOT-USE checks.

### The rehearsal (PRs #1194 `93ca41c0`, #1199 `ffc7df8c`)

1. Posted the 13 USD purchases, then 28 converted (10 EUR, 18 BRL).
2. Readback by id on all 41: every line's `account_id`, splits of 2, 3
   and 5 lines preserved, `paid_through` correct, audit envelope present,
   every converted row carrying its `Original:` tag.
3. Proved the readback can fail before trusting it: six corruptions of a
   real stored record (account, amount, date, reference, dropped split
   line, card) all caught, uncorrupted control clean.

### Gap 2 and the vendor fix (PRs #1197 `85f1540f`, #1199)

1. Found the export already carries an `Exchange Rate` column, populated
   on 12/12 EUR and 20/20 BRL rows and ignored by the builder. No FX
   service was needed.
2. Native-currency posting built, then blocked: TEST-BTS is
   `plan_name = 'FREE'`, which rejects any non-base currency outright.
3. Adopted the statement-currency house rule instead (owner call), with
   `_convert_lines` converting the total once and landing the residual on
   the largest line.
4. Vendor moved into the audit envelope after measuring that Zoho
   discards `vendor_name` entirely (0 of 13).

### The stale-date guard (PR #1199)

`period` + `stale_days` (default 45) refuses a purchase dated more than
45 days before the period's first day.

---

## Key Decisions Made

### Production orgs are unmapped by design

- **Choice:** `CATEGORY_ACCOUNT_CODES` holds the sandbox only;
  `test_no_production_org_is_mapped` is the tripwire.
- **Rationale:** which GL account a category posts to is an accounting
  decision that belongs to Brisken. An unmapped org refuses exactly as it
  did before rather than inheriting a sandbox guess.

### Post in the statement currency, not natively

- **Choice:** foreign receipts post as `amount x rate` in USD, with
  `Original: {cur} {amt} @ {rate}` in the note.
- **Rationale:** it is the house rule `posting_common` already states for
  the journal (the bank statement is what the company actually paid), and
  it walks around the FREE-plan limit rather than requiring an upgrade.

### `Travel & Transport` stays unmapped

- **Choice:** no default account for that category.
- **Rationale:** its two July rows are gasoline and a vehicle rental,
  which belong to different leaves, and Travel Expense has no generic
  leaf. A default wrong half the time is worse than a refusal that names
  the row.

### The Self Client credential posts, not the fullaccess one

- **Choice:** the sandbox `fullaccess` vault entry was used only for
  `GET /settings/currencies`; every write went through the Self Client
  grant.
- **Rationale:** CREATE + READ is all a post needs, and the narrower
  grant is what the production run will carry, so the rehearsal stays
  faithful to it.

---

## What Did NOT Work (and why)

- **Mapping three categories to PARENT accounts** (`Professional Fees`
  E600060, `Travel Expense` E100010, `Marketing & Selling Expenses`
  E600010): Zoho posts only to leaf accounts; parents are roll-ups.
  `ChartOfAccounts.leaf_accounts` already encoded the rule and caught all
  three before anything posted.
- **Native foreign-currency posting**: all 11 EUR expenses rejected 400,
  "Your current plan does not support creating Expense with any currency
  other than your organizations base currency". TEST-BTS is
  `plan_name = 'FREE'`.
- **`vendor_name` as text**: Zoho accepts it, returns 201 and stores
  nothing without a contact. 0 of 13 posted records carried a vendor.
- **Populating `vendor_id`**: TEST-BTS has 0 vendor contacts against
  July's 33 distinct vendors, so there is nothing to resolve against.
- **Growing the audit envelope without checking the field limit**: adding
  `Vendor:` and `Original:` pushed two descriptions to 523 and 630
  characters, and Zoho caps them under 500.
- **Regenerating payloads for the readback via `plan_expense_post`**: it
  refused all 13 with `already_in_ledger`, because the ledger had just
  recorded them. Correct behaviour, wrong tool.
- **Typing an expected total from memory** (125.42 against the planner's
  97.40): the tie-out assertion refused the run and posted nothing.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/zoho/category_accounts.py` | created | per-org category to GL code, fallback only |
| `src/expense_recon/zoho/accounts.py` | modified | `org_id` fallback, `via_category` provenance, `REASON_CATEGORY_CODE_MISSING` |
| `src/expense_recon/zoho/expense_post.py` | modified | currency map, statement conversion, stale-date guard, vendor in envelope, description cap |
| `tests/test_zoho_category_accounts.py` | created | 15 tests incl. the leaf-account assertion |
| `tests/test_zoho_currency_and_vendor.py` | created | 12 tests |
| `tests/test_zoho_statement_currency.py` | created | 18 tests |
| `docs/zoho-month-end-posting.md` | modified | the runbook; four sections added |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | modified | posting-engine element row |

---

## Current Status

TEST-BTS (org 822116290) holds 51 expenses: 10 pre-existing plus this
session's 41. Durable ledger at
`workspace/clients/brisken/context/zoho-post-ledger-testbts.sqlite`
records all 41 as `posted`. Occupancy for 2026-07 on the test card reads
`ALREADY_OCCUPIED`, so a re-run is blocked twice over.

Suite 2880 to **2925 passed, 2 skipped**. Six PRs merged: #1193, #1194,
#1196 (mini-checkpoint), #1197, #1199.

brisken ops platform: unknown plan, last assessed unknown. comms-log 15
days stale (last touched 2026-09-08).

---

## Next Steps

1. **With Criss** (owner is taking these): the 2 date-guard exceptions
   (ref `360172592` dated 2026-03-30; ref `00000031010` with an EMPTY
   date cell) and the 3 account-resolution refusals.
2. **Confirm the production orgs are on a paid Zoho tier** before
   assuming native-currency posting works there. The FREE-plan limit is
   believed sandbox-only but has not been checked.
3. **Production category-to-account mapping** needs Brisken sign-off
   before any production org joins `CATEGORY_ACCOUNT_CODES`.
4. Vendor contacts: filling `vendor_id` means creating 33 contacts, a
   write of a different kind that was out of scope here.
5. Per-org routing for the 5 cards across separate organizations; the
   rehearsal was one card.
6. `p2-product-decks.md` (62d) and `p2-targeting.md` (63d) are stale past
   threshold.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md`
- `.../src/expense_recon/zoho/category_accounts.py`
- `.../src/expense_recon/zoho/expense_post.py`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- Transaction date or statement period as the production selection rule?
  Zoho stored the June-dated rows as June and coerced nothing, so the
  choice is ours.
- Fix vendor attribution by creating contacts, or leave the envelope as
  the answer?
- Are custom fields wanted at all? They must be defined per org before
  import or they drop silently, as `cf_netting_key_exp` did.

### Working Notes
Posted ids are in `.scratch/july-posted-ids.json`,
`.scratch/july-converted-posted-ids.json` and `-2.json`. The July export
CSV is `.scratch/july-expenses.csv` (batch `50622baec444`, 54 expenses /
56 rows / 46 purchases).

Measured Zoho behaviours worth not rediscovering: `vendor_name` is
discarded without a contact; `description` must be under 500 characters;
only leaf accounts are postable; a FREE-tier org refuses any non-base
currency; `/organizations` with the sandbox fullaccess credential returns
exactly one org, so that credential cannot reach production books.

### Reference Materials
- Vault entry `Zoho API Brisken Sandbox` (org 822116290,
  `ZohoBooks.fullaccess.all`, includes `settings.READ` and
  `expenses.DELETE`).

---

## How to Continue

The posting path is proven end to end in the sandbox; the remaining work
is data and policy, not code. Resume with `/resume brisken`, read the
runbook's four 2026-09-23 sections, and pick up whichever of Criss's five
rows come back resolved.

---

## Strategic Feedback

### What Worked Well This Session

- **Proving the instrument before trusting it.** The readback passed 41
  of 41, which is exactly what the failed 2026-09-22 trial also looked
  like. Corrupting a real stored record six ways and confirming each was
  caught is what made the pass mean something.
- **Asking the chart instead of reasoning from names.**
  `ChartOfAccounts.leaf_accounts` caught three parent-account mappings
  that would have been rejected or misfiled. Every account pick after
  that came from the org's own data.
- **`regress_check` on the wiring, not the helper.** Five wirings were
  each disabled and watched go red. Two of them turned tests red that a
  helper-only suite would have left green.

### Suggestions

- **Enumerate an external field's constraints before changing what goes
  into it.** The 500-character description limit was discovered by a
  production-shaped POST, not by the suite, and it was introduced by this
  session's own envelope growth. A short "what are this field's limits"
  check at B7 time would have caught it before two rows failed.

### System Health

- The deny-by-default machinery was tested by real rejections for the
  first time rather than by tests, and held on every one: 13 rejections
  across two failures, every intent released, nothing written, no batch
  aborted mid-way, every retry possible without manual repair.
- **Autonomy: 0 corrections.** Six owner turns, all direction rather than
  correction; every error this session was caught by a guard, by the
  chart, or by Zoho before it reached a human.

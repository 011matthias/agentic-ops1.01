# Month-end posting into Zoho Books

Dirk needs the reconciled month imported properly into Zoho Books at month
end (owner direction 2026-09-22). The owner chose API injection over a CSV
hand-off, which reverses the 2026-08-22 "no ties to Zoho" directive; backlog
item 23 carries the reversal and the rounds it switches off.

The app is the matching engine. Zoho Books is the downstream ledger and
receives finished, pre-matched entries only. Nothing about that changes how
the month is reconciled; it changes only where the result lands.

## The one thing blocking live posting

**The Books refresh token is read-only.** Asked for its own grant, it
answers:

```
ZohoBooks.documents.READ ZohoBooks.expenses.READ ZohoBooks.bills.READ
ZohoBooks.accountants.READ ZohoBooks.settings.READ
```

No CREATE anywhere. Every posting path is built and tested against this
wall, and none of it can reach Zoho until the grant is widened. That is an
owner action in the Zoho console; an agent cannot consent on someone's
behalf.

### Widening the grant

Self Client flow, same client id and secret already in the gitignored
`workspace/clients/brisken/context/.env`. The scopes to request are the
current five plus:

| Scope | Why |
|---|---|
| `ZohoBooks.expenses.CREATE` | create the expense; this is the whole posting path |
| `ZohoBooks.contacts.READ` | resolve `vendor_id` from a vendor name |
| `ZohoBooks.contacts.CREATE` | create a vendor that does not exist yet, if we decide to |

Confirm the operation names against the console's own scope list before
consenting rather than trusting this table; Zoho renames occasionally.

Steps: Zoho API console, the existing Self Client, generate a grant code for
the scope list above with all 8 organizations in scope, paste it into
`ZOHO_BOOKS_GRANT_TOKEN` in `context/.env`, then exchange it for a refresh
token. The grant code, the client id and the refresh token are three
different strings and the grant code also starts with `1000.`, which is easy
to mis-paste.

Verify the result by reading the `scope` field off the token response, not
by attempting a write. A write that succeeds has already changed a client's
books.

## Why posting cannot be a hosted feature

`test_zoho_posting_is_gated.py` keeps the hosted web layer free of any Zoho
import or credential. Posting is an operator-run CLI action behind four
gates that must all be open: the `zoho.post.enabled` config flag, the
`EXPENSE_RECON_ZOHO_POST=1` environment flag, an explicit org allowlist, and
`--go`.

The reason is not tidiness. Criss works her months in the app, and
`feedback_recon_no_live_writes_criss_acts` says her data is hers to change.
If an HTTP route could post, a deploy could write into Brisken's live ledger
without anyone deciding to. Keeping the path in the CLI means a human ran it
on purpose, with the invasive-action gate in front.

## Not a feed problem, a handoff problem

The received wisdom in this repo was that Zoho holds these charges because a
bank feed puts them there. A read-only probe on 2026-09-22 says otherwise:
**0 of 39 sampled expense rows carry `imported_transactions`**, so nothing in
Books is linked to an imported bank transaction. The rows are hand-entered,
in catch-up bursts, weeks after the fact. Corporate Services' 108 July rows
were created across 13 days ending 2026-09-08, 45 of them on that last day.

So the duplicate hazard is not a feed to disconnect. It is that two parties
would be entering the same month. The handoff has to be explicit and agreed
with Criss before the first real post:

- **July is already entered.** 108 rows in Corporate Services, 10 in Cloud
  Services. It must never be injected.
- **August (5 rows) and September (9 rows) are barely started**, which makes
  them the clean first targets. The handful already there has to be matched
  or cleared first, not appended past.
- From the first injected month onward, Criss stops entering that month's
  card charges by hand. If both happen, the month doubles.

## What the TEST-BTS test actually proved

Read back off the sandbox (org `822116290`, card account
`4369050000000320002` "Visa dummy card Matthias") rather than from the test
summary:

| Claim | Verified |
|---|---|
| 9 expenses, 4,297.74 total | yes, to the cent |
| `reference_number` carries the bank key | yes, 9 of 9 |
| The AWS bill splits across two GL lines | yes: 2,400.00 ePaaS + 447.31 Other Infra, header `Itemized` |
| `cf_netting_key_exp` silently dropped when undefined | yes, absent on every row |
| Vendor blank when `vendor_id` is not sent | yes, 0 of 9 attributed |
| Audit string preserved in the description | **no, 7 of 9** |
| GL account selection | **6 of 9 fell back to `Office Infra and Admin`** |

The two failures are the design's real work. The audit envelope is missing
on exactly the split row, which is the structurally hardest case and the one
the summary held up as a success; the split path writes a different
description format (`Purpose: ... | ID: ...`) with no `[External Match
Audit]` block. And an account passed as a name rather than a numeric
`account_id` does not error, it silently defaults, so two charges in three
landed in the wrong expense account. On a real month that is the P&L
integrity the close is supposed to establish.

`cf_dn_repayment` did persist, but it is a checkbox and its value is `false`
on all 9 rows, so it survived as a field rather than as a data carrier.

## Account resolution

The chart of accounts is stable: refreshed from all 8 orgs on 2026-09-22 and
identical to the 2026-06-30 snapshot in 7 of them. The only delta was the
account the test itself created, which is what proves the refresh can see
change rather than reading blind.

Every org's chart carries `account_id`, so resolution is mechanical. It is
per-org: each legal entity is a separate Zoho organization with its own
chart, so a charge routes to an org first and an account second. The
existing COA gate already refuses an account that is inactive, non-leaf,
out of scope or marked "DO NOT USE", and posting reuses it rather than
growing a second opinion.

## Sandbox rehearsal in TEST-BTS

Owner direction 2026-09-22: decouple from the production blockers and the
Criss handoff by pointing integration testing at the sandbox org
**TEST-BTS (`822116290`)**, a clone of a production org. Real writes and
readbacks, no live books, July untouched.

`822116290` is now on `DEFAULT_ORG_ALLOWLIST` beside the two production
orgs. A run config can only ever INTERSECT that list, never extend it, so
admitting an org stays a reviewed code change; `test_zoho_org_allowlist.py`
pins both that property and the exact membership, so a fourth org fails a
test rather than passing quietly.

Nothing about a cloned org's id or chart announces that it is not
production. The only things keeping a real org out of a rehearsal are that
list and the `--org` the operator passes, which is why `SANDBOX_ORG_ID` and
`PRODUCTION_ORG_IDS` are kept as separate, disjoint sets.

### Rehearsing real months, starting with July

Owner direction 2026-09-22: empty the sandbox and rehearse real months,
July first. That exposed a flaw in the first cut of the occupancy guard,
now fixed.

**The standing July lock is production-only.** What makes July dangerous
is 118 rows a human typed, and those exist only in the production orgs. In
a clone July is empty, and it is the month most worth rehearsing because a
full month is the shape the tool has to survive. A global lock would
forbid exactly the rehearsal that de-risks the real run: a safety rule
protecting nothing, at the cost of the thing it exists to make safe. So
`LOCKED_PERIOD` now applies when `is_production_org(org_id)`, and a
sandbox run states in its verdict that the lock was waived rather than
skipping it silently. `ALREADY_OCCUPIED` is NOT waived for the sandbox: a
rehearsal that double-posts is still a bug, and catching it there is the
entire reason to rehearse.

`is_production_org` is a positive list, deliberately not "anything that is
not the sandbox". A typo'd or newly-cloned org must not inherit
production's protections by accident.

Driven live 2026-09-22, four cases through one instrument:

| Org | Period | Verdict | Why |
|---|---|---|---|
| TEST-BTS | 2026-07 | `CLEAR` | lock waived, clone holds no July rows |
| TEST-BTS | 2026-09 | `ALREADY_OCCUPIED` | the trial's 8 dummy-card rows |
| TEST-BTS | 2026-10 | `CLEAR` | never used |
| Corporate Services | 2026-07 | `LOCKED_PERIOD` | real books, refuses without an API call |

Three distinct verdicts is the differential that makes the `CLEAR`
trustworthy; a guard answering the same for all four would be blind
rather than correct.

### Emptying the sandbox

`zoho/sandbox_reset.py`. TEST-BTS holds **10 expenses, all ours** (every
one created 2026-09-21 or 09-22; the 2023 clone carried no expenses, and
bills and journals are both 0), so there is no inherited baseline to
destroy. Blocked only on `ZohoBooks.expenses.DELETE`; the dry run already
enumerates all 10 by id.

It is the one destructive path in the tool, so the guards are the module.
A clone is the dangerous case precisely because every signal that would
say "this is only a test" is missing: same chart, same account names, same
id shape. Therefore the org is asserted by equality against
`SANDBOX_ORG_ID` before anything is read, production is refused by name
rather than merely absent from a list, `execute_reset` re-asserts instead
of trusting the plan it was handed, deletion is by enumerated id with no
filter or bulk endpoint (`rule_brisken_graph_send_by_id`: a query that
decides what to destroy can match one row more than you meant), and the
report is `ok` only when a re-list confirms the org is empty, because a
200 per delete proves each call was accepted and nothing more.

## Built 2026-09-22

- **`zoho/accounts.py`** resolves a reference to a numeric `account_id` or
  returns a refusal naming why; there is no third branch and no default.
  Refuses on: empty reference, an export placeholder, a reference absent
  from this org's chart, a chart carrying no ids at all (the `from_csv`
  case), an inactive account, and one marked DO NOT USE. Resolution order
  is not re-derived; it comes from `posting_common.resolve_ref`, which the
  file exports also use, so the CSV a human reviews and the payload the API
  receives cannot disagree about which account a reference meant.
  Driven live against the TEST-BTS chart: 196 of 196 accounts carry an id,
  the four references the trial used resolve to four distinct ids, and
  `Meals & Entertainment` plus both placeholders refuse.
- **`zoho/occupancy.py`** refuses a month someone else already entered.
  The 4.8 ledger stops this tool re-posting but cannot see Criss, so this
  asks Zoho rather than our own records. `LOCKED_PERIOD` is a standing rule
  needing no call, scoped to production orgs (see the July rehearsal
  section); `ALREADY_OCCUPIED` is measured per run against the org, card
  and month, in every org including the sandbox; `UNVERIFIABLE` is what a
  failed query returns, because an unreadable month and an empty one must
  never take the same branch.
- **`zoho/orgs.py`** holds org identity as a leaf module, so the guard can
  ask whether an org is real books without importing the ledger (sqlite,
  the COA gate and the export writer come with it).
- **`zoho/sandbox_reset.py`** plus `client.delete_expense`, to empty
  TEST-BTS between rehearsals. Guards described in the section above.

## The posting path (`zoho/expense_post.py`)

`read_expense_csv` → `group_by_reference` → `plan_expense_post` →
`execute_expense_post`. It posts the reviewed CSV rather than rebuilding
from receipts, so what reaches Zoho is what someone approved.

**One receipt is one expense.** The CSV writes one row per ACCOUNT and a
split receipt's rows share a `Reference#`, so rows are grouped back into a
single itemized expense, which is the shape the trial produced (header
`Itemized`). A row with a blank reference never merges with another blank:
fusing on a shared absence would combine unrelated purchases into a record
that still ties out to the cent.

**The audit envelope has exactly one builder.** In the trial it was on 7 of
9 rows and missing on precisely the split, because the itemized path wrote
a different description format. Every payload now goes through
`audit_note`, and a parametrized test asserts it on both shapes.

**Refusals**, all deny-by-default: an account that does not resolve to a
numeric id; a blank amount (the export writes one when a receipt's total
was never read, and a blank is not a zero); a reference already in the
ledger; and any foreign-currency row, because Zoho wants a `currency_id`
rather than a code and the re-consented grant dropped `settings.READ`, so
`/settings/currencies` 401s and there is no way to resolve one. A plan
carrying any refusal refuses to post at all, since a partial post leaves a
month half-entered.

**Failure handling** follows the 4.8 shape: write-ahead `inflight`
committed before the POST fires, a clean 4xx releases the intent and the
batch continues (Zoho answered and wrote nothing), anything else marks
`ambiguous` and aborts the rest, because continuing past an unknown commit
turns one uncertainty into several.

### Do not post a test month into the sandbox

Without `ZohoBooks.expenses.DELETE`, **every month posted to TEST-BTS is
permanently occupied** and the occupancy guard will refuse it afterwards.
Posting synthetic rows into July to "try the loop" would burn the one
month we are preserving for the real rehearsal, and there would be no way
to clear it.

So the first real post is the real July data. Until then the loop is
exercised by its tests and by `plan_expense_post`, which resolves and
cross-references the ledger without touching Zoho.

## July dry run against TEST-BTS, 2026-09-23

Ran end to end: fetched the July batch's export from the live app
(`POST /api/login` for a bearer token, then `GET /runs/50622baec444/
expenses.csv`), pulled the TEST-BTS chart, checked occupancy, planned.
Posted nothing. Only Zoho org touched was `822116290`.

The batch has grown since the 09-10 note of 32 receipts: **54 expenses,
56 CSV rows, 46 purchases** (6 split across accounts). Occupancy for
2026-07 came back `CLEAR`, as designed.

**Result: 0 postable, 46 refused.** The tooling worked; the data is not
ready. Two independent gaps, and they do not overlap:

| | count |
|---|---|
| USD, account unresolved | 14 |
| account unresolved AND EUR | 12 |
| account unresolved AND BRL | 10 |
| account resolves, BRL blocks | 10 |
| **postable today** | **0** |

**Gap 1: 36 of 46 purchases carry no Zoho account.** The "Expense Account"
column holds the app's own CATEGORY taxonomy (`Software & Subscriptions`
x22, `Meals & Entertainment` x11, `Professional Services` x4, `Travel &
Transport`, `Equipment & Hardware`, ...). Resolved through the real
resolver against all 8 charts in the local snapshot, **none of those names
exists in any Brisken org**. Only `E100010-31 - Travel Expense | Food`
(x9) and `E100010 - Travel Expense` (x1) resolve. That is the fallback
echo item 23 already measured on the workbook (64 real GL codes of 341
cells, ~19%); this is the same ratio on the export, 10 of 56 rows. Closing
it is the merchant-registry / category-to-account mapping, not a posting
change.

**Gap 2: 34 of 56 rows are not USD** (USD 22, BRL 21, EUR 13). TEST-BTS is
a USD org and the poster refuses a foreign currency because Zoho wants a
`currency_id` and the re-consented grant dropped `settings.READ`. A
partial workaround exists and is worth knowing: currency ids can be
harvested from an org's OWN existing expenses (`currency_id` is on every
expense record), no settings scope needed. TEST-BTS currently yields only
`USD -> 4369050000000000097`, because every sandbox expense so far is USD,
so that route cannot cover EUR or BRL there yet.

**The two gaps are disjoint**, which is why the intersection is empty: all
10 rows carrying a real GL code are BRL, and all 22 USD rows carry an
unresolved category. So there is no subset of July that can be rehearsed
today, however the guards are configured.

A methodology note worth keeping: the first version of the account
diagnostic compared raw `account_name` strings and reported that even
`E100010-31 - Travel Expense | Food` was absent everywhere. That was the
instrument, not the data: `resolve_ref` also matches the `"CODE - name"`
label form by splitting the leading token as a code. Re-run through the
real resolver with a known-present control, two references resolved. A
name-only comparison fails in the dangerous direction, since it would have
sent someone renaming categories that were already fine.

## 2026-09-23, later: closing Gap 1 with a per-org category map

Gap 1 above turned out to have a more precise cause than "the categories
are not in the chart", and the precise version is what made it fixable.

**Why a category was sitting in an account column at all.** One branch in
`output.posting_common._debit_account_and_note` passes
`cat.zoho_account or cat.category` straight through when no chart is
loaded. So a receipt whose vendor has no account rule leaks its CATEGORY
into the account column. The July export took that branch: with a chart
the column can only ever hold a resolved chart name, `(account unmapped -
assign)` or `(uncategorized - assign)`, and the export has raw category
labels and not one `(account unmapped - assign)`. That is a code-path
reading, not an inference from the shape of the data.

So the category was a real signal being discarded, and the fix is to map
it rather than to re-categorize 36 receipts.

**`zoho/category_accounts.py`** holds a per-org table from the app's own
category to a GL **code**. Four properties are load-bearing:

- **Fallback, never override.** Consulted only after `resolve_ref` fails
  to match the reference as a code or a name, so a (company, vendor) rule
  that already picked an account still wins, exactly as the M1 registry
  design intends.
- **Keyed by org.** Brisken's own history is the reason: `anthropic`
  posts to different accounts under Corporate Services and Cloud
  Services. One global table would be wrong in some org by construction.
- **Production orgs are deliberately absent**, so an unmapped org refuses
  exactly as before rather than inheriting a sandbox guess. Which GL
  account a category posts to is Brisken's call; `test_no_production_org_is_mapped`
  is the tripwire.
- **Maps to a code, not an `account_id`.** The code goes back through the
  same `resolve_ref` the file exports use, so there is still one
  resolution order and the account still passes the inactive /
  DO-NOT-USE checks. It also sidesteps a name collision: two accounts are
  named `Other Expenses`.

**The leaf rule, which the first draft got wrong.** Zoho posts only to
leaf accounts; parents are roll-ups. The first version of the table
pointed three categories at parents (`Professional Fees`, `Travel
Expense`, `Marketing & Selling Expenses`). `ChartOfAccounts.leaf_accounts`
already knew the rule, and asking it caught all three before anything was
posted. `test_every_shipped_mapping_targets_a_leaf_account` now asserts
it, with a companion test proving that assertion can fail.

**The shipped table (TEST-BTS), each pick from data rather than from what
the name suggests:**

| Category | Code | Account | Why |
|---|---|---|---|
| Software & Subscriptions | E500010-30 | IT: Cloud Subscriptions-Others | the unbranded leaf; Microsoft / ZOHO siblings stay for vendor rules |
| Meals & Entertainment | E100010-31 | Travel Expense:Meals | the exact account the 9 already-resolving food rows post to |
| Professional Services | E600060-70 | Professional Fees > Other Expenses | July's rows are consulting, so the catch-all leaf under the right parent |
| Office Supplies & Consumables | E500030-20 | Office Supplies | direct |
| Equipment & Hardware | E500010-40 | IT: equipment, peripherals, phones, devices | direct |
| Marketing & Advertising | E600010-05-09 | Other Promotions and Advertising Channels | July's row is a 360Crossmedia listing, not channel ad spend |
| Utilities & Premises | E500030-60 | Utilities | direct |

**`Travel & Transport` is deliberately unmapped.** Its two July rows are
gasoline (POSTO ARCA DE NOE) and a vehicle rental (E A LOCACOES), which
belong to different leaves, and Travel Expense has no generic leaf to
hold both. A default wrong half the time is worse than a refusal naming
the row.

**Measured effect, live TEST-BTS, same script as the morning dry run:**

| | before | after |
|---|---|---|
| postable | 0 | **13** ($30,864.42) |
| refused: account unresolved | 14 | **1** |
| refused: foreign currency | 32 | 32 |

The single surviving account refusal is `(uncategorized - assign)` on
`G173514057`, which is the correct outcome: that marker means a human
still owes a decision, and `NEVER_MAPPED` keeps it refusing.

Verification was a `regress_check` on the wiring, not a green suite: with
`org_id` unthreaded from `plan_expense_post`, two caller-level tests go
red and return green on restore. A second run proved the leaf guard by
re-introducing the parent-account mistake.

**Worth flagging for month-end discipline:** 3 of the 13 postable
purchases are dated in JUNE (2026-06-30 x2, 2026-06-21) inside a batch
labelled "July 2026". Whether that is correct (a June transaction date on
a July card charge) or a boundary error is Criss's call, but a month-end
import should not decide it silently.

## 2026-09-23: the July rehearsal actually posted (13 rows, TEST-BTS)

Owner greenlight. Org 822116290 only; the Self Client credential was used
rather than the fullaccess one below, because CREATE + READ is all a post
needs and the real month-end run will carry the narrower grant, so the
rehearsal stays faithful to it.

**Posted: 13 of 13. Rejected 0, ambiguous 0, aborted false.**

Selection followed the send-by-id shape rather than "post the plan":
`execute_expense_post` refuses any plan carrying refusals, so the 13
references were named explicitly and **re-planned on their own**, giving
a plan with zero refusals instead of a filtered view of one holding 33.
Guards before `go`: sandbox asserted, production ids refused, count
`expect=13`, and a total tie-out to $30,864.42.

### Readback, by id, field by field

The accept code proves nothing here: the 2026-09-22 trial returned 201
with a valid `expense_id` on rows that had landed in the wrong account.
So each expense was read back from `GET /expenses/{id}` (the surface the
write lands on) and compared against the payload the builder produces.

**13/13 clean. Stored total $30,864.42, exact match.** Every line's
`account_id` matches what was sent, including the three splits (2, 3 and
5 line items), so itemization survived and nothing was re-defaulted.
`paid_through` is the card on all 13, and the `[External Match Audit]`
envelope is present on all 13.

**The readback was then proven able to fail**, because one that cannot is
not evidence. Corrupting each checked field in turn against a real stored
record: wrong account, wrong amount, wrong date, wrong reference, a
dropped split line, wrong paid-through card. All six caught; the
uncorrupted control passes clean.

### Both duplicate defenses fire, independently

- **Ledger:** re-planning the same 13 yields 0 postable / 13 refused,
  `already_in_ledger`.
- **Month occupancy:** `2026-07` went `CLEAR` to `ALREADY_OCCUPIED` after
  the post, naming the 10 July-dated rows on that card.

### Dates held; the period is ours to choose

The 3 June-dated rows (2026-06-30 x2, 2026-06-21) stored as June. Zoho
coerced nothing into the July period, so which period a row belongs to is
decided by our selection, not by Zoho. That is the fact the production
rule needs: filtering by transaction date and filtering by statement
period are both implementable, and the choice is Criss's.

### New defect: `vendor_name` is silently discarded

**0 of 13** posted expenses carry a vendor. Zoho accepts `vendor_name`
as text, returns 201, and stores nothing: every record reads back
`vendor_name=""` and `vendor_id=""`. The payload builder's comment
claimed this "at least keeps the name visible"; that was an assumption
and it is now measured false. The audit note does not carry the vendor
either, so **vendor attribution is absent from every posted record**.

This is the same silent-accept shape as the account defaulting: Zoho
neither rejects nor warns. Fixing it means resolving contacts to a real
`vendor_id`, or folding the vendor into `audit_note`. Not changed in this
slice, because it alters what posts.

### The sandbox credential is far wider than the Self Client grant

Vault entry `Zoho API Brisken Sandbox` (org_id `822116290`, org_name
`TEST`) mints a token carrying **`ZohoBooks.fullaccess.all`**. That
covers `expenses.DELETE` for automated cleanup, and **`settings.READ`**,
which is the scope the currency refusal says is missing. So Gap 2 is
reachable in the sandbox without re-consent. Note the scope is not
org-bound: only our own org guards keep it off production books.

## 2026-09-23: Gap 2 is a billing tier, not a scope or a bug

Owner greenlit the sandbox `fullaccess` credential for
`GET /settings/currencies`. The read worked, the code works, and the post
is blocked by something neither could fix.

### The export already carried the rate

The first finding cut the work in half. `EXPENSE_COLUMNS` has an
**`Exchange Rate`** column, populated on 12 of 12 EUR rows and 20 of 20
BRL rows, and the payload builder was ignoring it. So no FX lookup, no
rate service, no settings dependency for the rate: the reviewed CSV
already holds the rate a human approved, which is exactly what
"post the reviewed artifact" asks for. `build_expense_payload` now reads
it, and refuses (`exchange_rate_missing`) when a foreign row has none,
because Zoho would otherwise apply a rate nobody chose.

`currencies` (code to the org's numeric `currency_id`) is an injected
map, defaulting to `None`, so a caller that does not supply one refuses
foreign rows exactly as before. Deny-by-default survives the change.

### What the currency map showed

TEST-BTS defines 11 currencies: AED AUD CAD CNY EUR GBP INR JPY SAR USD
ZAR. **BRL is not among them**, and 20 of July's 46 purchases are BRL.
That is a config gap in the target org, so it gets its own reason code
(`currency_not_defined_in_org`) rather than being confused with missing
data.

Planning the whole batch with the map: **24 postable** (the 13 already
posted plus 11 new EUR), 20 refused on BRL, 2 on account. The second
account refusal is new only in the sense that it was previously masked:
the currency check ran first, so fixing currency uncovered it.

### The post was rejected, 11 for 11, by the subscription plan

> `Your current plan does not support creating Expense with any currency
> other than your organizations base currency.`

`GET /organizations` names it: TEST-BTS is
`plan_name = 'FREE'`. Multi-currency expenses are a paid-tier feature, so
**no amount of scope, config or code will post a EUR expense in this
sandbox.** Gap 2 cannot be rehearsed here at all, and that is true for
EUR, which the org defines, as much as for BRL, which it does not.

This is very likely sandbox-only. Brisken's production orgs run real BRL
and EUR operations, so they are on a paid tier; that should be confirmed
before the production run rather than assumed.

### The failure was the machinery working

Worth recording because it is the first time the guards were tested by a
real rejection rather than by a test:

- 400 is a clean rejection, so each intent was **released**, not left
  inflight: 0 of 11 references remain in the ledger, and a retry is
  possible the moment the block lifts.
- **23 expenses before, 23 after.** Nothing was written.
- Nothing was marked ambiguous, so the batch did not abort; it reported
  all 11 rejections rather than stopping at the first.
- The 13 USD rows from the earlier run are still `posted` and untouched.

### Blast radius of the fullaccess credential

`GET /organizations` with it returns **exactly one** organization,
822116290. So despite `ZohoBooks.fullaccess.all` being an unrestricted
scope name, this credential cannot see or reach Brisken's production
books at all. That is a stronger guarantee than the in-code org guard,
and independent of it.

### Vendor attribution restored

`audit_note` now carries `Vendor: {name}`, so a reviewer in the Zoho UI
sees the vendor even though `vendor_name` is discarded. It goes through
the one envelope builder, so splits carry it too; a blank vendor adds no
empty field. `vendor_name` is still sent, inert, so it starts working the
day contacts are resolved.

**`vendor_id` could not be populated.** TEST-BTS has **0 vendor
contacts**, and July names 33 distinct vendors, so there is nothing to
resolve against: filling it means CREATING 33 contacts, which is a write
of a different kind and was not in scope here.

## 2026-09-23: statement currency clears the batch, 41 of 46 posted

Owner call: adopt the house rule `posting_common` already states for the
journal. The bank statement is what the company actually paid, so a EUR
receipt on a USD card posts as `amount x rate` USD. That is both the
right answer for the books and the way past the FREE plan, which refuses
any expense in a non-base currency.

### What posted

| | count | |
|---|---|---|
| USD, posted 2026-09-23 earlier | 13 | $30,864.42 |
| EUR, converted | 10 | |
| BRL, converted | 18 | |
| converted subtotal | 28 | $25,476.02 |
| **total in TEST-BTS** | **41** | **$56,340.44** |

**Readback: 41 of 41 clean, tie-out exact.** Every line's `account_id`
matches, splits preserved, `paid_through` correct on all 41, the audit
envelope present on all 41, and every converted row carries its
`Original:` tag naming the source currency.

Refused, correctly: 3 `account_unresolved` and 2
`date_precedes_period_window`.

### Conversion details worth keeping

`_convert_lines` converts the TOTAL once and lands the residual on the
largest line, rather than rounding each line independently. Two lines of
10.005 round to 10.01 each (20.02) while the total rounds to 20.01, and
an expense that disagrees with its own line items by a cent is the kind
of wrong that survives review. Same allocation rule
`posting_common._posting_amounts` already uses.

`audit_note` gained `Original: {currency} {amount} @ {rate}`, so the
conversion is auditable from the record itself; without it the books show
a USD figure with no trace of the EUR or BRL receipt behind it. Rates are
the reviewed CSV's own, never fetched at post time.

`convert_foreign_to_base` defaults to False, so nothing converts unless a
caller opts in.

### The stale-date guard caught two, and the second was a surprise

`period` + `stale_days` (default 45) refuses a purchase dated more than
45 days before the period's first day. For 2026-07 the cutoff is
2026-05-17, which clears July's three legitimate June-dated rows and
refuses:

* **`360172592`**, dated **2026-03-30** (360Crossmedia, EUR 900). The
  outlier that prompted the guard.
* **`00000031010`**, whose `Expense Date` cell is **empty**. Not what the
  guard was built for, and the more interesting catch: without it that
  row would have posted with `date=""`. A date that cannot be verified is
  not posted.

### A defect this session introduced, caught by Zoho

Adding `Vendor:` and `Original:` to the envelope pushed two descriptions
over a limit nobody knew about:

> `Please ensure that the "Description" has less than 500 characters.`

Two Brazilian grocery receipts, whose itemisation runs 370 and 459
characters, came to 523 and 630. `audit_note` now caps at
`MAX_DESCRIPTION_CHARS = 499` by trimming **the receipt's own prose and
never the envelope**, with a `... (+N chars)` marker so the cut is
visible. The envelope is the audit trail; the prose is a line-item list
whose tail is the least load-bearing text in the record. Only 2 of 46
July purchases were ever over the cap, so no already-posted row drifted.

The rejection was clean again: both intents released, nothing written,
the batch reported both rather than aborting, and a re-run posted them.

### Two guards earned their keep this session

* The **tie-out assertion** refused a follow-up run because the expected
  total was typed from memory (125.42) instead of read from the plan
  (97.40). It posted nothing and named the difference.
* The **ledger** released every intent behind all 13 rejections across
  the two failures, so every retry was possible without manual repair.

## The runner: one command for the month end (2026-09-23)

`zoho/reconcile_month.py` composes the proven pieces into a single run.
Nothing in it re-derives resolution order, conversion math, the envelope
or a guard; each stage calls the function the sections above describe.

```
uv run python -m expense_recon.zoho.reconcile_month \
    --month 2026-08 --csv <reviewed export CSV> \
    --ledger workspace/clients/brisken/context/zoho-post-ledger-testbts.sqlite \
    --env-file workspace/clients/brisken/context/.env \
    [--org 822116290] [--card ID --card-name NAME] [--dry-run]
```

Run it from the app directory. `--csv` is the REVIEWED export (post the
reviewed artifact, never a rebuild). `--ledger` is the durable ledger and
is part of the guard: a fresh one would plan an already-posted month as
new. `--env-file` loads the gitignored credentials without overriding
anything already in the environment. Live posting also needs
`EXPENSE_RECON_ZOHO_POST=1`, the same deployment switch `zoho-post` uses;
without it the live path refuses before reading anything.

Stages, in order: ingest and group (`read_expense_csv`,
`group_by_reference`); occupancy (`check_month_occupancy` by card NAME);
chart pulled live (`ChartOfAccounts.from_api`, a CSV chart carries no
ids); plan (`plan_expense_post` with `convert_foreign_to_base=True` and
`period=<month>`, so the stale-date, ledger, account and rate checks all
run there); plan assertion; post (`execute_expense_post`, unchanged);
readback by id against `build_expense_payload` with the same flags;
summary. The planning flags are set in one place (`_plan_kwargs`) so the
plan, the send plan and the readback rebuild cannot disagree.

**Org.** Only `822116290` is accepted. A production id is refused by
name, any other id by not being the sandbox, before a client exists. Card
id `4369050000000320002`, card name `Visa dummy card Matthias` and
statement currency USD are the sandbox's profile in `ORG_PROFILES`; a
future org needs its own row, after Brisken signs off its mapping.

**The resume rule.** `ALREADY_OCCUPIED` is not fatal on its own. If the
ledger holds at least one of this batch's references as `posted` for the
org, the occupied month is at least partly ours: the runner reports the
occupancy and continues, and `already_in_ledger` refuses per reference.
If the ledger holds none of them, the rows are somebody else's
hand-entered month (Criss's, in production) and the run aborts before
the chart is pulled. `UNVERIFIABLE` and `LOCKED_PERIOD` always abort.

**Plan assertion, send-by-id.** The full plan is printed, every postable
row and every refusal grouped by reason. Then only the postable
references are re-planned on their own, and the runner asserts that plan
carries zero refusals, exactly those references, and the same tie-out
total as the full plan. The total the poster is held to is read from
that plan, never typed (a from-memory total already refused one run at
125.42 against the real 97.40). A postable row with a blank reference is
refused at the runner (`reference_blank`): it cannot be selected by id.

**Readback.** Expense ids are snapshotted before the post. Each posted id
is read back with `GET /expenses/{id}` and compared field by field
against a rebuild through `build_expense_payload`, not
`plan_expense_post` (which would refuse every row as `already_in_ledger`
by then): total, date, reference, `currency_code` USD, paid-through id,
per-line account and amount, envelope present, `Original:` on every
converted row, description under 500, id absent from the snapshot. The
exit code is non-zero on any mismatch, rejection, ambiguity or abort.

**Dry run.** `--dry-run` runs the first four stages and prints
`readback: SKIPPED (dry run)`. The post stage is a separate function
reached only from the live branch, so the dry-run path cannot call
`execute_expense_post` at all; the ledger is only read.

**Acceptance numbers, live TEST-BTS, 2026-09-23.** The July export
(batch `50622baec444`, 56 rows, 46 purchases) dry-run against the durable
ledger must report exactly **0 postable / 46 refused = 41
`already_in_ledger` + 3 `account_unresolved` + 2
`date_precedes_period_window`**, occupancy `ALREADY_OCCUPIED` (38 July
rows on the card) reported and not fatal because the ledger holds all
41, exit 0. Different numbers mean the composition is wrong; diagnose,
never adjust the expectation.

Tests run through `run_month` and `main` with an injected fake client
(`tests/test_zoho_reconcile_month.py`). Three `regress_check` bites on
the runner: unthreading `period=`, unthreading
`convert_foreign_to_base=`, and disabling the resume rule each turn
runner-level tests red and green again on restore.

## 2026-09-23: synthetic references collided across months

August's first dry run refused its OpenAI purchase as `already_in_ledger`
against a row July had posted. Both are real, different purchases, and
both are called `0003__rendered-body.pdf`.

The export writes `ref = detected_reference or document_id`
(`output/zoho_expense_export.py`), so a receipt whose invoice number was
never read falls back to its archive filename, and a mail-rendered
receipt's filename is `NNNN__rendered-body.pdf` where NNNN is only its
index within that batch. Those indexes restart every month. The app
already knew (`web/service.py: adjacent_pool_for_month`, "July and August
share four ids today"); what had never met it was the ledger, whose key
is `(org, reference)`.

`period_scoped_reference` now prefixes ONLY the filename fallback with
its month, so July's is `2026-07_0003__rendered-body.pdf` and August's is
`2026-08_...`. A real issuer reference is left untouched: it is already
unique across months, and rewriting one would break the tie back to the
vendor's own document. The detector needs both the `NNNN__` prefix and a
document extension; the negative cases in
`tests/test_zoho_synthetic_references.py` are the contract, and every one
of them is a real July or August reference.

### A read-time fallback cannot do this, and that was the first attempt

The first cut kept a fallback: when the scoped key missed, look up the
bare one. It passed its tests and failed on live data, because from
August that fallback finds JULY's row. The bare key carries no month, so
nothing at read time can tell which month's purchase it names. The test
that should have caught it seeded the ledger with the SCOPED July key,
which is not the shape the real ledger had.

So the ledger is migrated instead, by
`migrate_legacy_synthetic_references`, and the month is confirmed against
Zoho rather than assumed from the export being processed: the stored
expense is read back and its `date` must equal the group's own
`Expense Date`. Run from August against July's row, that comparison
refuses and the row is left alone. Date equality is exact here because
the payload's date is the CSV cell verbatim, and unlike a period-window
test it does not trip over July's three legitimate June-dated rows.

Applied to the durable ledger 2026-09-23 (backup first): one row,
`0003__rendered-body.pdf` to `2026-07_0003__rendered-body.pdf`, 41 rows
before and after. July's known-answer dry run is unchanged at 0 postable
/ 41 + 3 + 2, and August's false ledger refusal is gone.

### The sandbox reset can now take a subset

TEST-BTS holds months the durable ledger records as `posted`, so a full
reset would silently desynchronise the ledger from Zoho and destroy the
July rehearsal. `plan_reset(only_ids=[...])` deletes named rows and
keeps the rest; `ResetReport.ok` compares against
`expected_remaining` rather than demanding an empty org, and an id the
org does not hold aborts the whole plan instead of being skipped.

## Still open

- The scope grant above, which blocks every write.
- **The stray August row in TEST-BTS.** Expense `4369050000000330001`
  (Microsoft 365, USD 156.00, dated 2026-08-31, created 2026-09-21) is a
  rehearsal artifact that was never ledgered. It is the only thing
  occupying August, so the August run aborts: none of that batch's
  references are in the ledger, which is exactly the "someone else's
  hand-entered month" case the resume rule refuses. Deleting it needs
  `expenses.DELETE`, which the Self Client grant in `context/.env` does
  not carry; the sandbox vault credential does.
- Per-org routing for the 5 cards across separate organizations, and the
  BRL/EUR/USD cases. The trial was one card, nine rows, one currency.
- Wiring the two new guards into the posting CLI's pre-flight, and the
  expense payload builder itself.
- Whether custom fields are wanted at all, and if so they must be defined
  per org before import or they drop silently, as `cf_netting_key_exp` did.
- Whether to auto-create vendors or leave the field empty and let Criss
  attribute.

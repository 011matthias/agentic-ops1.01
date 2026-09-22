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

## Still open

- The scope grant above, which blocks every write.
- Per-org routing for the 5 cards across separate organizations, and the
  BRL/EUR/USD cases. The trial was one card, nine rows, one currency.
- Wiring the two new guards into the posting CLI's pre-flight, and the
  expense payload builder itself.
- Whether custom fields are wanted at all, and if so they must be defined
  per org before import or they drop silently, as `cf_netting_key_exp` did.
- Whether to auto-create vendors or leave the field empty and let Criss
  attribute.

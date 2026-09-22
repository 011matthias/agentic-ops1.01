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

## Still open

- The scope grant above.
- Per-org routing for the 5 cards across separate organizations, and the
  BRL/EUR/USD cases. The sandbox test was one card, nine rows, one currency.
- A month-occupancy guard: refuse to post into an org, card and month that
  already holds rows, unless explicitly overridden. This is what makes the
  July hazard structural rather than remembered.
- Whether custom fields are wanted at all, and if so they must be defined
  per org before import or they drop silently, as `cf_netting_key_exp` did.
- Whether to auto-create vendors or leave the field empty and let Criss
  attribute.

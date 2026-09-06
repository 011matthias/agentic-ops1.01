# API contract: list shapes on the two review payloads

The SPA (`brisken-reconcile-dash.lovable.app`) is a separate repo with no
type-check against this backend. Nothing in its build knows what a field
actually contains, so a list whose elements change from strings to objects
reaches the reviewer's screen as a blank page: React throws on a rendered
object and the root error boundary eats the whole route. That happened on
2026-08-22, when `parse_issues` (objects since 2026-07-22) met a `string[]`
renderer added the day before.

This file is the human-readable side of that contract. The executable side is
`tests/test_view_contract.py`, which probes both payloads over HTTP and fails
CI on an unpinned field, a changed element type, or a fixture that stopped
covering a field. **Change one, change the other**, and say so in the Lovable
prompt for the round.

## The two payloads

| View | Endpoint | Builder |
|---|---|---|
| Expense batch (receipt grid) | `GET /api/expense-batches/{id}` | `build_expense_view` |
| Run (statement workbench) | `GET /api/runs/{id}` | `build_view` |

`GET /api/runs/{id}` serves the EXPENSE payload for a batch with no statement
attached, and the run payload once one is (the batch graduates). Both shapes
must therefore render behind that one route.

## Element types (pinned)

`[]` means "an element of that list". Every entry below is what the SPA
receives after `jsonable_encoder`.

### Expense batch

| Path | Element |
|---|---|
| `parse_issues[]` | object `{file, line, message, severity}` |
| `parse_errors[]` | array `[file, line, message, severity]` (legacy raw rows) |
| `set_aside[]` | object |
| `statements[]` | object |
| `coverage[]` | object |
| `coverage[].digits[]` · `coverage[].statements[]` | string |
| `expenses[]` | object |
| `expenses[].line_items[]` | object |
| `expenses[].books_as[]` | object `{account, unassigned, amount}` |
| `expenses[].edited_fields[]` | string |
| `expenses[].category_variance.categories[]` | string |
| `duplicate_groups[]` | object |
| `duplicate_groups[].members[]` | string |
| `card_review.unresolved_hints[]` | object |
| `card_review.unresolved_hints[].documents[]` | string |
| `card_review.resolved[]` | object |
| `card_review.resolved[].hints[]` | string |
| `summary.upload_issues[]` | string (English prose; unchanged by design) |
| `summary.upload_issue_details[]` | object `{code, file, suffix, limit}` |
| `account_options[]` · `category_options[]` · `entity_options[]` | string |

### Run

| Path | Element |
|---|---|
| `parse_issues[]` | object `{file, line, message, severity}` |
| `parse_errors[]` | array `[file, line, message, severity]` (legacy raw rows) |
| `rows[]` | object |
| `rows[].candidates[]` | object |
| `rows[].candidates[].receipt.line_items[]` | object |
| `unmatched_transactions[]` · `unmatched_receipts[]` · `assignable_receipts[]` | object |
| `unmatched_receipts[].line_items[]` | object |
| `duplicate_groups[]` | object |
| `duplicate_groups[].members[]` | string |
| `duplicate_charges[]` · `duplicate_receipts[]` | array of objects |
| `duplicate_receipts[][].line_items[]` | object |
| `summary.setup_advisories[]` | object |
| `statements[]` | object |
| `coverage[]` | object |
| `coverage[].digits[]` · `coverage[].statements[]` | string |
| `category_options[]` | string |

## `parse_issues` specifically

```json
{ "file": "0000__0000__receipt_01_p7.png",
  "line": 0,
  "message": "looks like an expense-report summary page, not a purchase receipt",
  "severity": "warning" }
```

`severity` is `"error"` or `"warning"`. `line` is `0` for a whole-file issue.
The SPA renders `file` (with `:line` when non-zero) as a muted prefix and
`message` as the body, and keeps a `typeof item === "string"` fallback so an
older cached payload cannot crash the page.

## What the test does not check

Scalar types. `books_as[].amount` going from `"42.50"` to `42.50` passes; so
does a non-list field growing into an object. Lists are pinned because a list
is the only place the SPA maps over elements it did not individually type,
which is the shape the crash took. Widening the pin to every leaf is a
several-hundred-row table that churns every round; if a scalar flip ever bites,
that is the moment to widen it, not before.

## Upload rejections: prose plus a code

A file the upload refused (`upload_cap`, `unsupported_type`,
`empty_or_unreadable`, `too_large`) surfaces twice, on purpose:

```json
"upload_issues": ["notes.txt: unsupported type .txt (skipped)"],
"upload_issue_details": [
  { "code": "unsupported_type", "file": "notes.txt", "suffix": ".txt", "limit": null }
]
```

`issues` / `upload_issues` keep their English sentences and their `string[]`
type forever; the SPA localizes from `*_details` and falls back to the prose
when the list is empty (every run created before 2026-08-22 has no details).
Every detail object carries the same four keys, `suffix` and `limit` null
where the code does not use them, so a consumer maps over them without shape
checks. `service.upload_issue()` builds the sentence and the code in one
call, so a reworded message cannot drift from what the SPA translates.

This is rule 1 below in practice: the richer data arrives as a PARALLEL
field. The same three emission sites feed `expense_ingest.issues` (batch
create), the folder-ingest reply, and the add-receipts job summary.

## Summary counts: one name, one question

Types are not the only contract a payload carries. `n_categorized` shipped on
both the batch list and the batch page with two different meanings — the list
counted expenses that had a category, the page counted rows whose review state
was `ready` — so April 2026 read "35 categorized" on one screen and "5" on the
other (operator note, 2026-08-22). Nothing failed; the number was just false.

Each count answers exactly one question, and every payload that carries the
name answers the same one:

| Key | Question |
|---|---|
| `n_expenses` · `n_receipts` | how many expenses are in the batch |
| `n_categorized` · `n_uncategorized` | how many still need a category |
| `n_ready` | how many need NOTHING from the reviewer (category, entity, core fields, and — since item 40 — a person) |
| `n_review` | how many are flagged for a look (`check` or `pick`) |
| `n_needs_entity` | how many still need a legal entity (a confirmed private row needs none by design, so it does not count — item 41 sharpened the question the name always asked) |
| `n_needs_person` | how many rows no person owns yet (item 40; the fix is a person on the card, not a row edit) |
| `n_suggested_private` | how many rows are suggested as private expenses, unconfirmed (item 41) |
| `n_private` | how many rows the operator confirmed private (reimbursement rows) |
| `n_set_aside` | how many files the quarantine is still holding back |
| `n_duplicate_groups` | how many duplicate SITUATIONS were flagged |
| `n_duplicate_copies` | how many copies are redundant (every copy after the first in a group the reviewer has not dismissed) |

`service.categorized_counts` is the single implementation of the categorized
rule; `service.batch_list_summary` derives the list screen's counts from the
same live overlay the batch page renders, so a reviewer's edit moves both. A
new count gets a row here and its own name — never a second meaning on an
existing one.

## The statements a month has taken: `statements[]` (added 2026-08-25)

`POST /api/expense-batches/{id}/statement` is repeatable: a statement arrives
per card, and often twice (a mid-month partial, then the closing cycle). Each
upload appends one entry, oldest first, on BOTH review payloads. Parallel
field, per rule 1 below: empty on every month created before it, reconciling
ones included, so absence means "not recorded" and never "none loaded".
`has_statement` is still the answer to whether a month has a statement at all.

```json
{ "file": "statement-2.xlsx",
  "upload_name": "statement.xlsx",
  "card_key": "corp-1672",
  "account_id": "chase-2838-family",
  "sheet_name": null,
  "period_start": "2026-04-03",
  "period_end": "2026-04-28",
  "n_rows": 14,
  "n_new": 11,
  "uploaded_at": "2026-08-25T09:12:44",
  "writeback": true,
  "advisory": null }
```

Every entry carries the same keys, null where the upload does not use one.

| Key | Question it answers |
|---|---|
| `file` | the name on disk, and the value `?file=` addresses |
| `upload_name` | what the operator actually sent; differs when two per-card exports shared a filename |
| `n_rows` · `n_new` | what the file held, and what the fold put in the month |
| `period_start` · `period_end` | the dates this upload covers, null when it parsed no dated row |
| `writeback` | whether this file is an Excel workbook the L3 writeback can annotate |
| `advisory` | one sentence when the upload looks like it doubled the month, else null |

`n_rows` minus `n_new` is charges the month already held. That is the ordinary
result of a partial followed by the full cycle, not a problem.

`advisory` fires on two shapes, and NOTHING is dropped or merged when it does:
one card typed against two different account ids (which is part of transaction
identity, so the two uploads dedupe against nothing), and an upload over a
period the same account already covers that has no row in common with it (a
sign inference that differs between two exports gives one printed row two
ids). Both really are two rows; the advisory is there because on screen it
otherwise just looks like the month doubled itself.

`GET /runs/{id}/statement-categorized.xlsx` takes an optional `?file=`, matched
against `statements[].file`, to write back a statement other than the current
one. A name that is not in `statements[]` is a 404. Without the parameter the
route behaves exactly as before.

Each workbook is annotated for exactly the charges IT contains, at the rows it
puts them on, from a per-upload id-to-row map in the snapshot's
`statement_anchors`. That map is deliberately not in either payload: it is one
entry per statement row, nothing renders it, and the SPA needs `statements[]`
only. One charge occupies a row in every file that prints it, which is why the
row is recorded per upload rather than on the charge; anchoring on the charge
would leave the closing cycle blank wherever a mid-month partial got there
first.

## Per-card coverage: `coverage[]` (added 2026-08-26)

`statements[]` answers the FILE question. This answers the CARD question,
which is the one the work is organized around: a card is loaded across
several files (a mid-month partial, then the closing cycle) and one file
prints charges from several cards, so neither list can be derived from the
other. Parallel field, per rule 1, on BOTH review payloads and identical
between them for the same month.

```json
{ "key": "corp-1672",
  "card_key": "corp-1672",
  "label": "Corporate card (Chase)",
  "entity": "Corporate Services",
  "digits": ["2838", "1672"],
  "known": true,
  "statements": ["statement.xlsx", "statement-2.xlsx"],
  "period_start": "2026-04-03",
  "period_end": "2026-04-28",
  "n_transactions": 45,
  "n_reconciled": 30,
  "n_review": 2,
  "n_unmatched_tx": 12,
  "n_refunds": 1,
  "unreconciled_by_ccy": { "USD": "1,204.55" } }
```

| Key | Question it answers |
|---|---|
| `key` | which row this is, and the value `rows[].coverage_key` points at. Opaque: match it, never parse it |
| `card_key` | the card-registry key, or `""` when the registry does not know this card |
| `label` | what to call it on screen, always renderable: the registry's label, else the string the statement printed, else `"No card on the charge"` |
| `known` | whether the registry knows this card. `false` is a real finding, not an error: it is a card nobody has registered yet |
| `digits` | the digit tokens that identify it |
| `statements` | the uploads that covered this card, oldest first |
| `period_start` · `period_end` | the first and last charge dates this month holds FOR THIS CARD; null when it holds none |
| `n_transactions` and the four buckets | the same four counts the run summary carries, for this card's charges alone |
| `unreconciled_by_ccy` | this card's share of the month's unreconciled money, by the summary's own rule |

**The counts are the summary's counts.** `n_reconciled` + `n_review` +
`n_unmatched_tx` + `n_refunds` equals the entry's `n_transactions`, and
summing any of the five across `coverage[]` gives the run summary's value for
the same name. That is deliberate and pinned by
`tests/test_coverage_surface.py`: a panel a reader cannot add up against the
headline it sits under is the `n_categorized` failure above, with money on
it. Reconciled and refunded charges are settled and a posted charge is
settled by definition, which is why they carry no unreconciled money.

**Empty means nothing loaded.** A month with no charges and no uploads gets
`[]`, so a receipt-only month does not open with a column of registry cards
it has no business asking about yet, and `statements[]`'s own emptiness
already says the same thing.

**Which card a charge is on** starts from the string the matcher itself
reads: the per-row card column when the statement prints one, the account id
otherwise. That string is then resolved through `cards.resolve_card` against
the batch's own registry snapshot, the same resolver the per-receipt card
chain uses, so digit tokens and registry ALIASES both count and an ambiguous
string resolves to nothing (ambiguity surfaces instead of guessing). The
Chase cycle marker `2838` and the plastic's `1672` are therefore ONE row; a
card the registry never met gets a row of its own rather than being folded
into an "other" bucket; and a charge naming no card at all lands in the
empty-key row, never in some card already listed. Every row carries the
assignment as `rows[].coverage_key`.

A card the registry does not know is keyed `digits:<tokens>`, which is why
`key` must not be parsed. Cards are keyed by an operator-chosen slug and
nothing stops that slug from being digits that are not the card's own
(`"2838"` as the key of a card whose digits are 9999); without the namespace,
charges on the real 2838 would land in that card's row and its money would be
reported against the wrong plastic and the wrong entity.

**Which statements a card was loaded from** comes from two joins, unioned:
the operator's `card_key` on the upload (an explicit assertion, so it counts
even when that file printed nothing on the card), and the charges the file
actually printed via `statement_anchors`. `account_id` is the last resort,
used only when both are silent, because it names an ACCOUNT: on the real
corpserv export every row says `chase-2838-family` while the rows span
2838 / 3645 / 3876 / 0340, and reading that as a card would invent a coverage
row for a card that does not exist.

## The two batch functions: `batch_type` + `trip` (added 2026-09-06)

Item 38: expense creation splits into company months and trips, DECLARED
at creation and never inferred from content. Both fields are parallel
(rule 1); a stale SPA renders exactly what it rendered before.

**`batch_type`** — scalar string, `"company-month"` or `"trip"`, on the
expense-batch payload and on every row of `GET /api/expense-batches`. An
absent config marker reads as `"company-month"`: every batch that
predates the split is one, and an undeclared `POST /api/expense-batches`
stores no marker at all, so an un-updated caller produces the exact
pre-split config. Declaring is a form field on the create
(`batch_type`, plus `trip_id` when it is `"trip"`).

**`trip`** — object or null on the expense-batch payload. Null on every
company month; on a trip batch:

```json
{ "trip_id": "8c1f30aa2e41",
  "name": "Rome 2026",
  "start": "2026-09-20",
  "end": "2026-10-03",
  "travelers": ["Dirk Neumann", "Criss"] }
```

`travelers[]` is a list of person NAMES (item 40's vocabulary), pinned
`string` in `test_view_contract.py`. The roster is VARIABLE by owner
ruling; render the list, never assume one traveler.

**What a trip batch never does:** it never appears in
`GET /api/expense-batches` (the months screen stays months — trips list
via `GET /api/trips`), it never claims pooled month mail (month routing
skips trip batches structurally, even when the trip's name parses as a
month), it never carries a `period_suggestion` (trips span month
boundaries freely), and `POST .../statement` refuses it with a 400
(ruling 3: trip receipts reconcile against the company month's
statement; the cross-batch match pool is the R4 round).

### `GET /api/trips` (beside /api/expense-batches)

`{trips: [...]}`, newest range first. Each row is the trip entity plus
its batch join — `batch_id` and `summary` are null until the first
receipt joins, because the batch materializes on first join
(create-with-receipt) rather than being created empty:

| Key | Meaning |
|---|---|
| `trip_id` · `name` · `start` · `end` · `travelers[]` | the entity; dates inclusive, `YYYY-MM-DD` |
| `batch_id` | the trip's expense batch, or null while no receipt has joined |
| `summary` | `batch_list_summary` of that batch (same counts vocabulary as the months list), or null |

`POST /api/trips` (`{name, start, end, travelers[]}`) creates the
entity; `PUT /api/trips/{id}` updates it (`travelers` replaces the whole
roster); `DELETE /api/trips/{id}` refuses (409) while a batch still
references the trip. One batch per trip: a second
`POST /api/expense-batches` declaring the same `trip_id` is a 409
naming the existing batch.

## The month the receipts read as: `period_suggestion` (added 2026-08-29)

Expense-batch payload, top level, object or null. Backlog item 36: the
dates-plurality month the batch's receipts collectively read as, so the SPA
can OFFER a rename ("These receipts read as April 2026") instead of the
operator having to notice a mismatch. The label stays the only authority
(item 25 ruling: nothing about dates is auto-corrected); this field never
changes behavior on its own.

```json
{
  "month": "2026-04",
  "label_month": null,
  "n_dates": 5,
  "n_in_month": 5
}
```

| Field | Meaning |
|---|---|
| `month` | the consensus month, `YYYY-MM` |
| `label_month` | the month the batch LABEL names, `YYYY-MM` or null when the label names none |
| `n_dates` | how many expenses carried a date |
| `n_in_month` | how many of those fall in the consensus month |

Null (not an absent key) whenever no consensus exists: fewer than 4 dated
expenses, or no month holds at least max(3, 40%) of them while strictly
beating the runner-up (`batch_period.month_from_dates`). The SPA renders a
banner only when `month` exists AND (`label_month == null` or it differs);
render defensively per rule 3 below.

## Rules for changing a list field

1. **Enriching a field in place is the dangerous move.** Adding keys to an
   object element is safe; turning strings into objects is not. When richer
   data is needed on a `string[]`, add a PARALLEL field
   (`issues` + `issue_details`, backlog item 20) and let the SPA prefer the
   new one, rather than retyping the old one underneath a live renderer.
2. **Ship the SPA side in the same round.** The Lovable prompt names the field
   and its new shape; a backend-only round leaves a page that renders whatever
   it last expected.
3. **Render defensively.** Any list the SPA maps over gets a type check on the
   element, so a stale or unexpected payload degrades to plain text instead of
   an error boundary.
4. **Re-pin.** `tests/test_view_contract.py` fails until the contract table and
   this file agree with the payload. That failure is the reminder, not a
   formality.
5. **Growing an enum is the same move as retyping a field.** Rules 1-4 pin
   list ELEMENT types and say nothing about adding a new VALUE to an
   existing enum-ish field, which is how `status` grew three values on
   2026-08-24 and the SPA silently mislabelled all three: its map had no
   case for them, so `pooled`, `routing` and `claiming` all fell through to
   its in-flight label. Six of Dirk's resting receipts read **"Arriving"**
   with a blank Month, indefinitely. Nothing crashed and nothing was
   unpinned; the page was simply confidently wrong, which is worse than the
   held strip it replaced, because "Arriving" is an affirmative claim that
   resolves itself while "held" at least looks like it needs attention.

   The standing mitigation is rule 1 applied to meaning rather than type:
   **when a status set grows, ship a parallel human-readable label**, so an
   un-updated consumer degrades to correct text instead of somebody else's
   copy. `status_kind` + `status_label` (below) are that field for the
   inbound log. An enum whose values the SPA maps by hand and that has no
   parallel label is the open version of this hole; the next one to grow
   gets the same treatment.

   Enforced for the intake statuses by `test_every_status_has_a_label`: a
   new `STATUS_*` / `HELD_*` constant fails the suite until someone decides
   what it SAYS. That test is the reminder, the same way the view-contract
   pin is for element types.

## The month pool: fields added 2026-08-24

Mail is addressed by the receipt's PRINTED month, not by whichever batch is
open. Mail whose month has no batch rests in the pool (status `pooled`) and
is claimed when that month is created or renamed into. Every field below is
PARALLEL (rule 1): nothing existing changed type or meaning, so a stale SPA
renders exactly what it rendered before.

### `GET /api/inbound/log`

| Path | Type | Question it answers |
|---|---|---|
| `entries[].pool_month` | string `"YYYY-MM"` | which month this mail's receipts belong to |
| `entries[].receipt_month_source` | string | how that month was decided: `receipt` (a printed date), `arrival` (none readable), `implausible-receipt` (a printed date outside the plausibility window) |
| `entries[].mixed_months` | `true` (absent otherwise) | this mail spans more than one month, and routed by its earliest |
| `entries[].pool_month_state` | string | pooled rows only: `no_batch`, `open` (a claim is imminent), `reconciling` (the month has its statement and is still open, so a claim is imminent there too; 2b-2). `closed` is retired and no longer emitted -- the month used to shut when its statement arrived, and a pooled mail addressed to it was a dead end. An SPA that still branches on `closed` keeps working: it just never sees it, and `status_label` already says the right thing |
| `n_pooled` | number | top-level, beside `n_held`. Distinct MAILS, not log rows |
| `entries[].status_kind` | string | how to TREAT this row: `resting` (fine, waiting on something scheduled), `held` (needs a human), `working` (in flight, resolves in seconds), `done` (nothing owed), `unknown` (a status this backend build does not know). Added 2026-08-24 |
| `entries[].status_label` | string | what to SAY, already composed in English: "Waiting for July 2026", "Needs one click to read", "Added". For an unrecognised status this is the raw status value, never a borrowed label |
| `entries[].materialized` | `true` (absent otherwise) | item 39: this mail CREATED its month batch itself (arrival auto-materialization — known senders only, a stranger's mail pools exactly as before — or the operator backfill). Its `status_label` reads "Filed into July 2026" instead of "Added" — same status enum, no new value, the label pair carries the new meaning per rule 5. The ingested outcome still carries a `job_id` (a done job row is written for the create) |
| `n_refused` | number | top-level. Mail TURNED AWAY in the last 7 days (SMTP refusals). `0` is the answer to "is anything bouncing?", and before 2026-08-24 there was none |
| `n_refused_ours` | number | top-level, PARALLEL to `n_refused` (whose meaning is unchanged). Data-stage refusals in the same window: real submissions we accepted the envelope for and then turned away. This is the number that answers "did anyone's receipt bounce this week?" — added 2026-09-06 (item 42) because all 55 window rows were relay probes and a real refusal was invisible in the single count |
| `n_probes` | number | top-level, parallel. Rcpt-stage relay probes in the window (`relay not permitted`): spam scanners addressing mail outside the intake domain. Permanent background noise, not a delivery problem. The two splits do not have to sum to `n_refused` (a rcpt-stage "too many recipients" row is real mail addressed to us and sits in neither) |
| `refusals[]` | object `{at, stage, reason, from, to, peer, probe, kind_label}` | the newest refusal rows, oldest->newest. `stage` is `rcpt` (recipient refused) or `data` (accepted the envelope, then a guard turned the message away: disk floor, in-flight ceiling, day budget, archive failure). `probe` (bool) marks a relay probe; `kind_label` is its rule-5 prose ("Relay probe, not our mail" / "A real submission, turned away" / "Refused at the envelope"), so a consumer never has to decode the SMTP reason line |

`status_kind` / `status_label` follow the `issues` + `issue_details` pattern
in reverse: the PROSE is the new field and the CODE rides beside it, because
there was no prose before. Localize from `status_kind` and fall back to
`status_label`; both are parallel, so a stale SPA renders exactly what it
rendered before.

Refusals are deliberately NOT rows in `entries`. A refusal has no archive,
so it cannot be deduped, replayed or dismissed, and a row in `entries`
carrying a status no consumer knows is precisely the failure rule 5
describes. `n_refused` counts a 7-day WINDOW rather than the whole ledger,
because the ledger is trimmed at a size cap and "every row we kept" would
answer a question about our own retention instead of about this week's
mail.

`pooled` is a RESTING state, deliberately not `held_*`: nothing is wrong with
the mail, its month simply is not open yet. It therefore does NOT count toward
`n_held`, and the Held badge cannot be made to reach zero by fixing it. A
pooled row carries no `batch_id` and no `expenses`, because it belongs to no
batch yet.

### The travel pool (item 38, added 2026-09-06)

Mail addressed to the TRAVEL alias (settings `intake.travel_alias`, unset
until the owner picks the local-part) rests in the pool too, with three
parallel fields on its rows and one parallel count. The `status` enum did
NOT grow: travel rows are `pooled`, distinguished by `pool_kind`, and
`status_label` already says the right thing on a stale SPA.

| Field | Type | Meaning |
|---|---|---|
| `entries[].pool_kind` | `"travel"` (absent on month mail) | this mail waits for a TRIP and an operator's click, never for a month |
| `entries[].trip_suggestion` | object `{trip_id, name, start, end}` (absent otherwise) | present only when the mail's receipt dates fall inside EXACTLY ONE trip's range. A reading, not a decision: two covering trips surface as absence, and joining is always the click |
| `n_pooled_travel` | number | the travel share of `n_pooled` (which keeps counting ALL resting mail) |

Travel rows carry NO `pool_month_state` — a month state on them would
promise a claim that deliberately never happens. Their `status_label` is
`Travel, waiting for its trip`, or `Travel; reads as "{name}"` when the
suggestion is present. The month claim, the replay sweep, re-ingest and
auto-materialization all skip `pool_kind: "travel"` structurally.

`POST /api/inbound/{archive}/join-trip` (`{"trip_id": ...}`) is the
click: 409 unless the mail is travel-pooled, 404 on an unknown trip.
It creates the trip's batch WITH this mail's receipts when none exists
(reply carries `created_batch: true`), else appends incrementally like a
month claim; either way `submitted_by` provenance rides in and a failure
returns the mail to the travel pool.

`PUT /api/settings` `intake.travel_alias`: a bare local-part, `""` to
unset. Refused when it is `"receipts"` or collides with a person alias.
REMINDER: the `intake` object is whole-object-replace (see below), so an
SPA that does not know this key will silently drop it on its next
settings save — ship the SPA prompt before anyone sets the alias.

Both `n_pooled` and `n_held` count distinct ARCHIVES. The log holds more than
one row per archive by design (one at acceptance, another when a replay or a
claim ingests it), so counting rows would report two waiting mails where one
is waiting; the 2026-08-24 live drill read exactly that.

### Other endpoints

| Endpoint | Field | Type | Meaning |
|---|---|---|---|
| `POST /api/expense-batches` | `month` | string \| null | the month this label names; `null` means it names none |
| `POST /api/expense-batches` | `advisory` | string (only when `month` is null) | prose saying mailed receipts cannot join this batch until it is renamed |
| `POST /api/runs/{id}/rename` | `month` | string \| null | same, after the rename; a non-null value means the pool was just claimed |
| `POST /api/runs/{id}/delete` | `pooled_back` | number | month-stamped mail returned to the pool |
| `POST /api/inbound/replay-held` | `pooled` | number | held mail parked in the pool by this sweep |
| `POST /api/inbound/replay-held` | `claimed` | number | pooled mail ingested by this sweep |
| `POST /api/inbound/replay-held` | `still_pooled` | number | pool size after both halves |
| `POST /api/inbound/replay-held` | `re_pooled` | number | item 39: stranded `batch_deleted` archives lazily month-stamped and returned to the POOL. Present ONLY on `materialize: true` calls — the sweep never runs on a plain retry click (a flag-off deploy stays inert, no vision is spent, and the item-19 re-ingest path keeps its mail) — and it runs LAST, after the claim, so a freshly re-pooled archive rests one full round-trip before any later call may act on its just-guessed stamps. Dismissed archives are excluded; unstampable ones stay legacy |
| `POST /api/inbound/replay-held` | request `{"materialize": true}` | bool | item 39, the explicit operator backfill: month batches are CREATED for confidently-stamped (`receipt`-sourced) pooled mail, oldest month first, then the normal claim drains the rest, then the stranded sweep (above) runs. Requires `EXPENSE_RECON_AUTO_MATERIALIZE`; without the flag the call answers 409 and nothing changes |
| `POST /api/inbound/replay-held` | `materialized_months` | string[] | only with `materialize: true`: the labels of the months this backfill created ("July 2026", ...) |
| `POST /api/inbound/replay-held` | `materialize_failed` | number | only with `materialize: true`: creations refused or errored back to the pool |
| `GET /api/expense-batches` | `batches[].created_by` | string \| null | item 39 origin marker: `"intake"` when mail created this month itself; `null` on operator-created batches. Also on the batch view as `summary.created_by` |
| `POST /api/inbound/{archive}/render-ingest` | `pool_month` | string | present on both outcomes; with `status: "pooled"` the render succeeded and is waiting |
| `PUT /api/settings` | `intake.known_senders` | string[] | outside addresses that count as our own people. They get the acceptance ack, and their body-only mail is rendered on arrival instead of holding. At most 25 plain addresses; malformed entries are a 400 naming the field |

`inbound_marked` on delete keeps its OLD meaning (legacy mail stamped "month
deleted") and is normally `0` now; `pooled_back` is the number that moves.
Reading `inbound_marked` as "mail affected" was true before this change and is
not any more, which is exactly the second-meaning failure the counts section
above warns about; hence the parallel name.

The `intake` object is stored EXACTLY as sent (`set_settings` merges
shallowly at the top level), so a partial `{"intake": {"known_senders": [...]}}`
drops the aliases and caps with it. Read, change one key, send the whole
object back.

Body-only mail from a known sender no longer reaches `held_body_only` at all:
it renders on arrival and goes straight to `ingested` or `pooled`. No field
changed shape, but the Held strip now holds only unrecognised or genuinely
failed mail, which is what its copy should say.

`render-ingest` no longer returns 409 when no month is open. The render always
happens and the result always lands somewhere, so a 409 from that endpoint now
means only what it always meant for the other guards: the mail is not in a
renderable state.

## The living month: fields added 2026-08-25

PR 2b-1 extracted the attach path's match into `service.rematch_month`, the
one function every incremental path will call, and gave it a judgment cache.
Two additive fields, both numbers, both safe to ignore.

### Statement attach response

| Endpoint | Field | Type | Meaning |
|---|---|---|---|
| `POST /api/expense-batches/{run_id}/statement` | `judgments_reused` | number | LLM judgments answered from the run's own store instead of the model |
| `POST /api/expense-batches/{run_id}/statement` | `judgments_new` | number | judgments this pass actually paid for |

On a first attach `judgments_reused` is `0` by construction: nothing has been
judged yet. A non-zero value on a later re-match is the saving, not a warning.

### `llm_judgments` in the snapshot

Internal, never rendered. A content-keyed map of judgments already bought for
this run, so a re-match only pays for pairs it has not seen. Three properties
worth knowing before touching it:

- The key covers the CALL's content and the model that answered it. A
  reviewer correcting a receipt's amount, or a deployment moving to a
  stronger model, misses and re-judges rather than serving a stale verdict.
- It MERGES at commit rather than replacing, so a concurrent re-match that
  landed while this one matched does not lose the entries it paid for.
- It is never evicted. Entries are bounded by the pairs a month actually
  puts in front of the model, which is small; if a month ever grows one
  large enough to matter, prune at commit rather than at read.

Transaction ids became content-derived in PR 2a, so a `transaction_id` no
longer contains an account prefix or a row number and nothing may parse
structure out of one. Repeat charges carry a `-{n}` suffix.

## Duplicates, sorted out before ingestion (2026-08-25)

Owner directive: "we also need to be able to sort duplicates out before they
are ingested into the tool's workflow." The receipt pool has always deduped
identical files at ADD time, which created no second expense but still logged
the mail as "Added" — a row saying it added something when it added nothing —
and did nothing at all when a repeat routed to a different month.

### New status

`duplicate`, kind `resting`. Not `held_*` (nobody has to act) and not
`dismissed` (nobody judged it junk). Per rule 5 it ships with a label, which
names the mail it duplicates: `Already have this, from "July taxi"`.

### `GET /api/inbound/log`

| Field | Type | Meaning |
|---|---|---|
| `n_duplicates` | number | distinct MAILS parked as duplicates, counted like `n_held` |
| `duplicate_of` | string | archive id of the mail that already holds this content |
| `duplicate_of_subject` | string | that mail's subject, for the label and the row |
| `duplicate_of_at` | string | when it arrived |

A duplicate row carries no `expenses` join, because it never reached a batch.
That absence is the point, not a gap.

### `POST /api/inbound/{archive}/not-a-duplicate`

Routes a parked mail after all. Deny-by-default: 409 unless the mail is
currently `duplicate`. Byte-identical content can legitimately be two
purchases (a fixed-price subscription receipt with no invoice number, mailed
two months running), so a parked mail is never trapped. The archive keeps its
fingerprints, so the NEXT copy still detects against it.

`POST /api/inbound/{archive}/dismiss` now also accepts a `duplicate`, on the
same argument that let it accept a `pooled` mail: otherwise it rests forever
with no way to finish with it.

### What counts as the same

Byte-identical content, nothing softer. Attachments hash as
`sha1(bytes)[:16]` — the SAME shape the receipt pool uses, deliberately, so
the two layers cannot disagree about what "the same file" means. A body-only
mail has no attachment at arrival (its PDF does not exist until something
renders it), so its whitespace-collapsed, casefolded body stands in.

Two rules that decide the hard cases:

- **Only a mail that ENTERED the workflow owns its content** (`ingested`,
  `replayed`, `pooled`, and the two transient routing states). A dismissed or
  still-held first copy does not, because the tool does not hold that receipt
  and calling the next copy a duplicate would hide a receipt nobody ingested.
- **Every piece must be known.** A mail carrying one held file and one new one
  is not a duplicate; the pool's own dedupe drops the repeat at add time.

A near-miss MISSES, which is the old behavior. A false match would hide a real
receipt, which is worse than anything the detector prevents.

## Duplicates on the row: `duplicate` (added 2026-08-28)

Arrival-time detection above catches a mail whose every file the tool
already holds. It cannot catch the case that actually reaches the grid: the
same invoice as two different files, two different scans, two different
attachments in two different mails. `find_duplicate_receipts` and
`find_duplicate_charges` have caught that since Tier-1 #4, into
`duplicate_groups[]` — a side list of ids.

A side list of ids is not something a reviewer reads. The live April batch
carries one group (Pressmaster FZCO, 135.00 USD, forwarded twice under two
file names) and the 40-row grid above it showed both copies with nothing to
distinguish them from any other pair of rows. So the group is now carried on
the rows themselves.

| Payload | Field |
|---|---|
| Expense batch | `expenses[].duplicate` |
| Run | `rows[].duplicate` (charge groups) · `unmatched_receipts[].duplicate` and `assignable_receipts[].duplicate` (receipt groups) |

`null` on a row in no live group, which is most of them, and `null` on every
payload built before this. When present:

```json
{ "group_id": "cfdacfc912a79a47",
  "kind": "receipt",
  "n_copies": 2,
  "copy": 2,
  "of": "0039__Invoice-B2EA98DF-0020.pdf",
  "is_extra": true,
  "resolution": null }
```

- `copy` is this row's 1-based place in the group, `of` is the first
  member's id. Together they let a row say "same as 0039" rather than
  marking both copies equally guilty; the order is the group's own, so the
  answer does not move between renders.
- `is_extra` is true for every copy after the first, which is exactly the
  population that inflates a count. `summary.n_duplicate_copies` is how many
  of them there are.
- `group_id` is what `POST /api/runs/{id}/duplicates/resolve` takes, so the
  row can be acted on where it is read.

**A dismissal dismisses.** `resolution: "ignore"` removes the marker from
every row, drops the group out of `n_duplicate_copies`, and drops it from the
reconciliation document's exceptions. The group itself stays in
`duplicate_groups[]` carrying the ruling: "we looked at this and it is fine"
is worth keeping. `"confirmed"` keeps the marker, because acknowledging a
duplicate is not removing it — the second row is still on screen and still
in the total until somebody deletes it with
`DELETE /api/runs/{id}/expenses/{document_id}`.

**Totals still count every row.** `totals_by_ccy` sums the duplicates too.
The detector's whole contract is that it flags and never drops, and a total
that quietly disagreed with the rows printed above it would be worse than
one that is honestly too high with the reason marked on the row.

`POST /api/runs/{id}/duplicates/resolve` replies with the summary of the
payload the caller is on (grid for an unattached batch, workbench once a
statement is attached), the same dispatch `GET /api/runs/{id}` uses. It
previously always replied with the workbench's, so a grid header rendering
`n_expenses` went blank on the reply to its own click.

## The cards a month actually charges: `seen_undefined` (added 2026-08-28)

`GET /api/cards` composed the settings registry plus the shipped presets,
so the card-definition screen listed the cards somebody had already
defined and nothing else. On the live data that means 2838 plus four cards
carrying no charges, while 0340, 3645 and 4700 charge 53 of April's 94
rows and appear nowhere on the screen where a card gets defined. The
reviewer's actual move, define the card these charges are on, was the one
move the screen could not start.

The payload now carries a third key beside `cards[]` and
`entity_options[]`. Empty when every card the months charge is already
known, so a renderer that ignores it keeps working.

```json
"seen_undefined": [
  { "key": "digits:3645",
    "suggested_key": "3645",
    "observed": "3645",
    "digits": ["3645"],
    "n_charges": 18,
    "months": ["April 2026"] }
]
```

- `suggested_key` is what to define the card AS, taken from what the
  statement printed. `_card_keys` strips leading zeros deliberately, so
  that Chase's `0340` and the Zoho payment mode's `340` land on one match
  key; that is right for matching and wrong for a person, who would be
  offered `340` for a card they know as `0340`. `key` keeps the
  normalized, `digits:`-namespaced form because that is what joins to the
  charge.
- `n_charges` and `months` are there so the decision to define a card can
  be made from the row: busiest card first.
- The identity comes from the same `_charge_card_identity` the
  `coverage[]` panel uses. A card listed here is the same card a coverage
  row is about; two derivations would be two answers, and the reviewer
  would define a card the coverage panel then does not credit.

Defining one is the existing `PUT /api/settings` with `cards`, which
replaces the whole map, so send the current `cards[]` plus the new entry.
A card with no entity is still DEFINED and drops out of this list; the
missing entity is the entity column's business.

## The unknown-card strip, grouped by card: `spellings[]` + `digits` (added 2026-09-06)

Backlog item 35. `card_review.unresolved_hints[]` grouped by VERBATIM hint
string, so the April batch rendered ONE unregistered card (0340) as five
assignable rows — five spellings of the same masked number. Digit-bearing
hints now group by their canonical digit run (the zero-stripped form the
matcher's `_card_keys` uses, so "0340" and a label printing "340" are one
group). Digit-less hints keep one row per verbatim string.

Two fields on each entry, both parallel per rule 1 — `hint`, `n_rows`,
`documents[]`, `generic`, `ambiguous` all keep their meaning:

```json
{ "hint": "***********0340",
  "digits": "0340",
  "spellings": ["***********0340", "VISA - ******0340", "****0340"],
  "n_rows": 11,
  "documents": ["..."],
  "generic": false,
  "ambiguous": false }
```

| Field | Meaning |
|---|---|
| `hint` | now the group's representative spelling: the most frequent member that carries exactly ONE digit run, so an un-updated Assign submitting it teaches that digit and resolves every sibling spelling with it (a multi-run spelling like a Zoho payment-mode label teaches no digit and would strand its siblings). A group with no single-run member falls back to the most frequent spelling. Ties break lexicographically; always a real hint string from the batch |
| `digits` | the longest printed digit run in the group, leading zero preserved (`"0340"`, never `"340"`), for display. `null` on digit-less entries |
| `spellings[]` | every member spelling, most-frequent first. `[hint]` on digit-less entries |

The no-card-number sub-strip is a rendering partition, not a second list:
entries with `digits: null` and `generic: true` are tender words ("no card
number readable on the receipt; assignment applies to this month only");
`digits: null` with `generic: false` is a word-only identifying hint. The
SPA partitions on those two existing flags and maps over `spellings[]` for
the grouped Assign (`POST /api/expense-batches/{id}/cards` takes the full
assignment list in one call).

## Every expense belongs to a person, through the card (added 2026-09-06)

Backlog item 40, owner directive: "each card is attributed to a name and
therefore every expense can be attributed to a person. Even the ones
injected via email." All fields below are PARALLEL (rule 1).

**The card registry entry** gains `person` beside `entity`: accepted by
`PUT /api/settings` `cards`, emitted by `GET /api/cards` (`cards[].person`,
`""` when unset), snapshotted into a batch at creation, and reaching an
existing batch only through `POST .../refresh-master-data` (whose `changes`
gains a `row_persons` entry counting re-attributed rows). The cards map is
still WHOLE-MAP REPLACE: an SPA build that does not read and write `person`
in its Settings > Cards editor silently erases every stored person on save
— person data entry therefore waits until the round's Lovable prompt is
verified in the published bundle.

**Expense rows** gain:

| Field | Type | Meaning |
|---|---|---|
| `expenses[].person` | string | who this expense belongs to; `""` until its card carries a person |
| `expenses[].person_source` | string | `card` (the chain resolved it) or `none`. Item 41's round adds `private` |
| `expenses[].card.person` | string | the resolved card's own person (also on `card_review.resolved[].card`) |

Person resolution is the LAST link of the existing card chain (extraction
pick → hint → registry/batch assignment → stamped): whichever card the
chain lands on, its person wins. There is deliberately NO sender fallback:
`submitted_by` stays ingest provenance (a claim about who MAILED the file)
and never becomes attribution — pinned by
`test_submitted_by_never_becomes_the_person`.

**Review**: a row that would otherwise be ready reads `check` with the new
`reason_code: "needs_person"` (rule 5: the human label rides in `reason`).
It fires LAST — a missing category, entity, or core field always outranks
it, because those are per-row fixes while a person is registry work.
`n_needs_person` sits beside `n_needs_entity` on both `summary` and
`card_review`.

## Unknown payment methods suggest a private expense (added 2026-09-06)

Backlog item 41, owner directive: "when payment methods arise that have
not been defined in the system they must be suggested to the user as
private expenses that will require reimbursement to the person who
expensed." SUGGESTED, never stamped; nothing auto-books. All fields are
PARALLEL (rule 1).

**Expense rows** gain:

| Field | Type | Meaning |
|---|---|---|
| `expenses[].suggested_private` | boolean | a non-empty payment hint resolves to no registered card (not ambiguous, not confirmed, no entity override), so this reads as private money until someone decides |
| `expenses[].private` | boolean | the operator confirmed it: a reimbursement row |
| `expenses[].reimburse_to` | string | who gets reimbursed; `""` unless confirmed |
| `expenses[].reimburse_to_prefill` | string | the `submitted_by` person, offered ONLY on suggested/confirmed private rows as a pre-fill for the confirm dialog. The ONE sanctioned use of the sender claim — it never fills `person` and must never generalize into sender-based attribution |

A suggested row reads `check` / `reason_code: "suggested_private"` (rule
5: prose in `reason`). The suggestion takes the entity check's slot: it IS
the sharpened needs_entity question for a row whose payment method the
registry does not know. Ambiguous hints (two cards claim them) keep
`needs_entity` — that is a known-card contest, not private money. An
explicit entity override also clears the suggestion: an operator decision
stands.

**Confirming**: `POST /api/runs/{id}/expenses/{document_id}/private` with
`{"private": true, "reimburse_to": "Dirk"}` (`reimburse_to` required;
400 without it). The row becomes a reimbursement row: `person` =
`reimburse_to` with `person_source: "private"` (the one bounded exception
to item 40's card-only rule), no entity required (it leaves
`n_needs_entity`), grid `posting_paid_through` reads
`{"account": "Private (Dirk)", "source": "private"}` — note the new
`source` value `private` on that existing enum-ish field; the row's own
`private` flag is the parallel signal a stale consumer can read.
`{"private": false}` clears both fields and the suggestion returns.
Assigning or registering the real card clears the SUGGESTION through the
existing flows; a CONFIRMED row stays confirmed until cleared here. Both
fields also ride the generic field-edit PUT (`private` accepts only
`"1"`, and ONLY when `reimburse_to` is already stored for the row — set
the person first, or use the POST route which takes both), and
`edited_fields` lists them like any other override. A `private` flag
without a person is never treated as a confirmation anywhere: the row
stays suggested, stays in `n_needs_entity`, and never reaches the
reimbursements section — a report must not state a reimbursement owed
to nobody.

**Strip**: `card_review.unresolved_hints[]` entries gain
`suggested_private` (boolean; any member row still suggested), which is
what the digit-less sub-strip renders as "no card number readable;
suggested as a private expense". `n_suggested_private` + `n_private` sit
beside the other counts on `summary` and `card_review`.

**Report and export**: the month report partitions confirmed private rows
out of the company listing into a "Reimbursements owed" section, grouped
per person with per-currency sums, numbering continuing the listing's;
their receipts stay in the evidence pages. The CSV keeps them as rows
(mixed-entity ruling: one file) with `Legal Entity` = `(private expense)`
and `Paid Through` = `Private ({person})` — the same strings the grid
shows.

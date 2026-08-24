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
| `n_ready` | how many need NOTHING from the reviewer (category, entity, core fields) |
| `n_review` | how many are flagged for a look (`check` or `pick`) |
| `n_needs_entity` | how many could not resolve a legal entity |
| `n_set_aside` | how many files the quarantine is still holding back |

`service.categorized_counts` is the single implementation of the categorized
rule; `service.batch_list_summary` derives the list screen's counts from the
same live overlay the batch page renders, so a reviewer's edit moves both. A
new count gets a row here and its own name — never a second meaning on an
existing one.

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
| `entries[].pool_month_state` | string | pooled rows only: `no_batch`, `open` (a claim is imminent), `closed` (the month is already reconciled) |
| `n_pooled` | number | top-level, beside `n_held`. Distinct MAILS, not log rows |
| `entries[].status_kind` | string | how to TREAT this row: `resting` (fine, waiting on something scheduled), `held` (needs a human), `working` (in flight, resolves in seconds), `done` (nothing owed), `unknown` (a status this backend build does not know). Added 2026-08-24 |
| `entries[].status_label` | string | what to SAY, already composed in English: "Waiting for July 2026", "Needs one click to read", "Added". For an unrecognised status this is the raw status value, never a borrowed label |
| `n_refused` | number | top-level. Mail TURNED AWAY in the last 7 days (SMTP refusals). `0` is the answer to "is anything bouncing?", and before 2026-08-24 there was none |
| `refusals[]` | object `{at, stage, reason, from, to, peer}` | the newest refusal rows, oldest->newest. `stage` is `rcpt` (recipient refused) or `data` (accepted the envelope, then a guard turned the message away: disk floor, in-flight ceiling, day budget, archive failure) |

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

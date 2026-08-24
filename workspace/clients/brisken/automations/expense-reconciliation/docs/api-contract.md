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

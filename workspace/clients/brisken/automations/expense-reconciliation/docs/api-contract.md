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
| `summary.upload_issues[]` | string |
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

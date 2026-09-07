# Lovable prompt: cross-batch settlement badges (settled_by)

> **NOT YET APPLIED.** Paste after the R4 backend deploy.
>
> Every field named here is NEW, PARALLEL, and ABSENT unless a
> cross-batch settlement exists, so the page keeps working untouched
> and nothing breaks if you ship only part of this. Render defensively:
> check the object exists before reading its keys.

Backend is deployed. A month's statement matching now spans trips: a
charge on the company card during a trip finds its receipt in the trip's
own batch, and one receipt can never settle two charges across two
batches. The two payloads name each other where that happens.

---

## 1. Month workbench: rows carry `settled_by`

On `GET /api/runs/{id}`, a workbench row whose charge was settled by a
receipt from a trip carries a new optional object:

```json
"settled_by": { "run_id": "a0a62c55ecf4",
                "trip_id": "8c1f30aa2e41",
                "label": "Rome 2026" }
```

When present, render a small badge on the row next to the match state:
**"settled by trip {label}"**, linking to `/expenses/{run_id}` (the
trip's batch page). Absent on every row settled from the month's own
receipts, which is almost all of them.

The same key can appear on `unmatched_receipts[]` and
`assignable_receipts[]` entries, there shaped
`{run_id, label, transaction_id}`: that receipt belongs to this batch
but already settles a charge in ANOTHER batch. Badge it
**"settles a charge in {label}"** and do not offer it for hand-matching.

## 2. Trip batch page: expenses carry `settled_by`

On `GET /api/expense-batches/{id}` (a trip's batch), an expense whose
receipt settled a company month's charge carries:

```json
"settled_by": { "run_id": "b7d2e91c04aa",
                "label": "April 2026",
                "transaction_id": "..." }
```

Badge the row **"settles a charge in {label}"**, linking to
`/expenses/{run_id}`. This is the trip-side mirror of section 1; absent
on every receipt no statement has claimed.

## 3. A refused pick is a 409 with a sentence

`POST /api/runs/{id}/decisions` and `POST /api/runs/{id}/manual-match`
can now answer **409** with `{"error": "..."}` when the picked receipt
already settles a charge in another batch. Show the sentence as the
error toast exactly as other API errors are shown; nothing was written
when a 409 comes back.

## 4. The trip report button

Nothing to build: the existing report download on a trip's batch page
already returns the trip report (sectioned per traveler, titled by the
trip). If the button's label is hardcoded "Expense report", rename it to
just **"Report"** so it is honest on both batch kinds.

# Lovable prompt - a receipt borrowed from the month next door (item 61)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

A receipt is filed by the month printed on it; a charge lands in the statement
that billed it, and the two boundaries do not line up. Chase opens August's
workbook on 07-31 and July's on 06-30, so a subscription invoiced on the last
day of a month posts on the 1st of the next statement while its receipt is
already sitting in the previous month's batch. On 2026-09-15 August held two
Google receipts dated 08-31 (71.64 and 75.09) whose charges post on 09-01,
while August's own 08-01 Google 71.64 charge showed no receipt at all. The
backend now lets a month's matcher reach into the months either side of it,
under the same one-receipt-settles-one-charge rule that already governs trips.
The workbench already badges a charge settled from a TRIP; this extends that
badge to a neighbouring month and adds the same naming to candidates.

## 1. `settled_by` now has two kinds

`GET /api/runs/{id}` -> `rows[].settled_by`, unchanged for trips, new for
months. Absent (not null) on every row settled from the month's own receipts,
which is almost all of them.

```json
"settled_by": { "run_id": "a0a62c55ecf4",
                "trip_id": "8c1f30aa2e41",
                "label": "Rome 2026" }

"settled_by": { "run_id": "50622baec444",
                "label": "July 2026",
                "kind": "adjacent" }
```

Read `kind`, never the absence of `trip_id`. `kind === "adjacent"` means a
neighbouring month; anything else (today: no `kind` at all) is the trip badge
you already render.

- trip: **"settled by trip {label}"**, linking to `/expenses/{run_id}`.
- adjacent: **"from {label}"**, linking to `/expenses/{run_id}`.

## 2. The new field: `rows[].candidates[].from_batch`

Same object, on the candidate rather than the row. Parallel and **absent**
(not null) on every candidate from this month's own pool:

```json
"from_batch": { "run_id": "50622baec444",
                "label": "July 2026",
                "kind": "adjacent" }
```

A borrowed receipt used to be anonymous until it won: the row badge appeared
only once the pairing was chosen, so an offered candidate read as if it
belonged to this month. Render a small muted chip on any candidate carrying
`from_batch` - **"from {label}"** for `kind === "adjacent"`, **"from trip
{label}"** otherwise - clickable to `/expenses/{run_id}`. The candidate stays
fully pickable; this is provenance, not a restriction.

## 3. The tile: `summary.n_adjacent_borrowed`

Integer on the run payload, 0 on every month whose neighbours lent it nothing.
It counts the receipts this month is actually USING from the months either
side, not what the pool offered. Put it beside the existing tiles, labelled
`wb.tile.adjacentBorrowed`, neutral at 0.

## 4. i18n keys

| Key | EN | PT |
|---|---|---|
| `wb.charge.fromMonth` | From {label} | De {label} |
| `wb.candidate.fromMonth` | From {label} | De {label} |
| `wb.candidate.fromTrip` | From trip {label} | Da viagem {label} |
| `wb.tile.adjacentBorrowed` | Receipts from next door | Recibos do mes vizinho |

The existing trip string on the row (`settled by trip {label}`) keeps its key
and its copy.

## 5. The other side already works

On the LENDING month, the receipt carries `settled_by` shaped
`{run_id, label, transaction_id}` in `unmatched_receipts[]` /
`assignable_receipts[]` and on the expense grid, and you already render that
as "settles a charge in {label}". Nothing to build; it is now reachable
between two ordinary months instead of only between a month and a trip.

## 6. Do not change

The bucket, the section, `candidates[].is_chosen`, `held_by`, and every
existing count keep their meaning. `n_receipts` deliberately does NOT include
a borrowed receipt: it stays an expense of its own month, and this month's
export and report never absorb it. Every field here is additive, so a month
that borrows nothing renders exactly as it does today.

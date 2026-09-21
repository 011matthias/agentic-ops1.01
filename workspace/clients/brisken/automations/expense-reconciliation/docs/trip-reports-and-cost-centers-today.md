# Trip reports and cost centers, as they are today

Written 2026-09-21 as the input to the owner's brainstorm on implementing
both together (item 38, Q1: the trip entity survives, the design is on
hold). This file describes only what is BUILT and running. It proposes
nothing.

Every claim below is anchored in source at `218cdca0`, or measured on a
read-only copy of the live store on 2026-09-21.

## A cost center, today

**One flat map, authored by the owner and nobody else.**
`settings["cost_centers"]` is `{name: {kind, note, active}}`, replaced
whole at the settings edge like `cards` and `merchants`. `kind` is one of
`project` / `function` / `trip` / `""` and is display-only: it groups the
roll-up and never participates in resolution. There is no hierarchy and
there are no dates.

The tool never invents a cost center and never learns a new NAME. Learning
only ever re-uses a name the owner has already defined
(`cost_centers.py` D1).

**An empty registry resolves nothing and flags nothing.** This is the
load-bearing clause, not a convenience: without it, the day the field
shipped every row in every month would have read `needs_cost_center`.
`resolve()` short-circuits before it examines any candidate
(`cost_centers.py:184-186`).

**Resolution is per ROW, first hit wins** (`cost_centers.py:171-201`):

```
override  >  trip  >  merchant  >  card  >  unresolved
```

Person is deliberately not a resolver (it cannot separate "Nicolas in
Brazil" from "Nicolas on Lidar") and category is not one either. One row
gets one cost center; v1 refuses splits.

One asymmetry inside the chain: an override may name an INACTIVE center,
because a reviewer correcting history is deliberate; a default may not,
because a default must not resurrect a retired center
(`cost_centers.py:197-200`).

**What the row carries:** `cost_center`, `cost_center_source`,
`cost_center_source_label` (the human phrasing, e.g. "from the trip"),
and `needs_cost_center`. All parallel fields, absent or silent until the
registry has a name in it.

**Where it rolls up:** a company month's report partitions its listing by
cost center, and `GET /api/cost-centers/totals` aggregates across every
batch. Both carry the same stated limit verbatim
(`COST_CENTER_SCOPE_NOTE`): this tool sees card and receipt spend only,
never contractor invoices or salaries, so a figure here is not a total
project cost.

**Live state:** the registry is empty, so every line above is inert. Dirk
will author the four names (item 38 Q2, answered 2026-09-21). Measured
consequence of that first save, on a copy: `needs_cost_center` turns on
for **183 expense rows across all seven company months** (April 34, May 3,
June 7, July 54, August 25, September 60, January 0) and **none of them
resolve**, because no merchant and no card default names a center yet.

## A trip, today

**An entity plus exactly one batch.** A trip has a name, an inclusive
`start_date` and `end_date`, a `travelers` roster (a list of person names,
variable by owner ruling), and one `cost_center` string. Its expense batch
materializes on the first receipt join rather than being created empty, so
`batch_id` and `summary` are null until then.

**What a trip does that a label cannot:**

- owns a batch and holds receipts
- lends those receipts to every company month whose charge span overlaps
  its date range, with `receipt_claims` arbitrating so one receipt never
  settles two charges
- refuses a statement outright (400 `statement_on_trip`): a trip's
  receipts reconcile against the company month's statement
- carries a roster, and flags a row whose resolved person is not on it
- sections its report per person

**Its report** is the same listing plus receipt-evidence document as a
month's, with the LISTING grouped by person: roster order first, other
named persons after, unowned rows last, numbering continuous, a sum per
person, and an off-roster person captioned "(not on the trip roster)".
Title `Trip report: {name}`, subtitle `{start} to {end} · travelers: ...`
(`service.py:8909-8915`).

## Where the two touch today: one field

`TripRow.cost_center`, at position 2 of the chain. A human declares it
once when the trip is created, and every row of that batch then reads it
without anyone typing it again. The row's source reads `trip` and its
label "from the trip".

The design note in `store.py:283-286` states why it sits that high: a trip
is the strongest AUTOMATIC cost-center signal, because a human DECLARED it
at creation rather than anything inferring it from content.

Verified on real data 2026-09-21: a trip created with cost center Brazil
put `cost_center: "Brazil"` / `cost_center_source: "trip"` on all three of
its rows, and the cross-month totals route attributed the batch's full
USD 350.15 to that center.

One deliberate looseness: the trip's cost center is **not** checked against
the registry. Trips and cost centers are edited on independent screens, so
the edit ORDER must not matter, and a trip may name a center that does not
exist yet (`validate_trip_fields`). Only a row-level override is validated,
with a 400 `cost_center_not_defined`.

## Where the two do NOT touch

**The trip report never prints the trip's cost center, and never partitions
by it.** The branch in `build_expense_report` is exclusive
(`service.py:8433` onward): `is_trip_batch(run)` takes the per-person
sections, and only the `else` arm runs the cost-center partition. So a trip
report is sectioned by person and a company month by cost center, and
neither document does the other. The trip report also carries no
"Listing by ..." heading, because `sections_heading` is set only on the
company arm, where it reads "Listing by cost center".

Confirmed by differential probe on 2026-09-21, not by reading alone: with
the trip's center renamed to a string that appears nowhere else, the
rendered PDF contained neither that string nor the words "cost center",
while the grid and the totals route both carried it.

## Three frictions the design will meet

Stated, not solved.

**A trip is a container; a cost center is a label.** A cost center has no
dates, no batch, no lifecycle and no locks; it is one row in a whole-map
replace object. Everything in the "what a trip does that a label cannot"
list above would need a lifecycle bolted onto `settings["cost_centers"]`
for a cost center to absorb a trip. In the other direction, attribution is
genuinely the same question for both: a Brazil trip IS a cost center like
any other purpose, which is the owner's 2026-09-20 observation and it is
correct.

**Deactivating a center silently unlabels a finished trip's history.**
`resolve()` exempts only `SOURCE_OVERRIDE` from the inactive skip, so a
trip's declared center is treated like a card default. Retire the center
after the trip closes and every row of that trip loses its label, with
nothing pointing at the cause. The only pin for the inactive rule uses a
card (`test_cost_centers.py:99`), so no test covers the trip case.

**Sign-off teaches a trip-kind center to a merchant.**
`registry_cost_center_upserts_from_expense_run` folds a month's explicit
per-row picks into the merchant registry, and it reads `kind` zero times
(verified by grep over the function). One Lufthansa receipt picked as a
trip center would make every future Lufthansa receipt read that center,
with `cost_center_source: merchant` and no flag.

## Related

- `docs/api-contract.md`: "The two batch functions: `batch_type` + `trip`",
  "The trip-spanning pool (R4b)", "The trip report", "Cost centers"
- `status/p1-improvement-backlog.md` items 38 and 47
- `status/p1-expense-reconciliation.md`, the R4 row (the 2026-09-21
  real-data verification and its two lifecycle defects)

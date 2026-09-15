# Lovable prompt: cost centers, the second way to cut the money

> **NOT YET APPLIED.** Paste after the item-47 backend deploy (steps 1-5,
> branch `client/brisken/p1-cost-centers`).
>
> SEQUENCING, load-bearing: sections 1 and 2 (the Settings editors) must
> be live in the published SPA BEFORE the owner types a single cost
> center or card default in. Both maps are replaced WHOLE on save: a
> published SPA that does not read and write `cost_centers`, or that
> saves a card without its `default_cost_center`, silently erases them on
> its next settings save. This is the trap that hit `person` on cards.
> Everything else ships in any order; every field named here is NEW and
> PARALLEL, so the page keeps working if you ship only part of this.

Backend is deployed. An expense row now has a fourth attribute beside
category, legal entity and person: which project or purpose the money
belongs to. Dirk defines the list himself (a project like Lidar, a
function like marketing, a trip like Brazil); the tool never invents a
name. Until he has defined at least one, nothing in this prompt shows
anything: no flag, no chip, no empty section. Render defensively
throughout: a missing or unexpected `cost_center*` field degrades to
blank, never to an error boundary.

The stated limit, on every screen that sums by cost center: this tool
only sees money that flows through a Brisken card or a receipt.
Contractor invoices, salaries and anything paid another way never enter
it, so a cost-center figure here is card-and-receipt spend, not total
project cost. The backend sends this sentence verbatim as `note` on the
totals payload; show it, do not paraphrase it.

---

## 1. Settings > Cost centers (ship FIRST, see header)

`GET /api/settings` returns `cost_centers`: an object keyed by name,
each `{kind, note, active}`; `kind` is `project`, `function`, `trip`
or blank and is display-only. Add a list editor under Settings, beside
Merchants and Cards:

- Columns: name (text, required), kind (select: project / function /
  trip / blank), note (text, optional), active (toggle, default on).
- Save sends the WHOLE map back in `PUT /api/settings` as
  `cost_centers`, including entries this session did not touch. Read the
  current object, change the rows, send everything back.
- The backend 400s on an unknown `kind` and on two names that differ
  only in case (one cost center, two spellings); show the error verbatim.
- An empty list is a normal state. Render an explanatory empty view
  ("No cost centers defined yet. Define one to start attributing
  expenses to projects and purposes."), not an error.

## 2. Settings > Cards: one added field (ship FIRST, see header)

Each card gains `default_cost_center` (string, `""` unset) on
`GET /api/cards` and in the cards settings map. Add a picker per card
over the defined cost centers plus blank, labelled "Default cost
center". The cards save payload must keep carrying `entity`, `person`
and now `default_cost_center` for every card; a partial write erases the
rest. The default reaches an EXISTING month only through the batch's
refresh-master-data action, whose `changes` now carries a
`row_cost_centers` count beside `row_persons`; show it in the same
toast.

## 3. The expense row

Every row in `GET /api/expense-batches/{id}` carries:

- `cost_center` (string or null): the resolved name.
- `cost_center_source` (`override` | `trip` | `merchant` | `card` | `""`)
  and `cost_center_source_label`, its human-readable twin ("set by
  reviewer", "from the trip", "learned for this merchant", "default for
  this card"). Render the LABEL, never map the enum by hand.
- `needs_cost_center` (boolean).

Add a cost-center cell: a picker offering only the names in the batch's
`cost_center_options[]` (objects `{name, kind, note}`, active entries
only), ordered with the row's person's most-used first, blank allowed.
Show `cost_center_source_label` beside the value so a filled-in row says
WHY it is filled in. Picking a value sends
`PUT /api/runs/{id}/expenses/{doc}` with `{"field": "cost_center",
"value": "<name>"}`, exactly like every other field override; blank
clears it. The backend 400s on a name it does not define and stores its
own spelling, so a picked name and a typed one cannot read as two
centers. The row's `edited_fields` then contains `cost_center`.

## 4. Review

`reason_code: "needs_cost_center"` is a new value; render its `reason`
prose like any other. `summary.n_needs_cost_center` sits beside
`n_needs_person`; surface it as a chip in the same place. Both stay
invisible while the count is zero, which is the whole first phase: the
backend guarantees zero until at least one cost center exists.

## 5. Trip page

The trip object gains `cost_center` (string, `""` unset). Add one picker
on the trip, saved through `PUT /api/trips/{id}` with `{"cost_center":
"<name>"}`; omitted keeps, `""` clears, so the roster save can keep
sending only `travelers`. A trip's cost center fills every row in its
batch (source label "from the trip") unless a reviewer overrides a row.

## 6. Cross-month view

One screen over `GET /api/cost-centers/totals?from=&to=`, reachable from
the months list. A date range (both fields optional, inclusive), then
one row per entry in `cost_centers[]` (name-sorted; each carries `name`,
`kind`, `active`, `n_rows`, `n_batches`, `totals` as `{currency: amount}`,
amounts already formatted), then the `unassigned` row with the same
shape, never hidden, and the `note` sentence as a standing caption under
the table. An inactive center appears only while rows still sit on it;
mark it. Show `n_batches` ("across N months and trips") and, when
`n_undated` is above zero, one line saying that many rows carry no date
and are counted regardless of the range. A 400 carries `{"error": prose}`;
show it verbatim. With no cost center defined the list is empty and
everything is unassigned: render that as the fact it is, with the same
explanatory empty copy as section 1.

## 7. Month report

No SPA change. The month report PDF now groups its listing by cost
center once one is defined, with an unassigned section last and the
stated limit above the partition; a trip report is unchanged.

# Lovable prompt - a trip expense whose person is not on the roster (item 38)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

A trip carries a roster of travelers. Each of its expense rows resolves a
person through the card it was paid on. When the two disagree, the backend
says so on the row, and has done since 2026-09-07.

Nothing renders it. A cold browser drive on 2026-09-21 (a real trip, two
travelers, a third person's receipt in the batch) found the API reporting
`n_roster_mismatch: 1` and the printed PDF captioning that person
"(not on the trip roster)", while the trip page showed no marker at all. The
one surface where a human would act on it is the only one that stays silent.

This prompt is rendering only. There is no backend change.

## 1. The fields, both already live

`GET /api/expense-batches/{id}` on a TRIP batch:

`expenses[].roster_mismatch` - boolean. The key is **absent** on company
months, so nothing on a month page changes.

```json
"roster_mismatch": true
```

`summary.n_roster_mismatch` - integer, same trip-only presence.

The trip object on the same payload carries the roster to add to:

```json
"trip": {
  "trip_id": "e9fd8f89f231",
  "name": "Rome 2026",
  "start": "2026-09-20",
  "end": "2026-10-03",
  "travelers": ["Dirk Neumann", "Criss"],
  "cost_center": "Brazil"
}
```

Three rules the backend already applies, so the UI does not repeat them:
an EMPTY roster flags nothing; a row with no resolved person is
`n_needs_person`'s business and never a mismatch; the comparison is exact
after trim and casefold.

## 2. The row marker

On a trip batch row with `roster_mismatch: true`, render a quiet marker
beside the person, in the same muted weight the row uses for
`cost_center_source` ("from the trip"). Not a badge, not a colour that reads
as an error.

**This is a flag, never a block.** It must not enter any review bucket, any
readiness or completeness count, or anything that gates publish. A trip with
three mismatches is a trip somebody has not finished typing the roster for.

## 3. The fix is one action, and it is on the TRIP

The likely correction is that the roster is short, not that the row is wrong.
Beside the marker, offer one action: **"Add {person} to the roster"**.

It calls `PUT /api/trips/{trip_id}` with a roster-only body:

```json
{ "travelers": ["Dirk Neumann", "Criss", "Nicolas Neumann"] }
```

**`travelers` replaces the whole list.** Send the trip's current
`travelers` array with the new name appended, never the name alone, or every
other traveler is dropped. Every other key may be omitted: the route merges
omitted keys with the stored trip, so a roster-only body leaves the name,
the dates and the cost center untouched.

On 200, refetch the batch. The row's `roster_mismatch` clears and
`n_roster_mismatch` drops, because the backend recomputes both from the live
trip on every read.

Do **not** offer an "edit the person" action here. Changing the person is an
existing row edit and belongs where row edits already live.

## 4. The header count

`summary.n_roster_mismatch` in the trip page header, beside the existing
counts, labelled `trip.rosterMismatch.count`. Neutral styling at any value;
hide it at 0.

## 5. i18n keys

| Key | EN | PT |
|---|---|---|
| `trip.rosterMismatch.row` | Not on the trip roster | Fora da lista de viajantes |
| `trip.rosterMismatch.add` | Add {person} to the roster | Adicionar {person} a lista |
| `trip.rosterMismatch.count` | {n} not on the roster | {n} fora da lista |
| `trip.rosterMismatch.added` | {person} added to the roster | {person} adicionado a lista |

## 6. Do not change

`person`, `person_source`, the card chain display, `cost_center` and its
source label, `settled_by`, and every count on the trip page keep their
meaning. A company month never carries `roster_mismatch`, so no month page
changes. A trip with an empty roster carries `false` on every row and shows
nothing.

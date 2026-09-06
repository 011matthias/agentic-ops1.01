# Lovable prompt: trips beside months, declared batch type, the travel pool

> **NOT YET APPLIED.** Paste after the R3 backend deploy.
>
> SEQUENCING, load-bearing: section 5 (the Settings travel-alias field)
> must be live in the published SPA BEFORE anyone types the alias in.
> The `intake` settings object is replaced wholesale on save, so a
> published SPA that does not know the `travel_alias` key would silently
> erase it on its next settings save. Everything else can ship in any
> order; every field named here is NEW and PARALLEL, so the page keeps
> working if you ship only part of this.

Backend is deployed. The expense tool now has TWO functions: overall
monthly company expenses (everything the app did until now) and trips.
Which one a batch is gets declared when it is created, never guessed
from content.

---

## The change in one paragraph

A **trip** is its own thing: a name, a date range, and a variable list
of travelers. Trips live in their own list next to the months. Emailed
receipts addressed to the travel address wait in the pool like month
mail, but they are never added anywhere automatically: a person puts
each one on its trip with a click, and when the receipt's date falls
inside exactly one trip's range the row already suggests that trip.

## 1. Trips list beside /months

New API: `GET /api/trips` returns `{ trips: [...] }`, each:

```json
{ "trip_id": "8c1f30aa2e41",
  "name": "Rome 2026",
  "start": "2026-09-20",
  "end": "2026-10-03",
  "travelers": ["Dirk Neumann", "Criss"],
  "batch_id": null,
  "summary": null }
```

Add a **Trips** screen beside the months list (same nav level). One row
per trip: name, date range, travelers (render the list; it can be empty
or long), and the receipt counts from `summary` when `batch_id` is not
null. `batch_id: null` means no receipt has joined yet; show "No
receipts yet", never a zeroed summary. A row with `batch_id` links to
`/expenses/{batch_id}` exactly like a month row does.

Create / edit / delete:

- `POST /api/trips` with `{name, start, end, travelers}` (dates
  `YYYY-MM-DD`, travelers an array of names, may be empty).
- `PUT /api/trips/{trip_id}` with any of those fields; `travelers`
  replaces the whole list.
- `DELETE /api/trips/{trip_id}`; a 409 means the trip still has an
  expense batch (delete that first from its batch page).

## 2. Batch creation declares the type

`POST /api/expense-batches` accepts two new form fields:

- `batch_type`: `"company-month"` (the default when absent) or
  `"trip"`.
- `trip_id`: required when `batch_type` is `"trip"`.

Give the create dialog a type choice defaulting to company month. For a
trip upload, offer the trips that exist (from `GET /api/trips`) instead
of a free-text label; the label defaults to the trip's name server-side.
A 409 on create means the trip already has a batch — add the receipts to
that batch instead (the reply names it in `batch_id`).

The months list (`GET /api/expense-batches`) now carries `batch_type`
on every row; it will always be `"company-month"` there, because trip
batches appear only under Trips.

## 3. The batch page knows its trip

The batch payload (`GET /api/expense-batches/{id}`) carries two new
top-level fields:

- `batch_type`: `"company-month"` or `"trip"`.
- `trip`: `null` on company months; on a trip batch an object
  `{trip_id, name, start, end, travelers}`.

On a trip batch, show the trip header (name, range, travelers) where a
month page shows its month, and do NOT show the month-rename suggestion
banner (`period_suggestion` is always null on trips). The statement
upload control must be hidden on trip batches: the backend refuses it
with a 400 (trip receipts reconcile against the company month's
statement in a later round).

## 4. Travel mail in the inbound pool

`GET /api/inbound/log` rows gain two parallel fields, and one count:

- `entries[].pool_kind`: `"travel"` on travel mail; absent on month
  mail. A travel row is `status: "pooled"` like month mail, but it is
  waiting for a PERSON, not for a month: never show the month-waiting
  copy on it, and it has no `pool_month_state`.
- `entries[].trip_suggestion`: present only when the receipt's dates
  fall inside exactly one trip's range:
  `{trip_id, name, start, end}`. It is a suggestion; nothing happens
  without the click.
- `n_pooled_travel`: how many of `n_pooled` are travel mail.

Render travel rows with the backend's `status_label` (it already says
`Travel, waiting for its trip` or `Travel; reads as "Rome 2026"`), plus
a **Add to trip** action on the row:

- With a `trip_suggestion`: a one-click "Add to {name}" button plus a
  picker for choosing a different trip.
- Without: a picker over `GET /api/trips`.

The click: `POST /api/inbound/{archive}/join-trip` with
`{"trip_id": "..."}`. A 200 reply carries `batch_id` (open it or toast
it); `created_batch: true` means this receipt just opened the trip's
batch. 409 means the mail is not travel mail or is no longer waiting;
404 means the trip is gone — refresh the picker.

## 5. Settings: the travel address (ship FIRST, see header)

The intake settings gain `travel_alias`: the local-part of the travel
address (the part before the @). Add a text field to the mail-intake
settings section, labelled "Travel address", shown as
`{travel_alias}@{domain}` when set and "Not set" otherwise. Send it
inside the SAME `intake` object the page already reads and writes back
whole — read the current object, change this one key, send everything
back. Empty string clears it. The backend rejects `"receipts"` and any
value that collides with a person alias (400 with a plain-language
error; show it verbatim).

Until the owner sets this field, no mail is ever travel mail and
nothing in sections 1-4 changes anything about live behavior.

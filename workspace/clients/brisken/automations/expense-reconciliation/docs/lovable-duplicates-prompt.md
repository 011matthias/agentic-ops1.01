# Lovable prompt: duplicates on the row

Paste into Lovable against `brisken-reconcile-dash`. The backend half
shipped 2026-08-28; nothing here needs a deploy on our side.

## What changed on the API

Every row that belongs to a flagged duplicate group now carries a
`duplicate` object. It is `null` on ordinary rows and on every payload
built before today, so a renderer that ignores it keeps working.

Where it appears:

- expense grid: `expenses[].duplicate`
- workbench: `rows[].duplicate` (a charge billed twice),
  `unmatched_receipts[].duplicate` and `assignable_receipts[].duplicate`
  (the same receipt twice)

```json
{ "group_id": "cfdacfc912a79a47",
  "kind": "receipt",
  "n_copies": 2,
  "copy": 2,
  "of": "0039__Invoice-B2EA98DF-0020.pdf",
  "is_extra": true,
  "resolution": null }
```

`copy` is this row's place in the group and `of` is the id of the first
copy, so a row can point at the original instead of both rows looking
equally suspect. `is_extra` is false on the first copy and true on the
rest.

Two summary counts, and they answer different questions:
`summary.n_duplicate_groups` is how many duplicate situations there are;
`summary.n_duplicate_copies` is how many copies are redundant.

## 1. The row badge

On any row where `duplicate` is not null, show a small badge next to the
vendor:

- `is_extra: false` → muted grey, "1 of 2" (this is the original)
- `is_extra: true` → amber, "duplicate · copy 2 of 2"

Clicking the badge scrolls to and briefly highlights the row whose
`document_id` (or `transaction_id`) equals `duplicate.of`.

Guard every read: `row.duplicate?.is_extra`. The field is null on most
rows and absent on older payloads.

## 2. The header count

Where the batch header shows its counts, add one more only when
`summary.n_duplicate_copies > 0`:

> 1 duplicate copy

Plural past one. Clicking it filters the grid to rows with a non-null
`duplicate`.

## 3. Two actions on the badge's row

**Delete the extra** (only on `is_extra: true`):
`DELETE /api/runs/{runId}/expenses/{documentId}`. This is the action the
flag exists to prompt; after it the group is gone and the remaining row's
badge disappears on its own.

**Not a duplicate:**
`POST /api/runs/{runId}/duplicates/resolve`
`{ "group_id": row.duplicate.group_id, "action": "ignore" }`
clears the badge from every row in the group and drops it out of the
count. `"action": "confirmed"` acknowledges it and keeps the badge, for
when somebody has looked and the second copy still has to go.

Both endpoints reply `{ ok, summary }` with the summary of the payload
you are on, so the header can be updated from the reply without a refetch.

## 4. What not to do

Do not subtract duplicates from `totals_by_ccy`. The backend sums every
row on purpose: the tool flags and the reviewer decides, and a total that
disagreed with the rows printed above it would be a worse problem than
one that is honestly high with the reason marked on the row.

# Lovable prompt - the count beside the month total (item 65)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

The month total on the batch page sums the amounts the tool could read. A
receipt whose amount was never read is in no total at all: it is skipped in
silence, and the total above it looks complete. The backend now says how many
there are, so the number beside the total can carry its own caveat instead of
the reviewer discovering the gap by adding the column up. The PDF report got
the same disclosure on 2026-09-15 (a caption on the row, a footer naming the
excluded expense numbers); this is the screen half.

## 1. The new field

`GET /api/expense-batches/{id}` -> `summary.n_amounts_unreadable`, an integer,
beside the existing counts:

```json
"summary": {
  "totals_by_ccy": { "EUR": "700.00", "USD": "2,663.95" },
  "n_amounts_unreadable": 0
}
```

It counts expenses in this month whose amount could not be read, which is the
same population `totals_by_ccy` skips. It is `0` on both live months today.

## 2. The render rule

Beside the month total, small, muted, and **nothing at all when the value is
0** (which is the normal case, so the page must look unchanged today):

- `1` -> `wb.total.amountsUnreadable.one`
- `2` or more -> `wb.total.amountsUnreadable.many` with `{count}`

Not a badge, not a warning colour, not a tile: one line of muted helper text
under the total. It qualifies a number the reviewer is already reading. If the
field is absent (an older cached payload), render nothing.

## 3. i18n keys

| Key | EN | PT |
|---|---|---|
| `wb.total.amountsUnreadable.one` | 1 expense has no readable amount and is not in this total | 1 despesa nao tem valor legivel e nao esta neste total |
| `wb.total.amountsUnreadable.many` | {count} expenses have no readable amount and are not in this total | {count} despesas nao tem valor legivel e nao estao neste total |

## 4. Do not change

`totals_by_ccy` keeps its meaning and its format (a string per currency,
already grouped and to two decimals). Every other count keeps its name and its
question. `n_amounts_unreadable` is additive and scalar: a month where every
amount read carries `0`, and the page renders exactly as it does today.

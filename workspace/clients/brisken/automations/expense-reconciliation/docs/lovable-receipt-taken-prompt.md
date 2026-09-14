# Lovable prompt - "No receipt found" on a charge whose receipt is elsewhere (item 60)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

A charge can show candidate receipts and still be bucketed `unmatched`. That
is not a bug: `candidates[]` keeps every receipt the matcher paired with the
charge, while the bucket reflects the ASSIGNMENT, and one receipt settles
exactly one charge. When another charge takes the receipt, the first one keeps
the candidate on display and drops to `unmatched`.

The page currently derives its label from the bucket, so it says "No receipt
found" about a receipt sitting on the row above. Reported 2026-09-11.

## 1. The new field

`GET /api/runs/{id}` -> `rows[].candidates[].held_by`, parallel and **absent**
(not null) unless another charge holds that receipt:

```json
"held_by": {
  "transaction_id": "…",
  "vendor": "SUPABASE",
  "amount": "92.70",
  "currency": "USD",
  "date": "2026-08-19"
}
```

`summary.n_charges_receipt_taken` (integer, both payloads) is how many charges
are bucketed `unmatched` while every candidate they carry is held elsewhere.

## 2. The row label

Where a charge currently renders "No receipt found", check the row first:

- bucket `unmatched`, no candidates at all: keep "No receipt found".
- bucket `unmatched`, candidates present and **every** one has `held_by`:
  render "Receipt is on another charge" instead, and list each holder as
  `{vendor} · {amount} {currency} · {date}`, each clickable to scroll that
  charge into view (the transaction_id is on the row).
- bucket `unmatched`, some candidates without `held_by`: those are free
  receipts the reviewer can still pick; keep today's candidate list.

A candidate that carries `held_by` renders muted with the holder named, so it
reads as information rather than an option.

## 3. i18n keys

| Key | EN | PT |
|---|---|---|
| `wb.charge.receiptTaken` | Receipt is on another charge | O recibo esta noutro lancamento |
| `wb.charge.receiptTaken.holder` | On {vendor}, {amount} {currency}, {date} | Em {vendor}, {amount} {currency}, {date} |
| `wb.tile.receiptTaken` | Waiting on a pick | A aguardar escolha |

## 4. Optional tile

`summary.n_charges_receipt_taken` beside CHARGES WITHOUT A COMPANY, labelled
`wb.tile.receiptTaken`. Neutral at 0. It is the count of rows that look like
"no receipt" today and are really a contested pick.

## 5. Do not change

`candidates[].is_chosen`, the bucket, the section, and every other count keep
their meaning. `held_by` is additive: a month with nothing contested does not
carry the key at all, and the page renders exactly as it does today.

# Lovable prompt - show how each statement was read (item 64)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

This extends `lovable-attach-dialog-prompt.md`, which is already applied. That
prompt made the card and its currency pickable at attach time; this one shows,
afterwards, what the tool actually read the file as.

## Background

A wrong card currency silently ruins a month: the matcher reads every
statement amount as that currency, so a BRL entry against a USD card
reconciles near zero. That happened in April (operator, 2026-08-28) and was
invisible after the fact, because nothing on screen said which currency the
upload had been read at, or which column the parser had taken each field
from. Since 2026-09-15 the backend records both per upload, and the re-read
reuses them instead of guessing again. This puts them on screen.

## 1. The new fields

`GET /api/runs/{id}` and `GET /api/expense-batches/{id}` -> each
`statements[]` entry gains two PARALLEL keys, both **absent** (not null) on
uploads recorded before 2026-09-15:

```json
{ "file": "July2026.xlsx",
  "upload_name": "July2026.xlsx",
  "column_map": { "transaction_date": "Date", "vendor": "Description",
                  "amount": "Amount", "type": "Type", "card": "Card" },
  "card_currency": "USD" }
```

- `card_currency` is an upper-case currency code.
- `column_map` maps the backend's logical field name (key) to the column
  header in that file (value). Which keys appear depends on the file: only
  `transaction_date`, `vendor` and `amount` are always there.
- A PDF statement carries neither key, because it has no columns.

Both are absent on every upload in production today, so the fallback below is
the state you will see first, not an edge case.

## 2. The statements table

In the statements table (columns today: file, `stm.col.period`,
`stm.col.rows`, `stm.col.new`, `stm.col.uploaded`), add one column
`stm.col.readAs` before `stm.col.uploaded`.

Per row:

- `card_currency` present: render it as plain text, e.g. `USD`.
- `column_map` present: below it, a small toggle labelled
  `stm.readAs.columns` that expands a two-column list of
  `logical field` -> `column header`, one pair per line, the logical field in
  mono. **Do not translate the logical field names**; they are the backend's
  identifiers and the operator matches them against what the attach dialog
  showed. Collapsed by default.
- Neither key present: render `stm.readAs.unrecorded`, muted. This is not an
  error; it means the upload predates the recording.

Column header tooltip / helper: `stm.readAs.help`.

## 3. i18n keys

| Key | EN | PT |
|---|---|---|
| `stm.col.readAs` | Read as | Lido como |
| `stm.readAs.columns` | Columns | Colunas |
| `stm.readAs.unrecorded` | Not recorded | Nao registrado |
| `stm.readAs.help` | The card currency and the column mapping this upload was read with. A re-read reuses both. | A moeda do cartao e o mapeamento de colunas usados nesta leitura. Uma releitura reutiliza os dois. |

Both dictionaries in the same edit, EN and the PT mirror.

## 4. The attach dialog needs no change

It already asks for the card and the currency. The gap this closes is
afterwards, not during, so the statements table is the whole of it. Do not
add a confirmation step or a summary screen to the dialog.

## 5. Parse notes: also no change

`parse_issues[]` grows a third `severity` value, `"info"`, used for one note
per Type label the parser did not recognise ("Type 'Lastschrift' is not a
label this parser recognises (3 rows), so those rows kept the sign the export
printed."). The current renderer tests `severity === "error"` for the amber
styling and renders `message` otherwise, which already handles the new value
correctly. **Do not** add a severity map, an icon set, or a per-severity
colour: a map with a case per value is exactly what mislabels the next value
that gets added.

## 6. Do not change

Every existing `statements[]` key keeps its meaning and its place: `file`,
`upload_name`, `n_rows`, `n_new`, `period_start`, `period_end`, `writeback`,
`advisory`. The two new keys are additive, so a month whose uploads predate
them renders exactly as it does today apart from the muted "Not recorded".
No em-dashes in any UI copy.

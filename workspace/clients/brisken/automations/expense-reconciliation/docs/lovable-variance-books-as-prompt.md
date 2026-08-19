# Lovable prompt — variance chip, vendor drill-down, split depiction, multi-category toggle

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`. Change only the expense-batch grid and the Merchants
editor; leave everything else untouched.

The backend for all three areas is already deployed, so the API fields named
below are live now.

---

## 1. "Books as" split depiction on each expense row

A receipt whose contents belong to more than one expense account exports as
one row per account (that is correct accounting, it must not look like a
duplicate). Each expense row in `GET /api/expense-batches/{id}` now carries:

- `books_as`: `[{ account, amount }]` — the exact per-account split the
  export will write, sums matching the receipt total.
- `is_split`: true when there is more than one part.

Render: when `is_split` is true, show a compact breakdown inside the
expense row, under the total — one line per part, account name + amount,
with a small connector label so it reads as one receipt fanning out:

- **EN** "Books as:" / **PT** "Lançado como:"
- Example rendering: `Lançado como: Travel & Transport 19.15 · Meals &
  Entertainment 4.00 · (uncategorized - assign) 1.81`

The receipt's own total stays stated once on the row as today. When
`is_split` is false, render nothing extra. Do not compute any amounts
client-side — render the parts exactly as sent.

---

## 2. Category-variance chip + vendor drill-down

Each expense row now carries `category_variance`:

```json
{ "varies": true|false, "categories": ["...", "..."], "n_vendor_receipts": N }
```

`varies` is true when this row's vendor has receipts in THIS batch carrying
different categories. The backend decides; the SPA only renders.

- When `varies` is true, show a small warning-toned chip next to the
  category dropdown: **EN** "Mixed categories" / **PT** "Categorias
  diferentes". Tooltip lists `categories`.
- Clicking the chip filters the grid to that vendor's receipts (filter on
  `vendor.display`, `n_vendor_receipts` tells you how many to expect) with
  a clear active-filter bar: **EN** "Showing N receipts from {vendor}" /
  **PT** "Mostrando N recibos de {vendor}", and an X to clear.
- The chip must not look like an error — variance is sometimes legitimate
  (one shop selling different things). It is an invitation to glance, not
  a fault.

---

## 3. Merchants editor: "multiple categories" toggle

The merchants map (`GET/PUT /api/settings`, key `merchants`) now accepts an
optional boolean `multi_category` per merchant:

```json
"Mega Center": {
  "aliases": ["MEGA CENTER CONSTR LTDA"],
  "category": "Meals & Entertainment",
  "zoho_account": "...",
  "multi_category": true
}
```

In the Merchants editor, add a toggle per merchant: **EN** "This vendor uses
multiple categories" / **PT** "Este fornecedor usa várias categorias".

- When ON: send `"multi_category": true` in that merchant's entry on save.
  The merchant's name is still corrected everywhere, but the default
  category is NO longer applied automatically — each receipt gets judged on
  its own contents. Grey out (do not clear) the category and Zoho-account
  fields while the toggle is on, with a muted hint: **EN** "Ignored while
  multi-category is on" / **PT** "Ignorado enquanto várias categorias
  estiver ativo".
- When OFF: omit the key (do not send `"multi_category": false`).

No other Merchants-editor behavior changes.

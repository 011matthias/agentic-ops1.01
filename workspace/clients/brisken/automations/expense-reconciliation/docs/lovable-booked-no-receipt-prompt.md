# Lovable prompt: booked rows with no receipt get their own figure (item 102)

> **NOT YET APPLIED.** Backend: `summary.n_booked_no_receipt` and
> `summary.booked_no_receipt_by_ccy` on `GET /api/runs/{id}` (item 102).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One change in `src/components/RunWorkbench.tsx`, plus two optional fields on the run summary type in `src/lib/api.ts`. Render defensively: a summary without the new fields renders exactly as today.

## Why

A statement row Criss colours yellow is one she has already entered in her books. The month page folds those rows away and leaves them out of "still open", which is right for the books. It hides a second fact: many of them have no receipt. July 2026 has 48 yellow rows with no receipt behind them while the page says "USD 1,054.48 still open". The backend now counts them separately.

## 1. Fields

On the run summary type, add `n_booked_no_receipt?: number` and `booked_no_receipt_by_ccy?: Record<string, string>` (same shape as `unreconciled_by_ccy`: currency code to a formatted amount string).

## 2. The status line

In `StatusLine`, directly after the `ccyEntries.map(...)` spans that print `wb.status.stillOpen` and before the `adjacent > 0` span, render only when `(summary.n_booked_no_receipt ?? 0) > 0`:

- one `span` per entry of `Object.entries(summary.booked_no_receipt_by_ccy ?? {})`, `className="text-amber-700 dark:text-amber-300"`, text `t("wb.status.bookedNoReceipt", { amount: `${ccy} ${amt}`, n: summary.n_booked_no_receipt })`, with `title={t("wb.status.bookedNoReceipt.tip")}`.

If another change has restructured this line, keep the rule: the booked-without-receipt amount sits right after the still-open amount, in the same row, and is never added into it.

## 3. Do not change

"still open", the readiness pill, the broken-month banner, the posted fold, and every row.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `wb.status.bookedNoReceipt` | {amount} booked without a receipt ({n} charges) | {amount} lançados sem recibo ({n} cobranças) |
| `wb.status.bookedNoReceipt.tip` | Rows already entered in your books (yellow in the workbook) that no receipt settles. They are not in "still open". | Linhas já lançadas na contabilidade (amarelas na planilha) sem nenhum recibo. Não entram em "em aberto". |

## Checking it landed

1. July 2026 workbench (`/runs/50622baec444`): next to "USD 1,054.48 still open", an amber item reads "USD … booked without a receipt (48 charges)".
2. August 2026 (`/runs/074a7b8905d7`): no such item, because no booked row there lacks a receipt.
3. PT: "lançados sem recibo".
````

# Lovable prompt: let a category be set on a charge that has no receipt (item 109)

> **NOT APPLIED** (see PROMPT-STATUS.md). Backend: `PUT /api/runs/{id}/charges/{tx}/category`,
> `rows[].charge_category.is_edited` and `source: "EDITED"` on `GET /api/runs/{id}` (item 109).
> Backend deploy first.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One new control and one new badge in `src/components/RunWorkbench.tsx`, one call in `src/lib/api.ts`, one optional field on the run row type. Render defensively: a row without the new field renders exactly as today.

## Why

Criss's real month-end job is to give every charge a category. Most charges have no receipt: 101 of August's 114 rows and 73 of July's, and 146 of those carry a category the tool guessed from the bank's description. The dropdown that changes a category lives inside a candidate receipt card, so a charge with no candidate has no control at all. August's LOVABLE 15.00 of 2026-08-31 reads "Meals & Entertainment" and nobody can say otherwise; it goes into the reconciled CSV that way, and the same charge is guessed again next month.

The backend now takes a category on the charge itself and remembers it at Publish, so the same subscription is pre-filled next month. The screen is the missing half.

## 1. Field

On the run row type in `src/lib/api.ts`, `charge_category` gains one optional flag:

```ts
charge_category?: {
  category: string;
  zoho_account: string;
  source: string;
  provenance: string;
  is_learned: boolean;
  is_edited?: true;
} | null;
```

## 2. The call

In `src/lib/api.ts`, beside the existing category call:

```ts
export async function setChargeCategory(
  runId: string, transactionId: string, category: string,
): Promise<void> {
  await api(`/api/runs/${runId}/charges/${transactionId}/category`, {
    method: "PUT",
    body: JSON.stringify({ category }),
  });
}
```

An empty string clears the pick and the tool's guess comes back. The reply is `{ok, summary}`; on `400` or `404` show the backend's `error` in the existing toast and leave the row as it was.

## 3. The picker on the charge row

In `RunWorkbench.tsx`, in the block that renders a row's posting category (today read-only), when the row has no held receipt (`chosen_document_id` is null and `effective_bucket` is `"unmatched"`), render the same category `select` the candidate card already renders, populated from the run payload's `category_options`, valued at `row.charge_category?.category ?? ""`, with a first option `t("wb.chargeCat.none")` for the empty value. On change, call `setChargeCategory(runId, row.transaction_id, value)` and reload the run the way the candidate picker already reloads it after a category change.

A row whose bucket is `reconciled` or `review` keeps today's read-only posting category: its category belongs to the receipt, and the backend refuses it here.

## 4. Two badges beside the picker

- `row.charge_category?.is_edited`: render `t("wb.chargeCat.edited")` in the same style the receipt lines use for `EDITED`, with `title={t("wb.chargeCat.edited.tip")}`.
- `row.charge_category && !row.charge_category.is_edited && row.charge_category.source === "VENDOR"`: render `t("wb.chargeCat.guess")` in the existing amber chip style, with `title={t("wb.chargeCat.guess.tip")}`. This replaces the bare "AI?" badge on those rows, which said what it was but not that it could be changed.

`source: "LEARNED"` keeps whatever it renders today.

## 5. Reason copy

The backend reason for `reason_code: "receiptless_suggested"` changed. Update the i18n value for that key to the new EN and PT-BR below; the key itself is unchanged.

## Do not change

The candidate list and its own category dropdown, confirm and reject, the "already booked" and gray-fill chips, the Expenses page, the card tabs, and every count in the summary bar. `n_charges_category_guessed` is the backend's and already drops by one each time a pick is saved; do not compute it on the client.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `wb.chargeCat.none` | No category yet | Sem categoria ainda |
| `wb.chargeCat.edited` | EDIT | EDIT |
| `wb.chargeCat.edited.tip` | You set this category. It is used in the CSV and the report, and it is remembered for this merchant when you publish the month. | Você definiu esta categoria. Ela é usada no CSV e no relatório, e fica memorizada para este fornecedor quando você publica o mês. |
| `wb.chargeCat.guess` | Guess | Palpite |
| `wb.chargeCat.guess.tip` | No receipt is attached, so the tool guessed this from the bank's description. Pick the right category here to correct it. | Nenhum recibo anexado, então a ferramenta adivinhou pela descrição do banco. Escolha a categoria certa aqui para corrigir. |
| `wb.reason.receiptless_suggested` | No receipt is attached, so the tool guessed this category from the bank's description. Pick the right one on the row, or attach the receipt, before it posts. | Nenhum recibo anexado, então a ferramenta adivinhou esta categoria pela descrição do banco. Escolha a certa na linha, ou anexe o recibo, antes de lançar. |

## Checking it landed

1. August 2026 workbench (`/runs/074a7b8905d7`): the LOVABLE 15.00 row of 2026-08-31 shows a category dropdown reading "Meals & Entertainment" with a "Guess" chip beside it.
2. Pick "Software & Subscriptions" on it: the chip becomes EDIT, the summary's guessed count falls by one, and a reload keeps the pick.
3. Pick the blank first option on the same row: it returns to "Meals & Entertainment" with the Guess chip, and the count goes back up.
4. The OPENAI *CHATGPT SUBSCR 20.00 row of 2026-08-30 behaves the same; the SAP SE 1,574.24 row of 2026-08-28 does too.
5. A reconciled row (any row holding a receipt) shows no dropdown, exactly as today.
6. July 2026 (`/runs/50622baec444`): its 73 receiptless charges all show the dropdown; the gray-filled ones keep their "booked through recurring" chip unchanged.
7. PT: "Nenhum recibo anexado, então a ferramenta adivinhou pela descrição do banco."
````

# Lovable prompt: the Memory page shows each merchant's rules per company (note item M1)

> **NOT YET APPLIED.** Backend first: `by_vendor[]` and `categories[].seeded`
> on `GET /api/memory` (note item M1; contract in `docs/api-contract.md`,
> "Merchant-to-category is the default; the exceptions vary by company, on
> the account"). Until that deploy the field is absent and the page renders
> exactly as today.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. This edits `src/components/MemoryScreen.tsx`, the types in `src/lib/api.ts` and the dictionary in `src/lib/i18n.tsx`. Render defensively: a payload with no `by_vendor` renders the page exactly as today.

## Why

A merchant has ONE category (the Merchants editor's default), and what varies by company is the posting account. The learned-categories table lists one flat row per (company, vendor), so a reader cannot see that `anthropic` is one merchant with two accounts, or that a rule's category differs from the category the merchant's receipts will actually read. The backend now groups the same rows per vendor and says, per vendor, which registry merchant it is and which category its receipts read.

## 1. Types (`src/lib/api.ts`)

Add `seeded: boolean` to the memory category row type. Add:

```ts
export interface MemoryVendor {
  vendor: string;            // the normalized vendor the rules are keyed on
  merchant: string;          // the registry merchant it resolves to; "" when none
  category: string;          // what its receipts read: the registry default, or "" (judged per receipt)
  multi_category: boolean;
  companies: MemoryCategoryRow[];   // the flat rows for this vendor, minus `vendor`, sorted by entity
}
```

and `by_vendor?: MemoryVendor[]` on the memory view type.

## 2. The learned-categories table becomes grouped (`src/components/MemoryScreen.tsx`)

When `by_vendor` is present and non-empty, render the categories section as groups instead of the flat table; when it is absent, keep the flat table unchanged.

Each group has a vendor line and one company line per entry in `companies`.

The vendor line:

- `merchant` when non-empty, else `vendor`; when both are present and differ, `vendor` follows in `text-muted-foreground` inside parentheses.
- A category chip: `category` when non-empty, with the tooltip `t("memory.vendor.readsDefault")`; when `category` is empty and `multi_category` is true, the chip reads `t("memory.vendor.multi")`; when `category` is empty and `multi_category` is false, the chip reads `t("memory.vendor.perCompany")`.
- A count: `t("memory.vendor.companies", { n: companies.length })`.

Each company line (indented `ml-4`, same columns the flat rows have today):

- The entity, or `t("memory.company.none")` when `entity` is `""`.
- The row's own `category`. When the vendor line carries a non-empty `category` and the row's differs, render the row's category with `text-muted-foreground line-through` and the tooltip `t("memory.company.categoryOverridden", { category: <vendor category> })`: the merchant's default is what the receipt reads; this row contributes its account only.
- `zoho_account`, or `t("memory.company.noAccount")` in `text-muted-foreground` when `""`.
- A chip `t("memory.company.seeded")` when `seeded` is true, tooltip `t("memory.company.seeded.tip")`.
- `count`, `last`, the validated check and date exactly as today.
- The existing per-row actions (Edit, Delete, Validate, the row checkbox for "Validate selected") exactly as today. Every write body still needs `legal_entity_id: row.entity` and `vendor: <the group's vendor>`: take `vendor` from the GROUP, since the company line no longer carries it.

The "Needs review" filter (`GET /api/memory?unvalidated=1`) applies as today; the grouped payload is already filtered by the backend. Badge counts keep using `categories.length`.

## 3. i18n (`src/lib/i18n.tsx`, EN and PT in the same edit)

| Key | EN | PT |
|---|---|---|
| `memory.vendor.readsDefault` | Receipts of this merchant read this category (the merchant's default). | Os recibos deste fornecedor leem esta categoria (padrão do fornecedor). |
| `memory.vendor.multi` | Judged per receipt | Avaliado por recibo |
| `memory.vendor.perCompany` | No default; each company's rule decides | Sem padrão; a regra de cada empresa decide |
| `memory.vendor.companies` | {n} company rules | {n} regras por empresa |
| `memory.company.none` | No company | Sem empresa |
| `memory.company.noAccount` | no account | sem conta |
| `memory.company.categoryOverridden` | The merchant's default is {category}; this rule contributes its account only. | O padrão do fornecedor é {category}; esta regra contribui apenas com a conta. |
| `memory.company.seeded` | from posting history | do histórico de lançamentos |
| `memory.company.seeded.tip` | Seeded from Zoho Books posting history, not a person's decision. Validate it to stand behind it. | Semeado do histórico de lançamentos do Zoho Books, não uma decisão de uma pessoa. Valide para confirmar. |

## 4. Do not change

The write endpoints and their bodies (`PUT`/`DELETE /api/memory/categories`, `POST /api/memory/categories/validate`, `/api/memory/forget`, `/api/memory/reset` with its confirm step). The aliases, FX, entities and field-corrections tables. The Merchants editor in Settings. Nothing here saves settings.

## 5. After publishing, check

1. `by_vendor` and `memory.vendor.readsDefault` are in the bundle.
2. On `/memory` the `anthropic` group shows one vendor line and two company lines (Cloud Services, Corporate Services), each with a different account and the "from posting history" chip.
3. Editing a company line's category still sends `legal_entity_id` and `vendor` and the row refreshes from the reply.
4. "Needs review" still filters, and validating a line removes it from the filtered view.
````

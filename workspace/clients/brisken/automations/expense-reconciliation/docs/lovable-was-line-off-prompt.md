# Lovable prompt: the "Was: …" line under a category goes (item 228, note #94)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request. The backend keeps serving `posting_category.stamped`; nothing
> else reads it (the CSV, the Excel report and both PDFs never did).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/RunWorkbench.tsx`, `src/components/ExpensesReviewGrid.tsx`, `src/components/GlAccountPicker.tsx` and `src/lib/i18n.tsx`. No new field and no new request.

## Why

The owner left a note on September 2026's Matching page (`/runs/51a22ad72864`), pointing at the muted line "Was: IT: Computer and Internet Expenses (suggested)" under a row's category: "remove this "was..." line, no need for that". The line shows what a row read before the merchant list decided its account; on several rows (GITHUB, DIGITALOCEAN, SERVERPILOT in September) it repeats the account the row already shows. It goes everywhere it renders; the account the row reads now stays exactly as it is.

## 1. `RunWorkbench.tsx`: the Matching row

- Delete `<StampedLine stamped={row.posting_category?.stamped} />` (the line right after the `ChargeCategoryCell` / `PostingCategoryCell` conditional, inside the category `TableCell`).
- Remove `StampedLine,` from the import list from `./GlAccountPicker`.

## 2. `ExpensesReviewGrid.tsx`: the Expenses grid

- Delete `<StampedLine stamped={posting?.stamped} />` (the line right before `<SourceBadge`).
- Remove `StampedLine` from the import from `./GlAccountPicker`; keep every other name in that import.

## 3. `GlAccountPicker.tsx`

Delete the `StampedLine` component and its doc comment ("Muted "Was: ..." line for what a row read before the merchant list decided it."). Keep `MerchantSuffix` and everything else in the file.

## 4. `i18n.tsx`

Delete `category.stamped.was`, `category.stamped.suggested` and `category.stamped.rule` from both languages (EN "Was: {account} ({origin})" / "suggested" / "rule", PT-BR "Antes: {account} ({origin})" / "sugerido" / "regra"). Before deleting, search the project for each key; if anything besides the component removed in section 3 uses one, keep that key.

## 5. Do not change

- The `stamped` type in `src/lib/api.ts`: the backend still sends it, so leave the type as it is.
- The category picker, the category label, the "Suggested" badge and its Confirm button, the source badge, the merchant name after the vendor (`MerchantSuffix`), and the "lines don't add up" line.

## Checking it landed

Read only; do not click Save, Confirm or any category.

1. September 2026 Matching (`/runs/51a22ad72864`, 19 rows carry the line today): no text on the page starts with "Was:". The TWILIO SENDGRID row still reads "COGS - Other Infra and IT Costs for Cloud Business".
2. September 2026 Expenses (`/expenses/51a22ad72864`): no "Was:" line under any category.
3. PT on the same two pages: no text starts with "Antes:".
````

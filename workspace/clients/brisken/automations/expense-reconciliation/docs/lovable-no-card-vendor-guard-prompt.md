# Lovable prompt: say why a no-card pair whose merchant disagrees waits for a click (item 204 step 6)

> **NOT APPLIED** (see PROMPT-STATUS.md). Backend: `rows[].candidates[].review_code`
> value `no_card_vendor_disagrees` on `GET /api/runs/{id}` (case-9 build 2,
> owner D5, 2026-09-25). Builds on `lovable-no-card-evidence-prompt.md` (applied).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One more branch in the small muted line under a candidate in `src/components/RunWorkbench.tsx`, and one more value on the candidate type's `review_code` in `src/lib/api.ts`. Render defensively: a candidate without the new value renders exactly as today.

## Why

When a receipt prints no card and nobody picked one, the tool matches it on amount, date and currency across every card. Two such pairs were wrong: a Lovable invoice sat on a BASE44 charge of the same 50.00, and a 21 EUR Erste Fracht receipt sat on a hotel charge. Both rows then took that charge's card, company and person. The backend no longer books such a pair when the charge's merchant words do not match the receipt's vendor: the pair goes to review and stays the top candidate, so confirming it is still one click. The page today shows the generic "No card on the receipt" line and does not say why the row is waiting.

## 1. Field

Widen the existing optional field on the candidate type:

```ts
review_code?: "no_card_rival_on_other_card" | "no_card_vendor_disagrees";
```

It comes from `GET /api/runs/{id}` on `rows[].candidates[]`. When it is `no_card_vendor_disagrees`, `requires_review` is `true` on the same candidate, `card_evidence.receipt` is `"none"`, `vendor_pct` is below 50, and the row's `effective_bucket` is `"review"`.

## 2. The line

In the muted line under a candidate's reason (the one that already renders `wb.noCardRival` / `wb.noCardOnReceipt`), add a branch BEFORE the `wb.noCardOnReceipt` fallback:

- when `candidate.review_code === "no_card_rival_on_other_card"`: `t("wb.noCardRival")` (unchanged).
- else when `candidate.review_code === "no_card_vendor_disagrees"`: `t("wb.noCardVendorDisagrees")`.
- else when `candidate.card_evidence?.receipt === "none"`: `t("wb.noCardOnReceipt")` (unchanged).
- else render nothing.

The ` · ` + `t("wb.chargeCardFromAccount")` suffix keeps working exactly as today.

## 3. Do not change

The confirm and reject buttons, the candidate ordering, every count, the `reason` text (it already ends "Review: the receipt names no card and the charge's merchant words do not match its vendor (40%), so the pair is not booked until someone confirms it."), the `cards_differ` chip, the date-gap chip, the card picker on the Expenses page.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `wb.noCardVendorDisagrees` | No card on the receipt, and this charge's merchant does not match the receipt's vendor. Confirm only if it is the same purchase. | Sem cartão no recibo, e o estabelecimento deste lançamento não corresponde ao fornecedor do recibo. Confirme só se for a mesma compra. |

## Checks

1. On a month whose re-match has run since this backend shipped, open a row in review whose top candidate carries `review_code: "no_card_vendor_disagrees"` (August 2026: BASE44 50.00 on Aug 22 with the Lovable invoice): the line reads "No card on the receipt, and this charge's merchant does not match the receipt's vendor. Confirm only if it is the same purchase."
2. A candidate with `review_code: "no_card_rival_on_other_card"` still shows the "Check which card paid" line; a no-card candidate with no `review_code` still shows "No card on the receipt; matched on amount and date across all cards."
3. The confirm button on the flagged candidate still works, and "Confirm all matched" does not confirm it.
4. Switch the language: the new line reads in PT-BR.
````

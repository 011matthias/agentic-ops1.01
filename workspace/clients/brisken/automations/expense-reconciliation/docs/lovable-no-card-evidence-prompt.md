# Lovable prompt: say when a pair was matched with no card on the receipt (item X1)

> **NOT APPLIED** (see PROMPT-STATUS.md). Backend: `rows[].candidates[].card_evidence`
> and `rows[].candidates[].review_code` on `GET /api/runs/{id}` (item X1, 2026-09-18).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One new line under a candidate in `src/components/RunWorkbench.tsx` and two optional fields on the candidate type in `src/lib/api.ts`. Render defensively: a candidate without the new fields renders exactly as today.

## Why

When a receipt prints no card and nobody picked one, the tool still matches it against every card's charges on amount, date and currency. That is the right default, but the page never said the card was unknown, and when a second charge of the same amount sits on another card the tool cannot tell which card paid. The backend now marks such a pair: it keeps the match, asks for review, and says why. Nothing on the page shows that yet.

## 1. Fields

On the candidate type, add:

```ts
card_evidence?: {
  receipt: "override" | "hint" | "learned" | "printed" | "none";
  charge: "row" | "account" | "none";
};
review_code?: "no_card_rival_on_other_card";
```

Both come from `GET /api/runs/{id}` on every element of `rows[].candidates[]`. `card_evidence` is present on every candidate the backend serves; `review_code` is present only when the backend flagged the pair, and then `requires_review` is `true` on the same candidate.

## 2. The line

Directly under a candidate's existing reason text, render one small muted line (`className="text-[11px] text-muted-foreground"`):

- when `candidate.review_code === "no_card_rival_on_other_card"`: `t("wb.noCardRival")`.
- else when `candidate.card_evidence?.receipt === "none"`: `t("wb.noCardOnReceipt")`.
- else render nothing.

When `candidate.card_evidence?.charge === "account"`, append ` · ` and `t("wb.chargeCardFromAccount")` to whichever line rendered, or render it alone when neither line above did.

The existing `reason` text already ends with "Review: the receipt names no card and a charge on another card also fits (...)" on a flagged pair and keeps rendering as today; the new line is the short reading beside it.

## 3. Do not change

The confirm and reject buttons, the card picker on the Expenses page, every count, the `cards_differ` chip (item 137), the date-gap chip, the candidate ordering.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `wb.noCardRival` | No card on the receipt, and a charge on another card also fits. Check which card paid before confirming. | Sem cartão no recibo, e um lançamento em outro cartão também combina. Confira qual cartão pagou antes de confirmar. |
| `wb.noCardOnReceipt` | No card on the receipt; matched on amount and date across all cards. | Sem cartão no recibo; conciliado por valor e data em todos os cartões. |
| `wb.chargeCardFromAccount` | Card taken from the statement's account, not printed on this row. | Cartão tirado da conta do extrato, não impresso nesta linha. |

## Checks

1. Open a month whose receipt printed no card and whose charge sits alone: the candidate shows "No card on the receipt; matched on amount and date across all cards." and no review flag.
2. A flagged candidate (`review_code` present) shows the "Check which card paid" line, the confirm button still works, and the row is not confirmed by "Confirm all matched".
3. A candidate with `card_evidence.receipt` `hint`, `override`, `learned` or `printed` shows no new line.
4. Switch the language: both lines read in PT-BR.
````

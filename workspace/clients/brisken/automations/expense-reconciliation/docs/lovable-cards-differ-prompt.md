# Lovable prompt: say when a receipt sits on another card's charge (item 137)

> **NOT YET APPLIED.** Backend: `rows[].cards_differ` and
> `summary.n_cards_differ` on `GET /api/runs/{id}` (item 137).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One new chip in `src/components/RunWorkbench.tsx` and one optional field on the run row type in `src/lib/api.ts`. Render defensively: a row without the new field renders exactly as today.

## Why

Matching is now separated by card. A receipt whose card was picked by hand, assigned through a hint, or remembered only pairs with charges on that card when one exists. When no charge on its card fits, the tool keeps the pair on the other card but asks for a look, and it names both cards. August 2026 has one live case: LOVABLE 25.00 charged on card 3645, held by a Lovable invoice whose card is set to 2838. Either the pair or the card on the receipt is wrong, and until now nothing on the page said so.

## 1. Field

On the run row type, add:

```ts
cards_differ?: {
  document_id: string;
  charge_card: string;
  receipt_card: string;
  receipt_card_key: string;
  receipt_card_label: string;
  receipt_card_source: "override" | "hint" | "learned";
};
```

## 2. The chip

Add a `CardsDifferChip({ row }: { row: RunRow })` next to `DateGapChip`, and render it directly after `<DateGapChip row={row} />` in the row's chip strip. Return `null` when `row.cards_differ` is absent. Otherwise render a `span` with `className="rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200"`, text `t("wb.cardsDiffer", { charge: row.cards_differ.charge_card, receipt: row.cards_differ.receipt_card })`, and `title={t("wb.cardsDiffer.tip." + row.cards_differ.receipt_card_source, { label: row.cards_differ.receipt_card_label })}`.

The chip shows on confirmed rows too: a confirmed pair can still sit on the wrong card.

## 3. Do not change

The candidate list, the confirm and reject buttons, the card picker on the Expenses page, every count. The reason text on the candidate already says "the cards differ" and renders as it does today.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `wb.cardsDiffer` | Card {charge} charge, receipt on card {receipt} | Cobrança no cartão {charge}, recibo no cartão {receipt} |
| `wb.cardsDiffer.tip.override` | The receipt's card was picked by hand as {label}, but this charge is on another card. Change the card on the receipt, or reject the pair. | O cartão do recibo foi escolhido manualmente como {label}, mas esta cobrança está em outro cartão. Altere o cartão no recibo ou rejeite o par. |
| `wb.cardsDiffer.tip.hint` | The receipt's payment method points to {label}, but this charge is on another card. Check which card paid. | A forma de pagamento do recibo indica {label}, mas esta cobrança está em outro cartão. Verifique qual cartão pagou. |
| `wb.cardsDiffer.tip.learned` | The receipt's card was remembered from an earlier month as {label}, but this charge is on another card. Check which card paid. | O cartão do recibo foi lembrado de um mês anterior como {label}, mas esta cobrança está em outro cartão. Verifique qual cartão pagou. |

## Checking it landed

1. August 2026 workbench (`/runs/074a7b8905d7`): the LOVABLE 25.00 row of 2026-08-05 shows an amber chip "Card 3645 charge, receipt on card 2838"; hovering it names "Credit Card - 2838" and says it was picked by hand.
2. No other August row and no July row (`/runs/50622baec444`) shows the chip.
3. PT: "Cobrança no cartão 3645, recibo no cartão 2838".
````

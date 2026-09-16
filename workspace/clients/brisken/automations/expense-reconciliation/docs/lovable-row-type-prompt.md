# Lovable prompt - a statement row says what it is (item 73)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

Backend gate: the two fields below must be live first (`GET /api/runs/{id}`
on July `50622baec444` carries `rows[].row_type`). Lands on either page shape,
before or after `lovable-month-views-prompt.md` (item 79): it touches only the
company chip in the charge row's vendor cell, one new chip beside it, and the
credits label.

## Background

Note #42 (July, on `Payment Thank You-Mobile`, -9,664.81 USD): "how can this
item be 'refund' if you dont even know which card it was payed with". That row
is the card balance being paid, and August has the same row at -7,823.16. The
statement's own Type column says `Payment`; the tool only knew "credit", and
the page printed every credit under "Refund". The backend now says what each
line is, and where its company came from. The row did print its card (2838),
and the page never showed that.

## 1. The new fields

`GET /api/runs/{id}` -> on every element of `rows[]`, two strings:

```json
{
  "vendor": "Payment Thank You-Mobile",
  "effective_bucket": "refund",
  "legal_entity_id": "Corporate Services",
  "coverage_key": "card-2838",
  "row_type": "payment",
  "entity_source": "card"
}
```

- `row_type`: `purchase` | `payment` | `refund` | `reversal` | `fee` | `interest`.
- `entity_source`: `card` (the company of the card the row printed) | `batch`
  (the company the statement was uploaded under; the row printed no card) |
  `none` (no company).

In `src/lib/api.ts`, add to `RunRow`:

```ts
/** What the statement says this line is. Absent on an old payload. */
row_type?: string;
/** Where legal_entity_id came from. Absent on an old payload. */
entity_source?: "card" | "batch" | "none" | string;
```

`effective_bucket` does not change: a card payment stays in the `refund`
bucket, because that bucket means "money back to the card, never matched to a
receipt". Membership, counts and view keys stay as they are.

## 2. The row-type chip

In `RunWorkbench.tsx`, add a `RowTypeChip` and render it in the charge row's
vendor cell, immediately before `<EntityChip ... />`.

- Render nothing when `row_type` is absent or `purchase` (the ordinary case,
  almost every row).
- Otherwise a neutral chip in the `EntityChip` style (`rounded border
  bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground`),
  never amber or red: this is information, not a warning. Text
  `t("wb.rowType.{row_type}")`, tooltip `t("wb.rowType.{row_type}.tip")`.
- A value with no i18n key renders the raw value as the chip text, with no
  tooltip. Never fall back to another value's label.

## 3. The company chip says where the company came from

Change `EntityChip` to take the row: `<EntityChip value={row.legal_entity_id}
source={row.entity_source} cardLabel={...} />`, where `cardLabel` is
`data.coverage.find((c) => c.key === row.coverage_key)?.label` (pass
`undefined` when there is no match; type-check `coverage` is an array).

- `source === "card"`: same chip as today, wrapped in a tooltip:
  `t("wb.entity.fromCard", { card: cardLabel })` when `cardLabel` is set, else
  `t("wb.entity.fromCard.noLabel")`.
- `source === "batch"`: the chip text is `{value}` followed by a muted
  ` · {t("wb.entity.fromUpload")}`, tooltip `t("wb.entity.fromUpload.tip")`.
- Anything else, including absent, `none` and an empty value: exactly today's
  behaviour (plain chip, or the "Card not defined" link when empty).

## 4. The credits label

- If `wb.bucket.refund` still exists in `src/lib/i18n.tsx` (month-views not
  yet applied), change its value to EN "Credits on the statement" / PT
  "Créditos no extrato", and `wb.bucket.refund.tip` to the `wb.credits.tip`
  text below.
- If `wb.view.refund` exists (month-views applied), leave its label and add
  `t("wb.credits.tip")` as the tooltip of card 4.

## 5. i18n keys (EN and PT in the same edit)

| Key | EN | PT |
|---|---|---|
| `wb.rowType.purchase` | Purchase | Compra |
| `wb.rowType.payment` | Card payment | Pagamento do cartão |
| `wb.rowType.payment.tip` | The card balance being paid. Not a purchase and not a refund, so no receipt is expected. | Pagamento da fatura do cartão. Não é compra nem estorno, então não se espera recibo. |
| `wb.rowType.refund` | Refund | Estorno |
| `wb.rowType.refund.tip` | A merchant gave money back on this card. | Um comerciante devolveu dinheiro neste cartão. |
| `wb.rowType.reversal` | Reversal | Reversão |
| `wb.rowType.reversal.tip` | A charge the bank reversed. | Uma cobrança que o banco reverteu. |
| `wb.rowType.fee` | Card fee | Tarifa do cartão |
| `wb.rowType.fee.tip` | A fee the card issuer charged, not a purchase from a merchant. | Tarifa cobrada pelo emissor do cartão, não uma compra num comerciante. |
| `wb.rowType.interest` | Interest | Juros |
| `wb.rowType.interest.tip` | Interest the card issuer charged, not a purchase from a merchant. | Juros cobrados pelo emissor do cartão, não uma compra num comerciante. |
| `wb.entity.fromCard` | Company of the card on this row: {card} | Empresa do cartão desta linha: {card} |
| `wb.entity.fromCard.noLabel` | Company of the card on this row | Empresa do cartão desta linha |
| `wb.entity.fromUpload` | from upload | do envio |
| `wb.entity.fromUpload.tip` | This row printed no card, so it carries the company the statement was uploaded under. | Esta linha não mostra cartão, então usa a empresa com que o extrato foi enviado. |
| `wb.credits.tip` | Card payments, refunds and reversals. Never matched to a receipt; each row says which it is. | Pagamentos do cartão, estornos e reversões. Nunca associados a recibo; cada linha diz o que é. |

## 6. Do not change

`effective_bucket` membership, `BUCKET_ORDER` or the month-views view keys,
`rows[].section`, every summary count, `RowStatusBadge` and the Status cell
(item 76 owns them), `WarningChip`, `DupBadge`, the forget button,
`CandidateRow`, every mutation, every query key and every backend call. The
reconciliation PDF and the report workbook are rendered by the backend and
need nothing here.

## 7. Render defensively

`row_type` and `entity_source` are optional: a payload without them renders
exactly as today. `coverage` may be missing or not an array; then `cardLabel`
is `undefined`.

## Verify after publish

- Bundle (`uv run tools/lovable-bundle-audit.py`): `row_type`,
  `entity_source` and `wb.rowType.payment` in `chunk-runs._runId` / the i18n
  chunk.
- Browser, July `50622baec444`, cold from the login gate: the credits section
  (or card 4, "Credits on the statement") holds "Payment Thank You-Mobile"
  with a "Card payment" chip; its "Corporate Services" chip's tooltip names
  the 2838 card. No purchase row carries a type chip.
- August `074a7b8905d7`: "ANNUAL MEMBERSHIP FEE" 150.00 among the charges
  without a receipt carries "Card fee"; the payment row carries "Card payment".

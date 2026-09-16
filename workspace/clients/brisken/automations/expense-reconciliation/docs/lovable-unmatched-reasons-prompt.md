# Lovable prompt - the unmatched lists say why (items 83 + 75)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

On the Matching view, "Receipts without a charge" counted copies of documents
that had already settled their charge, and no row on either unmatched list said
why it was there, so every row read as a miss. Criss asked for decided
duplicates to leave the area where work waits, and the owner asked why receipts
already in the month were not matched. The backend now keeps decided copies in
their own list, out of the open list and its count, and gives every unmatched
receipt and charge a short reason.

## 1. The new fields (`GET /api/runs/{id}`)

- `copies_set_aside[]`: receipt objects, the same shape as
  `unmatched_receipts[]` (the `duplicate` marker included). These receipts are
  no longer in `unmatched_receipts[]` or `assignable_receipts[]`, and
  `summary.n_unmatched_rec` no longer counts them.
- `summary.n_copies_set_aside` (integer): the length of that list.
- `reason_code` (string):
  - on every `unmatched_receipts[]` element: `card_statement_not_loaded`,
    `not_a_card_charge`, `charge_in_neighbouring_period` or
    `no_charge_on_any_loaded_statement`;
  - on every `copies_set_aside[]` element: `duplicate_copy`;
  - on every `rows[]` element whose `effective_bucket` is `"unmatched"`:
    `not_a_purchase`, `receipt_held_by_another_charge`, `already_booked` or
    `no_receipt_found`;
  - absent on every other row. Never null.

## 2. The copies fold reads the new list (`RunWorkbench.tsx`)

`receiptCopiesAll` currently filters `data.unmatched_receipts` on
`duplicate.is_extra === true`. When `Array.isArray(data?.copies_set_aside)`,
use `asArray<UnmatchedReceipt>(data.copies_set_aside)` instead; otherwise keep
today's filter. Leave `receiptsOpenAll`, `receiptsDecided`, the
"copies set aside" fold labels and the settled-outside record exactly as they
are. Add `reason_code?: string` to `UnmatchedReceipt` and `RunRow` in
`src/lib/api.ts`, and `copies_set_aside?: UnmatchedReceipt[]` to the run type.

## 3. The reason on each row

- **Receipts** (`receiptTable`, rows of kind `"open"` only): in the vendor
  cell, under the existing vendor line and badges, one muted line
  (`text-xs text-muted-foreground`) reading
  `t("wb.reason.receipt." + r.reason_code)` when `reason_code` is one of the
  four receipt values in section 1. Nothing otherwise.
- **Charges** (`RowView`, the vendor cell): when
  `row.effective_bucket === "unmatched"`, the same muted line reading
  `t("wb.reason.charge." + row.reason_code)` when `reason_code` is one of the
  four charge values. Nothing otherwise, and nothing on any other bucket.

## 4. One breakdown line per view

Add to `captions`, after the captions already pushed for that view:

- **Receipts view** (`isReceipts`): count `receiptsOpenAll` by `reason_code`
  and push one line, `t("wb.reason.breakdown", { parts })`, where `parts` joins
  `"{n} {label}"` with " · " in this order, skipping zeros:
  `no_charge_on_any_loaded_statement`, `card_statement_not_loaded`,
  `charge_in_neighbouring_period`, `not_a_card_charge`. The label is
  `t("wb.reason.receipt.<code>.short")`. Omit the line when no open receipt
  carries a known code.
- **Charges without a receipt** (`view === "unmatched"`): the same, over the
  OPEN rows of that view (not the decided fold), order `no_receipt_found`,
  `receipt_held_by_another_charge`, `not_a_purchase`, `already_booked`, labels
  `t("wb.reason.charge.<code>.short")`.

## 5. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `wb.reason.breakdown` | Why: {parts} | Motivo: {parts} |
| `wb.reason.receipt.no_charge_on_any_loaded_statement` | No charge on the loaded statement matches this receipt. | Nenhuma transação do extrato carregado corresponde a este recibo. |
| `wb.reason.receipt.no_charge_on_any_loaded_statement.short` | no charge found | sem transação |
| `wb.reason.receipt.card_statement_not_loaded` | Paid with a card whose statement is not loaded. | Pago com um cartão cujo extrato não foi carregado. |
| `wb.reason.receipt.card_statement_not_loaded.short` | card not loaded | cartão sem extrato |
| `wb.reason.receipt.charge_in_neighbouring_period` | Dated at the edge of this statement; the charge is likely in the previous or next month. | Data no limite deste extrato; a transação deve estar no mês anterior ou seguinte. |
| `wb.reason.receipt.charge_in_neighbouring_period.short` | next or previous month | mês vizinho |
| `wb.reason.receipt.not_a_card_charge` | Paid by debit card, cash or transfer, not on this card. | Pago com débito, dinheiro ou transferência, não neste cartão. |
| `wb.reason.receipt.not_a_card_charge.short` | not a card payment | não é cartão |
| `wb.reason.charge.no_receipt_found` | No receipt for this charge has arrived yet. | Nenhum recibo desta transação chegou ainda. |
| `wb.reason.charge.no_receipt_found.short` | no receipt yet | sem recibo |
| `wb.reason.charge.receipt_held_by_another_charge` | The receipt found for this charge is paired with another charge. | O recibo encontrado está associado a outra transação. |
| `wb.reason.charge.receipt_held_by_another_charge.short` | receipt used elsewhere | recibo em outra transação |
| `wb.reason.charge.not_a_purchase` | A fee or interest line; no receipt exists for it. | Tarifa ou juros; não existe recibo. |
| `wb.reason.charge.not_a_purchase.short` | not a purchase | não é compra |
| `wb.reason.charge.already_booked` | Marked yellow in your statement workbook, so already booked. | Marcada em amarelo na planilha do extrato, portanto já lançada. |
| `wb.reason.charge.already_booked.short` | already booked | já lançada |

## 6. Do not change

- The five cards, their whole counts (`summary.n_unmatched_rec` keeps being
  card 1's number), the folds, filters, sort and bulk actions.
- The duplicates panel and its pairing of `duplicate_groups` with
  `duplicate_receipts` by index. "Not a copy" stays where it is; after it, both
  receipts come back in `unmatched_receipts[]` with no marker.
- The hand-match picker keeps reading `assignable_receipts[]` (the backend
  already left the copies out of it).
- Every decision, attach and settle-outside call.

## 7. Render defensively

Every field may be absent on an older payload: without `copies_set_aside`,
today's filter decides the fold; without `reason_code`, no line and no
breakdown. An unknown `reason_code` renders nothing. Never print a raw key.

## 8. After publishing, check

Re-read `GET /api/runs/{id}` for July `50622baec444` and August
`074a7b8905d7` first.

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit):
   `copies_set_aside`, `wb.reason.breakdown`,
   `wb.reason.receipt.card_statement_not_loaded`,
   `wb.reason.charge.receipt_held_by_another_charge` (not `reason_code` alone:
   other payloads already carry one).
2. August, Matching, Receipts without a charge: the card reads
   `n_unmatched_rec`; each open row shows its reason line; the breakdown line's
   numbers add up to the open rows; the "copies set aside" fold lists exactly
   `copies_set_aside` (`n_copies_set_aside` rows) once "Show" is clicked.
3. July, Charges without a receipt: the GOOGLE *Workspace 71.64 row reads
   "The receipt found for this charge is paired with another charge." The
   open rows' breakdown adds up to the open row count.
4. PT on August: "Motivo:", "cartão sem extrato", "sem recibo".
5. Network: no POST other than `/api/login` during the drive.

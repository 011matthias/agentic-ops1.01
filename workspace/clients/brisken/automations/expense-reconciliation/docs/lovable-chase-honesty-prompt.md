# Lovable prompt: charges with nothing behind them say what they are (front 1)

Status: written 2026-09-25, NOT PASTED. Backend half live with the front-1 PR.

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`, served at `expenses.brisken.com`). It
calls the existing FastAPI backend at `api.expenses.brisken.com` as a JSON
API. **Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

The charge side of a month disagreed with itself. July's 24 and August's 40
charges that Criss filled gray (booked through Zoho recurring expenses) are
closed for sign-off, but the Charges-without-a-receipt view counted them as
open ("73 · 24 open" on July) with no reason line. A card with no statement
loaded contributes no open charge, so "0 charges need a receipt" read as
"nothing owed" while 3 to 7 of the 9 cards were missing. The chase list
called July-dated charges August's, because a Chase cycle file cuts on the
4th. And "asked on" had no age and had to be clicked once per charge. The
backend now answers all four; this prompt renders them.

## 1. The fields (all on `GET /api/runs/{id}`, all parallel)

- `rows[].reason_code` and `unmatched_transactions[].reason_code` gain two
  values: `closed_recurring` (the gray fill closed it) and
  `no_receipt_expected` (a reviewer marked no receipt will exist).
  `already_booked` now also covers the reviewer's "already booked" verdict.
- Every element carrying a charge `reason_code` also carries
  `reason_label`, an English sentence. Use it only as the fallback for a code
  you have no i18n key for.
- `summary.n_cards_uncovered` (int) and `summary.cards_uncovered` (string[],
  card labels): active cards with nothing loaded for this month.
- `receipt_chase[].date_range`: `{ "start": "2026-07-03", "end": "2026-08-04" }`,
  absent when no charge has a date.
- `receipt_chase[].n_overdue` (int).
- `receipt_chase[].charges[].charge_month`: `"2026-07"`, the charge's own
  month.
- `receipt_chase[].charges[].days_since_requested` (int) and
  `receipt_chase[].charges[].overdue` (bool): ABSENT on a charge nobody asked
  for.
- New route `POST /api/runs/{run_id}/receipt-requests/mark-all`, body
  `{ "holder": group.holder }` (the string, `""` for the no-holder group).
  Reply `{ ok, holder, n_marked, summary }`. 400 with `code`
  `holder_has_no_open_charge` when the holder has nothing open.

## 2. Charges without a receipt: the reason and the fold

- The reason line on a charge row (`RowView`, vendor cell, the existing muted
  line): `t("wb.reason.charge." + row.reason_code)` for the six known codes;
  for any other non-empty `reason_code`, render `row.reason_label` instead;
  nothing when both are absent.
- A row whose `reason_code` is `closed_recurring` or `no_receipt_expected`
  belongs to the decided / settled fold, exactly where `already_booked` rows
  sit today. It is not "open". After this change July reads 0 open in this
  view, August 57 (the month's own `summary.n_charges_need_receipt`).
- The breakdown line (`wb.reason.breakdown`) is unchanged: it counts OPEN
  rows only, so the two new codes never appear in it.

## 3. The coverage line

In the month's status line (`StatusLine`), when
`(summary.n_cards_uncovered ?? 0) > 0`, one amber `span`:
`t("wb.status.cardsUncovered", { n: summary.n_cards_uncovered, cards: summary.cards_uncovered.join(", ") })`,
`title={t("wb.status.cardsUncovered.tip")}`. Render it whether or not the
month is complete; it is the reason "0 need a receipt" is not "nothing owed".
It never disables Publish.

## 4. The chase panel

- Group header, after the amounts: when `group.date_range` is present, a
  muted `span` `t("chase.dateRange", { start: group.date_range.start, end: group.date_range.end })`
  (when `start === end`, `t("chase.date", { date: group.date_range.start })`).
  When `group.n_overdue > 0`, an amber `span` `t("chase.overdueCount", { n: group.n_overdue })`.
- Charge table: when `charge.charge_month` differs from the run's own month
  (the run label parsed as a month, "August 2026" -> `2026-08`; show no chip
  when the label does not parse), a muted chip after the date:
  `t("chase.otherMonth", { month: <localized month name + year of charge.charge_month> })`.
- The asked marker at the end of a charge row: when
  `charge.days_since_requested` is present, replace today's
  `chase.requestedOn` text with `t("chase.requestedAgo", { date: charge.receipt_requested_at.slice(0, 10), n: charge.days_since_requested })`,
  amber and with `title={t("chase.overdue.tip")}` when `charge.overdue` is
  true, muted otherwise.
- Footer row: a third button beside Preview and Send,
  `t("chase.markAll")`, enabled when at least one of `group.charges` has no
  `receipt_requested_at`. On click, confirm with
  `t("chase.markAll.confirm", { n: <count without receipt_requested_at>, holder: group.holder_label })`,
  then POST `{ holder: group.holder }` to the mark-all route and refetch the
  run. Show the reply's `n_marked` in a toast `t("chase.markAll.done", { n })`.
  On a 400 show `err.holder_has_no_open_charge`.

## 5. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `wb.reason.charge.closed_recurring` | Booked through a Zoho recurring expense (gray in your workbook), so no receipt is needed. | Lançada por uma despesa recorrente do Zoho (cinza na planilha), portanto não precisa de recibo. |
| `wb.reason.charge.closed_recurring.short` | booked as recurring | lançada como recorrente |
| `wb.reason.charge.no_receipt_expected` | Marked by a reviewer: no receipt will exist for this charge. | Marcada por um revisor: esta transação não terá recibo. |
| `wb.reason.charge.no_receipt_expected.short` | no receipt expected | sem recibo esperado |
| `wb.status.cardsUncovered` | {n} cards have no statement for this month: {cards} | {n} cartões sem extrato neste mês: {cards} |
| `wb.status.cardsUncovered.tip` | Charges on these cards are not counted until their statement is loaded. A card that is not used any more is listed too. | As transações destes cartões só contam depois de o extrato ser carregado. Um cartão fora de uso também aparece. |
| `chase.dateRange` | charges from {start} to {end} | lançamentos de {start} a {end} |
| `chase.date` | charge of {date} | lançamento de {date} |
| `chase.overdueCount` | {n} asked over the limit | {n} cobrados há muito tempo |
| `chase.otherMonth` | {month} charge | lançamento de {month} |
| `chase.requestedAgo` | asked {date} ({n} days ago) | cobrado em {date} (há {n} dias) |
| `chase.overdue.tip` | Asked longer ago than the reminder limit in Settings | Cobrado há mais tempo que o limite de lembrete nas Configurações |
| `chase.markAll` | Mark all as asked | Marcar todos como cobrados |
| `chase.markAll.confirm` | Record that {holder} was asked for {n} receipts today? | Registrar que {holder} foi cobrado por {n} recibos hoje? |
| `chase.markAll.done` | {n} marked as asked | {n} marcados como cobrados |
| `err.holder_has_no_open_charge` | This card holder has no charge waiting for a receipt in this month. | Este titular não tem lançamento aguardando recibo neste mês. |

Keep `wb.status.cardsUncovered` singular-safe: when `n === 1`, render
"1 card has no statement for this month: {cards}" / "1 cartão sem extrato
neste mês: {cards}".

## 6. Do not change

- The Send button stays disabled; do not call the send route.
- The per-row "Mark the receipt as asked for" / "No receipt will exist"
  controls, their routes and their chips.
- `summary.n_charges_need_receipt` stays the chase title's count; do not
  subtract or add anything to it on the client.
- Publish stays enabled or disabled exactly as today; the coverage line is
  advisory.
- No Supabase, no new auth, no new storage.

## 7. Checking it landed

1. July `/runs/50622baec444`, Charges without a receipt: 0 open; the 24 gray
   rows sit in the settled fold reading "Booked through a Zoho recurring
   expense ...". The status line reads "3 cards have no statement for this
   month: Apple Credit Card - 0113, Credit Card - 6013, Credit Card - 8311".
2. August `/runs/074a7b8905d7`: the chase group "Brisken Cloud Services"
   reads "charges from 2026-07-03 to 2026-08-04" and 13 of its rows carry a
   "July 2026 charge" chip; the status line names 4 cards.
3. September `/runs/51a22ad72864`: the status line names 7 cards.
4. PT on August: "lançamentos de 2026-07-03 a 2026-08-04".
5. No non-GET request during the checks (mark-all is a write on Criss's
   month; exercise it only on a TEST month).

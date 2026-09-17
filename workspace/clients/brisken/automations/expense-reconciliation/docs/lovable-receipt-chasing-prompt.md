# Lovable prompt: the missing-receipts list per card holder, and the request that is not sent yet (item 107)

> **NOT YET APPLIED.** Backend: `receipt_chase[]`,
> `rows[].receipt_requested_at` / `requested_to` / `no_receipt_expected`,
> `summary.n_charges_receipt_requested` / `n_charges_no_receipt_expected` /
> `no_receipt_expected_by_ccy` on `GET /api/runs/{id}`, plus
> `POST /api/runs/{id}/receipt-requested`,
> `POST /api/runs/{id}/no-receipt-expected` and
> `GET /api/runs/{id}/receipt-requests` (item 107). Paste after that deploy.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One new panel and one new row control in `src/components/RunWorkbench.tsx`, plus optional fields on the run payload, run row and run summary types in `src/lib/api.ts`. Render defensively: a payload without the new fields renders exactly as today.

## Why

Chasing receipts is the biggest thing Criss does by hand every month. She reads the month for charges with nothing behind them, works out whose card each one is, and mails Dirk and Nicolas herself. August 2026 has 61 such charges across three card holders: 36 on Nicolas's card 3876, 24 on Dirk's 2838, 1 on the Consulting card. The tool already knew all of it and showed none of it, and there was no way to record that somebody was asked or that a charge will never have a receipt.

The backend now hands the page the grouped list, takes the two marks, and composes the request mail. Sending is not built: the owner approves the first real send separately, so the send button ships visible and disabled.

## 1. Fields

On the run payload type, add:

```ts
receipt_chase?: {
  holder: string;
  holder_label: string;
  holder_address: string | null;
  cards: { key: string; card_key: string; label: string }[];
  n_charges: number;
  n_requested: number;
  amounts_by_ccy: Record<string, string>;
  charges: {
    transaction_id: string;
    date: string;
    vendor: string;
    amount: string;
    currency: string;
    card_key: string;
    card_label: string;
    coverage_key: string;
    portal_hint?: string;
    receipt_requested_at?: string;
    requested_to?: string;
  }[];
}[];
```

On the run row type, add `receipt_requested_at?: string`, `requested_to?: string`, `no_receipt_expected?: string`. On the run summary type, add `n_charges_receipt_requested?: number`, `n_charges_no_receipt_expected?: number`, `no_receipt_expected_by_ccy?: Record<string, string>` (same shape as `unreconciled_by_ccy`).

## 2. The panel

Add a `ReceiptChasePanel({ view, onRefresh }: { view: RunView; onRefresh: () => void })` and render it on the Matching page directly above the rows table, after the status line. Return `null` when `(view.receipt_chase ?? []).length === 0`, so a month with nothing to chase shows nothing.

Otherwise a bordered card, `className="rounded border border-border bg-muted/30 p-3"`, with:

- a heading row: `t("chase.title", { n: view.summary.n_charges_need_receipt ?? 0 })`, and on the right, when `(view.summary.n_charges_receipt_requested ?? 0) > 0`, a muted `span` reading `t("chase.alreadyAsked", { n: view.summary.n_charges_receipt_requested })`.
- one collapsible section per entry of `view.receipt_chase`, collapsed by default except the first. Its header line is the holder: `group.holder_label`, then the cards as `group.cards.map(c => c.label).join(", ")`, then `t("chase.count", { n: group.n_charges })` and the amounts as `Object.entries(group.amounts_by_ccy).map(([ccy, amt]) => ccy + " " + amt).join(", ")`. When `group.holder_address` is `null`, add an amber `span` reading `t("chase.noAddress")`.
- inside the section, a plain table of `group.charges`: date, vendor, `charge.currency + " " + charge.amount`, `charge.card_label`, and `charge.portal_hint` when present (muted, prefixed with `t("chase.portal")`). A charge with `receipt_requested_at` gets a muted `span` at the end of its row reading `t("chase.requestedOn", { date: charge.receipt_requested_at.slice(0, 10) })`.
- a footer row with two buttons: `t("chase.preview")` and `t("chase.send")`.

## 3. The two buttons

**Preview** calls `GET /api/runs/{run_id}/receipt-requests` and opens a dialog listing one block per returned `mails[]` entry: the holder, `to` (or `t("chase.noAddress")` when `mail.blocked === "no_address"`), the subject, and the body in a `pre`. Show the PT-BR pair (`subject_pt` / `body_pt`) instead when the UI language is PT. Add a copy-to-clipboard button per block so Criss can paste the mail into Outlook herself today.

**Send** is `disabled` always in this release, with `title={t("chase.send.tip")}`. Do not call the send route on click; do not enable the button on any response field. The backend refuses the route in both of its states, and `can_send` in the preview response is false in both.

## 4. The row control

In the row's existing overflow / actions menu, add two items, both only for a row whose `effective_bucket` is `"unmatched"` and whose `section` is not `"posted"`:

- `t("row.markRequested")`, which posts `{ transaction_id, to: null }` to `/api/runs/{run_id}/receipt-requested`; on a row that already has `receipt_requested_at`, the label is `t("row.clearRequested")` and it posts `{ transaction_id, clear: true }`.
- `t("row.noReceiptExpected")`, which opens a small prompt for a reason and posts `{ transaction_id, reason }` to `/api/runs/{run_id}/no-receipt-expected`. An empty reason is refused by the backend with a 400, so keep the dialog's confirm disabled until the field has text. On a row that already carries `no_receipt_expected`, the label is `t("row.clearNoReceipt")` and it posts `{ transaction_id, clear: true }`.

Both routes reply `{ok, summary}`; refresh the run the same way the decision buttons already do.

On the row itself, render two chips next to the existing chip strip: when `row.receipt_requested_at` is present, a muted chip `t("row.chip.requested", { date: row.receipt_requested_at.slice(0, 10) })`; when `row.no_receipt_expected` is present, a slate chip `t("row.chip.noReceipt")` with `title={row.no_receipt_expected}`.

## 5. The status line

In `StatusLine`, after the booked-without-receipt item, render only when `(summary.n_charges_no_receipt_expected ?? 0) > 0`: one `span` per entry of `Object.entries(summary.no_receipt_expected_by_ccy ?? {})`, `className="text-slate-600 dark:text-slate-300"`, text `t("wb.status.noReceiptExpected", { amount: ccy + " " + amt, n: summary.n_charges_no_receipt_expected })`, `title={t("wb.status.noReceiptExpected.tip")}`. It is never added into "still open": the backend already took it out.

## 6. Do not change

The readiness pill and its rule, the publish gate, "still open", the booked-without-receipt figure, the posted fold, the candidate list, the confirm and reject buttons, the coverage panel, and every existing count. The chase panel reads the payload and adds no arithmetic of its own: never re-derive `n_charges` from the rows, and never sum the groups yourself.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `chase.title` | Receipts to chase ({n}) | Recibos a cobrar ({n}) |
| `chase.count` | {n} charges | {n} cobranças |
| `chase.alreadyAsked` | {n} already asked for | {n} já solicitados |
| `chase.noAddress` | No address on file | Sem e-mail cadastrado |
| `chase.portal` | invoice: | fatura: |
| `chase.requestedOn` | asked on {date} | solicitado em {date} |
| `chase.preview` | Preview the request | Ver a mensagem |
| `chase.send` | Send request | Enviar solicitação |
| `chase.send.tip` | Sending is switched off until the owner approves it. Use Preview and send the message yourself for now. | O envio está desativado até a aprovação. Por enquanto, use Ver a mensagem e envie você mesma. |
| `chase.copy` | Copy the message | Copiar a mensagem |
| `row.markRequested` | Mark the receipt as asked for | Marcar recibo como solicitado |
| `row.clearRequested` | Remove "asked for" | Remover "solicitado" |
| `row.noReceiptExpected` | No receipt will exist | Não haverá recibo |
| `row.clearNoReceipt` | Remove "no receipt will exist" | Remover "não haverá recibo" |
| `row.reasonLabel` | Why will this charge never have a receipt? | Por que esta cobrança nunca terá recibo? |
| `row.chip.requested` | asked on {date} | solicitado em {date} |
| `row.chip.noReceipt` | no receipt expected | sem recibo previsto |
| `wb.status.noReceiptExpected` | {amount} with no receipt expected ({n} charges) | {amount} sem recibo previsto ({n} cobranças) |
| `wb.status.noReceiptExpected.tip` | Charges you ruled will never have a receipt, with the reason on each. They are not in "still open". | Cobranças que você marcou como sem recibo, com o motivo em cada uma. Não entram em "em aberto". |

## Checking it landed

1. August 2026 workbench (`/runs/074a7b8905d7`): the panel reads "Receipts to chase (61)" with three holder sections, Nicolas Neumann first with 36 charges and USD 1,011.15, then Dirk Neumann with 24 and USD 6,361.53, then the Consulting card with 1 and USD 36.00. Each section says "No address on file" until the addresses are configured.
2. July 2026 (`/runs/50622baec444`): no panel at all, because every charge without a receipt there is already closed.
3. Marking one August charge "Mark the receipt as asked for" leaves the heading at 61, adds "1 already asked for", and puts "asked on 2026-09-17" on the row. The readiness pill does not move.
4. Marking one charge "No receipt will exist" with a reason drops the heading to 60, moves that charge's amount out of "still open" into the new "with no receipt expected" item, and puts a chip on the row whose tooltip is the reason.
5. Preview opens a dialog with one block per holder, each showing the subject "August 2026: N receipts still missing" and a body ending in `receipts@expenses.brisken.com`. Send is greyed out and does nothing when clicked.
6. PT: "Recibos a cobrar", "sem recibo previsto", "solicitado em".
````

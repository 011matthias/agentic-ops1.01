# Lovable prompt: keep a guessed category, change any card, view set-aside pages, drop-page matching line

> **NOT YET APPLIED.** Needs the backend from the notes #52/#53/#62/#63 PR
> deployed (`category_confirmable`, `POST .../confirm-category`,
> `set_aside[].receipt_image_available`, drop ledger `has_statement` /
> `rematch`). Notes answered: #62, #63 (Criss), #52, #53 (owner).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Five changes, each independent. Render defensively: a missing new field degrades to the screen as it is today, never to an error or a raw key.

## 1. Expenses: keep a category the tool guessed (`ExpensesReviewGrid.tsx`)

Criss corrected a row, and it still said "needs a look". The flag was about the CATEGORY (guessed from the vendor's name), and nothing on the row let her say the guess was right.

- API, `src/lib/api.ts`: add `category_confirmable?: boolean` to the expense row type, and
  `export function confirmExpenseCategory(runId: string, documentId: string)` = `apiFetch<ExpenseMutationResponse>(`/api/runs/${runId}/expenses/${documentId}/confirm-category`, { method: "POST" })`. No body. A 400 carries `error`; show it with `toast.error`.
- In the expense row, directly under the italic review reason line (`{reason ? (...) : null}`), when `row.category_confirmable === true` and `row.posting_category?.category` is non-empty, render one outline button: `Button size="sm" variant="outline" className="mt-1 h-7 px-2 text-xs"`, label `t("expx.category.keep", { category: row.posting_category.category })`. Click calls `confirmExpenseCategory`, then `afterExpenseEdit(queryClient, t, runId, res)`. Disable it while pending.
- After it succeeds the row comes back with `posting_category.source: "override"`, so the existing "Undo my category" item in the category dropdown undoes it. Change nothing else in the category cell.

## 2. Expenses: two reason lines say what they mean

The current copy for `vendor_guess` says the VENDOR was guessed; it is the category. Replace the text of these two existing keys in both languages (same keys, new text):

| Key | EN | PT-BR |
|---|---|---|
| `expx.review.reason.vendor_guess` | The category was guessed from the vendor's name, not from the items on the receipt. If it fits, keep it. | A categoria foi deduzida pelo nome do fornecedor, não pelos itens do recibo. Se estiver certa, mantenha-a. |
| `expx.review.reason.unknown_provenance` | The tool could not record how it chose this category. If it fits, keep it. | A ferramenta não registrou como escolheu esta categoria. Se estiver certa, mantenha-a. |

## 3. Expenses: change the card on any row

Criss: "I can't change the card if I need to." `CardFixCell` returns nothing when `row.card_source === "hint"` (the receipt printed the card), so a misread or wrong printed card could not be corrected. The backend now accepts the fix on every row and re-matches the month when the card changes.

- In `CardFixCell`, when `row.card_source === "hint"`, render a small ghost button `Button size="sm" variant="ghost" className="mt-1 h-6 px-1.5 text-[11px] text-muted-foreground"` labelled `t("expx.cardFix.change")`. Clicking it reveals the same `Select` the other sources use (value `row.card?.key ?? ""`, the active cards from `getCards()`, saving `card_key` through the row's field saver). Local state only; pressing Escape or closing the Select without a pick hides it again.
- `none`, `override`, `learned` keep rendering exactly as today.
- A row with `row.private === true` shows no card control at all, "Change card" included (the backend refuses a card pick on a private row). If `CardFixCell` already returns nothing for private rows, keep that check first.
- After a `card_key` save whose reply carries `rematch` without `error`, show `toast.success(t("expx.cardFix.rematched"))`. `afterExpenseEdit` keeps handling the failure toast.

## 4. Expenses: look at a set-aside page before restoring it (`SetAsideStrip`)

Owner: "need to be able to view these, or else user has really nothing to go by."

- Add `receipt_image_available?: boolean` to `SetAsideEntry` in `src/lib/api.ts`.
- On each strip row, before the Restore button (and on restored rows too), when `e.receipt_image_available !== false`, render `Button size="sm" variant="outline" className="h-7 px-2 text-xs"` labelled `t("expx.setaside.view")`. Click opens the existing `ReceiptViewerDialog` with `runId={batchId}`, `documentId={e.file}`, `fileName={e.display}`, `title={e.display}`; closing sets the viewed entry back to null. The file is served by the same `/api/runs/{id}/receipts/{file}/image` route the expense rows use.
- Put the view button and Restore in one `ml-auto flex items-center gap-2` group. Restore itself is unchanged.

## 5. Receipts page: say whether the month was matched (`ReceiptsDropScreen.tsx`)

Owner: "if user inserts receipts here, do they automatically and immediately get sorted into respective months?" They do, and a month whose statement is already loaded is matched again straight away. The job result now says so per month.

- `src/lib/api.ts`, `ReceiptDropMonth` gains
  `has_statement?: boolean | null;` and
  `rematch?: { ok: boolean; n_transactions?: number; n_matched?: number; n_review?: number; n_unmatched_tx?: number; error?: string } | null;`
- `mergeResults`: for the same month across chunks, `has_statement: prev.has_statement || m.has_statement` and `rematch: m.rematch ?? prev.rematch` (the later chunk describes the month after everything landed).
- In `FiledSection`, after the per-month duplicate notes, one muted line per month entry (`mt-2 text-xs text-muted-foreground`), chosen in this order:
  1. `m.rematch?.ok === true`: `t("rcpt.rematch.done", { label: m.label, matched: m.rematch.n_matched ?? 0, review: m.rematch.n_review ?? 0, open: m.rematch.n_unmatched_tx ?? 0 })`, followed by a `Link to="/runs/$runId" params={{ runId: m.batch_id }}` reading `t("rcpt.rematch.open")` when `m.batch_id` is set.
  2. `m.rematch?.ok === false`: `t("rcpt.rematch.failed", { label: m.label, error: m.rematch.error ?? "" })`.
  3. `m.has_statement === false`: `t("rcpt.rematch.noStatement", { label: m.label })`.
  4. `m.has_statement === true` and no `rematch`: `t("rcpt.rematch.nothingNew", { label: m.label })`.
  5. Anything else (field absent): no line.
- Replace the text of `rcpt.help` and `rcpt.explain` (same keys, both languages): the help line still says 80 files while the page accepts 500.

## New and changed strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.category.keep` | Keep "{category}" | Manter "{category}" |
| `expx.cardFix.change` | Change card | Trocar cartão |
| `expx.cardFix.rematched` | Card changed. The month was matched again with it. | Cartão trocado. O mês foi comparado novamente com ele. |
| `expx.setaside.view` | View | Ver |
| `rcpt.rematch.done` | {label} was matched against its statement again: {matched} matched, {review} to review, {open} charges still without a receipt. | {label} foi comparado novamente com o extrato: {matched} com recibo, {review} para revisar, {open} cobranças ainda sem recibo. |
| `rcpt.rematch.open` | Open matching | Abrir comparação |
| `rcpt.rematch.failed` | {label}: the receipts are filed, but matching against the statement failed ({error}). It runs again on the month's next change. | {label}: os recibos foram arquivados, mas a comparação com o extrato falhou ({error}). Ela roda de novo na próxima alteração do mês. |
| `rcpt.rematch.noStatement` | {label} has no statement loaded yet, so nothing was matched. Matching runs when the statement is added. | {label} ainda não tem extrato carregado, então nada foi comparado. A comparação roda quando o extrato for adicionado. |
| `rcpt.rematch.nothingNew` | {label}: nothing new to match, every file was already in the month. | {label}: nada novo para comparar, todos os arquivos já estavam no mês. |
| `rcpt.help` (changed) | Images and PDFs, one file per receipt. Max 15 MB per file, up to 500 files. | Imagens e PDFs, um arquivo por recibo. Máx. 15 MB por arquivo, até 500 arquivos. |
| `rcpt.explain` (changed) | Each receipt files into the month printed on it. Months that do not exist yet are created automatically. A month whose statement is already loaded is matched again right away. Trip receipts are joined from the trip's own page or by mailing the travel address. | Cada recibo vai para o mês impresso nele. Meses que ainda não existem são criados automaticamente. Um mês com extrato já carregado é comparado novamente na hora. Recibos de viagem entram pela página da viagem ou pelo endereço de email de viagens. |

## Do not change

The category dropdown and its Undo item, the entity Select, `CardChip`, `CardEndingNote`, `PaidThroughCell`, the private-expense controls, the card-review strip, Restore, the needs-month and rejected sections of the Receipts page.

## Checking it landed

1. August Expenses (`/expenses/074a7b8905d7`): the OpenAI 80.04 row reads the new vendor_guess sentence and shows `Keep "Software & Subscriptions"`. Do not click it on Criss's month; the button's presence is the check.
2. PT: the same row reads "A categoria foi deduzida pelo nome do fornecedor..." and `Manter "Software & Subscriptions"`.
3. August Obsidian 96.00 (printed card 3645) shows "Change card"; clicking it opens the card list. Close with Escape, pick nothing.
4. July Expenses (`/expenses/50622baec444`): the set-aside strip shows "View" on each row; View on the AWS invoice opens the PDF in the receipt dialog.
5. Receipts page reads "up to 500 files". The matching line needs a real drop, so it is checked on the next receipt dropped into a month with a statement.
````

# Lovable prompt: compare the copies of a duplicate side by side (item 140, note #67)

> **NOT YET APPLIED.** SPA only, no backend change. Owner ruling 2026-09-17:
> "duplicates should be shown next to each other for easier comparison".
> Extends `lovable-duplicates-prompt.md` (row badges, `expx.dup.*`) and
> `lovable-duplicates-decided-prompt.md` (the Matching view's panel,
> `wb.dups.*`); nothing either of them built changes, and every ruling button
> keeps its route, payload and handler.
>
> **Data, read live 2026-09-17 (July `50622baec444`, August `074a7b8905d7`).**
> Every member of every duplicate group, the set-aside copy included, is a row
> of `expenses[]` on `GET /api/expense-batches/{id}` (July 10 of 10 members,
> August 10 of 10), and `duplicate_groups[]` on that payload names the members.
> The run payload adds what the batch lacks: which copy a charge holds
> (`rows[]` with `effective_bucket: "reconciled"` and `chosen_document_id`),
> and `duplicate_receipts[i]` repeats date, vendor, total, currency, reference,
> payment text and file name per member as a fallback. The image route
> `GET /api/runs/{id}/receipts/{doc}/image` served both Aposto JPEGs and the
> August train PDFs 200. Nothing the panel needs is missing from the payloads.
> The batch payload carries no matched charge on its rows; the dialog reads it
> from the run query, which both pages already load on a month with a
> statement (the Expenses page's `ReconciliationLine`).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No new request type and no backend change: the dialog reads the two queries the pages already hold, `["expense-batch", runId]` (`getExpenseBatch`) and `["run", runId]` (`getRun`), plus the existing receipt image route. Changes: a new `src/components/CompareCopies.tsx`, one new export in `src/components/ReceiptViewer.tsx`, and one button in each of `ExpensesReviewGrid.tsx` (`DuplicateCell`) and `RunWorkbench.tsx` (`DuplicatesPanel` and the "Receipts without a charge" table). Render defensively: any field below may be absent, null or an empty string.

## Why

On a duplicate row the Expenses page shows "duplicate · copy 2 of 2" and a jump to the first copy. The owner, on July's Aposto Karlsruhe copy: "if this is a potential duplicate, the tool needs to show all the available data to each of the duplicates next to each other for manual comparison. Just labeling it is not going to cut it because then user has to search for the other duplicate and this slows comparison process." Ruling 2026-09-17: "duplicates should be shown next to each other for easier comparison". A "Compare copies" button opens every copy of the group in columns, with the values that differ highlighted and the receipt images next to each other, and the same ruling buttons the row already has.

## 1. `ReceiptPreview` (`src/components/ReceiptViewer.tsx`)

Add and export `ReceiptPreview({ runId, documentId, fileName, available }: { runId: string; documentId: string; fileName?: string | null; available?: boolean })`, an inline version of what `ReceiptViewerDialog` renders inside its dialog:

- Same module-level `cache`, same `fetchReceiptImage(runId, documentId)`, same rule that the blob's MIME type decides the element (never the file name).
- `available === false`: no request; muted text `t("dup.compare.noImage")`.
- Loading: `Loader2` spinner with `t("wb.receipt.loading")`. Failed: `t("receipt.view.failed", { file })` in `text-destructive`.
- PDF: `<iframe>` `h-[60vh] w-full rounded border`. Image: `<img>` `max-h-[60vh] w-full rounded border object-contain`. Anything else: the failed line plus the existing "Download instead" link, as the dialog does.
- Under a loaded PDF or image, a small link `t("dup.compare.openFull")`: `<a href={loaded.url} target="_blank" rel="noopener noreferrer">`.

`ReceiptViewerDialog` itself does not change.

## 2. The dialog (`src/components/CompareCopies.tsx`)

Export `CompareCopiesButton({ runId, groupId, openedFrom, actions }: { runId: string; groupId: string; openedFrom?: string | null; actions?: (close: () => void) => React.ReactNode })`.

- The trigger: `<Button type="button" variant="outline" size="sm" className="h-7 px-2 text-xs">` with the lucide `Columns2` icon (`mr-1 h-3 w-3`) and `t("dup.compare.open")`.
- The dialog mounts its content only while open, so nothing is fetched until the button is clicked. `DialogContent className="max-w-[min(96vw,80rem)] max-h-[92vh] overflow-y-auto"`.
- It reads `useQuery({ queryKey: ["expense-batch", runId], queryFn: () => getExpenseBatch(runId), retry: 1 })` and `useQuery({ queryKey: ["run", runId], queryFn: () => getRun(runId), retry: 1, enabled: batch?.has_statement === true })`. On a month with a statement both are already cached on the Expenses page (`ReconciliationLine`) and on the Matching page. A month without a statement has no charges, so the run query stays off and the rules below that read `run` find nothing. While the batch query has no data, show the `wb.receipt.loading` spinner.

### Which copies

1. `group` = `batch.duplicate_groups` entry with this `group_id`, else the `run.duplicate_groups` entry.
2. Member ids, in order: `group.members` (deduplicated). Without a group: every `batch.expenses` row whose `duplicate?.group_id === groupId`, sorted by `duplicate.copy`, then `openedFrom` and that row's `duplicate.of` if not already listed.
3. For each id, `exp` = the `batch.expenses` row with that `document_id`. `rec` = the same id in the run's paired `duplicate_receipts` list, else in `run.unmatched_receipts`, `run.copies_set_aside` or `run.assignable_receipts`. The pairing is the panel's: `duplicate_receipts[k]` belongs to the k-th group of kind `"receipt"` in `run.duplicate_groups`; use it only when its `document_id`s are exactly `group.members`.
4. Every value below comes from `exp` when `exp` exists, else from `rec`. An id found in neither is still a column: its header, the id in `font-mono text-xs`, and `t("dup.compare.missing")`.

### Layout

- Title: `t("dup.compare.title", { vendor })` with the first column's vendor; `t("dup.compare.open")` when that is empty.
- Description: `t("dup.compare.body", { n })`, n = number of columns. Under it, one muted line with the group's reason, the rule `DuplicatesPanel` uses today (`decided_by === "reviewer"` gives `wb.dups.byReviewer.copy` or `wb.dups.byReviewer.distinct`; otherwise `wb.dups.basis.{basis}`, `wb.dups.basis.unknown` for any other value). Move `BASIS_KEYS` and `reasonOf` into this file as an exported `duplicateReason(group, t)` and have `DuplicatesPanel` import it; its text must not change. No group: no reason line.
- Body: `<div className="overflow-x-auto">` holding a CSS grid, `gridTemplateColumns: "10rem repeat(N, minmax(18rem, 1fr))"`. First row: an empty label cell, then per column `t("dup.compare.copy", { copy: i + 1, n: N })` in `font-medium`, and under it `t("dup.compare.thisRow")` as a small muted badge on the column whose id is `openedFrom`.
- Then one grid row per field: label cell (`text-xs text-muted-foreground`), then one value cell per column. An empty value renders `-` in muted text.

### Fields, top to bottom

Compared fields (highlight when they differ):

| Label key | Value |
|---|---|
| `dup.compare.field.date` | `exp.date` (plus a space and `exp.time` when present), else `rec.date` |
| `dup.compare.field.vendor` | `vendorDisplay(exp.vendor)`, else `rec.vendor` |
| `dup.compare.field.total` | `exp.total`, else `rec.total`: remove `,` thousands separators before parsing (the payload sends `"13,200.00"`, and `parseFloat` alone reads that as 13), then show with 2 decimals in the page locale; a value that does not parse shows as sent |
| `dup.compare.field.currency` | `currency` |
| `dup.compare.field.tax` | `exp.tax`, with `exp.tax_label` after it when present |
| `dup.compare.field.card` | `exp.card?.label`, else `exp.card?.key` |
| `dup.compare.field.payment` | `exp.payment_mode`, else `exp.payment_hint`, else `rec.payment_mode` |
| `dup.compare.field.reference` | `reference` |
| `dup.compare.field.invoiceNumber` | `exp.invoice_number` |
| `dup.compare.field.receiptNumber` | `exp.receipt_number` |
| `dup.compare.field.category` | `exp.posting_category?.category` |
| `dup.compare.field.entity` | `exp.legal_entity_id` |
| `dup.compare.field.person` | `exp.person` |
| `dup.compare.field.costCenter` | `exp.cost_center` |

Shown, never highlighted (two copies differ here by nature):

| Label key | Value |
|---|---|
| `dup.compare.field.status` | first that applies: a `run.rows` entry with `effective_bucket === "reconciled"` and `chosen_document_id` equal to the id gives `dup.compare.status.matched`; the id in `run.copies_set_aside`, or `exp.counts_in_total === false`, gives `dup.compare.status.setAside`; the id in `run.unmatched_receipts` gives `dup.compare.status.waiting`; otherwise `dup.compare.status.counts` |
| `dup.compare.field.charge` | that reconciled row as `{date} · {vendor} · {amount} {currency}` |
| `dup.compare.field.arrived` | `exp.submitted_by`: `address` (else `person`), then ` · ` and `received_at` as a date in the page locale |
| `dup.compare.field.file` | `exp.source_file`, else `exp.receipt_name`, else `rec.receipt_name`; under it the `document_id` in `font-mono text-[10px] text-muted-foreground` |
| `dup.compare.field.receipt` | `<ReceiptPreview runId documentId fileName available={exp?.receipt_image_available ?? rec?.receipt_image_available} />` |

Rules:

- Hide a field row when every column's value is empty.
- Differ test for compared fields: trim and collapse whitespace; for Total, remove thousands commas and compare the number to 2 decimals; an empty value counts as its own value. When the columns do not all agree, give that row's value cells `bg-amber-500/10 rounded` and put `t("dup.compare.differs")` under the label in `text-[10px] font-medium text-amber-700 dark:text-amber-300`.

### Footer

`DialogFooter`: `actions?.(close)` when given, then a `variant="ghost"` button `t("receipt.view.close")`. `close` closes the dialog.

## 3. Expenses page (`ExpensesReviewGrid.tsx`, `DuplicateCell`)

After the badges (the copy badge and the "not in total" badge), before "Delete the extra", render:

```tsx
<CompareCopiesButton
  runId={runId}
  groupId={dup.group_id}
  openedFrom={documentId}
  actions={(close) => (<>
    {isExtra ? <Button type="button" variant="outline" size="sm" className="h-7 px-2 text-xs text-rose-600 border-rose-300 dark:text-rose-400 dark:border-rose-800" onClick={() => { close(); onDelete(); }}>{t("expx.dup.deleteExtra")}</Button> : null}
    <Button type="button" variant="outline" size="sm" className="h-7 px-2 text-xs" disabled={ignore.isPending} onClick={() => { ignore.mutate(); close(); }}>{t("expx.dup.notDuplicate")}</Button>
  </>)}
/>
```

`DuplicateCell` needs the row's `document_id`: add a `documentId: string` prop and pass `documentId={row.document_id}` from `ExpenseRowView`. The footer buttons are the row's own two buttons with the same handlers: "Delete the extra" opens the same delete confirmation, "Not a copy" runs the same `ignore` mutation. The row buttons stay where they are.

## 4. Matching page (`RunWorkbench.tsx`)

`runId` comes from `useContext(RunIdContext)` inside `DuplicatesPanel` (it renders inside the provider).

**The duplicates panel.** In `renderOpen` and `renderDecided`, put a `CompareCopiesButton` (`groupId={group.group_id}`, no `openedFrom`) immediately left of the existing button(s) in the card header. Its `actions` are that card's buttons with the same `onResolve` calls and `busy` state, each followed by `close()`: an open card offers `wb.dups.real` and `wb.dups.notDup`; a card in COPIES offers `wb.dups.notCopy`; a card in KEPT APART offers `wb.dups.sameDocument`.

**"Receipts without a charge" (`receiptTable`).** In the last cell, when `r.duplicate?.group_id` is set, wrap the cell's content in `<div className="flex items-center justify-end gap-1">` with a `CompareCopiesButton` (`groupId={r.duplicate.group_id}`, `openedFrom={r.document_id}`) before today's control. Its `actions` come from the group in `data.duplicate_groups` with this `group_id`, partitioned by the panel's rule: COPIES gives `wb.dups.notCopy` (`duplicates.mutate({ group_id, resolution: "ignore" })`), KEPT APART gives `wb.dups.sameDocument` (`resolution: "confirmed"`), OPEN gives `wb.dups.real` (`"confirmed"`) and `wb.dups.notDup` (`"ignore"`); each click then calls `close()`. The partition is the panel's own: open when `state === "open"` (or, with `state` absent, when neither `resolution` is set nor `kind === "receipt"`), else KEPT APART when `verdict === "distinct"` (or, with `verdict` absent, `resolution === "ignore"`), else COPIES. No group found: no actions.

## 5. Do not change

- The resolve route, its body, the delete route and their reply handling.
- The row badges, their jump to the first copy, the "not in total" badge, the "1 copy set aside" bar and its filter, "Delete the extra" and "Not a copy" on the row.
- The panel's partition, fold line, Show/Hide toggle, member tables and the index pairing of `duplicate_groups` with `duplicate_receipts`.
- `ViewReceiptButton`, `ReceiptViewerDialog`, `DupBadge`, the settle-outside control and every count.
- No em-dash in any new string.

## New strings

`t()` has no plural logic; `{n}` is always 2 or more here.

| Key | EN | PT-BR |
|---|---|---|
| `dup.compare.open` | Compare copies | Comparar cópias |
| `dup.compare.title` | Compare copies · {vendor} | Comparar cópias · {vendor} |
| `dup.compare.body` | {n} copies side by side. Highlighted rows differ between the copies. | {n} cópias lado a lado. As linhas destacadas diferem entre as cópias. |
| `dup.compare.copy` | Copy {copy} of {n} | Cópia {copy} de {n} |
| `dup.compare.thisRow` | The row you opened | A linha que você abriu |
| `dup.compare.differs` | differs | difere |
| `dup.compare.missing` | Not in this month's list | Não está na lista deste mês |
| `dup.compare.noImage` | No file to show for this copy | Nenhum arquivo para mostrar nesta cópia |
| `dup.compare.openFull` | Open full size | Abrir em tamanho real |
| `dup.compare.field.date` | Date | Data |
| `dup.compare.field.vendor` | Vendor | Fornecedor |
| `dup.compare.field.total` | Total | Total |
| `dup.compare.field.currency` | Currency | Moeda |
| `dup.compare.field.tax` | Tax | Imposto |
| `dup.compare.field.card` | Card | Cartão |
| `dup.compare.field.payment` | Payment printed on the receipt | Pagamento impresso no recibo |
| `dup.compare.field.reference` | Reference | Referência |
| `dup.compare.field.invoiceNumber` | Invoice number | Número da fatura |
| `dup.compare.field.receiptNumber` | Receipt number | Número do recibo |
| `dup.compare.field.category` | Category | Categoria |
| `dup.compare.field.entity` | Legal entity | Entidade legal |
| `dup.compare.field.person` | Person | Pessoa |
| `dup.compare.field.costCenter` | Cost center | Centro de custo |
| `dup.compare.field.status` | In this month | Neste mês |
| `dup.compare.field.charge` | Matched charge | Lançamento conciliado |
| `dup.compare.field.arrived` | Arrived | Chegada |
| `dup.compare.field.file` | File | Arquivo |
| `dup.compare.field.receipt` | Receipt | Recibo |
| `dup.compare.status.matched` | Matched to a charge | Conciliada com um lançamento |
| `dup.compare.status.setAside` | Set aside as a copy, not in the total | Separada como cópia, fora do total |
| `dup.compare.status.waiting` | No charge yet | Ainda sem lançamento |
| `dup.compare.status.counts` | Counts in the total | Conta no total |

Reused unchanged: `expx.dup.deleteExtra`, `expx.dup.notDuplicate`, `wb.dups.real`, `wb.dups.notDup`, `wb.dups.notCopy`, `wb.dups.sameDocument`, `wb.dups.byReviewer.*`, `wb.dups.basis.*`, `wb.receipt.loading`, `receipt.view.failed`, `receipt.view.download`, `receipt.view.close`.

## Checking it landed

Re-read `GET /api/expense-batches/{id}` and `GET /api/runs/{id}` for July `50622baec444` and August `074a7b8905d7` minutes before driving and substitute live values below. Read-only throughout: open and close dialogs with Close or Escape, never click "Delete the extra", "Not a copy", "Same document", "Real duplicate" or "Not a duplicate" (Criss's live months).

1. **Bundle.** Fetch every `/assets/*.js` from `https://expenses.brisken.com`, following references until the set stops growing (baseline 2026-09-17: 44 files, 1,103 KB). The controls `ready_to_post` and `coverage` must hit before any absence counts. Then: `dup.compare.open`, `dup.compare.differs`, `dup.compare.status.setAside` and `dup.compare.field.payment` in `chunk-i18n` with "Comparar cópias" beside them; `dup.compare.open` and `dup.compare.status.setAside` also in at least one chunk other than `chunk-i18n` (the call sites). All four were absent from every chunk on 2026-09-17.
2. **Cold drive, EN.** Fresh named browser session, no cookie, 1440x900, sign in at the gate. July Expenses `/expenses/50622baec444`, row Aposto Karlsruhe, 2026-07-13, 80.00 EUR, badge "duplicate · copy 2 of 2" (`0030__...ZE_8100599.jpg`). Click "Compare copies". The dialog reads "Compare copies · Aposto Karlsruhe", "2 copies side by side. Highlighted rows differ between the copies." and "Set aside by a reviewer". Two columns, "Copy 1 of 2" and "Copy 2 of 2", the second marked "The row you opened". Total reads 80.00 in both columns and Currency EUR in both; Reference 4563, Payment printed on the receipt "VISA CREDIT" and Category "Meals & Entertainment" in both, and no label carries "differs". In this month: "Matched to a charge" / "Set aside as a copy, not in the total". Matched charge: "2026-07-13 · UZR*Aposto Karlsruhe · 91.70 USD" / "-". File: `2026-07-13__ZE__Aposto_Karlsruhe__ZE_7150901.jpg` / `2026-07-13__ZE__Aposto_Karlsruhe__ZE_8100599.jpg`. Both receipt images are visible: read back two `<img>` elements in the dialog with `naturalWidth > 0`. Footer: "Delete the extra", "Not a copy", "Close". Close it.
3. July Expenses, Lovable Labs Incorporated 200.00 USD, either copy: Payment printed on the receipt "-" / "Link" and Reference "H0LHY2WQ-0029" / "H0LHY2WQ0029" both marked "differs"; both receipts render as PDFs (two `<iframe>`).
4. August Expenses `/expenses/074a7b8905d7`: the Petit Train pair (32.00 EUR, 2026-08-23) marks Vendor ("SARL TRAIN'S" / "Petit Train Touristique de Colmar"), Payment and Category ("Software & Subscriptions" / "Travel & Transport") as differing and Card "Credit Card - 2838" as equal; the Lovable Labs 15.00 USD pair marks Card ("Credit Card - 2838" / "Credit Card Chase Visa - 3645") and Legal entity ("Brisken Corp Services, LLC" / "Corporate Services") as differing.
5. July Matching `/runs/50622baec444`: open the panel fold ("Copies set aside (2) · 3 kept apart"); every card has "Compare copies" left of its one button. Google LLC 71.64 USD (kept apart): Reference "5608449734" / "5614551183" and Payment "...2544" / "0501-1462-9129" differ, Tax 4.44 equal, footer "Same document", "Close".
6. August Matching `/runs/074a7b8905d7`, "Receipts without a charge": Lovable Labs 15.00 (`0008`) and Anthropic, PBC 100.00 (`0015`) show "Compare copies" beside today's control, and so does every row in the fold of copies; the dialog from `0008` marks "The row you opened" on column 1 and offers "Not a copy".
7. PT on July Expenses, the Aposto row: "Comparar cópias", "Cópia 2 de 2", "A linha que você abriu", "Separada como cópia, fora do total", "Conciliada com um lançamento".
8. Unchanged: the row badges, "Delete the extra" and "Not a copy" on the rows, the panel's fold line and buttons, and "View receipt".
9. Network over the whole drive: no POST, PUT, PATCH or DELETE other than `/api/login`; receipt images load as `GET /api/runs/{id}/receipts/{doc}/image` 200.
````

# Lovable prompt - controls that read as text are buttons, and "booked" names its workbook (items 85 + 86)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`. No backend change: every field used here is
already on the payloads.

## Background

On the month pages several actions and toggles are styled as underlined or
grey text, so they read as labels, not as things to click. The owner left
three notes on July: "Confirm private expense" should be a real button; the
duplicates panel's "Hide/View" should be a button; the Matched card's
"Hide/Show" should be a button. A fourth note asked, on "30 already posted in
your workbook": "what is the workbook? where does this come from". The
workbook is the statement spreadsheet uploaded for the month; a row the
reviewer colours yellow there is already booked, and a grey row is a
subscription. The page never says so.

## 1. One button style for every action and toggle on the two month pages

Every control listed in sections 2 and 3 becomes the app's `Button` from
`@/components/ui/button` with `variant="outline" size="sm"` and
`className="h-7 px-2 text-xs"` (add `gap-1` when it carries an icon). Keep
each control's existing `onClick`, `disabled`, `title`, tooltip, dialog trigger
and handler exactly as they are; change only the element and its classes. A
`Link` or `<a>` becomes `<Button asChild variant="outline" size="sm"
className="h-7 px-2 text-xs">` wrapping the same `Link` / `<a>` (same `to`,
`href`, `target`, `rel`). Remove `underline`, `underline-offset-*`,
`decoration-dotted` and `hover:underline` from these controls.

## 2. Matching view (`src/components/RunWorkbench.tsx`)

| Where (search for) | Control | After |
|---|---|---|
| `ViewReceiptButton`, the branch with `label` (`font-mono text-xs text-primary underline`) | opens the receipt | Button; the label keeps `font-mono`, add `max-w-[16rem] truncate` |
| the setup advisories box, `Link to="/settings"` with `wb.setup.open` / `wb.setup.openCards` | open Settings | Button asChild |
| `DecidedFold`, the Show / Hide toggle (`wb.decided.show` / `wb.decided.hide`) | fold toggle | Button, label from section 4 |
| the "receipt taken" line, the buttons calling `scrollToCharge(h.transaction_id)` | jump to the holding charge | Button |
| the FX summary line, the toggle with `wb.fx.details` / `wb.fx.hideDetails` | FX details | Button, labels `wb.fx.showDetails` / `wb.fx.hideDetailsButton` |
| the rejected candidate line, `wb.cand.rejectedUndo` | undo a reject | Button, label `wb.cand.undoReject` |
| a candidate's held-by line, `wb.charge.receiptTaken.holder` | jump to the holder | Button, `block` removed, keep `text-left` |
| the receipt preview, `<a>` with `wb.receipt.openOriginal` | open original | Button asChild around the `<a>`, icon kept |
| the duplicates panel, the Show / Hide toggle beside the fold label (`showDecided`) | fold toggle | Button, labels `wb.dup.showGroups` / `wb.dup.hideGroups` with `{n}` = groups in the fold |
| the card filter chips, the toggle with `wb.filter.card.empty` | show empty cards | Button, labels `wb.filter.card.showEmpty` / `wb.filter.card.hideEmpty` with `{n}`; drop the `˅` / `›` glyph |

## 3. Expenses view (`src/components/ExpensesReviewGrid.tsx`)

| Where (search for) | Control | After |
|---|---|---|
| the receipt coverage line, the toggle with `grid.filter.notInReport` | filter | Button |
| the duplicate copies bar, the toggle showing `expx.dup.count` / `expx.dup.count_one` | filter | Button; keep the amber text colour classes |
| the learned-row cell, `expx.review.forget` | forget the learning | Button |
| the held-mail strip, `Link to="/inbound"` with `inbound.held.viewAll` | open email intake | Button asChild |
| the duplicate marker, `expx.dup.deleteExtra` | delete the extra copy | Button, add `text-rose-600 border-rose-300 dark:text-rose-400 dark:border-rose-800` |
| the duplicate marker, `expx.dup.notDuplicate` | not a copy | Button |
| the settled-outside cell, `expx.settledOutside.undo` | put back | Button |
| the private badge, `expx.private.undo` | not private | Button |
| the private cell, the `DialogTrigger` child with `expx.private.confirm` | confirm private expense | Button inside `DialogTrigger asChild` |
| the card-review strip, the toggle with `expx.cards.strip.showSpellings` / `hideSpellings` | fold toggle | Button |

The NEEDS PERSON tile's `Link to="/settings"` is not in this list: the
item-84 Expenses boxes prompt replaces that tile. If that prompt is not
applied yet, leave that link as it is.

## 4. A fold toggle names what it shows

`DecidedFold` takes two new props, `showLabel: string` and `hideLabel: string`,
and its button reads `shown ? hideLabel : showLabel`. The callers pass:

| Fold | `showLabel` | `hideLabel` |
|---|---|---|
| every row booked (the `section === "posted"` branch) | `wb.decided.showBooked` `{n}` | `wb.decided.hideBooked` `{n}` |
| every row a copy (the `foldCopies` branch) | `wb.decided.showCopies` `{n}` | `wb.decided.hideCopies` `{n}` |
| any other fold | `wb.decided.showDecided` `{n}` | `wb.decided.hideDecided` `{n}` |

`{n}` is the same number the fold label uses (`decidedShown`). Pick `.one` when
it is 1.

## 5. "Already booked" names its workbook (item 86)

In the posted branch of the fold label (where `wb.decided.foldPosted.one` /
`.many` are used today), use `wb.decided.foldBooked.one` / `.many` with
`{n}` and `{file}` instead, where `{file}` is
`asArray<{ file?: string }>(data.statements).map((s) => s.file).filter(Boolean).join(", ")`.
When that string is empty, use `wb.decided.foldBookedNoFile.one` / `.many`
with `{n}` only. Render the label inside a `Tooltip` whose content is
`t("wb.decided.foldBooked.tip")` (the existing `Tooltip` / `TooltipTrigger` /
`TooltipContent` imports; the trigger is the label `<span>`, never the
button). `wb.decided.foldPosted.*` stay in the dictionary, unused.

## 6. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `wb.decided.foldBooked.one` | 1 row marked yellow in {file}, already booked | 1 linha marcada em amarelo em {file}, já lançada |
| `wb.decided.foldBooked.many` | {n} rows marked yellow in {file}, already booked | {n} linhas marcadas em amarelo em {file}, já lançadas |
| `wb.decided.foldBookedNoFile.one` | 1 row marked yellow in the statement workbook, already booked | 1 linha marcada em amarelo na planilha do extrato, já lançada |
| `wb.decided.foldBookedNoFile.many` | {n} rows marked yellow in the statement workbook, already booked | {n} linhas marcadas em amarelo na planilha do extrato, já lançadas |
| `wb.decided.foldBooked.tip` | The workbook is the statement spreadsheet uploaded for this month. A row coloured yellow there is already booked; a grey row is a subscription. The colours are read when the statement is loaded. | A planilha é o extrato enviado para este mês. Uma linha pintada de amarelo já foi lançada; uma linha cinza é uma assinatura. As cores são lidas quando o extrato é carregado. |
| `wb.decided.showBooked.one` | Show 1 booked row | Mostrar 1 linha lançada |
| `wb.decided.showBooked.many` | Show {n} booked rows | Mostrar {n} linhas lançadas |
| `wb.decided.hideBooked.one` | Hide 1 booked row | Ocultar 1 linha lançada |
| `wb.decided.hideBooked.many` | Hide {n} booked rows | Ocultar {n} linhas lançadas |
| `wb.decided.showCopies.one` | Show 1 copy | Mostrar 1 cópia |
| `wb.decided.showCopies.many` | Show {n} copies | Mostrar {n} cópias |
| `wb.decided.hideCopies.one` | Hide 1 copy | Ocultar 1 cópia |
| `wb.decided.hideCopies.many` | Hide {n} copies | Ocultar {n} cópias |
| `wb.decided.showDecided.one` | Show 1 decided row | Mostrar 1 linha decidida |
| `wb.decided.showDecided.many` | Show {n} decided rows | Mostrar {n} linhas decididas |
| `wb.decided.hideDecided.one` | Hide 1 decided row | Ocultar 1 linha decidida |
| `wb.decided.hideDecided.many` | Hide {n} decided rows | Ocultar {n} linhas decididas |
| `wb.dup.showGroups.one` | Show 1 group | Mostrar 1 grupo |
| `wb.dup.showGroups.many` | Show {n} groups | Mostrar {n} grupos |
| `wb.dup.hideGroups.one` | Hide 1 group | Ocultar 1 grupo |
| `wb.dup.hideGroups.many` | Hide {n} groups | Ocultar {n} grupos |
| `wb.fx.showDetails` | Show FX details | Mostrar detalhes do câmbio |
| `wb.fx.hideDetailsButton` | Hide FX details | Ocultar detalhes do câmbio |
| `wb.cand.undoReject` | Undo reject | Desfazer rejeição |
| `wb.filter.card.showEmpty` | Show {n} cards with nothing this month | Mostrar {n} cartões sem lançamentos neste mês |
| `wb.filter.card.hideEmpty` | Hide {n} cards with nothing this month | Ocultar {n} cartões sem lançamentos neste mês |

Also change two existing EN values that read badly on a button:
`expx.review.forget` "forget" -> "Forget", PT "esquecer" -> "Esquecer".

## 7. Do not change

- What any control does, its handler, its disabled rule or its tooltip.
- The five Matching cards, the Expenses tiles (item 84's prompt owns those),
  the Reject / Confirm match buttons, the dialogs' own buttons.
- Row layout, table columns, filters, sort and the `filters.decided` switch.

## 8. Render defensively

`data.statements` may be absent or empty: the no-file keys apply. A missing
`file` on an entry is skipped. Never print a raw key.

## 9. After publishing, check

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit):
   `wb.decided.foldBooked.many`, `wb.decided.showBooked.many`,
   `wb.dup.showGroups.many`, `wb.fx.showDetails`, `wb.filter.card.showEmpty`.
2. July, Matching, Charges without a receipt: the fold reads "48 rows marked
   yellow in July2026.xlsx, already booked" (72 charges, 24 open: the number
   is the fold's own count), its hover names the yellow and grey rule, and the
   toggle is an outline button reading "Show 48 booked rows"; clicking it
   reads "Hide 48 booked rows".
3. July, Matching, Matched: same shape for its booked fold (note #51 read
   "16 already posted in your workbook").
4. July, the duplicates panel toggle is an outline button reading "Show 5
   groups".
5. July, Expenses: "Confirm private expense" on a suggested-private row is an
   outline button that opens the same dialog (cancel it; do not save).
6. No control listed in sections 2 and 3 carries an underline class in the
   rendered DOM.
7. PT on July: "linhas marcadas em amarelo", "Mostrar", "Confirmar despesa
   particular".
8. Network: no POST other than `/api/login` during the drive.

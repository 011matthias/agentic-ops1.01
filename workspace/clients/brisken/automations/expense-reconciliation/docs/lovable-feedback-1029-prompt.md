# Lovable prompt - feedback notes #123, #125, #126, #128, #130, #132, #136 (2026-10-07 to 2026-10-29)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). Front-end only: no new request, no new API field, no
change to any count or box. **Do NOT add Supabase or any database.** Every
string below goes into `src/lib/i18n.tsx` in English and Portuguese.

## 1. Review actions sit in the top bar (note #128)

`ExpensesReviewGrid.tsx`, the header block that renders
`t("expx.review.subtitle")`. The button group on the right (Add receipts, Add
expense, Save corrections to memory, and the rest) must sit on the SAME line
as the page title at the top of the page, right-aligned, and must not wrap
below the subtitle on a desktop-width screen. Below `md`, wrapping is fine.
The subtitle stays under the title. Do not change what any button does.

## 2. "Open" explains itself (note #132)

`RunWorkbench.tsx`, the view tab `wb.view.open` ("{n} open"). The meaning
already exists as a hover tip (`wb.view.open.tip`) and nobody found it. Render
the same sentence as a visible one-line caption under the tab row while the
"Charges with no receipt" view is selected, and keep the tooltip.

| Key | EN | PT |
|---|---|---|
| `wb.view.open.caption` (new) | Open = still needs a person. Charges already booked, closed by a recurring booking, or marked "no receipt exists" are not counted. | Aberto = ainda precisa de uma pessoa. Lançamentos já registrados, fechados por uma recorrência ou marcados como "não existe recibo" não entram na conta. |

## 3. "Set aside" has room to work (note #130)

`ExpensesReviewGrid.tsx`, `SetAsideStrip`. The strip lists receipts and also
statement pages, and the reader has to judge each one. Change layout only:

- Every entry gets its own full-width row: file name, the reason wrapped in
  full (never truncated), and the existing View and Restore actions on the
  right.
- Entries are sorted so entries with the same `reason` sit together, and each
  group has a small sub-heading with its reason text and a count.
- The strip is collapsed to its heading when it holds more than 6 entries,
  and opens on click; the heading keeps showing the count.

## 4. Card form: help text and example numbers (note #123)

`CardsCard.tsx`, the "digits" field (`set.cards.help.digits`, the chips field
above it). While the field holds at least one chip, or the draft input holds
text, hide the help paragraph under it and hide any example number (the
placeholder text such as 2838). Show them again when the field is empty. Apply
the same rule to the aliases field (`set.cards.help.aliases`).

## 5. Fuzzy search on the Cards settings (note #125)

`CardsCard.tsx` / `SettingsScreen.tsx`. Add a search box above the card list
(`set.cards.search.placeholder`). It filters the visible card rows as the
person types, matching label, digits, aliases, company, person and Zoho
account. Matching is forgiving: case-insensitive, accent-insensitive, and a
row matches when every typed word is a prefix of a word in it or when the typed
text is a subsequence of the row text. No new dependency; a small local
function. Rows keep their own edit state; filtering must never discard an
unsaved edit. Show "No card matches" when nothing matches.

| Key | EN | PT |
|---|---|---|
| `set.cards.search.placeholder` (new) | Find a card: name, last digits, company, person | Buscar cartão: nome, final, empresa, pessoa |
| `set.cards.search.none` (new) | No card matches | Nenhum cartão encontrado |

## 6. Receipt overview (notes #126, #136)

`ReceiptOverviewTable.tsx`.

- **#126.** A row whose `status` is `set_aside` ("Set aside (not a receipt)")
  has no receipt, so the File column must not offer to open it: render the
  file name as plain muted text with no View action and no link. Rows that
  have a receipt are unchanged.
- **#136.** Add an "Open expense" link in the File cell for every row with
  `batch_id` and `document_id` and a status other than `set_aside`, `removed`
  and `dismissed`. It navigates to `/expenses/$batchId` (the same route the
  Month column already links to) and passes `document_id` as a search
  parameter `doc`. If the expense grid has a text filter, pre-fill it with the
  file name from `doc`; if it does not, plain navigation is enough.

| Key | EN | PT |
|---|---|---|
| `rov.openExpense` (new) | Open expense | Abrir despesa |

## Verify after publishing

1. A month's Expenses page: action buttons share the title's line on a wide screen.
2. Matching page, "Charges with no receipt" view: the caption under the tabs reads the Open definition.
3. Settings > Cards: type a digit group, the example number and help vanish; clear it, they return. Type "chase" in the search box, rows narrow; clear it, all return, edits intact.
4. Receipt overview: a "Set aside (not a receipt)" row has no link on its file name; a matched row shows "Open expense" and it lands on that month.

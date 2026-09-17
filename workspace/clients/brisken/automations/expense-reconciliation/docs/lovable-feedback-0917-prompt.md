# Lovable prompt: the 2026-09-17 feedback notes

> **NOT YET APPLIED.** Section 6 reads `card_ending`, which ships with the
> notes-#54/#60 backend deploy; every other section works against the API as
> it is. Notes answered: #55, #56, #57 (Criss), #58, #59 (owner), item 78.

The app calls the FastAPI backend at `https://api.expenses.brisken.com`.
Seven small changes, each independent. Render defensively: a missing new
field degrades to the screen as it is today, never to an error.

## 1. Settings > Advanced: take the export switch out

The Advanced tab shows an "Export policy" section with the switch "Send only
confirmed rows to Zoho". Remove it. The app is moving away from Zoho, and a
control whose only effect is on the Zoho export does not belong in Settings.

- Delete the whole section: heading, switch, help sentence and the "Applies
  to months created from now on" sentence. Clear memory stays exactly as it
  is and becomes the only thing in the tab.
- Nothing reads or sends `export_approved_only` any more. Do not send
  `{"export_approved_only": false}` as part of the removal; the stored value
  is already false and stays untouched.
- Delete `set.export.title`, `set.export.approvedOnly`, `set.export.help`,
  `set.export.scope` in both languages. Keep `set.tabs.advanced`.
- The Advanced tab never shows the unsaved-changes dot. It has nothing to
  save, so typing in the "Type CLEAR to enable" box is not an unsaved edit;
  today it marks the tab and nothing ever clears the mark.

## 2. Settings > Legal entities: say what two fields do

The owner asked whether "Default paid through" recognises card endings
separated by commas. It does not, and the screen should say so. Add one
muted help line under each of these two fields; change nothing else in the
tab and add no dropdowns.

- Under **Default paid through**: `set.entities.help.defaultPaidThrough`.
- Under **Account picks**: `set.entities.help.accountPicks`.

## 3. Settings > Merchants: what to do here

Criss opened Merchants and could not tell what to add, change or fill in.
Add a short guidance block between the section's description and the first
row, `set.merchants.howTo`, as plain text in the muted style of the other
help lines. It stays visible when the list is empty and when it is full.

## 4. Expenses: mark any expense as a reimbursement

Criss looked for "Reimbursement" on an ordinary row and it was not there. It
exists, but only on rows the tool suggested as private
(`suggested_private: true`), through the "Confirm private expense" dialog
(`expx.private.confirm`).

- Offer **Mark as reimbursement** (`expx.reimburse.mark`) in every expense
  row's actions, whatever `suggested_private` says. It opens the SAME dialog
  the suggested rows use, with the same `reimburse_to` field, prefilled from
  `reimburse_to_prefill` when it is non-empty, else from the row's `person`.
  It sends the same request:
  `POST /api/runs/{id}/expenses/{doc}/private` with
  `{"private": true, "reimburse_to": "<name>"}`. The backend 400s when the
  name is empty; show that error verbatim.
- On a row with `private: true`, offer **Undo reimbursement**
  (`expx.reimburse.undo`), sending `{"private": false}` to the same route.
- Nothing else about the dialog or the suggested-private flow changes.

## 5. Expenses: take a category back

A category picked by mistake could not be undone from the dropdown.

- When a row's `posting_category.source` is `"override"` (the reviewer
  picked it), add **Undo my category** (`expx.category.undo`) as the first
  option of that row's category dropdown.
- Picking it sends `PUT /api/runs/{id}/expenses/{doc}` with
  `{"field": "category", "value": ""}`. The row comes back with the tool's own
  category, or with no category at all (`posting_category` null) when the tool
  had none. Render both.
- Rows whose category the reviewer did not pick do not show the option.

## 6. Expenses: a card named by its last two digits

Some receipts print only the last two card digits (`42463153XXXXXX38`). The
backend now names the card from them when exactly one card ends in those two
digits, and says so on the row: `card_ending` is `"38"` in that case and `""`
otherwise.

- When `card_ending` is non-empty, show a muted note beside the row's card:
  `expx.card.byEnding` with `{digits}` = `card_ending`. The card, company and
  person render as for any other card.
- In the card strip, an unresolved group whose `digits` has two characters is
  an ending, not a card number: show it as `••76`, not `76`. Such groups are
  often `ambiguous: true` (two cards end in the same digits); the existing
  ambiguous rendering applies unchanged.

## 7. Matching: say that the statement is already loaded

Criss, on a month's Matching page: "it should show that the statement was
already added." The run payload carries `statements[]`, oldest first, each
with `upload_name`, `period_start`, `period_end`, `n_rows`, `uploaded_at`.

- Under the page title, one muted line per entry: `wb.statement.loaded` with
  `{name}` = `upload_name`, `{from}` / `{to}` = the period dates in the page's
  date format, `{n}` = `n_rows`, `{date}` = the date part of `uploaded_at`.
  When `period_start` is null, use `wb.statement.loadedNoPeriod`.
- When `has_statement` is true but `statements[]` is empty (months from before
  the list was recorded), show `wb.statement.loadedOld` once.
- Nothing when there is no statement; the page already offers the upload.

## New strings (EN, PT-BR)

| Key | EN | PT |
|---|---|---|
| `set.entities.help.defaultPaidThrough` | Only used by the Zoho export, as the Paid Through account when no card names one. Card numbers typed here are not read as cards: which card belongs to this company is set on the Cards tab. | Usado apenas pela exportação Zoho, como conta Paid Through quando nenhum cartão indica uma. Números de cartão digitados aqui não são lidos como cartões: qual cartão pertence a esta empresa se define na aba Cartões. |
| `set.entities.help.accountPicks` | The accounts the expense list offers for this company's rows. Leave empty to offer the company's chart of accounts. | As contas que a lista de despesas oferece para as linhas desta empresa. Deixe vazio para oferecer o plano de contas da empresa. |
| `set.merchants.howTo` | Use this list when one vendor shows up under different names. Put the name you want to see under Canonical name, add every other spelling from receipts or statements as an alias, and pick the category its expenses should get. If the vendor sells different kinds of things, leave the category to the tool or switch on "This vendor uses multiple categories". | Use esta lista quando um fornecedor aparece com nomes diferentes. Coloque o nome que você quer ver em Nome canônico, adicione cada outra grafia dos recibos ou extratos como apelido e escolha a categoria que as despesas dele devem receber. Se o fornecedor vende coisas de tipos diferentes, deixe a categoria com a ferramenta ou ative "Este fornecedor usa várias categorias". |
| `expx.reimburse.mark` | Mark as reimbursement | Marcar como reembolso |
| `expx.reimburse.undo` | Undo reimbursement | Desfazer reembolso |
| `expx.category.undo` | Undo my category | Desfazer minha categoria |
| `expx.card.byEnding` | matched on the last two digits ({digits}) | identificado pelos dois últimos dígitos ({digits}) |
| `wb.statement.loaded` | Statement loaded: {name}, {from} to {to}, {n} charges, added {date} | Extrato carregado: {name}, de {from} a {to}, {n} cobranças, adicionado em {date} |
| `wb.statement.loadedNoPeriod` | Statement loaded: {name}, {n} charges, added {date} | Extrato carregado: {name}, {n} cobranças, adicionado em {date} |
| `wb.statement.loadedOld` | Statement loaded | Extrato carregado |

## Checking it landed

1. `/settings?tab=advanced`: only Clear memory; typing in its box leaves no
   dot on the Advanced trigger.
2. Legal entities: the two help lines sit under their fields, EN and PT.
3. Merchants: the guidance block shows above the first row.
4. An August expense that was never suggested private offers Mark as
   reimbursement; the dialog opens prefilled. Close it with Escape.
5. A row with a reviewer-picked category offers Undo my category first; a row
   the tool categorized does not.
6. No live row carries a `card_ending` yet (the one receipt printing two
   digits was fixed by hand, which outranks the rule). Check the note on the
   next receipt that prints only two card digits, and check the strip shows a
   two-character group as `••76`.
7. August's Matching page shows one "Statement loaded" line per statement.

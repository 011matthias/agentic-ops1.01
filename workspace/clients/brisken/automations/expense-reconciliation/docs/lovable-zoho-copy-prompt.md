# Lovable prompt: Remove the Zoho wording the flow no longer has

**APPLIED. Verified 2026-09-01 in the published bundle (`brisken-reconcile-dash.lovable.app`): "Download journal CSV" and "matched against this month's receipts" are both present.**

Paste into `brisken-expense-review` (production
`brisken-reconcile-dash.lovable.app`). No backend change. This is a
copy-only sweep of `src/lib/i18n.tsx`: the EN dictionary and the PT
mirror further down in the same file. Every change below must be made in
BOTH dictionaries. The PT strings below are final copy; use them
verbatim (the dictionary is accented pt-BR and uses "conciliação",
"transações", "CSV de lançamentos" as its established vocabulary).

## Why

Operator, 2026-08-28, on the run page: "why are we still matching things
against zoho data? ... i dont want this connected to zoho." The app has
no Zoho connection (removed 2026-08-22), but the copy still claims one,
and it made a disconnected system read as connected in front of the
operator. The rule for this sweep: copy that claims Zoho as the SOURCE
or DESTINATION of the flow changes; labels that truthfully name a
Zoho-shaped artifact (the journal CSV's content, the yellow
already-posted rows from Criss's workbook, the "Zoho Expense PDF" file
format) stay for now, pending the owner's decision on the export shape.

Exact current EN strings are quoted so the right keys are unmistakable.

## 1. Run page (the ones the operator hit)

- `wb.subtitle.template` (EN i18n.tsx:167-168, PT :1260-1261): "{n}
  charges from the bank statement, matched against Zoho Expense
  receipts. Confirm or reject each suggested match." becomes
  EN "{n} charges from the bank statement, matched against this month's
  receipts. Confirm or reject each suggested match."
  PT "{n} transações do extrato bancário, cruzadas com os recibos deste
  mês. Confirme ou rejeite cada par sugerido."
  Keep the {n} placeholder in both.
- `wb.howto.step1` (EN :331-332): "The tool matched each bank-statement
  charge to the closest Zoho receipt." becomes
  EN "The tool matched each bank-statement charge to the closest
  receipt in this month."
  PT "A ferramenta cruzou cada transação do extrato com o recibo mais
  próximo deste mês."
- `wb.howto.step3` (EN :335): "Confirmed rows are what gets exported to
  Zoho." becomes
  EN "Confirmed rows are what lands in the export and the reports."
  PT "As linhas confirmadas são o que entra na exportação e nos
  relatórios."
- `wb.receipt.noImage.hint` (EN :299): "(attach it in Zoho Expense)"
  becomes EN "(add the receipt to this month)" / PT "(adicione o recibo
  a este mês)".

## 2. Dashboard and landing

- `dash.pub.download` (EN :91): "Download Zoho CSV" becomes
  EN "Download journal CSV" / PT "Baixar CSV de lançamentos".
- `dash.pub.empty.body` (EN :89-90; the key is `dash.pub.empty.body`,
  not `dash.pub.hint`): "Open a run, resolve every row, then hit
  Publish. The Zoho journal CSV will show up here for download."
  becomes
  EN "Open a run, resolve every row, then hit Publish. The journal CSV
  will show up here for download."
  PT "Abra uma execução, resolva todas as linhas e clique em Publicar.
  O CSV de lançamentos aparecerá aqui para download."
- `expx.landing.subtitle` (EN :645): "Upload receipts and get Zoho-ready
  expenses. No statement required." becomes
  EN "Upload receipts and get export-ready expenses. No statement
  required."
  PT "Envie recibos e obtenha despesas prontas para exportar. Sem
  precisar de extrato bancário."
- `expx.landing.empty.body` (EN :649): the ending "Nothing posts to Zoho
  until you export the CSV." becomes
  EN "... Nothing leaves the tool until you download the export."
  PT (full string) "Solte uma pasta de recibos e receba uma linha por
  despesa. Nada sai da ferramenta até você baixar a exportação."

## 3. Review reasons and tooltips

- `expx.review.reason.NO_CATEGORY` (EN :815) and
  `expx.review.reason.uncategorized` (EN :820): "Pick a category to send
  this to Zoho." becomes EN "Pick a category before export." /
  PT "Escolha uma categoria antes de exportar."
- `expx.review.reason.category_account_mismatch` (EN :836): "The
  category and Zoho account do not match." becomes EN "The category and
  GL account do not match." / PT "A categoria e a conta contábil não
  combinam."
- `expx.review.account.tooltip` (EN :176): "Zoho GL account for the
  export (optional)" becomes EN "GL account for the export (optional)" /
  PT "Conta contábil para a exportação (opcional)".

## 4. Intake prepare and guide

- `new.useLlm.hint` (EN :108-109; the AI toggle help on the
  intake-prepare screen and the classic form): "On by default on this
  server. Slower, but it classifies receipts into Zoho categories
  automatically." becomes
  EN "On by default on this server. Slower, but it classifies receipts
  into your categories automatically."
  PT "Ativada por padrão neste servidor. Mais lenta, mas classifica os
  recibos nas suas categorias automaticamente."
- `guide.flow.p1` (EN :414): "Through the month, receipts and expenses
  pile up in Zoho Expense. At month-end you take the card statement and
  reconcile it against those receipts." becomes
  EN "Through the month, receipts arrive in the tool: uploaded on the
  month page or emailed to the intake address. At month-end you attach
  the card statement and reconcile it against those receipts."
  PT "Ao longo do mês, os recibos chegam à ferramenta: enviados na
  página do mês ou por e-mail para o endereço de entrada. No fim do mês,
  você anexa o extrato do cartão e o concilia com esses recibos."
- `guide.finish.p2` (EN :427): change only the artifact name, "Then
  download: Zoho journal (.csv), ..." becomes "Then download: the
  journal (.csv), ...". The sentence TAIL "and, for an Excel statement,
  your sheet with a Zoho-account column." STAYS unchanged in both
  languages: that column is literally named "Zoho Account (tool)" in the
  written-back file, so the words name a real artifact.
  PT (full string) "Então baixe: o lançamento (.csv), dados conciliados
  (.csv), relatório (.xlsx) e, para um extrato em Excel, sua planilha
  com uma coluna de conta do Zoho."
- `guide.good.p1` (EN :432): "Nothing posts to Zoho on its own."
  becomes EN "Nothing leaves the tool on its own." / PT "Nada sai da
  ferramenta sozinho."

## Deliberately unchanged (do not touch)

- "Zoho Expense PDF" as a FILE FORMAT name (`new.source.pdf`,
  `new.receipts.hint`, `guide.start.p1`). Note it appears on the
  months-flow intake-prepare screen as well as the classic screen; it is
  the real name of the export format the tool reads, so it stays on
  both.
- Truth labels about rows that really were posted in Zoho: the "Already
  in Zoho" status and tip (they can appear on any run whose upload
  carried already-posted rows), "Zoho's rate", "Uploaded here, not from
  Zoho Expense", the yellow-row hints on the classic upload screen.
- Settings and Memory column labels naming the Zoho account field; they
  follow the owner's pending decision on the export shape, together with
  the backend's own Zoho strings (the paid-through banner, download
  filenames, CSV and Excel column headers), which ship in a backend
  round.
- The SPA's fallback download filenames (`zoho-journal-...csv`); they
  mirror the backend's filenames and change together with them.
- Head-meta descriptions in `src/routes/expenses.*.tsx` (not on-page
  copy).

## Verify after publish

1. Run page subtitle now says "matched against this month's receipts"
   (EN) / "cruzadas com os recibos deste mês" (PT).
2. The how-it-works steps and the missing-receipt hint no longer mention
   Zoho.
3. The dashboard button reads "Download journal CSV" and still downloads
   the same file.
4. The intake-prepare and classic screens still name the "Zoho Expense
   PDF" format.

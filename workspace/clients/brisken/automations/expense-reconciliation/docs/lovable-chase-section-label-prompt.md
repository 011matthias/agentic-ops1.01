# Lovable prompt: the chase section says what it lists (item 161)

**Background.** On April's reconciliation page the owner pointed at the
section "Receipts to chase (65)" and wrote "what is this". Asked which half
of the question they meant, they answered: what the section LISTS. The
section lists charges, not receipts. Four lines above it the page already
says so correctly, in the box "Charges without a receipt · 65" - the same 65,
labelled two different ways on one screen. The section's own table proves the
label wrong: its columns are Date, Vendor, Amount, **Card**, while the
receipts table on the same page reads Date, Vendor, Total, **Document**. This
prompt makes the title name its contents and says where the number comes
from. Copy only: no backend change, no new field, no new request.

The name is not nonsense shorthand to delete; the list exists so a person can
be asked for the receipts those charges need, and it is grouped by card
holder for exactly that. Keep the purpose in the title, add the population.

## Paste this into Lovable

1. In `src/lib/i18n.tsx`, change one existing key and add one new one.
   `{n}` is already interpolated on `chase.title`; interpolate it the same way
   on the new key.

   English:
   - `"chase.title"`: change from `"Receipts to chase ({n})"` to
     `"Charges with no receipt, to chase ({n})"`
   - add `"chase.subtitle": "The same {n} as \"Charges without a receipt\" above: every charge on the statement that no receipt has been matched to, grouped by the card holder who can find it."`

   Portuguese (pt-BR):
   - `"chase.title"`: change from `"Recibos a cobrar ({n})"` to
     `"Lançamentos sem recibo, para cobrar ({n})"`
   - add `"chase.subtitle": "Os mesmos {n} de \"Lançamentos sem recibo\" acima: todo lançamento do extrato ao qual nenhum recibo foi vinculado, agrupado pelo portador do cartão que pode encontrá-lo."`

   The new title reuses the exact words of `wb.view.unmatched` ("Charges
   without a receipt" / "Lançamentos sem recibo"), which is the box above it.
   That is the point: the reader should see one population named once.

2. In the reconciliation page's chase section (the component that renders
   `chase.title` over the `receipt_chase` groups), render `chase.subtitle`
   directly under the title, in the muted small style the page already uses
   for section subtitles. One line, no icon, no tooltip, no link.

3. Nothing else changes. Do not touch the grouping by card holder, the
   per-holder counts and amounts, `chase.noAddress`, the Send / Copy /
   Preview controls, `chase.requestedOn`, `chase.alreadyAsked`, the table
   columns, or the box row above it (`wb.view.unmatched`,
   `wb.view.receipts`, `dash.tiles.review`, `wb.view.refund`).

**Do not change:** any API call, any field name, auth (bearer token,
`API_BASE` `https://api.expenses.brisken.com`), the Expenses page, or any
other `chase.*` string.

## Verify after publish

1. Open April (`/runs/0603bb0e6f38`). The box row reads "Charges without a
   receipt · 65"; the section below now reads "Charges with no receipt, to
   chase (65)" with the subtitle under it. The same words, the same number,
   twice, with no third name for it.
2. The subtitle's `{n}` reads 65, not `{n}`.
3. Switch to Portuguese and read both again.
4. August (`/runs/074a7b8905d7`) reads 61 in both places. July reads 0 and the
   section does not render at all, as today.

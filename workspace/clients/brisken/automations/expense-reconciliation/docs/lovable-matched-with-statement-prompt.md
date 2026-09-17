# Lovable prompt - "Reconciled" on the months list says what it means (item 89)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`. No backend change.

## Background

On the Months page the Statement column shows a green "Reconciled" badge on
every month that has a statement loaded. It appears as soon as a statement is
attached, while the month still has open charges and receipts (July: 24
charges without a receipt), so "Reconciled" claims the month is done when it
only means the statement was matched against the receipts. The owner asked
for "Matched with statement".

## 1. The badge (`src/components/MonthsHome.tsx`)

In the Statement column, the `Badge` shown when `reconciled`
(`!!b.has_statement`) reads `t("months.state.matchedStatement")` instead of
`t("months.state.reconciling")`. Keep its classes, its condition and its
place. Wrap it in the existing `Tooltip` / `TooltipTrigger asChild` /
`TooltipContent`, content `t("months.state.matchedStatement.tip")`.
`months.state.reconciling` stays in the dictionary, unused.

## 2. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `months.state.matchedStatement` | Matched with statement | Comparado com o extrato |
| `months.state.matchedStatement.tip` | A statement is loaded and its charges were matched against this month's receipts. Open the month to see what is still open. | Um extrato foi carregado e as transações foram comparadas com os recibos deste mês. Abra o mês para ver o que ainda está em aberto. |

The PT wording is a draft for Criss.

## 3. Do not change

The months table, its columns, row click, the Actions menu, the origin badges
("drop", "intake") and every other page.

## 4. After publishing, check

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit):
   `months.state.matchedStatement`, `months.state.matchedStatement.tip`.
2. `/months`: July 2026 and August 2026 read "Matched with statement"; months
   with no statement show no badge; "Reconciled" appears nowhere in the table.
3. Hover the badge: the tooltip text above.
4. PT: "Comparado com o extrato".

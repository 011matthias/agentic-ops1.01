# Lovable prompt - charges on an unnamed card show the gap (item 59)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

A Chase workbook prints several cards. Until now every charge in it took the
entity of the card the upload was filed under, so all 111 of August's charges
read Corporate Services while 77 of them were on cards 3645 and 3876, which
the registry has never met and the Coverage panel already labels "not in your
card list".

Backend now resolves the entity per row from the card the row printed, and
leaves it EMPTY when the registry cannot name that card. Owner ruling: a
visible gap beats a wrong posting.

Two field changes:

| Field | Where | Meaning |
|---|---|---|
| `rows[].legal_entity_id` | `GET /api/runs/{id}` | may now be `""` on a charge whose card the registry does not know. Same type, new value. |
| `summary.n_charges_no_entity` | both payloads, always present | how many charges carry no entity. 0 before a statement is loaded. |

## 1. The charge row

Wherever the workbench renders a charge's company, an empty value gets the
neutral placeholder the grid already uses for an unresolved entity, not a
blank cell and not the batch's entity. Suggested: a muted chip reading
`Card not defined` that links to Settings > Cards, the same destination the
Coverage panel's "not in your card list" link already uses.

Do not offer a per-row entity editor for charges. The fix is the card.

## 2. New tile: CHARGES WITHOUT A COMPANY

Add `summary.n_charges_no_entity` to the workbench stat row, after
UNMAPPED ACCOUNTS. Neutral when 0, warning tone above 0. Clicking it filters
the charge list to those rows (reuse the existing filter mechanism; no new
API call).

## 3. Copy

| Key | EN | PT |
|---|---|---|
| `wb.tile.chargesNoEntity` | Charges without a company | Lancamentos sem empresa |
| `wb.charge.cardNotDefined` | Card not defined | Cartao nao definido |
| `wb.charge.cardNotDefined.help` | This charge is on a card the tool does not know yet. Define it once in Settings > Cards and every charge on it gets its company. | Este lancamento esta num cartao que a ferramenta ainda nao conhece. Defina-o uma vez em Configuracoes > Cartoes e todos os lancamentos dele recebem a empresa. |

## 4. Do not change

`n_needs_entity` keeps its meaning: it counts EXPENSES (receipt rows) that
still need a company. The new count is the charge-side question and has its
own name. The Coverage panel already reads `coverage[].entity` and
`coverage[].known`; nothing there changes.

# Lovable prompt - the card's Zoho account is picked from a list (backlog item 265, note #124)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). One field changes. **Do NOT add Supabase or any
database.** Every string below goes into `src/lib/i18n.tsx` in English and
Portuguese.

## Background

Note #124 (Settings > Cards, the Zoho account field): "this should be a drop
down list of available zoho accounts for credit cards." The field is a free
text `Input` today, so a typo or another card's label is only caught after
saving, by the account check.

`GET /api/settings` now carries `card_account_options`: every active Zoho
credit-card account per company, never an expense account, an inactive one or
one marked DO NOT USE.

```ts
card_account_options?: {
  company: string;    // the entity name the card's "Company" select uses; "" when no entity maps to the org
  org_id: string;
  name: string;       // what the card stores in zoho_account
  account_id: string;
}[];
```

It is derived and read-only: the settings PUT accepts it back and ignores it,
so the existing whole-object save keeps working unchanged.

## 1. The Zoho account field becomes a picker (`CardsCard.tsx`)

The `zoho_account` field (label `set.cards.col.zoho`, the `Input` with
placeholder "1010 Chase Corporate"):

- Replace the `Input` with a searchable combobox built from the project's
  `Popover` (`@/components/ui/popover`) and `Command`
  (`@/components/ui/command`, with `CommandInput` for the search) whose
  options are the `card_account_options`
  entries whose `company` equals the row's company (`row.entity`). When the
  row has no company, list every entry and show its company beside the name.
- Choosing an option sets `zoho_account` to the option's `name` (call
  `markEdited(i)` and `update(i, { zoho_account: name })` exactly as the
  input's `onChange` does now).
- A first option "None (this card does not post to Zoho)" sets
  `zoho_account` to "".
- **A stored value that is not in the list stays visible and selected**,
  shown as-is with the existing warning under it. Never blank it or swap it
  for the first option on render: the account check below must keep
  describing what is actually stored.
- Keep everything under the field as it is: the green check icon on
  `account_check.status === "ok"`, the amber warning, "Did you mean
  {closest}?" (its button still sets the field), the stale-chart line, and the
  help line `set.cards.help.zoho`.
- When `card_account_options` is absent or empty (no chart on the server),
  fall back to the current free-text `Input` unchanged.

| Key | EN | PT |
|---|---|---|
| `set.cards.zoho.none` (new) | None (this card does not post to Zoho) | Nenhuma (este cartão não lança no Zoho) |
| `set.cards.zoho.placeholder` (new) | Choose the card's Zoho account | Escolha a conta Zoho do cartão |
| `set.cards.zoho.search` (new) | Search accounts | Buscar contas |

## Verify after publishing

1. Settings > Cards, a Corporate Services card: the field opens a list of that
   company's credit-card accounts only; no expense account appears.
2. A card whose stored account is flagged today still shows that stored name
   and its warning, not a blank field.
3. Pick an account and save: the check icon reads ok for that card.

# Lovable prompt: cards under an account (item 147)

> **NOT YET APPLIED.** Backend first: `card_sections[].subcards`, `.own`,
> `.parent` and `.statement_on_account` on `GET /api/runs/{id}` and
> `GET /api/expense-batches/{id}`, plus `cards[].parent` on `GET /api/cards`
> (item 147; contract in `docs/api-contract.md`, "Cards under an account").
> Two gates, not one: the fields are absent until that deploy, AND they stay
> absent until the owner sets the three parents in Settings, Cards. Until
> both, every tab renders exactly as it does today.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. This edits `src/components/CardTabs.tsx`, the card editor in the Settings page, and the types in `src/lib/api.ts`. Render defensively: a payload whose sections carry no `subcards` and no `parent` renders both pages exactly as today.

## Why

A card and an account are not the same thing. Chase issues ONE statement for card 2838 and the cards 3876, 3645 and 0340 that sit under it, so the tab strip showed four peers where the business has one account, an account's spend was never one figure, and the same file name was printed on four tabs. The owner ruled: 2838 is an account with those three as subcards, and no other card has subcards. The backend now sends the tree, sums an account's figures over itself plus its subcards, and names a shared statement once.

## 1. Types (`src/lib/api.ts`)

Add to `CardSection`:

```ts
  subcards?: string[];            // an account: the keys under it, in tab order
  own?: Omit<CardSection, "key" | "label" | "digits" | "subcards" | "own">;
  parent?: string;                // a subcard: its account's key
  statement_on_account?: boolean; // a subcard whose statement is the account's
```

Add `parent?: string` to the card type `GET /api/cards` returns and the Settings editor writes.

Two helpers beside `safeCardSections`:

```ts
export const isAccount = (s: CardSection) =>
  Array.isArray(s.subcards) && s.subcards.length > 0;
export const isSubcard = (s: CardSection) =>
  typeof s.parent === "string" && s.parent !== "";
```

`parent` is a card KEY, never a label. Compare with `===`.

## 2. The tab strip (`src/components/CardTabs.tsx`)

The sections already arrive in tree order: an account, then its subcards, then the next top-level card, No card last. Do not re-sort.

- A subcard's tab button is indented and visually attached to the account above it: add `ml-3` and `text-xs` to its button, and render a `span` `text-muted-foreground` with `└` before the text. Its `title` is `t("cardTabs.under", { account: <the account section's label> })`, looked up by `parent` in the sections array.
- An account's tab keeps its current shape and gains, after the count, a muted `span` `text-xs`: `t("cardTabs.subcards", { n: section.subcards.length })`.
- The count on an account's tab is the section's own `n_charges` / `n_expenses`, which the backend already sums over the group. Do NOT add them up in the client.

Under the tab row, when the selected tab is an ACCOUNT, the line gains one part at the FRONT: `t("cardTabs.group")`, so the reader knows the figures that follow are the group's. Then, at the END, one more part built from `own`: `t("cardTabs.ownLine", { n, amounts })` where `n` is `own.n_charges` and `amounts` is `own.unreconciled_by_ccy` rendered like every other money map (pre-formatted strings, sorted by currency, `${ccy} ${value}`, never parsed). Leave that part out when `own.n_charges` is 0.

When the selected tab is a SUBCARD whose `statement_on_account` is true, replace part 2 of the line (the statement part) with `t("cardTabs.statementOnAccount", { account })`, the account's label from the sections array. A subcard whose `statement_on_account` is false or absent keeps the statement part exactly as it is: its file is named nowhere else.

Everything else about the line is unchanged.

## 3. Settings, Cards

Each card row gains one control under the entity picker: **Account** (`t("cards.parent")`), a select whose options are the blank option `t("cards.parent.none")` plus every OTHER card in the registry that is active and whose own `parent` is empty, by label, value the card key. Writes `parent` into the card entry on save.

Three client-side rules, so the reader is not sent to the server to be refused:

- The card's own row is not an option.
- A card that already has subcards (some other card names it as `parent`) shows the control DISABLED with the hint `t("cards.parent.isAccount")`. An account cannot itself sit under one.
- A card whose `parent` is set shows the hint `t("cards.parent.hasAccount")` under it.

The cards map is a whole-map replace, so the save payload must carry `parent` for every card it sends, exactly as it carries `person` and `default_cost_center`. A build that drops the field erases every stored account on the next save.

The server refuses a tree it cannot stand behind with `card_parent_self`, `card_parent_unknown`, `card_parent_inactive`, `card_parent_cycle` and `card_parent_not_top_level`. Add the five to the `err.*` dictionary used by the error-codes prompt; the English sentence stays the fallback for any code the app does not know.

## 4. Do not change

- Which tab a row belongs to: `rows[].card_section` and `expenses[].card_section` name the card that PAID, never its account. A charge on 3876 stays on 3876's tab.
- Every filter, count and caption already built on the tabs. Selecting an account shows the account card's own rows only, which is what its own tab has always meant; its subcards are one click away, directly beneath it.
- The All tab, `MonthHeader`, `SummaryBar`, every download, every backend call. No new request: the tree rides the GETs the pages already make.
- A month whose registry names no parent: no indent, no subcard row, no group line.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `cardTabs.subcards` | +{n} | +{n} |
| `cardTabs.under` | Under {account} | Dentro de {account} |
| `cardTabs.group` | This account and its cards | Esta conta e seus cartões |
| `cardTabs.ownLine` | on this card alone: {n} charges, {amounts} still open | só neste cartão: {n} lançamentos, {amounts} em aberto |
| `cardTabs.statementOnAccount` | Statement on {account} | Extrato em {account} |
| `cards.parent` | Account | Conta |
| `cards.parent.none` | No account (stands alone) | Sem conta (independente) |
| `cards.parent.isAccount` | Other cards sit under this one, so it cannot sit under another. | Outros cartões estão dentro deste, então ele não pode ficar dentro de outro. |
| `cards.parent.hasAccount` | This card's charges are settled by its account's statement. | Os lançamentos deste cartão são liquidados pelo extrato da conta. |
| `err.card_parent_self` | A card cannot be its own account. | Um cartão não pode ser a própria conta. |
| `err.card_parent_unknown` | No card with that key: define the account card first. | Nenhum cartão com essa chave: defina primeiro o cartão da conta. |
| `err.card_parent_inactive` | That account is deactivated. Reactivate it first. | Essa conta está desativada. Reative-a primeiro. |
| `err.card_parent_cycle` | Those cards point at each other. | Esses cartões apontam um para o outro. |
| `err.card_parent_not_top_level` | That card is already inside another account. An account holds cards; a card inside one holds none. | Esse cartão já está dentro de outra conta. Uma conta contém cartões; um cartão dentro de uma não contém nenhum. |

Add every key to both dictionaries in the same edit. No em-dashes in any UI copy.

## Checking it landed

The live account does not exist until the owner sets it in Settings, so check the editor first and the tabs after. Field names are the decisive signatures; display copy is not, because the build minifies local names away and CSS uppercases some chips.

1. Bundle: `subcards`, `statement_on_account`, `cards.parent` and `err.card_parent_not_top_level` appear in the `/assets/*.js` chunks. Crawl the lazy route chunks through their imports (this build writes dynamic imports with backticks); do not trust a crawler that only follows quoted ones. Controls still present: `card_sections`, `card_section`, `person`.
2. Settings, Cards, cold from the login gate: every one of the nine card rows shows the Account control. On `card-2838` the options list the other eight and not itself. Save nothing yet.
3. Set `3876`, `3645` and `0340` to account `card-2838` and save. The response's `applied` contains `cards`; reload and all three still read `card-2838`. Then try setting `card-2838`'s own account to `3876`: the control is disabled with the "Other cards sit under this one" hint, and if it is sent anyway the screen shows the Portuguese sentence for `card_parent_not_top_level`, not English.
4. August Matching (`/runs/074a7b8905d7`): the strip reads All, then `card-2838` with `+2`, then the indented `3645` and `3876` under it, then `card-1176`, `card-9693`, No card. Live keys as of 2026-09-17; `0340` has nothing in August, so it is not a tab there.
5. Click `card-2838`: the line starts "This account and its cards", reads 111 charges and 9 matched (against 34 and 4 before this change), still open USD 10,862.66, 19 receipts, 5 without a charge, and ends "on this card alone: 34 charges, USD 7,438.36 still open". `August2026.xlsx` is named once.
6. Click `3876`: the statement part reads "Statement on Credit Card - 2838" and the file name is absent. Its charges (37) and its open money (USD 1,031.15) are unchanged from today.
7. `card-1176` and `card-9693` are not indented, carry no `+n`, and read exactly what they read today (1176: 3 charges, still open USD 36.00; 9693: no statement, 2 receipts).
8. PT: the account line starts "Esta conta e seus cartões" and 3876 reads "Extrato em Credit Card - 2838".
9. Nothing was clicked that writes on a month. The Settings save in step 3 is the only write, and it is the owner's own master data.
````

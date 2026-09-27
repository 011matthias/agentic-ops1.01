# Lovable prompt: "Save corrections to memory" lists what changes, in sentences (item 225, note #91)

> **NOT YET APPLIED.** Backend half shipped with item 225 (`lessons[].description`
> in plain sentences, card labels instead of card keys, and the receipts behind
> every merchant-list card change in `lessons[].sources`). No new request: the
> dialog already fetches `GET /api/runs/{id}/memory-plan`.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/MemoryPlan.tsx` (the `MemoryPlanDialog` only), `src/lib/api.ts` (one optional type field if missing) and `src/lib/i18n.tsx`. No new request.

## Why

The owner left a note on April 2026's Expenses page: "make sure the corrections displayed to user when 'Save corrections to memory' button is clicked are tangible, dirk and i had trouble understanding it". Today the dialog on April reads:

| What | About | Value |
|---|---|---|
| Company | erick sports | Brisken Holding, LLC |
| Correction | erick sports · Brisken Holding, LLC · card_key | card-8311 |

"This also updates 16 merchants in the merchant list." and a "Save 2 rules" button.

That is the storage key of each rule, not what the rule does, and the 16 merchant-list changes are a number with nothing behind it. The same reply (`memory-plan`) already carries `lessons[]`: one entry per change the save makes, each with a plain `description` sentence that says what the next receipt gets and which rows it came from. The Publish checklist already shows them. The dialog should show them too, instead of the table.

The button saves exactly the lessons whose `kind` is `"correction"`, `default_keep` is `true` and `owner_gated` is not `true` (the backend applies the same selection), so those are the ones to list as saved.

## 1. `MemoryPlanDialog`: sentences instead of the table

From `plan.data?.lessons` (treat a missing or non-array value as `[]`):

- `saved` = lessons with `kind === "correction"`, `default_keep === true` and `owner_gated !== true`.
- `notSaved` = every other lesson.

Replace the What / About / Value table and the "This also updates {n} merchants" paragraph with:

1. **Section "Your corrections"** (`mplan.sec.rules`), only when non-empty: every `saved` lesson whose `table !== "registry"`, in order. Each is one list item showing `description` as plain text (`text-sm`, normal wrapping, no truncation).
2. **Section "Merchant list"** (`mplan.sec.merchants`), only when non-empty: every `saved` lesson whose `table === "registry"`, in order, same item style. Under the heading, one muted line: `mplan.sec.merchants.sub`, with "merchant list" linking to `/settings?tab=merchants` exactly as the current `mplan.registry.link` does.
3. **Section "Not saved by this button"** (`mplan.sec.notSaved`), only when non-empty: every `notSaved` lesson, same item style but `text-muted-foreground`, and one muted line under the heading: `mplan.sec.notSaved.sub`.

Section headings: `text-xs font-medium uppercase tracking-wider text-muted-foreground`, with the count in parentheses. The three sections sit inside the existing scroll box (`max-h-80 overflow-auto rounded-md border`), padded `p-3`, `space-y-3` between sections, `space-y-1.5` between items.

Nothing to save: when `saved` is empty, show `mplan.nothing` as today (and still show section 3 if `notSaved` is non-empty). The footer keeps its logic, keyed on `saved.length` instead of `writes.length`: Close when there is nothing to save, otherwise Cancel and the save button labelled `t("mplan.save", { n: saved.length })`.

Fallback: when the reply has no `lessons` array at all (an older backend), render today's table from `writes` unchanged.

The "Saved rules live on the Memory page …" line stays as it is.

## 2. `api.ts`

If `MemoryPlan` does not already declare it, add `lessons?: MemoryLesson[]` (the `MemoryLesson` type the Publish checklist uses). No other type change.

## 3. Strings

| Key | EN | PT-BR |
|---|---|---|
| `mplan.save` (change) | Save {n} changes | Salvar {n} alterações |
| `mplan.sec.rules` | Your corrections ({n}) | Suas correções ({n}) |
| `mplan.sec.merchants` | Merchant list ({n}) | Lista de comerciantes ({n}) |
| `mplan.sec.merchants.sub` | What the next receipt from each merchant gets, from this month's receipts. Edit it on the merchant list. | O que o próximo recibo de cada comerciante recebe, a partir dos recibos deste mês. Edite na lista de comerciantes. |
| `mplan.sec.notSaved` | Not saved by this button ({n}) | Não salvo por este botão ({n}) |
| `mplan.sec.notSaved.sub` | Rows that disagree and changes to a decided account are chosen on the Publish checklist. OpenAI, Anthropic and Lovable change only when the owner decides. | Linhas que discordam e mudanças numa conta já decidida são escolhidas na lista de verificação da publicação. OpenAI, Anthropic e Lovable só mudam quando o dono decide. |

For `mplan.sec.merchants.sub`, render "merchant list" / "lista de comerciantes" as the link (split the string the way `mplan.registry.pre/link/post` is split today, or add `.pre` / `.link` / `.post` keys). `mplan.registry.pre`, `mplan.registry.link`, `mplan.registry.post`, `mplan.col.value` are no longer used by the dialog; keep `mplan.col.what` and `mplan.col.who` (the Memory page's saves table uses them). Delete a key only if a project search shows nothing else uses it.

The sentences themselves come from the backend in English, as they already do on the Publish checklist.

## 4. Do not change

- The Publish checklist, the Memory page and its saves table.
- The save itself: the button still calls the same mutation with no body.
- The "Save corrections to memory" button and its tooltip on the Expenses page.

## Checking it landed

Open the dialog on April 2026 Expenses (`/expenses/0603bb0e6f38`) and press Cancel; do not press Save.

1. No What / About / Value table. "Your corrections (2)" lists:
   - "From now on, ERICK SPORTS receipts go to the company Brisken Holding, LLC. From 1 corrected row: ERICK SPORTS 49.98 BRL 2026-04-01."
   - "From now on, ERICK SPORTS receipts in Brisken Holding, LLC are filled in as paid with Credit Card - 8311 (Dirk Neumann - Cloud Services). From 1 corrected row: ERICK SPORTS 49.98 BRL 2026-04-01."
2. "Merchant list (16)" lists 16 sentences starting "Merchant list, …", for example "Merchant list, Americanas: paid with Credit Card Chase Visa - 0340 (Criss Neumann), so its next receipt gets that card. Seen on 1 receipt: americanas sa - 5288 50.45 BRL 2026-04-01." and "Merchant list, MEGA CENTER: paid with Credit Card Chase Visa - 0340 (Criss Neumann) and Credit Card - 2838 (Dirk Neumann - Corp Services), so no card is filled in for it. Seen on 2 receipts: …".
3. No "Not saved by this button" section on April (every lesson there is saved).
4. The text "card-" appears nowhere in the dialog. The button reads "Save 18 changes".
5. PT: headings "Suas correções (2)", "Lista de comerciantes (16)", button "Salvar 18 alterações" (the sentences stay English).
````

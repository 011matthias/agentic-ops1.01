# Lovable prompt: the settings page becomes tabs

> **NOT YET APPLIED.** Paste after the item-91 backend deploy (`applied` /
> `ignored` on `PUT /api/settings`, api-contract "What a settings save
> wrote"). Sections 1 to 3 work without it; section 4's save check reads
> `applied`, so pasting before the deploy would show "nothing was saved" on
> every save.

The app calls the FastAPI backend at `https://api.expenses.brisken.com`.
No editor on this page changes what it sends. What changes is where the
editors live, plus one new control and one new check on the save.

Settings is one long scrolling column today: FX reference rates, Cards,
Cost centers, Expense categories, Merchants, Email intake, Legal entities,
then the Clear memory danger zone. Seven editors deep, so reaching the last
one means scrolling past six, and nothing on the way tells the owner which
one needs attention. Group them into tabs, one tab per setting.

---

## 1. The tabs

Seven, in this order. The first six reuse the i18n keys the page already
carries, so their labels need no new strings and stay translated:

| # | Tab label | i18n key | What moves into it |
|---|---|---|---|
| 1 | Cards | `set.cards.title` | the Cards editor, including the "Seen on your statements, not defined yet" block |
| 2 | Merchants | `set.merchants.title` | the Merchants editor, plus the read-only Expense categories list |
| 3 | Cost centers | `cc.title` | the Cost centers editor |
| 4 | Legal entities | `set.entities.title` | the Legal entities editor |
| 5 | Email intake | `set.intake.title` | the Email intake editor, whole |
| 6 | Currency | `set.fx.title` | the FX reference rates editor |
| 7 | Advanced | `set.tabs.advanced` (new) | the export policy (section 4) and the Clear memory danger zone |

Each editor moves as it is: same fields, same help text, same validation,
same Save button, same request. This is a regrouping, not a rewrite.

Two placements worth stating, because they are the only judgement calls:

- **Expense categories** (`set.categories.*`, read-only, server-managed)
  goes inside the Merchants tab, under the table, as a compact reference
  row of chips. It is the list the merchant category picker offers; it
  belongs where it is used rather than as a tab holding eight words.
- **Clear memory** stays exactly as it is, destructive styling and the type
  CLEAR confirmation included, and lives in Advanced. It is not a settings
  group, so it does not get a tab of its own.

**The page header.** Keep the `set.title` heading. The subtitle is wrong
now: `set.subtitle` describes the export policy ("Applies to runs created
from now on...") and under tabs it would sit above seven unrelated groups.
Give that sentence to the export policy where it belongs (section 4) and
change `set.subtitle` to the new text in section 6.

## 2. How the tabs behave

- **The URL names the tab.** `/settings?tab=cards`, `?tab=merchants`,
  `cost-centers`, `entities`, `intake`, `currency`, `advanced`. Use the
  router's search params, the way other routes here already validate
  search. No parameter means the Cards tab; an unrecognised value falls
  back to Cards silently, never an error screen.
- **Every panel stays mounted.** Switching tabs must not discard an edit in
  progress, so render all seven panels and hide the inactive ones
  (`forceMount` on the tab content) instead of unmounting them. The page
  already renders all seven editors at once today, so nothing gets slower.
- **An editor resets only when its own group changed.** Each editor seeds
  its local state from the settings payload and re-seeds when that value
  changes. After any save the whole payload is re-fetched, so every editor
  currently re-seeds and an unsaved row in another tab is lost. Compare the
  editor's own slice by value (its JSON) rather than by object identity, so
  saving Cards leaves an unsaved merchant row alone.
- **A tab with unsaved edits shows a dot** on its trigger, so the owner can
  see where the unfinished work is from any tab.
- **Counts on the triggers**, muted, beside the label: cards defined,
  merchants, cost centers, entities, intake addresses, FX rates. Advanced
  carries none.
- **Attention markers**, amber, only where the backend actually reports a
  problem. There are exactly two, and they are the reason counts are worth
  showing at all: tabs hide what a scrolling page showed.
  - Cards: `seen_undefined.length` from `GET /api/cards`, the cards your
    statements charge that nobody has defined. Accessible name reuses
    `set.cards.seen.title`.
  - Merchants: `merchants_inert.length` from `GET /api/settings`, the
    merchants whose Zoho account can never fire. Reuses
    `set.merchants.inertHint`.
  Nothing else gets a marker. An empty cost-center list or an unset travel
  address is a normal state, not a warning.
- **Both payloads stay at page level.** `GET /api/settings` and
  `GET /api/cards` are fetched once for the page, as today, not per tab.
  A count on a closed tab cannot render from a payload the tab did not
  fetch yet.
- **Layout.** Widen the container to `max-w-5xl`. Horizontal tab strip that
  scrolls rather than wraps on a narrow window; below `sm`, render the tab
  list as a full-width select instead. Keep the panel content at its
  current width.

## 3. Saving: one tab, one group, and proof it landed

Each tab saves only its own key, which is what the page already does:
`PUT /api/settings` with `{"cards": {...}}` alone, `{"merchants": {...}}`
alone. Never send two groups in one request, and never send the whole
settings object back.

The backend now answers what it wrote:

- `applied`: string[], the keys this request wrote.
- `ignored`: string[], derived keys the request carried (`categories`,
  `entity_options`, `cards_effective`, `merchants_inert`,
  `cost_center_options`). Served by the GET, never stored.

So: **show the success toast only when `applied` contains your tab's key.**
A 200 whose `applied` does not name it wrote nothing; show
`set.save.nothing` instead, as an error. A key the backend does not write is
now a `400 {"error": "unknown settings key(s): cost_centres"}` that writes
nothing at all, the good keys in the same body included; show that error
verbatim, as this page already does for a 400.

**The trap that has bitten this page twice, restated because a layout change
is exactly when it bites again.** Every key REPLACES its whole map. A save
that omits a field erases that field for every row:

- The **intake** editor must keep spreading the loaded `intake` object into
  its save. `domain`, `retention_years`, `sender_daily_cap` and
  `global_daily_cap` are stored but never rendered; drop them from the
  payload and they are gone.
- The **cards** editor must keep sending `entity`, `person`,
  `default_cost_center`, `currency`, `digits`, `aliases`, `zoho_account`
  and `active` on every card, including cards this session did not touch.
- The same holds for `merchants`, `entities` and `cost_centers`: read the
  whole map, change the rows, send the whole map back.

`applied` says the key landed. It does not say the group was complete.

## 4. The Advanced tab: the export policy that has never had a control

`export_approved_only` is a live setting on `GET`/`PUT /api/settings`,
boolean, enforced in the Zoho export, and no screen has ever offered it.
Add a switch:

- Label `set.export.approvedOnly`, help `set.export.help`, scope note
  `set.export.scope` (the sentence taken off the page header).
- Reads `export_approved_only` from `GET /api/settings`; saves
  `{"export_approved_only": true|false}` on its own, like every other group,
  and follows the `applied` check in section 3.
- It is off by default and must stay off unless the owner turns it on.

Above it, keep the Clear memory block unchanged.

## 5. Out of scope

- No new endpoints and no new API fields beyond `applied` / `ignored`.
- Do not merge two settings into one tab to make the strip fit, and do not
  add a tab for anything not in the table in section 1.
- Do not touch what any editor sends, validates or displays. If an editor
  looks wrong to you, leave it wrong; it ships separately.
- No new colours, no card redesign, no icon set on the triggers.

## 6. New strings (EN, PT-BR)

| Key | EN | PT |
|---|---|---|
| `set.tabs.advanced` | Advanced | Avançado |
| `set.subtitle` (replaces the current text) | What the tool reads before it reconciles a month: your cards, merchants, cost centers, legal entities, mail intake and rates. | O que a ferramenta lê antes de conciliar um mês: seus cartões, fornecedores, centros de custo, entidades legais, recebimento por e-mail e taxas. |
| `set.tabs.unsaved` | Unsaved changes | Alterações não salvas |
| `set.save.nothing` | Nothing was saved. Try again, and tell Matthias if it repeats. | Nada foi salvo. Tente de novo e avise o Matthias se repetir. |
| `set.export.title` | Export policy | Política de exportação |
| `set.export.approvedOnly` | Send only confirmed rows to Zoho | Enviar ao Zoho somente linhas confirmadas |
| `set.export.help` | With this on, the Zoho journal carries only the matches a reviewer confirmed. An auto-match nobody has looked at stays out of the export and keeps showing in the month report and the reconciled CSV. | Com isso ligado, o lançamento do Zoho leva apenas as correspondências confirmadas por um revisor. Uma correspondência automática que ninguém revisou fica fora da exportação e continua aparecendo no relatório do mês e no CSV conciliado. |
| `set.export.scope` | Applies to months created from now on. A month already created keeps the policy it was created under. | Vale para os meses criados de agora em diante. Um mês já criado mantém a política com que foi criado. |

Existing keys move with their editors and keep their text, `set.subtitle`
excepted.

## 7. Checking it landed

Drive it, do not read it:

1. Open `/settings`. Seven tabs, Cards first, its panel showing.
2. `/settings?tab=intake` opens Email intake directly.
   `/settings?tab=nonsense` opens Cards, no error.
3. Type a merchant row, switch to Cards, switch back: the row is still
   there, and the Merchants trigger showed the unsaved dot while you were
   away.
4. Save one tab. The toast fires, and the other tabs keep their unsaved
   edits.
5. Cards: change one card's label, save, reload the page. The card's
   person, default cost center, entity and digits are all still set.
6. Advanced: the export switch reads off, the Clear memory block is
   unchanged, and the scope sentence is under the switch rather than under
   the page title.
7. Both languages: switch to PT and walk the seven triggers. No key
   renders as its own name.

# Lovable prompt - the Expenses view's boxes open their rows (item 84)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

On a month's Expenses view the overview boxes (CATEGORIZED, NEEDS CATEGORY,
READY, MISSING ENTITY, NEEDS PERSON, MISSING RECEIPT IMAGE) show a number and
do nothing when clicked; NEEDS PERSON even links to Settings instead of the
expenses it counts. The owner wants each box to open the expenses it counts,
the way the Matching view's cards already do. The backend now tells every
expense which boxes it belongs to, and every box count equals the rows that
carry it. MISSING ENTITY and NEEDS PERSON become one box.

## 1. The new fields (`GET /api/expense-batches/{id}`)

- `expenses[].boxes` (array of strings, always present on a current payload):
  the boxes this row belongs to, from `categorized`, `uncategorized`, `ready`,
  `needs_entity`, `needs_person`, `needs_company_or_person`,
  `needs_cost_center`, `suggested_private`, `private`,
  `missing_receipt_image`, `receipts_unrenderable`.
- `summary.n_needs_company_or_person` (integer): rows missing their company or
  their person. For every box, `summary["n_" + box]` equals the number of rows
  whose `boxes` include it.
- `summary.n_missing_receipt_image` now counts only rows whose receipt the app
  cannot show (0 on July and August).

## 2. A box filter (`ExpensesReviewGrid.tsx`)

- Add `const [boxFilter, setBoxFilter] = useState<string | null>(null);` beside
  `dupFilter`, and in the `grouped` memo add
  `.filter((r) => !boxFilter || (Array.isArray(r.boxes) && r.boxes.includes(boxFilter)))`
  after the existing filters (add `boxFilter` to its dependencies). Add
  `boxes?: string[]` to `ExpenseRow` and `n_needs_company_or_person?: number`
  to the batch summary type in `src/lib/api.ts`.
- `Tile` takes two optional props, `onClick?: () => void` and
  `active?: boolean`. With `onClick`, render the tile as a `<button
  type="button">` with the same classes plus `text-left w-full
  hover:border-primary/60 transition-colors`, and `border-primary
  ring-1 ring-primary` when `active`. Without `onClick`, render exactly as
  today.
- A tile is clickable only when its count is above 0 AND
  `data.expenses.some((e) => Array.isArray(e.boxes))`. Clicking an inactive
  tile sets `boxFilter` to its box; clicking the active tile clears it.
- The EXPENSES tile clears `boxFilter` when clicked. TOTALS is never a button.
- When `boxFilter` is set, render a banner in the same place and style as the
  `notInReportFilter` banner:
  `t("expx.box.active", { n: <rows shown>, box: t("expx.box.label." + boxFilter) })`
  with the existing clear button (`expx.review.vendorFilter.clear`), which sets
  `boxFilter` to null. When `boxFilter` is `needs_company_or_person`, add one
  muted line under that banner: `t("expx.box.fixCard")` followed by a
  `<Link to="/settings">` reading `t("expx.box.fixCard.link")`.

| Tile | Box |
|---|---|
| CATEGORIZED | `categorized` |
| NEEDS CATEGORY | `uncategorized` |
| READY | `ready` |
| the merged tile (section 3) | `needs_company_or_person` |
| its "N suggested private" caption | `suggested_private` |
| cost center (`cc.tile.needsCostCenter`) | `needs_cost_center` |
| PRIVATE | `private` |
| MISSING RECEIPT IMAGE | `missing_receipt_image` |
| NOT IN REPORT (`expense.tile.notInReport`) | `receipts_unrenderable` |

## 3. MISSING ENTITY and NEEDS PERSON become one box

When `typeof data.summary.n_needs_company_or_person === "number"`:

- Do not render the MISSING ENTITY tile or the NEEDS PERSON tile (with its
  Settings link). Render ONE tile in their place, when the count is above 0:
  label `t("expx.box.tile.companyOrPerson")`, value
  `n_needs_company_or_person`, `tone="warning"`, help
  `t("expx.box.tile.companyOrPersonHelp")`.
- Move the "N suggested private" caption (`expx.private.subCount`) from the
  NEEDS CATEGORY tile to this tile, as a small button inside it that sets
  `boxFilter` to `suggested_private` (stop the click from also toggling the
  tile's own filter).

When the field is absent (an older payload), render both old tiles and the
caption exactly as today.

## 4. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `expx.box.active` | Showing {n}: {box} | Mostrando {n}: {box} |
| `expx.box.label.categorized` | categorized | categorizadas |
| `expx.box.label.uncategorized` | need a category | precisam de categoria |
| `expx.box.label.ready` | ready | prontas |
| `expx.box.label.needs_company_or_person` | no company or person yet | sem empresa ou pessoa |
| `expx.box.label.suggested_private` | suggested private | sugeridas como particulares |
| `expx.box.label.needs_cost_center` | need a cost center | precisam de centro de custo |
| `expx.box.label.private` | private | particulares |
| `expx.box.label.missing_receipt_image` | missing receipt image | sem imagem do recibo |
| `expx.box.label.receipts_unrenderable` | not in the report | fora do relatório |
| `expx.box.tile.companyOrPerson` | No company or person | Sem empresa ou pessoa |
| `expx.box.tile.companyOrPersonHelp` | The card that paid is not known yet. Pick the card, or mark the receipt private. | O cartão que pagou ainda não é conhecido. Escolha o cartão ou marque o recibo como particular. |
| `expx.box.fixCard` | Add a card and its person once, and every receipt paid with it is fixed: | Cadastre o cartão e a pessoa uma vez, e todos os recibos pagos com ele ficam resolvidos: |
| `expx.box.fixCard.link` | Settings, Cards | Configurações, Cartões |

## 5. Do not change

- The grouped tables (Needs a look / Assign a category / Ready), every cell,
  dialog and inline action.
- The duplicate, not-in-report and vendor filters; they combine with the box
  filter (a row must pass all of them).
- TOTALS, the card-review strip, set aside, parser notes, the month-move
  banner.
- No new API calls; the filter is client-side over `data.expenses`.

## 6. Render defensively

Rows without `boxes`: no tile is clickable. The banner prints a box label only
from the keys above; never a raw key, never `undefined`.

## 7. After publishing, check

Re-read `GET /api/expense-batches/{id}` for July `50622baec444` and August
`074a7b8905d7` first.

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit):
   `n_needs_company_or_person`, `expx.box.active`,
   `expx.box.tile.companyOrPerson`, `expx.box.fixCard.link`.
2. July, Expenses: click each tile with a count; the rows listed across the
   three groups equal the tile's number (CATEGORIZED 49, NEEDS CATEGORY 3,
   READY 14, No company or person 33, its suggested-private caption 24).
   Click the active tile again: all 52 rows return.
3. The merged tile replaces MISSING ENTITY and NEEDS PERSON; its filtered view
   shows the Settings, Cards link.
4. MISSING RECEIPT IMAGE reads 0 and is not clickable.
5. PT: "Sem empresa ou pessoa", "Mostrando".
6. Network: no POST other than `/api/login` during the drive.

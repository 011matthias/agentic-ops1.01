# Lovable prompt - the READY tile (optional polish)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

**This one is optional.** The count defect it comes from is already fixed in
the backend and needs no SPA change: `summary.n_categorized` and
`summary.n_uncategorized` now answer "how many still need a category" on BOTH
screens, so the CATEGORIZED / NEEDS CATEGORY tiles and the landing badges show
the same numbers for the same batch without touching this project. Apply the
tile below when you want the signal the old count was accidentally showing.

## Background

Until 2026-08-22 the batch page's CATEGORIZED tile was fed a number that
counted rows with review state `ready` — a row that had a category but no
legal entity yet was reported as uncategorized. April 2026 read "35
categorized" on the landing screen and "5" on the batch page, and NEEDS
CATEGORY claimed 31 rows when exactly 1 needed a category.

## 1. New tile: READY

`GET /api/expense-batches/{id}` -> `summary.n_ready` (integer, always
present). It counts rows the reviewer can leave alone entirely: category
resolved AND legal entity resolved AND date/amount/currency present. It is
the number the CATEGORIZED tile used to show.

Add it to the stat row on the batch page beside CATEGORIZED / NEEDS CATEGORY,
in a neutral tone (it is not a warning; a low READY on a fresh month is
normal). Suggested order:

`EXPENSES · CATEGORIZED · NEEDS CATEGORY · READY · TOTALS`

## 2. i18n keys

| Key | EN | PT |
|---|---|---|
| `expx.review.tile.ready` | Ready | Prontas |

Tooltip / help text, if the tile carries one:

- EN: "Nothing left to do on these: category, company, and the amounts are all
  settled."
- PT: "Nada a fazer nestas: categoria, empresa e valores ja resolvidos."

## 3. Do not change

The CATEGORIZED and NEEDS CATEGORY tiles keep reading `n_categorized` /
`n_uncategorized`. MISSING ENTITY keeps reading `n_needs_entity`. No other
field changed shape or type in this round.

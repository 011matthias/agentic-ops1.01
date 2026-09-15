# Lovable prompt - workbench filter/sort: fix the amount sort, add card + entity + candidates, persist in the URL (item 17)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

The workbench control bar already ships: a vendor search box, the BUCKET
toggles (Needs review / Unmatched / Reconciled / Refund / Posted), a STATUS
select, a SORT select (Default / Vendor A-Z / Date, newest first / Date,
oldest first / Amount, high to low / Amount, low to high), six FILTERS toggles
and "Clear filters". Vendor A-Z is correct as it stands. **This prompt is a
delta; it does not rebuild the bar.**

No backend field changes in this round. Every field below already ships on
`GET /api/runs/{id}`.

## 1. The amount sort is wrong on any charge over 999 (fix first)

`rows[].amount` is a DISPLAY string built server-side as `f"{v:,.2f}"`, so it
carries group separators: `1,574.24`, `2,484.00`, `-7,823.16`. `Number()`
returns `NaN` on those and `parseFloat` returns `1`, `2` and `-7`.

Driven on the live August month, 2026-09-15, "Amount, high to low" on the
93-row UNMATCHED group:

- head: `LinkedIn 575.61`, `SP MOERGO 441.29`, `SAP SE 211.40`
- tail: `ZOHO* ZOHO-ONE 2,484.00`, `WILLAMS 1.55`, `CANTINHO 1.54`,
  `COMERCIO ACAI 1.17`, `MarceloEzequiel 1.16`, **`SAP SE 1,574.24` last**

The two biggest unreviewed charges of the month sit at the bottom of "highest
first". A reviewer working top-down on the largest exposures never reaches
them.

Parse the amount once, in one helper, and sort on the number:

```ts
const amountValue = (s: string): number => {
  const n = Number(String(s ?? "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
};
```

Strip the separators, keep the sign and the decimal point. Use it for both
amount sorts, and anywhere else the page compares an amount as a number.
Every amount string on both payloads (`rows[].amount`,
`candidates[].receipt.total`, `unmatched_receipts[].total`, the coverage
totals) comes from the same formatter, so the same helper covers them.

## 2. Three filters to add, beside the existing FILTERS toggles

**Card.** Options come from `coverage[]` on the same payload, one per entry:
value `coverage[].key`, label `coverage[].label` ("Credit Card Chase Visa -
3645"). A row belongs to an option when `rows[].coverage_key === key`. Do not
parse the key and do not derive a card from `account_id`: the key is either
the registry's card key (`card-2838`) or the charge's own digit token
(`3645`), and `coverage[]` is the only thing that maps either to a name. Six
of August's nine cards carry zero charges, so options with a zero count are
disabled, not hidden (see §4).

**Company.** Options are the distinct non-empty `rows[].legal_entity_id`
values in the payload. Both live months are single-entity (`Corporate
Services`, 223 of 223 rows), so hide the control entirely when the month has
fewer than two distinct values rather than showing a select with one option.

**Has a suggested receipt.** A three-state toggle on `rows[].candidates`:
any / with candidates (`candidates.length > 0`) / without. August is 17 of
111, July 38 of 112. This is not the existing "No receipt" toggle, which is
about the matched receipt; a charge can have candidates and still be
unmatched.

## 3. "Unmatched" means `effective_bucket`, not `section`

Whatever the new controls filter, the unmatched question stays on
`rows[].effective_bucket` (`unmatched` / `reconciled` / `review` / `refund`).
Do not switch any of it to `rows[].section`: `section` is a display lane and
`is_posted` overrides it, so on July `section: "posted"` holds 85 rows that
are really 49 unmatched, 24 reconciled, 11 review and 1 refund. A filter
reading "unmatched" off `section` reports 24 of July's 73 unmatched charges.
The BUCKET toggles are already correct; this is a note for the new code.

## 4. A count on every filter option

Each option shows how many rows it would leave, computed against the OTHER
active filters (so the numbers tell the reviewer what the next click does):
`Unmatched 93`, `Credit Card Chase Visa - 3645 40`, `Apple Credit Card -
0113 0`. A zero-count option renders disabled and muted. The existing
"111 of 111 charges" line stays as it is.

## 5. Filter and sort state lives in the URL

Today `/runs/074a7b8905d7` carries no state: choosing "Amount, high to low"
leaves the URL untouched, so a refresh or a shared link loses the view. Put
every control in the query string, read it on mount, replace (not push) on
change so the back button still leaves the page:

`?q=&bucket=unmatched&status=all&sort=amount_desc&card=3645&entity=&cands=any&f=noreceipt,uncategorized`

Names: `q` (search), `bucket`, `status`, `sort`, `card`, `entity`, `cands`,
`f` (comma-joined FILTERS toggles). Omit a key at its default. An unknown
value falls back to the default instead of rendering an empty queue, and
"Clear filters" clears the query string too.

## 6. i18n keys (EN + PT)

| Key | EN | PT |
|---|---|---|
| `wb.filter.card` | Card | Cartao |
| `wb.filter.card.all` | All cards | Todos os cartoes |
| `wb.filter.entity` | Company | Empresa |
| `wb.filter.entity.all` | All companies | Todas as empresas |
| `wb.filter.cands` | Suggested receipt | Recibo sugerido |
| `wb.filter.cands.any` | Any | Qualquer |
| `wb.filter.cands.with` | Has a suggestion | Com sugestao |
| `wb.filter.cands.without` | No suggestion | Sem sugestao |
| `wb.filter.empty` | No charges match these filters | Nenhum lancamento corresponde a estes filtros |
| `wb.filter.emptyClear` | Clear filters | Limpar filtros |

The existing BUCKET / STATUS / SORT / FILTERS labels keep their current keys
and copy.

## 7. Do not change

The row tables, the group headings and their counts, "Confirm N shown" /
"Reject N shown" (they keep acting on the filtered set, which is why the
counts in §4 matter), the Coverage and Statements panels, the stat row, the
Vendor A-Z comparison, and every backend call. Nothing on this page changes
shape: `GET /api/runs/{id}` returns exactly what it returns today.

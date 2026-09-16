# Lovable prompt - a one-day gap is not a date mismatch (item 80, note #44)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend at
`brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

On the reconciliation workbench (`/runs/{id}`), `getRowWarnings` in
`src/components/RunWorkbench.tsx` pushes "date mismatch" whenever the chosen
candidate's `date_pct` is below 99, which is any gap of one day or more. That
chip also makes the row count under the "Warnings only" filter. In July 2026
it sits on six reconciled rows (AMAZON 315.56, MP *24HBEBIDAS 24.88, GOOGLE
Workspace 71.64, three ANTHROPIC top-ups) that are all correct: each receipt
is dated one day before its charge, the ordinary midnight, time-zone and
charged-at-shipment case. The backend now says how far apart the two dates
are and which zone that falls in, so the page can stop calling a normal lag
a mismatch.

## 1. The new fields

`GET /api/runs/{id}` -> every `rows[].candidates[]` entry carries two
parallel fields:

```json
"date_gap_days": 3,
"date_gap_zone": "lag"
```

- `date_gap_days`: integer, signed. The charge's date minus the receipt's
  date in calendar days. Positive means the receipt is dated BEFORE the
  charge; negative means the receipt is dated AFTER it.
- `date_gap_zone`: one of `"none"` (-1 to +1 days), `"lag"` (+2 to +7, or
  -3 to -2), `"mismatch"` (anything further).
- Both are **absent** (never null) when either date is missing. Always read
  them together.

Add to the `Candidate` interface in `src/lib/api.ts`:

```ts
/** Charge date minus receipt date, calendar days. Absent when either is missing. */
date_gap_days?: number;
/** Absent when either date is missing. */
date_gap_zone?: "none" | "lag" | "mismatch";
```

## 2. The row chips

In `getRowWarnings`, keep reading the same candidate it reads today
(`row.candidates.find((c) => c.is_chosen)`). Replace ONLY the line that pushes
"date mismatch" with this rule:

- `date_gap_zone === "mismatch"`: push `"date mismatch"`, exactly as today.
  It stays a warning and still counts under "Warnings only".
- `date_gap_zone === "lag"`: push nothing into the warnings.
- `date_gap_zone === "none"`: push nothing.
- `date_gap_zone` absent, or any value other than the three above: keep
  today's rule unchanged (`date_pct` below 99 pushes `"date mismatch"`).

Then render the lag as its own neutral chip, NOT through `getRowWarnings` (so
`isWarning` and the "Warnings only" filter never see it). On the charge row,
right after `<WarningChip warnings={getRowWarnings(row)} />`, add
`<DateGapChip row={row} />`:

- Take the chosen candidate the same way. Render nothing unless
  `date_gap_zone === "lag"` and `date_gap_days` is a number.
- `date_gap_days > 0`: text `t("wb.dateGap.chargedAfter", { n: date_gap_days })`.
- `date_gap_days < 0`: text `t("wb.dateGap.receiptAfter", { n: Math.abs(date_gap_days) })`.
- Style it like `WarningChip`'s size and shape (same `text-[10px]` pill) but
  neutral: `border bg-muted/40 text-muted-foreground`, no amber, and no
  `AlertTriangle` icon.

That cell is the vendor cell of the charge row in `RowView` (the one holding
the vendor name, `DupBadge`, `WarningChip` and `EntityChip`). Touch nothing
else in `RowView`: the Status cell and `RowStatusBadge` belong to another
change. If the month-views change has moved the charge row, put the chip
wherever `WarningChip` now renders on a charge row.

A hand-matched candidate (`match_type: "manual"`) has `date_pct: null`, so it
never showed "date mismatch" before. It now carries the zone like any other
candidate, so a hand match 8 or more days from its receipt shows
"date mismatch" and one 2 to 7 days out shows the neutral chip. That is
intended.

## 3. i18n keys

| Key | EN | PT |
|---|---|---|
| `wb.dateGap.chargedAfter` | charged {n} days after the receipt | cobrado {n} dias depois do recibo |
| `wb.dateGap.receiptAfter` | receipt dated {n} days after the charge | recibo datado {n} dias depois da cobrança |

`{n}` is always 2 or more when the chip renders, so the plural is always
right.

## 4. Do not change

- The "amount mismatch" chip and its `amount_pct` rule.
- The date `ScoreBar` (`wb.score.date`) in the candidate breakdown; it keeps
  showing `date_pct`.
- `WarningChip` itself, the "Warnings only" filter code (`isWarning`), and
  the other warnings (`near miss`, `currency unknown`).
- The literal `"date mismatch"` string.

## 5. What to expect after publishing

- July 2026 (`/runs/50622baec444`): no row says "date mismatch" any more
  and no neutral chip appears (all six are one day apart, zone `none`).
  GOOGLE Workspace 71.64 and the three ANTHROPIC rows lose their warning
  chip entirely; AMAZON 315.56 and MP *24HBEBIDAS 24.88 keep
  "AMOUNT MISMATCH" and lose the "+1". Counted across all of July's charge
  rows with no other filter, "Warnings only" matches 23 rows instead of 27
  (2026-09-16 payload; a re-match can move it, and with the month split into
  views each view shows its own share).
- August 2026 (`/runs/074a7b8905d7`): no visible change. Its one `lag`
  candidate (ANTHROPIC 50.52 on 08-03 against a receipt dated 08-05) belongs
  to a charge that is still awaiting a decision and has no chosen receipt,
  and the chips only read the chosen one.

# Lovable prompt - the FX block shows the conversion at our rate (item 81)

Backlog item 81, note #43 (Matthias, July, on AMAZON 315.56 USD against the
Amazon.de receipt 276.08 EUR): "maybe in cross currency cases show the
calculation of what the receipt's amount is in $ using our FX rate."

SPA only; the backend fields ship first (every field below is on the live
payload once the item 81 backend is deployed). Written against SPA main
`c9f30bf` (2026-09-16). Item 79 (month views) may be restructuring the
workbench at the same time and leaves `CandidateRow` alone, so anchor on the
component names `FxSummary` / `FxPanel` and the `wb.fx.*` keys, not on line
numbers.

Paste everything between the two rules into the `brisken-expense-review`
Lovable project.

---

Paste into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend as a JSON API
at `api.expenses.brisken.com`. **Do NOT add Supabase or any database.** Auth
stays the existing `Authorization: Bearer <token>`. No new backend call and no
new query: the fields below arrive on the `GET /api/runs/{id}` payload the
workbench already loads.

## Why

On a cross-currency pair the FX block shows only the rate the pairing NEEDS
("This match needs 1.143002 USD per EUR"). The rate the tool actually matched
with (1.162275, from Settings) is buried in the reason sentence, and "Receipt
is worth" never renders because it only reads `zoho_converted`, which no
receipt on July or August carries. The reviewer cannot see the one calculation
that answers "is this the same purchase": the receipt converted at our rate,
next to the charge.

## 1. The new fields

`rows[].candidates[].fx` gains six keys. They arrive **all together or not at
all**: when the tool has no rate for the currency pair, none of the six keys
exists (absent, never null, never an empty string).

```json
"fx": {
  "charge_amount": "315.56", "charge_currency": "USD",
  "receipt_amount": "276.08", "receipt_currency": "EUR",
  "rate_label": "USD per EUR", "implied_rate": "1.143002",
  "zoho_rate": "", "zoho_converted": "", "converted_gap": "",
  "converted_gap_pct": null,
  "reference_rate": "1.162275",
  "reference_rate_source": "settings",
  "reference_converted": "320.88",
  "reference_gap": "-5.32",
  "reference_gap_pct": -1.66,
  "reference_gap_band": "match"
}
```

- `reference_rate` (string): charge currency per one receipt-currency unit,
  the same direction as `implied_rate`, so `rate_label` labels both.
- `reference_rate_source` (string): `"settings"`, `"statement"` or
  `"receipts"` today. More values are coming (`"ecb_month"` next), so treat it
  as open: an unknown value is shown as the raw string.
- `reference_converted` (string, 2 dp): the receipt total at that rate.
- `reference_gap` (string, signed: `"-5.32"`, `"+0.24"`, `"0.00"`): charge
  minus `reference_converted`. Print it as sent; it already carries its sign.
- `reference_gap_pct` (number, signed, 2 dp): the difference as a percentage
  of the converted amount.
- `reference_gap_band` (string): `"match"`, `"review"` or `"outside"`.

Extend the `CandidateFx` type in `src/lib/api.ts` with all six as OPTIONAL
properties (`reference_rate?: string`, ..., `reference_gap_pct?: number`,
`reference_gap_band?: string`). Leave the ten existing properties exactly as
they are.

Formatting helpers, used in both places below:

- percentage: `(p > 0 ? "+" : "") + p.toFixed(2) + "%"`, so `-1.66%`,
  `+2.93%`, `0.00%`.
- source label: `settings` -> `wb.fx.source.settings`, `statement` ->
  `wb.fx.source.statement`, `receipts` -> `wb.fx.source.receipts`, anything
  else -> the raw `reference_rate_source` string.
- attention: `reference_gap_band !== "match"` renders amber with the classes
  the block already uses for a large gap (`text-amber-700
  dark:text-amber-400 font-medium`).

## 2. `FxSummary` (the one-line summary under the suggested receipt)

Keep the `hasConverted` branch (`zoho_converted` present) and the
`converted_gap` span exactly as they are.

In the OTHER branch, the one that today prints only
`{receipt_amount} {receipt_currency}`: when `fx.reference_converted` is
present, print instead

```
276.08 EUR x 1.162275 = 320.88 USD · difference -5.32 USD (-1.66%)
```

built as `{receipt_amount} {receipt_currency} x {reference_rate} =
{reference_converted} {charge_currency}` followed by `· {wb.fx.summaryDifference}
{reference_gap} {charge_currency} ({percentage})`. The whole line is amber when
the band is not `"match"`, muted otherwise. When `reference_converted` is
absent, the branch prints `{receipt_amount} {receipt_currency}` exactly as
today. The Details / Hide toggle is unchanged.

## 3. `FxPanel` (the details table)

The rows become, in this order:

1. Bank statement (`wb.fx.bank`), unchanged
2. Receipt (`wb.fx.receipt`), unchanged
3. Zoho's rate (`wb.fx.zohoRate`), unchanged, still only when `zoho_rate`
4. Receipt is worth (`wb.fx.receiptWorth`), unchanged, still only when
   `zoho_converted`
5. **Reference rate** (`wb.fx.referenceRate`), only when `reference_rate`:
   value `{reference_rate}` then muted `({rate_label})` then muted
   `· {source label}`
6. **Receipt in {currency}** (`wb.fx.receiptIn`, `{currency}` =
   `charge_currency`), only when `reference_converted`: value
   `{reference_converted}` with the muted currency, like row 1
7. **Difference** (`wb.fx.difference`), only when `reference_gap`: value
   `{reference_gap}` with the muted currency and the percentage; label and
   value amber when the band is not `"match"`
8. This match needs (`wb.fx.needs`), unchanged, still only when
   `implied_rate`, and still LAST

The footer below the rows (the `converted_gap` "Gap" block with its top
border) stays as it is, where it is. `FxPanel` renders in two places (under
the suggested receipt, and inside each candidate's expanded card); both get the
new rows because both use the same component.

## 4. i18n keys

| Key | EN | PT |
|---|---|---|
| `wb.fx.referenceRate` | Reference rate | Taxa de referência |
| `wb.fx.receiptIn` | Receipt in {currency} | Recibo em {currency} |
| `wb.fx.difference` | Difference | Diferença |
| `wb.fx.summaryDifference` | difference | diferença |
| `wb.fx.source.settings` | Settings | Configurações |
| `wb.fx.source.statement` | bank statement | extrato bancário |
| `wb.fx.source.receipts` | receipts | recibos |

Add them to both dictionaries beside the existing `wb.fx.*` keys. No
em-dashes in any UI copy. "Zoho" appears in no new string.

## 5. Do not change

`zoho_rate`, `zoho_converted`, `converted_gap`, `converted_gap_pct` and every
conditional that reads them (a receipt from an expense-report PDF still fills
them); the existing `wb.fx.*` keys and their text; `rate_label`; the "This
match needs" row and its position; the reason sentence; `ScoreBar`s; the band
chip; the cross-currency badge; `CandidateRow`, `RowView` and the Status cell
(item 76 owns it); the month views item 79 is building; every mutation, query
key and backend call; Settings; auth; the API base URL.

## 6. Render defensively

Read each new key with a type check (`typeof fx.reference_rate === "string"`,
`typeof fx.reference_gap_pct === "number"`). A payload from before the deploy
carries none of them and must render exactly as today, with no "undefined",
"NaN" or empty "x =" fragment anywhere.

## 7. After publishing, check

1. July 2026 (`/runs/50622baec444`), row `AMAZON* Z11US7DF5`: the summary reads
   `276.08 EUR x 1.162275 = 320.88 USD · difference -5.32 USD (-1.66%)`, not
   amber. Details shows Reference rate `1.162275 (USD per EUR) · Settings`,
   Receipt in USD `320.88 USD`, Difference `-5.32 USD (-1.66%)`, then This
   match needs `1.143002 (USD per EUR)` last.
2. July, row `SUPERMEC SAO JOSE`: `41.85 BRL x 0.192448 = 8.05 USD · difference
   +0.24 USD (+2.93%)`, not amber.
3. July, row `NOBRE ATACAREJO SAO JOS`: expand its candidate; Difference reads
   `+4.01%` and is amber.
4. August 2026 (`/runs/074a7b8905d7`): `ANTHROPIC* CLAUDE SUB` 247.32 reads
   `214.20 EUR x 1.162275 = 248.96 USD · difference -1.64 USD (-0.66%)`;
   `PETIT TRAIN TOUR` reads `32.00 EUR x 1.162275 = 37.19 USD · difference
   +0.29 USD (+0.77%)`.
5. Switch the language to PT: "diferença", "Taxa de referência",
   "Configurações", "Recibo em USD".

---

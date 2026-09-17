# Lovable prompt - FX rates come from the ECB each month (item 82)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

Receipts in another currency are compared with the card charge through a
reference rate. Until now that rate was one number per currency pair typed in
Settings, and the Settings page told the operator to update it every month.
The backend now fetches the European Central Bank's monthly average rates when
a month is created and when its statement is added, and reads the rate for the
month each purchase was made in. A rate typed in Settings still overrides the
ECB, for every month. Nothing about saving rates changes; only the copy and
one label.

## 1. The API

`rows[].candidates[].fx` gains one optional key beside the existing
`reference_*` keys:

```json
"fx": {
  "reference_rate": "1.141748",
  "reference_rate_source": "ecb_month",
  "reference_rate_period": "2026-07",
  "reference_converted": "315.21",
  "reference_gap": "+0.35",
  "reference_gap_pct": 0.11,
  "reference_gap_band": "match"
}
```

- `reference_rate_source` gains the value `ecb_month`.
- `reference_rate_period` (string, `YYYY-MM`) is present ONLY when the source
  is `ecb_month`: the month whose ECB average the rate is. It is absent, never
  null, for every other source.

In `src/lib/api.ts`, add `reference_rate_period?: string;` to `CandidateFx`
next to `reference_rate_source`.

## 2. The FX panel (`RunWorkbench.tsx`, `FxPanel`)

In `FxPanel`, add `const locale = useLocale();` beside `const t = useT();`
(import `useLocale` from `@/lib/i18n` next to `useT`). In the `srcLabel`
chain, before the raw-string fallback, add:

```tsx
: src === "ecb_month"
  ? t("wb.fx.source.ecbMonth", { month: fxPeriodLabel(fx.reference_rate_period, locale) })
```

with a small helper in the same file:

```tsx
function fxPeriodLabel(period: string | undefined, locale: string): string {
  if (!period || !/^\d{4}-\d{2}$/.test(period)) return period ?? "";
  const [y, m] = period.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString(locale, {
    month: "long", year: "numeric", timeZone: "UTC",
  });
}
```

The row then reads `Reference rate 1.141748 (USD per EUR) · ECB average, July
2026`. `FxSummary` needs no change.

## 3. Settings copy (`SettingsScreen.tsx` uses the keys; change only the text)

Replace the text of `set.fx.desc`, and of `months.attach.currencyHelp`, in
both languages (table below). The FX rates editor itself stays exactly as it
is: same pair/rate rows, same save call.

## 4. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `wb.fx.source.ecbMonth` (new) | ECB average, {month} | média do BCE, {month} |
| `set.fx.desc` (replace) | Rates come from the European Central Bank's monthly average for the month of each purchase, fetched when a month is created and when its statement is added. Add a rate here only to override the ECB: a rate set here is used for every month. | As taxas vêm da média mensal do Banco Central Europeu para o mês de cada compra, obtidas quando um mês é criado e quando o extrato é adicionado. Adicione uma taxa aqui só para substituir a do BCE: a taxa definida aqui vale para todos os meses. |
| `months.attach.currencyHelp` (replace) | The currency the card settles in. This is not the receipts' currency: receipts in other currencies are converted at the ECB's monthly average for the purchase month, or at a rate set in Settings. | A moeda em que o cartão é cobrado. Não é a moeda dos recibos: recibos em outras moedas são convertidos pela média mensal do BCE do mês da compra, ou por uma taxa definida em Configurações. |

## 5. Do not change

- The FX rates editor's behaviour, validation or save payload
  (`fx_reference_rates`).
- `FxSummary`, the band colours, the `reference_gap*` rendering, or any
  `zoho_*` conditional.
- The existing `wb.fx.source.settings` / `statement` / `receipts` labels, and
  the raw-string fallback for a source the panel does not know.
- Any route, query key or other page.

## 6. How to check after publishing

1. Settings: the FX reference rates card shows the new description, EN and PT.
2. A month whose FX candidate reads `reference_rate_source: "ecb_month"` shows
   `· ECB average, <Month YYYY>` after the rate in the FX panel (PT:
   `· média do BCE, <mês de AAAA>`). On 2026-09-17 no live month does yet:
   July and August were matched on the rates typed in Settings, which still
   win, so their panels keep reading `· Settings`.
3. Nothing else on the workbench moved.

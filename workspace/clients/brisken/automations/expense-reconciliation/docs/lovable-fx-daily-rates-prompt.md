# Lovable prompt - FX rates are polled daily from OpenTickers (note #79)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

Receipts in another currency are compared with the card charge through a
reference rate. The backend now polls the daily central-bank reference rates
(European Central Bank when it publishes the pair) from OpenTickers every 24
hours, keeps every day, and reads the rate for the DAY each purchase was made.
It sits above the ECB monthly average (item 82) and below a rate typed in
Settings, which still overrides everything for every month. The FX tab in
Settings shows the polled rates beside the typed ones and can trigger a poll;
the FX panel on a match names the day the rate is for.

## 1. The API

### `GET /api/settings` gains one derived, read-only key

```json
"fx_daily_rates": {
  "provider": "opentickers",
  "enabled": true,
  "poll_interval_hours": 24,
  "last_fetched_at": "2026-09-23T14:02:11+00:00",
  "last_error": "",
  "backfilled_from": "2025-12-01",
  "history_refused": false,
  "n_days": 205,
  "first_day": "2025-12-01",
  "last_day": "2026-09-22",
  "currencies": ["BRL", "USD"],
  "latest": {
    "day": "2026-09-22",
    "per_eur": {"BRL": "5.8726", "USD": "1.1463"},
    "pairs": {
      "BRL:EUR": "0.170282", "BRL:USD": "0.195195", "EUR:BRL": "5.872600",
      "EUR:USD": "1.146300", "USD:BRL": "5.123092", "USD:EUR": "0.872372"
    }
  }
}
```

- `enabled` false means no provider key is configured on the server; the
  block is still present with `n_days: 0` and `latest: {}`.
- `latest` is `{}` until the first successful poll. `pairs` uses the same
  `FROM:TO` keys as the typed `fx_reference_rates`, six decimals, so the two
  can be set side by side.
- `last_error` is a sentence when the last round failed (the table keeps what
  it had), `""` otherwise. `history_refused` true means the plan does not
  include history: only the newest day arrives each round.
- Sending the key back in a `PUT /api/settings` body is accepted and ignored
  (`ignored: ["fx_daily_rates"]`), like every derived key.

### `POST /api/fx/poll` (new)

No body. Runs one poll round now and answers the same summary:

```json
{"ok": true, "n_stored": 4, "currencies": ["BRL", "USD"], "backfilled_from": null,
 "errors": [], "fetched_at": "2026-09-23T14:02:11+00:00",
 "n_days": 205, "first_day": "2025-12-01", "last_day": "2026-09-22"}
```

`ok: false` with `errors[]` when the provider failed. `409 {"error": "...",
"code": "fx_poll_disabled"}` when no key is configured. After a 200, refetch
`GET /api/settings` (or write the `fx_daily_rates` fields the response
carries into the cache) and re-render the block.

### `rows[].candidates[].fx`

`reference_rate_source` gains the value `opentickers_day`. When it is that
value, `reference_rate_period` is present and is a DAY, `YYYY-MM-DD` (for
`ecb_month` it stays `YYYY-MM`; absent for every other source, never null).

In `src/lib/api.ts`, `reference_rate_period?: string` already exists; add
`fx_daily_rates` to the settings type as above, and the poll response type.

## 2. The FX panel (`RunWorkbench.tsx`, `FxPanel`)

In the `srcLabel` chain, before the raw-string fallback and beside the
`ecb_month` branch:

```tsx
: src === "opentickers_day"
  ? t("wb.fx.source.dailyRate", { day: fxDayLabel(fx.reference_rate_period, locale) })
```

with a helper next to `fxPeriodLabel`:

```tsx
function fxDayLabel(period: string | undefined, locale: string): string {
  if (!period || !/^\d{4}-\d{2}-\d{2}$/.test(period)) return period ?? "";
  const [y, m, d] = period.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(locale, {
    day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
  });
}
```

The row then reads `Reference rate 1.143000 (USD per EUR) · daily rate, 2
July 2026`. `FxSummary` needs no change.

## 3. Settings, FX tab (`SettingsScreen.tsx`, the `currency` tab)

Above the existing typed-rates editor, add one card, "Polled daily rates",
reading the `fx_daily_rates` block:

- Header line: `set.fxDaily.title`, and under it `set.fxDaily.desc`.
- Status line: when `enabled` is false, `set.fxDaily.off` and nothing else.
  Otherwise `set.fxDaily.status` with `{day}` = `latest.day` formatted like
  `fxDayLabel`, `{n}` = `n_days`, `{from}` = `first_day` formatted; and when
  `last_error` is non-empty, a second line `set.fxDaily.error` with `{error}`
  = the sentence, in the amber warning style the page already uses.
- A small table of `latest.pairs`: one row per pair whose left side is not
  EUR-to-X's inverse duplicate is NOT needed; show every pair as delivered,
  two columns `set.fxDaily.pair` / `set.fxDaily.rate`, sorted as delivered.
  When `latest` is `{}`, the table is replaced by `set.fxDaily.none`.
- A button `set.fxDaily.pollNow` (outline, `h-8`) that POSTs
  `/api/fx/poll`, disabled while in flight and when `enabled` is false. On
  200 with `ok: true`, toast `set.fxDaily.polled` with `{n}` = `n_stored`
  and refetch settings; on `ok: false`, toast `set.fxDaily.failed` with the
  first error; on 409, toast `set.fxDaily.off`.

The typed-rates editor itself stays exactly as it is: same pair/rate rows,
same save call (`fx_reference_rates`). Replace only its description text
(`set.fx.desc`) per the table below, so it says that a typed rate overrides
the daily rate.

## 4. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `wb.fx.source.dailyRate` (new) | daily rate, {day} | taxa diária, {day} |
| `set.fxDaily.title` (new) | Polled daily rates | Taxas diárias consultadas |
| `set.fxDaily.desc` (new) | Central-bank reference rates (ECB where it publishes the pair) polled from OpenTickers every 24 hours. A purchase in another currency is converted at the rate of its own day. | Taxas de referência de bancos centrais (BCE quando publica o par) consultadas na OpenTickers a cada 24 horas. Uma compra em outra moeda é convertida pela taxa do próprio dia. |
| `set.fxDaily.status` (new) | Newest rates: {day}. {n} days stored since {from}. | Taxas mais recentes: {day}. {n} dias guardados desde {from}. |
| `set.fxDaily.error` (new) | Last poll failed: {error} | Última consulta falhou: {error} |
| `set.fxDaily.none` (new) | No rates polled yet. | Nenhuma taxa consultada ainda. |
| `set.fxDaily.off` (new) | Daily rate polling is not configured on the server. | A consulta diária de taxas não está configurada no servidor. |
| `set.fxDaily.pair` (new) | Pair | Par |
| `set.fxDaily.rate` (new) | Rate | Taxa |
| `set.fxDaily.pollNow` (new) | Poll now | Consultar agora |
| `set.fxDaily.polled` (new) | Rates updated ({n} stored). | Taxas atualizadas ({n} guardadas). |
| `set.fxDaily.failed` (new) | Poll failed: {error} | Consulta falhou: {error} |
| `set.fx.desc` (replace) | Rates are polled daily from OpenTickers and read for the day of each purchase; the ECB monthly average covers a day with no rate. Add a rate here only to override them: a rate set here is used for every month. | As taxas são consultadas diariamente na OpenTickers e lidas para o dia de cada compra; a média mensal do BCE cobre um dia sem taxa. Adicione uma taxa aqui só para substituí-las: a taxa definida aqui vale para todos os meses. |

## 5. Do not change

- The FX rates editor's behaviour, validation or save payload
  (`fx_reference_rates`).
- `FxSummary`, the band colours, the `reference_gap*` rendering, or any
  `zoho_*` conditional.
- The existing `wb.fx.source.settings` / `statement` / `receipts` /
  `ecbMonth` labels, and the raw-string fallback for a source the panel does
  not know.
- Any route, query key or other page.

## 6. How to check after publishing

1. Settings > FX reference rates: the "Polled daily rates" card shows a
   newest day, a day count and six pairs (EUR:USD near 1.15, BRL:USD near
   0.195 in September 2026), EN and PT; "Poll now" answers with a toast and
   the day count does not drop.
2. A month whose FX candidate reads `reference_rate_source:
   "opentickers_day"` shows `· daily rate, <D Month YYYY>` after the rate in
   the FX panel (PT: `· taxa diária, <D de mês de AAAA>`). On 2026-09-23 no
   live month does yet: July and August were matched on the rates typed in
   Settings, which still win, so their panels keep reading `· Settings`;
   September's cross-currency pairs are the first to show it after the
   month's next re-match.
3. Nothing else on the workbench moved.

# Lovable prompt - exchange rates are fetched, not typed (note #79 + the 2026-09-23 retirement)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

> This prompt replaces an earlier draft of the same file that added the
> polled-rates card while KEEPING the typed-rate editor. The owner then
> retired typing rates altogether, so it is one prompt now: the editor goes,
> the fetched rates take its place. Nothing of the earlier draft was ever
> pasted, so there is nothing to undo.

## Background

A receipt in another currency is compared with the card charge through a
reference rate. Until now the operator could type that rate in Settings, and
a typed rate overrode everything, for every month, forever.

The backend now fetches rates instead: the European Central Bank's daily
reference rate for the day each purchase was made (polled every 24 hours
from OpenTickers), falling back to the ECB's monthly average for that month.
Typing a rate is gone from the product. The Settings tab that held the
editor becomes a read-only view of what the app has fetched, plus a button
to poll now.

## 1. The API

### `GET /api/settings`

- **`fx_reference_rates` no longer exists.** Remove it from the settings
  type, from any form state, and from every save payload. The backend
  accepts the key and ignores it (so nothing breaks in the meantime) but
  never stores or returns it.
- **`fx_daily_rates` is new, derived and read-only** (a PUT carrying it is
  reported in `ignored`):

```json
"fx_daily_rates": {
  "provider": "opentickers",
  "enabled": true,
  "poll_interval_hours": 24,
  "last_fetched_at": "2026-09-23T14:02:11+00:00",
  "last_error": "",
  "backfilled_from": "2025-12-01",
  "history_refused": false,
  "n_days": 45,
  "first_day": "2026-07-22",
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

`enabled: false` means no provider key is configured on the server; the block
is still present, with `n_days: 0` and `latest: {}`. `latest` is `{}` until
the first successful poll. `last_error` is a sentence when the last round
failed (the stored rates are kept), `""` otherwise.

### `POST /api/fx/poll` (new)

No body. Runs one poll round now and answers:

```json
{"ok": true, "n_stored": 4, "currencies": ["BRL", "USD"], "backfilled_from": null,
 "errors": [], "fetched_at": "2026-09-23T14:02:11+00:00",
 "n_days": 45, "first_day": "2026-07-22", "last_day": "2026-09-22"}
```

`ok: false` with `errors[]` when the provider failed. `409 {"error": "...",
"code": "fx_poll_disabled"}` when no key is configured. After a 200, refetch
`GET /api/settings` and re-render the panel.

### `rows[].candidates[].fx`

`reference_rate_source` gains **`opentickers_day`** (and keeps `ecb_month`,
`statement`, `receipts`). The value `settings` can no longer occur.

`reference_rate_period` is present for both fetched sources: a **day**
(`YYYY-MM-DD`) for `opentickers_day`, a **month** (`YYYY-MM`) for
`ecb_month`. Absent for every other source, never null.

In `src/lib/api.ts`, add `reference_rate_period?: string` to `CandidateFx` if
it is not there yet, add the `fx_daily_rates` shape above to the settings
type, remove `fx_reference_rates` from it, and add the poll response type.

## 2. Settings: the FX tab becomes read-only

In `SettingsScreen.tsx`, the sixth tab (URL value `currency`) currently
renders the rate editor. Replace its whole panel.

**Delete:** the pair/rate row list, the add-row control, the remove-row
buttons, the per-row validation, the `fx_reference_rates` form state, and its
save mutation (`b.mutate({fx_reference_rates: e})`). This tab no longer
saves anything, so it has no Save button and no unsaved-changes state.

**Keep the tab in place**, relabelled `set.tabs.rates` ("Exchange rates").
Leave the URL value `currency` exactly as it is, so existing links still
open it.

**Render instead**, from `settings.fx_daily_rates`:

- Heading `set.rates.title`, description `set.rates.desc`.
- When `enabled` is false: `set.rates.off`, and nothing below it.
- Otherwise a status line `set.rates.status` with `{day}` = `latest.day`
  formatted long (e.g. "22 September 2026"), `{n}` = `n_days`, `{from}` =
  `first_day` formatted long. When `last_error` is non-empty, a second line
  `set.rates.error` with `{error}`, in the amber warning style the page
  already uses for advisories.
- A two-column table of `latest.pairs` in the order delivered, headed
  `set.rates.pair` / `set.rates.rate`. When `latest` is `{}`, render
  `set.rates.none` instead of the table.
- A button `set.rates.pollNow` (outline, `h-8`), disabled while in flight.
  On 200 with `ok: true`: toast `set.rates.polled` with `{n}` = `n_stored`,
  then refetch settings. On `ok: false`: toast `set.rates.failed` with the
  first entry of `errors`. On 409: toast `set.rates.off`.

## 3. The FX panel on a match (`RunWorkbench.tsx`, `FxPanel`)

Add both fetched sources to the `srcLabel` chain, before the raw-string
fallback:

```tsx
: src === "opentickers_day"
  ? t("wb.fx.source.dailyRate", { day: fxDayLabel(fx.reference_rate_period, locale) })
: src === "ecb_month"
  ? t("wb.fx.source.ecbMonth", { month: fxPeriodLabel(fx.reference_rate_period, locale) })
```

with `const locale = useLocale();` beside `const t = useT();` (import
`useLocale` from `@/lib/i18n`), and these two helpers in the same file:

```tsx
function fxPeriodLabel(period: string | undefined, locale: string): string {
  if (!period || !/^\d{4}-\d{2}$/.test(period)) return period ?? "";
  const [y, m] = period.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString(locale, {
    month: "long", year: "numeric", timeZone: "UTC",
  });
}

function fxDayLabel(period: string | undefined, locale: string): string {
  if (!period || !/^\d{4}-\d{2}-\d{2}$/.test(period)) return period ?? "";
  const [y, m, d] = period.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(locale, {
    day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
  });
}
```

A row then reads `Reference rate 1.143000 (USD per EUR) · daily rate, 2 July
2026`. Delete the `wb.fx.source.settings` branch: that source can no longer
be sent. `FxSummary` needs no change.

## 4. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `wb.fx.source.dailyRate` (new) | daily rate, {day} | taxa diária, {day} |
| `wb.fx.source.ecbMonth` (new) | ECB average, {month} | média do BCE, {month} |
| `set.tabs.rates` (new) | Exchange rates | Taxas de câmbio |
| `set.rates.title` (new) | Exchange rates | Taxas de câmbio |
| `set.rates.desc` (new) | The app fetches central-bank reference rates every 24 hours and converts each purchase at the rate of its own day. There is nothing to set here. | O app busca as taxas de referência dos bancos centrais a cada 24 horas e converte cada compra pela taxa do próprio dia. Não há nada para configurar aqui. |
| `set.rates.status` (new) | Newest rates: {day}. {n} days stored since {from}. | Taxas mais recentes: {day}. {n} dias guardados desde {from}. |
| `set.rates.error` (new) | Last update failed: {error} | A última atualização falhou: {error} |
| `set.rates.none` (new) | No rates fetched yet. | Nenhuma taxa obtida ainda. |
| `set.rates.off` (new) | Rate fetching is not configured on the server. | A busca de taxas não está configurada no servidor. |
| `set.rates.pair` (new) | Pair | Par |
| `set.rates.rate` (new) | Rate | Taxa |
| `set.rates.pollNow` (new) | Update now | Atualizar agora |
| `set.rates.polled` (new) | Rates updated ({n} stored). | Taxas atualizadas ({n} guardadas). |
| `set.rates.failed` (new) | Update failed: {error} | Falha na atualização: {error} |

**Delete** `set.fx.title`, `set.fx.desc`, `wb.fx.source.settings`, and every
other key the removed editor used, in both languages. Also update
`months.attach.currencyHelp` in both languages to:

- EN: The currency the card settles in. This is not the receipts' currency:
  receipts in other currencies are converted at the central-bank rate for the
  day of each purchase.
- PT: A moeda em que o cartão é cobrado. Não é a moeda dos recibos: recibos em
  outras moedas são convertidos pela taxa do banco central do dia de cada
  compra.

## 5. Do not change

- `FxSummary`, the band colours, the `reference_gap*` rendering, or any
  `zoho_*` conditional.
- The raw-string fallback for a source the panel does not know.
- The other six Settings tabs, their save payloads, or the `?tab=` values.
- Any route or query key other than adding `POST /api/fx/poll`.

## 6. How to check after publishing

1. Settings > Exchange rates: no editable rate rows anywhere, no Save
   button. A newest day, a day count, and six pairs (EUR:USD near 1.15,
   BRL:USD near 0.195 in September 2026), EN and PT. "Update now" answers
   with a toast and the day count does not drop.
2. Save any other tab (Cards, say) and confirm the request body carries no
   `fx_reference_rates` key.
3. A cross-currency match shows `· daily rate, <D Month YYYY>` (PT: `· taxa
   diária, ...`) or `· ECB average, <Month YYYY>` after the rate. No panel
   anywhere reads `· Settings` / `· Configurações`.
4. Nothing else on the workbench moved.

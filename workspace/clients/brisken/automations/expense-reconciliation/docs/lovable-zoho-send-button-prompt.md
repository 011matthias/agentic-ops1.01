# Lovable prompt: the "Send to Zoho" button (owner decision 2026-09-28)

> **NOT PASTED.** SPA half of the in-app send. The backend half is LIVE
> (PR #1530, deployed e38e29e7) and SWITCHED OFF on the server, so until the
> switch is set the preview answers `enabled: false` and the dialog shows
> that reason; pasting this first is safe. Contract:
> `docs/api-contract.md`, last section. Design and guards:
> `docs/zoho-month-end-posting.md`, "Sending from the app".

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>` (use `apiFetch`).

## Why

When Criss has finished a month she sends it into Zoho Books from the app. The backend builds the same file as the "Download CSV (data export)" button, shows what would be entered, and only sends after she confirms. For now it writes only to the Zoho TEST company.

## Scope

`src/lib/api.ts`, `src/components/ExpensesReviewGrid.tsx`, `src/lib/i18n.tsx`. Every new text in BOTH `en` and `pt`.

## 1. The button

Next to the existing "Download CSV (data export)" button on the month page, same size and outline style, lucide `Send` icon. Label en "Send to Zoho", pt "Enviar ao Zoho".

Clicking it opens a dialog and calls `GET /api/runs/{runId}/zoho-send`. While it loads show a spinner and "Checking Zoho…" / "Verificando o Zoho…" (it can take about 10 seconds).

## 2. The dialog, from that response

- `enabled === false`: show `reason`, only a Close button.
- `status === "blocked"`: show `reason` in an amber callout, only Close.
- `status === "nothing_to_send"`: "Nothing new to send for {month}." / "Nada novo para enviar em {month}." plus "{already_sent} entries were sent before." / "{already_sent} lançamentos já foram enviados." Only Close.
- `status === "ready"`:
  - Title "Send {month} to Zoho" / "Enviar {month} ao Zoho".
  - If `test_company` is true, a clear notice at the top: "This goes to the Zoho test company ({company}), not the real books." / "Isto vai para a empresa de teste do Zoho ({company}), não para a contabilidade real."
  - Summary: "{count} entries, total {total} {currency}" / "{count} lançamentos, total {total} {currency}".
  - A table of `entries[]`: Date, Vendor, Amount ("{amount} {currency}"), Account (`accounts` joined with ", ").
  - If `held_back[]` is not empty: a collapsible "Not sent ({n})" / "Não enviados ({n})" listing `reference` and `message`.
  - Buttons: Cancel, and primary "Send {count} entries" / "Enviar {count} lançamentos".
- HTTP 409 with code `zoho_send_no_month` or `zoho_send_refused`: show the response's `error` text in the dialog.

Never show the `detail` or `confirm` fields.

## 3. Sending

- On the primary button: `POST /api/runs/{runId}/zoho-send` with body `{"confirm": <the preview's confirm value>}`. It answers `{job_id}`. Disable the button at once; never retry a send automatically.
- Poll the existing `getJob(job_id)` every 2 seconds until `status` is `"done"` or `"error"`. Show "Sending to Zoho…" / "Enviando ao Zoho…" with a spinner, and do not let the dialog close while sending.
- `status === "error"`: show `job.error`.
- `status === "done"`, read `job.result`:
  - `result.ok` true: a green message "Sent {sent} entries. Zoho shows the same total: {total_in_zoho} {currency}." / "{sent} lançamentos enviados. O Zoho mostra o mesmo total: {total_in_zoho} {currency}."
  - `result.ok` false: an amber callout with `result.reason` when present; then "Sent {sent}, {checked_ok} checked OK." / "Enviados {sent}, {checked_ok} conferidos." when `sent > 0`; then list `result.problems` (reference and its problems joined), `result.rejected` and `result.unsure` (reference and message).
  - Never show `result.log`.
- After done or error, invalidate this month's queries so the page reloads.
````

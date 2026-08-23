# Lovable prompt - the two report documents (PDF)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Backend is live.

## Why this exists

The month's output is no longer a file for an accounting system to import,
because there is no system to import it into (owner directive 2026-08-23). It
is a document a person reads and an auditor accepts: an organized listing,
then every receipt behind the expense it proves.

## 1. New primary action on the batch page

`GET /runs/{batch_id}/expense-report.pdf`

Returns `application/pdf` with a `Content-Disposition` filename like
`expense-report-April-2026.pdf`. Send the bearer token; stream it to a
download the way the CSV download already works.

Label it **"Download expense report (PDF)"** (PT: "Baixar relatorio de
despesas (PDF)") and make it the **primary** action in the batch page's
action row, above the CSV.

It is regenerated on every request from the current state, so a category fix
or a card assignment is reflected the moment it is downloaded; there is
nothing to invalidate or cache.

## 2. Demote, do not remove, the CSV

The existing "Download Zoho Expenses CSV" button keeps working. Two changes:

- Rename it to **"Download CSV (data export)"** (PT: "Baixar CSV (exportacao
  de dados)"). The word "Zoho" is going away everywhere; the app has no
  connection to Zoho any more.
- Style it as a secondary action beside the PDF.

## 3. What the reader gets, so the button copy can promise it

- Page 1: the month's title, the expense count and totals per currency, then
  the numbered listing (date, vendor, account, entity, paid-through, amount,
  currency).
- Then one caption page per receipt — "Expense 3 · Trenitalia" with the date,
  amount, account and entity — followed by that receipt's own pages.
- A receipt that books to two accounts writes two listing rows and appears
  once, captioned "Expenses 3, 4".
- An expense with no document says "No receipt document for this expense" on
  its caption page. A file that exists but cannot be rendered says that too.
  Nothing is silently dropped.

## 4. Expect it to take a moment

The report reads every receipt off the volume and stitches them, so a large
month is not instant. Disable the button while the request is in flight and
show a spinner; do not add a timeout shorter than 60 seconds.

## 5. The reconciliation document (statement runs)

`GET /runs/{run_id}/reconciliation-report.pdf` — the same treatment for a run
that has a statement attached. Add it to the workbench page as the primary
action, labelled **"Download reconciliation (PDF)"** (PT: "Baixar
reconciliacao (PDF)").

What it contains, in this order: the header (charges, how many matched, what
is still unreconciled per currency), **what needs attention** (charges with
no receipt, receipts with no charge, possible duplicate groups), then every
charge with its matched receipt and status, then the receipts themselves —
matched ones captioned with the charge they settle, unmatched ones captioned
as unmatched.

The existing XLSX download stays as the working sidecar; keep it visible and
secondary. The reconciled CSV stays available and demoted, same treatment as
the expenses CSV.

## 6. Do not change

No payload shapes changed in this round. The grid, the summary counts, and
the CSV are all untouched.

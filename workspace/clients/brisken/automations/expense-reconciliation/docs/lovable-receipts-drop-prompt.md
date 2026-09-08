# Lovable prompt: the Receipts page — DELTA (v1 is applied)

> **v1 APPLIED 2026-09-08** (owner pasted mid-day, bundle-verified the
> same evening, 46 chunks: `chunk-receipts` reads `n_filed` /
> `n_needs_month` / `needs_month`, `/api/receipts` + "Recibos" +
> "Dos recibos" live in the i18n chunk). v1 scope: the `/receipts` drop
> page, the needs-month picker, the "From receipts" months badge, the
> quiet empty-month state, and the create-form upload-area removal. The
> exact applied text is the #709 version of this file in git history.
>
> **What remains below is the DELTA** — everything decided later the
> same day and NOT yet in the published bundle (verified absent:
> `upload-cap` has zero hits, "Start a new month" and `expenses/new`
> references are still present): the cap raise copy + client-side
> chunking, full removal of month creation from the UI (owner ruling,
> backlog item 46), the top-bar navigation redesign, and the
> pooled-mail "Open {month}" release. Paste sections in order.

Copy everything below the line into Lovable.

---

Four changes to the existing app. The Receipts page already exists; do
not rebuild it — sections 1 amends it, the rest touch navigation, month
creation, and the Email intake page.

## 1. Receipts page: bigger drops, honest cap copy

The backend's per-drop bound was raised from 80 to 500 files per month.
Two changes on the existing `/receipts` page:

- If more than 300 files are dropped at once, split them into
  sequential POSTs to `POST /api/receipts` of at most 300 files each
  (the server parses at most ~1000 form parts per request), show one
  combined progress line ("Uploading part 2 of 3"), and merge the
  resulting ledgers into one list.
- The per-file ledger can now return a new rejected `reason`:
  `upload-cap`, carrying `limit` and `month`. Render it as: "more
  receipts for {month label} than one drop can take; the first {limit}
  were filed — drop the rest again, anything already filed is skipped
  automatically." (PT equivalent.)

## 2. Month creation leaves the UI entirely

Delete the "Start a new month" button/link everywhere it appears — the
top bar of the months overview and the button in the page body — and
remove the company-month create form at `/expenses/new`. Months are
never created by hand any more: they come into existence automatically
when receipts arrive (email intake, or the Receipts drop page) and
through the "Open {month}" release in section 4. A direct visit to the
removed route should just redirect to `/months`.

The TRIP creation flow is unchanged: trips are created from the Trips
page and a trip batch is still created with its first receipt. If the
`/expenses/new` form is shared with trip creation, keep the trip arm
and remove only the company-month arm.

"Add a statement" stays exactly where it is today, inside each month's
page.

## 3. The top bar lives only on the main menu

The months overview (`/months`) is the app's main menu. It keeps the
full top bar exactly as today: the nav tabs, the language toggle, the
signed-in state, and Log out.

Every other route — Receipts, Trips, Email intake, Memory, Compare,
Guide, Settings, and every detail page (a month's expenses page, a
trip, an intake mail) — hides the top bar completely. In its place,
show one sticky button pinned at the top left of every non-menu page:
"← Menu" (same wording in PT), which navigates to `/months`, where the
top bar is visible again. The button stays visible while scrolling, so
there is always exactly one way back to the main menu from anywhere.

Consequence to implement deliberately, not fight: the language toggle
and Log out now appear only on the main menu. Do not re-add a second
bar or partial header to the other pages; each page keeps its own h1
and content, plus the Menu button.

## 4. Pooled mail: the one-click month release

Some mail deliberately waits in the pool instead of creating its
month: mail from senders the tool does not recognise, and mail whose
receipt shows no readable date. On the Email intake page, a pooled row
(`status === "pooled"`) whose month has no batch yet
(`pool_month_state === "no_batch"`) currently just says it is waiting.
Give exactly those rows a small button: "Open {month label}" (PT
"Abrir {month label}"), where the label is the English month name and
year built from the row's `pool_month` ("2026-07" → "July 2026").

Clicking it POSTs to the existing `POST /api/expense-batches` as form
data with a single field `label` set to that English label ("July
2026" — always English regardless of the UI language, because batch
labels are canonical English) and NO files. The reply is `{ok,
batch_id, job_id, label, month}`; poll `GET /jobs/{job_id}` like other
jobs. When it flips to done, the month exists and the waiting mail
claims itself into it automatically in the background — refresh the
intake list a few seconds after the job completes (the row's mail will
show as ingested) and refresh the months list, which now carries the
new month.

Never show this button on travel rows (`pool_kind === "travel"`):
travel mail waits for its trip, not a month. Only non-travel pooled
rows with `pool_month_state === "no_batch"` get it.

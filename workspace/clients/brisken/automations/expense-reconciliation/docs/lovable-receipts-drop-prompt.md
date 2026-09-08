# Lovable prompt: the Receipts page (drop receipts any time)

> Backend shipped 2026-09-08. Receipt entry is DECOUPLED from month
> creation: months are created empty, and receipts enter through one
> manual entrance — the new Receipts page — plus the existing mail
> intake. Section 2 removes the upload area from the create-month form;
> the server now refuses files there (400), so an unpasted SPA cannot
> corrupt anything, it just shows an error when someone tries the old
> flow. Amended same day: the per-ingest cap was raised 80 → 500 and
> the ledger gained the `upload-cap` rejected reason (section 1), and
> section 5 is the owner's navigation redesign (top bar only on the
> main menu). Amended again same day (owner ruling): section 2 now
> removes month creation from the UI entirely — not just its upload
> area — and section 6 adds the pooled-mail "Open {month}" release
> that replaces the button's last real job. Paste sections in order.

Copy everything below the line into Lovable.

---

Add a "Receipts" page and decouple receipt upload from month creation.
The backend already works this way; this change makes the UI match.

## 1. The Receipts page (new route `/receipts`)

Add a nav entry "Receipts" (PT "Recibos") pointing at a new page
`/receipts`. The page is one large drag-and-drop zone (click to browse
also works) that accepts image and PDF receipt files, several at once —
big backfill piles included. Like every page outside the main menu it
carries the "← Menu" button from section 5, so there is always a way
back to the months overview.

On drop, POST the files to `POST /api/receipts` as multipart, field name
`files` (repeatable). If more than 300 files were dropped at once, split
them into sequential POSTs of at most 300 files each (the server parses
at most ~1000 form parts per request), show one combined progress line
("Uploading part 2 of 3"), and merge the resulting ledgers into one
list. The reply per POST is `{ok, job_id, n_files}`. Poll
`GET /jobs/{job_id}` like other uploads; while it runs, show the job's
`stage` text ("reading receipts", "filing September 2026"). When status
is `done`, the job object carries a `result` field:

```
result = {
  files: [{file, status, month?, month_source?, batch_id?, reason?,
           mixed_months?}],
  months: [{month, label, batch_id?, created_batch, n_files, n_added,
            issues?, error?}],
  n_filed, n_needs_month, n_rejected
}
```

Render `result.files` as a list, grouped by `status`:

- `filed`: "Filed into {label}" with a link to `/expenses/{batch_id}`.
  Use the matching `months` entry for the label. When that entry has
  `created_batch: true`, say "Filed into {label} (month created)". When
  the entry's `n_added` is less than its `n_files`, add one line for
  the group: "{n} of these were already in the month (duplicates are
  skipped)". A row with `mixed_months: true` gets a small note "this
  file shows dates from more than one month; filed by the earliest".
- `needs_month`: "No readable date on this receipt" (reason
  `no-readable-date`) or "The date on this receipt looks implausible"
  (reason `implausible-date`). Each such row gets a month picker
  (a month input, format YYYY-MM) and a "File into this month" button
  that re-submits JUST that file to `POST /api/receipts` with the extra
  form field `month` set to the picked value. The backend believes a
  typed month.
- `rejected`: per `reason` — `unsupported-type` ("not a receipt file
  type; images and PDFs only, one file per receipt — zips are not
  expanded here"), `empty-file`, `too-large`, and `upload-cap` ("more
  receipts for {month label} than one drop can take; the first {limit}
  were filed — drop the rest again, anything already filed is skipped
  automatically", reading the row's `limit` and `month`).
- `failed`: show the row's `reason` verbatim.

Explain the page in one quiet line under the drop zone: "Each receipt
files into the month printed on it. Months that do not exist yet are
created automatically. Trip receipts are joined from the trip's own
page or by mailing the travel address."

All strings in EN and PT.

## 2. Month creation leaves the UI entirely

Delete the "Start a new month" button/link everywhere it appears — the
top bar of the months overview and the button in the page body — and
remove the company-month create form at `/expenses/new`. Months are
never created by hand any more: they come into existence automatically
when receipts arrive (email intake, or the Receipts page from section
1) and through the "Open {month}" release in section 6. A direct visit
to the removed route should just redirect to `/months`.

The TRIP creation flow is unchanged: trips are created from the Trips
page and a trip batch is still created with its first receipt. If the
`/expenses/new` form is shared with trip creation, keep the trip arm
and remove only the company-month arm.

"Add a statement" stays exactly where it is today, inside each month's
page.

## 3. Months list: the drop origin badge

The months list already renders a "From email" badge when a row's
`created_by` is `"intake"`. Add the sibling: `created_by === "drop"`
renders "From receipts" (PT "Dos recibos"). Any other value renders
nothing, as today.

## 4. Empty months look intentional, not broken

A month batch with `summary.n_expenses === 0` (now a normal state right
after creation) should show a quiet empty state on the batch page:
"No receipts yet. They arrive by email or through the Receipts page;
the statement can be uploaded at any time." Never an error styling.

## 5. The top bar lives only on the main menu

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

## 6. Pooled mail: the one-click month release

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

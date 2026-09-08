# Lovable prompt: the Receipts page (drop receipts any time)

> Backend shipped 2026-09-08. Receipt entry is DECOUPLED from month
> creation: months are created empty, and receipts enter through one
> manual entrance — the new Receipts page — plus the existing mail
> intake. Section 2 removes the upload area from the create-month form;
> the server now refuses files there (400), so an unpasted SPA cannot
> corrupt anything, it just shows an error when someone tries the old
> flow. Paste sections in order.

Copy everything below the line into Lovable.

---

Add a "Receipts" page and decouple receipt upload from month creation.
The backend already works this way; this change makes the UI match.

## 1. The Receipts page (new route `/receipts`)

Add a nav entry "Receipts" (PT "Recibos") pointing at a new page
`/receipts`. The page is one large drag-and-drop zone (click to browse
also works) that accepts image and PDF receipt files, several at once.

On drop, POST the files to `POST /api/receipts` as multipart, field name
`files` (repeatable). The reply is `{ok, job_id, n_files}`. Poll
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
  expanded here"), `empty-file`, `too-large`.
- `failed`: show the row's `reason` verbatim.

Explain the page in one quiet line under the drop zone: "Each receipt
files into the month printed on it. Months that do not exist yet are
created automatically. Trip receipts are joined from the trip's own
page or by mailing the travel address."

All strings in EN and PT.

## 2. Month creation loses the upload area

On the create-month form (`/expenses/new`), REMOVE the receipts upload
area for company months entirely. Creating a month now needs only the
label (and the optional legal entity); submit with no files and the
server creates an empty month. The server refuses files on this call
(400), so leaving the upload area would only produce errors.

Replace the removed area with one line of copy: "A month starts empty.
Receipts arrive by email or through the Receipts page and file
themselves into the right month." (PT equivalent.)

The TRIP creation flow is unchanged: a trip batch is still created with
its first receipt, so keep the trip upload exactly as it is.

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

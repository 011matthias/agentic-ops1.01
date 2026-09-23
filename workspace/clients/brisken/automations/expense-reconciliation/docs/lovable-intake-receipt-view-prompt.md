# Lovable prompt: open a receipt from the Email intake page (item 185)

**What this is.** The Email intake page lists every mail the tool received
and what came of it. Its Files column is plain grey text. To actually look at
a receipt that arrived by email, Criss has to leave the page, open the month,
find the row and click the receipt there. This makes the intake page open the
receipt itself.

**The viewer already exists and is published.** Item 178 shipped it: the live
bundle carries `?as=png` + `X-Receipt-Pages` and the `receipt.*` strings in
both languages. This prompt builds no viewer. It wires the intake page into
the one that is already there.

## The measurement that decides the design

Read off the live log on 2026-09-24 (`GET /api/inbound/log?detail=1`, 143
mails):

- **72 mails show `-` in the Files column. 61 of those 72 produced a receipt
  the tool went on to reconcile.** Those are forwarded notices with no
  attachment: the app renders the email body to a PDF and files it as the
  expense. The cell reads `files` (attachment names) when the thing worth
  opening is `documents`. So `-` is wrong on 43% of the page, and wrong in
  the direction that reads as "nothing arrived".
- 95 of the 116 file names join to a document; 21 do not (dismissed test
  mails, set-aside images). The join has to degrade, not throw.

## The data each row already carries

```jsonc
// attachments, the ordinary case
{
  "archive":   "20260923T201931-4c6eaeba",
  "batch_id":  "51a22ad72864",              // this is the runId the viewer needs
  "n_files":   2,
  "files":     ["Invoice-B2EA98DF-0021.pdf", "Receipt-2179-5147.pdf"],
  "documents": ["0078__Invoice-B2EA98DF-0021.pdf", "0079__Receipt-2179-5147.pdf"],
  "expenses":  [{ "document_id": "0078__Invoice-B2EA98DF-0021.pdf",
                  "vendor": "Pressmaster FZCO", "date": "2026-09-23",
                  "total": "135.00", "currency": "USD" }]
}

// body-only: the shape that shows "-" today
{
  "n_files": 0,
  "files": [],
  "documents": ["0077__rendered-body.pdf"],
  "expenses": [{ "document_id": "0077__rendered-body.pdf", "vendor": "OpenAI",
                 "date": "2026-09-23", "total": "90.11", "currency": "USD" }]
}
```

A `document_id` is `NNNN__<filename>`. Split on the FIRST `__` to recover the
filename; if there is no `__`, the whole id is the name.

## The endpoint (shipped, live, verified today)

```
GET /api/runs/{batch_id}/receipts/{encodeURIComponent(document_id)}/image?as=png&page=0
```

Probed against September this morning: `0079__Receipt-2179-5147.pdf` returns
`image/png`, 161 KB, `X-Receipt-Pages: 1`; the same id without `?as=png`
returns `application/pdf`. The rendered body `0077__rendered-body.pdf` returns
a 763 KB PNG. A document an operator has since deleted still serves. Nothing
new is needed on the backend.

## Paste this into Lovable

### 1. The Files cell becomes openable

Today `FilesCell` takes `{ files, nFiles }`, joins the names with `", "` and
renders one truncated `<span>`, falling back to `-` when `files` is empty or
`n_files` is 0. Give it the whole `entry` instead and render a list where each
name that maps to a document is a button that opens the viewer.

```ts
/** "0078__Invoice-B2EA98DF-0021.pdf" -> "Invoice-B2EA98DF-0021.pdf" */
function docFilename(documentId: string): string {
  const i = documentId.indexOf("__");
  return i === -1 ? documentId : documentId.slice(i + 2);
}

/** What this mail has that can be opened, in display order. */
function viewableFiles(entry: InboundEntry): { label: string; documentId: string }[] {
  const docs = entry.documents ?? [];
  const names = (entry.files ?? []).filter(Boolean);

  if (names.length > 0) {
    return names.map((name) => {
      const hit = docs.find((d) => docFilename(d) === name);
      return { label: name, documentId: hit ?? "" };   // "" = not openable
    });
  }

  // No attachment: the receipt IS the rendered email body.
  return docs
    .filter((d) => docFilename(d) === "rendered-body.pdf")
    .map((d) => ({ label: t("mail.files.emailBody"), documentId: d }));
}
```

Rules for the cell:

- A name with a `documentId` renders as a button carrying the filename, and
  opens the viewer on `batch_id` + that id. A name without one keeps exactly
  today's grey text.
- `-` only when `viewableFiles(entry)` is empty AND `files` is empty. A
  body-only mail must never read `-` again.
- No `batch_id`, or `batch_deleted: true`: everything stays plain text. There
  is no run to fetch from.
- **The `<tr>` already has an `onClick` that toggles the expander**, so every
  button in this cell needs `e.stopPropagation()` or one click does both
  things.
- Keep the cell narrow. Stack the names, truncate each one, keep the full list
  in the `title`.

### 2. The expanded row gets a View receipt control

Expanding a row already lists each created expense as `vendor - date - total`,
wrapped in a `<Link to="/expenses/$batchId">` that opens the whole month. Keep
that link on the text, and add a separate small `receipt.view` control at the
end of the line that opens the viewer for `expense.document_id`. Two different
destinations must not share one hit area.

A `deleted: true` expense keeps its line-through and its "removed by reviewer"
note, and keeps the view control: the file is still there and seeing it is
often the point of asking why it went.

### 3. Reuse the viewer, do not fork it

Call the published helper (the one that hits
`/receipts/{id}/image?as=png&page={n}` and reads `X-Receipt-Pages`) and open
the same modal the month view uses, with the same zoom, paging, download and
`renderFailed` fallback. Revoke every object URL on close and on page change;
this page can open a dozen receipts in a sitting.

The modal title should name the mail, not just the file: the subject line plus
the filename. Use `receipt.view.title` if it already takes a parameter,
otherwise pass the filename through.

### 4. Optional: the set-aside files

`not_added[]` entries carry a `document_id` too, and it does serve. Worth a
view control on the "read as not a receipt, set aside" line so Criss can check
the call without opening the month.

One caveat, stated because it is visible in the live data rather than
theoretical: all six set-aside rows in the log share the id
`0028__image.png`. They are the repeated brand logo in a forwarded Zoho
receipt, collapsed to one stored file by content dedupe. So the control opens
*the file that was set aside*, which in this data is the same image every
time, not provably this mail's own copy. Ship it if that reads as useful;
skip it if it reads as confusing.

### 5. Strings

English:

- `"mail.files.emailBody": "Email text"`
- `"mail.files.view": "Open"`
- `"mail.files.notStored": "not kept"`

Portuguese:

- `"mail.files.emailBody": "Texto do e-mail"`
- `"mail.files.view": "Abrir"`
- `"mail.files.notStored": "nao guardado"`

`receipt.view`, `receipt.zoom.*`, `receipt.page`, `receipt.download`,
`receipt.render_failed` and `receipt.loading` already exist in both
languages. Do not add second copies.

## How to check you are done

Open Email intake and use these two live rows.

1. **"FW: Your receipt from Pressmaster FZCO #2179-5147"** (Sep 23, 10:19 PM).
   Two file names in the cell. Both must open, and the receipt must be
   readable without downloading it.
2. **"FW: Your OpenAI API account has been funded"** (Sep 23, 4:01 PM). Shows
   `-` today. It must show one openable entry reading "Email text", and
   opening it must show the rendered notice (a 763 KB PNG). This row is the
   whole point of the change.

Then the instrument check: with devtools on the network tab, click a file
name. Today that click produces **no request at all**. Afterwards it must show
a request to `/receipts/.../image?as=png`. A modal that opens with a spinner
and no request is the same bug wearing a viewer.

Last, click a file name and confirm the row does **not** also expand or
collapse. That is the `stopPropagation` from step 1.

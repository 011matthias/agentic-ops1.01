# Lovable prompt - the View receipt button does nothing (item 52)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## The defect

Criss reported "Recibo nao estar abrindo" on the August month (2026-09-08).
Measured on the live app 2026-09-15: on **Review expenses**
(`/expenses/{batchId}`), every row's **View receipt** button is enabled, has a
click handler, and does nothing at all. With `window.fetch`, `window.open`,
`URL.createObjectURL` and anchor clicks all instrumented, a click produced no
request, no dialog, no iframe, no tab and no error. 31 rows on August, 32 on
September, statement month and open month alike.

It is not the API. `GET /api/runs/{id}/receipts/{doc}/image` returns `200` with
the right `Content-Type` for all 31 August receipts and all 51 July ones, and
`expenses[].receipt_image_available` is `true` on every one of them.

## What to build

**A viewer that opens the receipt.** The fetch helper already exists in the
bundle (`GET /api/runs/{runId}/receipts/{documentId}/image`, raw, `.blob()`);
what is missing is a component that renders what it returns.

1. On click, fetch the blob for that row's `document_id`, then
   `URL.createObjectURL(blob)` and open it in a modal. Revoke the object URL
   when the modal closes.
2. **Render by the blob's own `type`, not by the file extension.** Almost
   every receipt in production is `application/pdf` (mail bodies rendered to
   PDF, invoices, Anthropic/OpenAI receipts); a minority are `image/jpeg` or
   `image/png`. A PDF blob put in an `<img>` renders nothing, which looks
   exactly like the button doing nothing.
   - `application/pdf` -> `<iframe src={objectUrl}>` filling the modal.
   - `image/*` -> `<img src={objectUrl}>`, contained, scrollable if tall.
   - anything else -> a download link rather than a blank frame.
3. **Say so when it fails.** A non-200 from the image route, or a blob whose
   type you cannot render, shows a short message naming the file. Silence is
   the defect being reported; a failed preview must never look like a
   successful one.
4. Include the receipt's file name in the modal header (`source_file` on the
   expense row, already populated).

## Where else the same viewer belongs

The reconciliation workbench (`/runs/{batchId}`) has **no way to open a
receipt at all** today: the UNMATCHED RECEIPTS table's Document column is
plain text with no handler, and the candidate rows offer nothing either.
Reuse the same modal there:

- UNMATCHED RECEIPTS: make the Document cell open the viewer.
- `rows[].candidates[].receipt`: a small view control beside the candidate,
  so a reviewer deciding a match can see the receipt they are deciding about.

Both payloads carry `receipt_image_available` and, since 2026-09-15, both
resolve it the same way: **true means the image route will serve that
document**. Use it to decide whether to render the control at all; do not use
`has_receipt_image`, which answers a different question (whether the source
document named a comprovante) and is `false` on receipts that open fine.

## i18n keys

| Key | EN | PT |
|---|---|---|
| `receipt.view.title` | Receipt | Recibo |
| `receipt.view.failed` | This receipt could not be opened ({file}) | Nao foi possivel abrir este recibo ({file}) |
| `receipt.view.download` | Download instead | Transferir em vez disso |
| `receipt.view.close` | Close | Fechar |

## How to verify (do this, do not assume)

Open `/expenses/074a7b8905d7` (August 2026) and click **View receipt** on the
first row. A PDF must render in the modal. Then do the same on
`/expenses/51a22ad72864` (September 2026, no statement attached), because the
button is dead on both and a fix that only works on one is not the fix.
Finally open `/runs/074a7b8905d7` and open a receipt from UNMATCHED RECEIPTS.

A click that produces no visible change is the bug, so "no error in the
console" is not a pass. The pass is a receipt on screen.

# Lovable prompt: a receipt you can actually read (item 178)

**Background.** The same person has asked for this three times in 69 days:

| Note | Date | What she wrote |
|---|---|---|
| #3 | 2026-07-16 | *Precisa ser baixado a foto do recibo para ser usada.* |
| #32 | 2026-09-08 | *recibo nao estar abrindo* |
| #82 | 2026-09-23 | *Se possivel ter uma lupa para ampliar a foto do recibo.* |

The reason is in the payload: `/image` used to hand back the stored file with
its own media type, and **70 of September's 75 receipts are PDFs**. A PDF
cannot go in an `<img>`, so the only thing the screen could do with one was
download it, which is note #3 word for word.

**What the published app does today, measured 2026-09-24** by driving the
live September month over CDP, not inferred from the bundle:

- **Zero `<img>` elements on the entire page.** Not just on the row with the
  receipt: the whole month view renders no image element at all.
- **Zero network requests to `/receipts/`.** The page never asks the API for
  a receipt, so there is no broken image and no failed fetch to find in
  devtools. Nothing is attempted.
- The receipt cell is **column 9**, and it renders the filename as text
  inside a single button, e.g.
  `processed-0EDA78B9-0BCF-4620-8842-A66CF80CA032.jpeg`.

So this is not a repair of a broken viewer. There is no viewer. Item 52 read
the same symptom from the other side and recorded it as a dead "View receipt"
button; the drive says the control is now the filename in column 9.

**The backend half is shipped.** The API can now render any receipt to an
image, so this is a pure front-end change: no new endpoint, no payload field.

Two things to get right, because they are what she is actually asking for:

- She is reading amounts and dates off phone photos of paper receipts. The
  row that got note #82 is a **444 x 2573** JPEG, almost six times taller than
  wide. Fit-to-window puts that at about a third of full size and the text is
  gone. **Zoom is the feature**, not a bigger thumbnail.
- Most receipts are multi-page PDFs. The viewer has to page.

## The API contract you are building against

```
GET /api/runs/{run_id}/receipts/{document_id}/image?as=png&page=0
```

- `?as=png` returns something a browser can display **whatever was stored**.
  A PDF page comes back as `image/png`; a JPEG comes back as itself,
  unchanged, because re-encoding it would only cost quality.
- `?page=N` is 0-based and clamped, so asking past the end returns the last
  page rather than an error.
- Response header **`X-Receipt-Pages`** is the page count. Use it to decide
  whether to show page navigation at all.
- Response header **`X-Receipt-Render: failed`** means the file was a PDF the
  server could not rasterize; the body is then the original bytes. Offer the
  download and say so, rather than showing a broken image.
- Without `?as=png` the endpoint behaves exactly as it does today. Do not
  remove any existing call; just add the parameter where you display.

`document_id` must be `encodeURIComponent`-ed. It contains `__` and a
filename, for example `0024__processed-0EDA78B9-0BCF-4620-8842-A66CF80CA032.jpeg`.

## Paste this into Lovable

1. **In `src/lib/api.ts`**, beside the existing receipt-image helper, add one
   that returns the blob URL and the page count together:

   ```ts
   /** Fetch one page of a receipt as a displayable image.
    *  Works for PDFs and photos alike: the server rasterizes when it has to.
    *  Returns the object URL, the page count, and whether the server failed
    *  to render (in which case the blob is the original file, not an image). */
   export async function fetchReceiptPage(
     runId: string,
     documentId: string,
     page = 0,
   ): Promise<{ url: string; pages: number; renderFailed: boolean }> {
     const res = await apiRaw(
       `/api/runs/${runId}/receipts/${encodeURIComponent(documentId)}/image?as=png&page=${page}`,
     );
     const blob = await res.blob();
     return {
       url: URL.createObjectURL(blob),
       pages: Number(res.headers.get("X-Receipt-Pages") || "1"),
       renderFailed: res.headers.get("X-Receipt-Render") === "failed",
     };
   }
   ```

   Use whatever the existing raw-fetch helper is called; the one the current
   receipt-image call already uses with `{raw: true}` is the right one, so the
   bearer token and the error handling stay identical.

   **Revoke the object URL** when the viewer closes or the page changes, or a
   long review session leaks a blob per receipt opened.

2. **Add a `ReceiptViewer` modal component.** Requirements, in priority order:

   - Opens on clicking the receipt cell or the receipt name in a row. The
     whole cell is the target, not a small icon; she is clicking this dozens
     of times per month.
   - Shows the image at **natural size inside a scrollable, pannable area**,
     not scaled to fit. Start at fit-width, because a tall receipt scaled to
     fit-height is unreadable.
   - **Zoom**: buttons for `-` / `100%` / `+`, plus ctrl+wheel and pinch.
     Range 25% to 400%. Clicking the `100%` button toggles between fit-width
     and 100%. Double-clicking the image zooms to 200% at the clicked point.
   - **Pan** by dragging when zoomed in.
   - **Pages**, only when `pages > 1`: `‹ 2 / 5 ›`, with left/right arrow keys.
     Keep the zoom level across a page change; re-fetch the new page.
   - **Keyboard**: `Esc` closes, `+` / `-` zoom, arrows page, and the modal
     traps focus and returns it to the row on close.
   - A **Download** button stays available; it is the fallback when
     `renderFailed` is true, and some receipts she wants to forward.
   - While the fetch is in flight show a spinner in the frame, not a layout
     jump.

3. **Wire the receipt cell to open the viewer.** Column 9 of the expense
   table currently renders the receipt filename as text inside one button,
   and that button does not fetch anything. Make it open this modal. Keep the
   filename visible as the label; it is how she tells two receipts on one
   charge apart. If any older "View receipt" control survives elsewhere and
   downloads the file, point it here instead: download is now the secondary
   action inside the viewer.

4. **In `src/lib/i18n.tsx`**, add in both languages:

   English:
   - `"receipt.view": "View receipt"`
   - `"receipt.zoom.in": "Zoom in"`
   - `"receipt.zoom.out": "Zoom out"`
   - `"receipt.zoom.reset": "Actual size"`
   - `"receipt.zoom.fit": "Fit width"`
   - `"receipt.page": "Page {n} of {total}"`
   - `"receipt.download": "Download"`
   - `"receipt.render_failed": "This file could not be shown here. Download it to open it."`
   - `"receipt.loading": "Loading receipt"`

   Portuguese:
   - `"receipt.view": "Ver recibo"`
   - `"receipt.zoom.in": "Ampliar"`
   - `"receipt.zoom.out": "Reduzir"`
   - `"receipt.zoom.reset": "Tamanho real"`
   - `"receipt.zoom.fit": "Ajustar a largura"`
   - `"receipt.page": "Pagina {n} de {total}"`
   - `"receipt.download": "Baixar"`
   - `"receipt.render_failed": "Nao foi possivel mostrar este arquivo aqui. Baixe para abrir."`
   - `"receipt.loading": "Carregando recibo"`

## How to check you are done

Open the September month and click the receipt on the row
`0024__processed-0EDA78B9-...jpeg` (DB Fernverkehr AG, 16.00 EUR). It is the
tall narrow photo note #82 was left on. You should be able to read the fare
without leaving the page, and without downloading anything.

Then open any row whose receipt name ends `.pdf` (most of them). It must
display, and if it has more than one page the pager must appear.

Both of those failing today is the whole of item 178.

To confirm you have actually wired it, open devtools on the network tab and
click a receipt. Today that click produces **no request at all**; afterwards
it must show a request to `/receipts/.../image?as=png`. A viewer that opens
with a spinner and no request is the same bug in a new shape.

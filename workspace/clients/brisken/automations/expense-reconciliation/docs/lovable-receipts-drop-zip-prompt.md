# Lovable prompt: the Receipts page takes a .zip (item 237)

> **NOT YET APPLIED.** The backend half is live first: `POST /api/receipts`
> opens a dropped zip and files each member on its own row (item 237). Until
> this is pasted the page never sends a zip: its file picker accepts only
> `image/*,application/pdf`, and the same file-name filter drops a zip from
> the picked or dragged list before upload (bundle read 2026-09-27,
> `chunk-receipts`: `A=/\.(pdf|png|jpe?g|webp|heic|tiff?)$/i`).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes on the Receipts page (the `/receipts` route, the component that renders `rcpt.help` and maps drop reasons like `"no-readable-date": "rcpt.reason.noDate"`) and in `src/lib/i18n.tsx`. No new request: the page keeps posting to `POST /api/receipts` exactly as now.

## Why

The backend now opens a .zip dropped on the Receipts page and files every receipt inside it by the month printed on it, one ledger row per receipt, skipping any receipt the tool already holds. Someone who keeps receipts as a zip can drop it as it is. The page currently filters zips out before they are sent.

## 1. Let a .zip through

- The hidden file `<input>`: change `accept` from `image/*,application/pdf` to `image/*,application/pdf,.zip,application/zip`.
- The file-name filter used for BOTH the picker and drag-and-drop (currently `/\.(pdf|png|jpe?g|webp|heic|tiff?)$/i`): add `zip`, so it reads `/\.(pdf|png|jpe?g|webp|heic|tiff?|zip)$/i`.
- Nothing else about sending changes. A zip is one file in the selection count and one part in the multipart body; the result ledger lists the receipts inside it, each under its own file name.

## 2. Copy (both languages)

| Key | EN | PT |
|---|---|---|
| `rcpt.help` (changed) | Images and PDFs, one file per receipt, or a .zip of them. Max 15 MB per file, up to 500 files. | Imagens e PDFs, um arquivo por recibo, ou um .zip com eles. Máx. 15 MB por arquivo, até 500 arquivos. |
| `rcpt.reason.unsupported` (changed) | not a receipt file type; images and PDFs only (a zip inside a zip is not opened) | não é um tipo de ficheiro de recibo; apenas imagens e PDFs (um zip dentro de um zip não é aberto) |
| `rcpt.reason.zipUnreadable` (new) | this zip could not be opened (it is damaged, or not really a zip) | este zip não pôde ser aberto (está danificado ou não é realmente um zip) |
| `rcpt.reason.zipTooMany` (new) | unpacking this zip would take the drop past {limit} files; drop it on its own, or split it into smaller zips | abrir este zip levaria o envio a mais de {limit} ficheiros; solte-o sozinho ou divida-o em zips menores |
| `rcpt.reason.zipNoSpace` (new) | the server does not have the free space to unpack this zip right now; nothing in it was filed | o servidor não tem espaço livre para abrir este zip agora; nada dele foi arquivado |
| `rcpt.fromZip` (new) | from {zip} | de {zip} |
| `rcpt.fromZipNeedsMonth` (new) | This receipt came from {zip}. Take it out of the zip and drop it here on its own to pick its month. | Este recibo veio de {zip}. Tire-o do zip e solte-o aqui sozinho para escolher o mês. |

## 3. Map the new reasons

In the reason map (`"no-readable-date": "rcpt.reason.noDate"`, ...), add:

- `"zip-unreadable": "rcpt.reason.zipUnreadable"`
- `"zip-too-many-files": "rcpt.reason.zipTooMany"`, rendered with `{limit}` from the row's `limit`, the same way `upload-cap` passes `limit`.
- `"zip-no-space": "rcpt.reason.zipNoSpace"`

Then change the fallback for a reason the map does not know: show the row's `reason_label` when the backend sends one, and only then the raw `reason` code. (`reason_label` is plain English prose the backend ships beside any new reason code, so a future code never shows as a raw token.)

## 4. Rows that came out of a zip

Each result row for a file that was inside a zip carries `from_zip` (the zip's file name); a file dropped on its own has no `from_zip`.

- On any row with `from_zip`, add a small muted `rcpt.fromZip` note after the file name ("from bundle.zip").
- A `needs_month` row with `from_zip`: do NOT show the month picker for it. The page holds the zip, not this file, so the picker's re-send of "just that file" cannot work (re-sending the whole zip with a month would file every other receipt in it a second time). Show `rcpt.fromZipNeedsMonth` in its place.
- A `needs_month` row WITHOUT `from_zip` keeps the month picker exactly as now.

## 5. Do not change

The month picker for `needs_month` rows without `from_zip`, the `upload-cap` sentence, the result summary counts, the rematch lines, and the month upload screens (their zip handling is separate and stays as it is).

## Checking it landed

Read only; do not drop anything on the live page.

1. On `/receipts`, open the file picker: `.zip` files are selectable (not greyed out).
2. The help line reads "Images and PDFs, one file per receipt, or a .zip of them." and in PT "... ou um .zip com eles."
````

## After publish

Bundle audit (`tools/lovable-bundle-audit.py`): `rcpt.reason.zipUnreadable`,
`rcpt.reason.zipTooMany`, `rcpt.reason.zipNoSpace`, `rcpt.fromZipNeedsMonth`,
`from_zip`, `zip-no-space` and `application/zip` present in
the Receipts chunk and i18n, and the filter regex carries `zip`. A live drop is
Criss's action; a TEST- drill, if one is run, drops a zip of two synthetic
receipts with the `month` override set to a scratch month, then deletes that
month in the same session.

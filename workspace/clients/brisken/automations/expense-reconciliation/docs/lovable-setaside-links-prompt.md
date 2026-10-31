# Lovable prompt: remove a set-aside file, show a mail's links, hide non-receipt files (items 261 + 262, notes #126, #127, #129, #130)

> **NOT PASTED.** The backend half ships in the same PR and is safe against a
> stale SPA (new route + parallel fields only): `POST
> /api/expense-batches/{id}/set-aside/dismiss`, `set_aside[].dismissed`, and
> `links[]` on `GET /api/inbound/{archive}/body`.
>
> Not in this prompt, on purpose: deleting a STATEMENT (note #127's own
> anchor) and recognising a mailed card statement (note #129's 1176 case).
> Both wait on backend work recorded under items 261/262.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`.

## Why

The operator, 2026-10-09 to 2026-10-29:

- *"need to improve room of action for user here, as there are also statement appearing here"* (October, "Set aside (not counted as expenses)", 6 files)
- *"Preciso ter a opcao de deletar documentos."*
- *"need to know if links to documents can be processed"*
- *"'not a receipt' so dont show receipt's file if there is no receipt"* (Receipt overview, `ATT00001.png`)

A set-aside file can only be restored as a receipt today; there is no way to take a logo or a stray PDF off the month. A mail whose receipt sits behind a link shows nothing that says so. The tool never opens links a mail contains (a mail must not decide what the tool fetches); it now lists them so a person can.

## Scope

`src/lib/api.ts`, `src/components/ExpensesReviewGrid.tsx` (`SetAsideStrip` only), `src/components/InboundLogScreen.tsx` (`BodyDialog` only), `src/components/ReceiptOverviewTable.tsx` (the File column only), `src/lib/i18n.tsx`.

## 1. Remove a set-aside file from the month (and put it back)

In `src/lib/api.ts`, beside `restoreSetAside`, add:

```ts
export interface DismissSetAsideResponse {
  ok: boolean; file: string; dismissed: boolean; n_set_aside: number;
  batch: ExpenseBatchDetail;
}
export function dismissSetAside(batchId: string, file: string, undo = false) {
  return apiFetch<DismissSetAsideResponse>(`/api/expense-batches/${batchId}/set-aside/dismiss`, {
    method: "POST",
    body: undo ? { file, undo: true } : { file },
  });
}
```

Add `dismissed?: boolean` to `SetAsideEntry`.

In `SetAsideStrip`:

1. Each row that is not restored gets a second button after "This is a receipt, restore": **Remove from this month** (`expx.setaside.dismiss`), outline style, same size. It calls `dismissSetAside(batchId, e.file)` and writes the returned `batch` into the `["expense-batch", batchId]` cache exactly as the restore mutation does (no refetch). No confirm dialog: it is reversible. Success toast `expx.setaside.dismissed` with an **Undo** action that calls `dismissSetAside(batchId, file, true)`.
2. Rows with `dismissed === true` leave their reason groups and the strip's count, and appear in one collapsed fold at the bottom of the strip, **Removed from this month ({n})** (`expx.setaside.removedGroup`), each with the file name, View (unchanged) and **Put back** (`expx.setaside.putBack`, calls `dismissSetAside(batchId, file, true)`). The fold is hidden when there are none.
3. Old payloads carry no `dismissed`; treat `undefined` as false.
4. A 400 with code `set_aside_dismissed` or `set_aside_already_restored` shows the existing `errorText(e, t)` toast.

## 2. Links in a held mail's body

`getInboundBody` now returns `links?: { url: string; host: string; text: string }[]`. In `BodyDialog`, under the body text:

- When `links` has entries: a small heading **Links in this email** (`inbound.body.links`) and a list, one line per link: the `text` when not empty, else the `host`, as an `<a href={url} target="_blank" rel="noopener noreferrer nofollow">`, with the `host` in muted text after it. Under the list, muted: `inbound.body.links.note`.
- When `text` is empty AND there are no links: the muted line `inbound.body.empty` instead of an empty box.

Do not fetch, preview or prefetch any of these URLs from the app.

## 3. Receipt overview: no file shown for what is not a receipt

In `ReceiptOverviewTable`'s File column, for a row with `status === "set_aside"`, show the muted text `rov.notAReceipt` instead of the file name (keep the file name in the `title` tooltip). Every other status renders exactly as today.

## 4. Strings (English and Portuguese, both in `i18n.tsx`)

| key | EN | PT |
|---|---|---|
| `expx.setaside.dismiss` | Remove from this month | Remover deste mês |
| `expx.setaside.dismissed` | Removed from this month. The file is kept. | Removido deste mês. O arquivo foi mantido. |
| `expx.setaside.removedGroup` | Removed from this month ({n}) | Removidos deste mês ({n}) |
| `expx.setaside.putBack` | Put back | Devolver |
| `inbound.body.links` | Links in this email | Links neste e-mail |
| `inbound.body.links.note` | The tool does not open links. If the receipt is behind one, open it, save the file and add it with Add receipts. | A ferramenta não abre links. Se o recibo estiver atrás de um, abra, salve o arquivo e adicione com Adicionar recibos. |
| `inbound.body.empty` | This email has no readable text. | Este e-mail não tem texto legível. |
| `rov.notAReceipt` | Not a receipt | Não é um recibo |

Reuse the app's existing Portuguese label for "Add receipts" in `inbound.body.links.note` if it differs from "Adicionar recibos".

## Checks

1. On October Expenses, each set-aside row shows "Remove from this month". Removing one moves it into "Removed from this month (1)", the strip count drops by one, and Undo or Put back returns it.
2. "This is a receipt, restore" still works on a row that was not removed.
3. On the Email intake page, opening the body of a mail with links lists them under "Links in this email"; a mail with no text and no links says "This email has no readable text."
4. On the Receipt overview, the `ATT00001.png` row's File cell reads "Not a receipt".
5. No request goes to any URL a mail contains.
````

# Lovable prompt: a count and a dialog in front of both bulk buttons (item 101)

> **NOT YET APPLIED.** Backend: `summary.n_confirm_matched` on
> `GET /api/runs/{id}`, and `POST /api/runs/{id}/decisions/confirm-matched`
> now answers `{ok, confirmed, remaining, skipped_rule, summary}` and confirms
> only the pairs the owner's rule lets through (item 101).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/SummaryBar.tsx` (the "Confirm all matched" button) and `src/components/RunWorkbench.tsx` (its mutation, and the "Reject N shown" button of the bulk bar), one optional field on the run summary type and three optional fields on the confirm-matched response type in `src/lib/api.ts`, and new strings in `src/lib/i18n.tsx`. Render defensively: a summary or a response without the new fields renders as today, with no crash.

## Why

"Confirm all matched" confirmed every matched row in one click, with no dialog. The backend now confirms only exact pairs where the vendor agrees and no other charge claims the receipt, which is the rule the owner set for pairs that need no closer look, and it says up front how many that is. The button should show that number, refuse to do nothing, and ask once before it writes. "Reject N shown" rejects every open row in the current view the same way and can only be undone one row at a time, so it asks once too.

## 1. Types (`src/lib/api.ts`)

On the run summary type, add `n_confirm_matched?: number;`.

On the response type of the call that posts to `/api/runs/{id}/decisions/confirm-matched`, add `remaining?: number; skipped_rule?: number;` next to the existing `confirmed`.

## 2. "Confirm all matched" (`SummaryBar.tsx`, mutation in `RunWorkbench.tsx`)

Let `n = summary.n_confirm_matched` (a number, or `undefined` when absent).

- **Count.** When `n` is a number, render it in a small badge inside the button, after the existing label: `<Badge variant="secondary" className="ml-2 h-5 px-1.5 text-xs">{n}</Badge>` (`@/components/ui/badge`). No badge when `n` is `undefined`.
- **Disabled at 0.** When `n === 0`, the button is `disabled`. Wrap it in a `span` with `tabIndex={0}` inside the existing `Tooltip` primitive (`@/components/ui/tooltip`) so the tooltip still opens on a disabled button, content `t("sum.confirmMatched.none.tip")`.
- **Dialog.** A click no longer calls the mutation directly. It opens an `AlertDialog` (`@/components/ui/alert-dialog`):
  - title: `t("sum.confirmMatched.dialog.title.one")` when `n === 1`, `t("sum.confirmMatched.dialog.title.many", { n })` when `n > 1`, `t("sum.confirmMatched.dialog.title.unknown")` when `n` is `undefined`;
  - body: `t("sum.confirmMatched.dialog.body")`, then on its own line `t("sum.confirmMatched.dialog.undo")`;
  - `AlertDialogCancel`: `t("sum.confirmMatched.dialog.cancel")`;
  - `AlertDialogAction`: `t("sum.confirmMatched.dialog.confirm", { n })` when `n` is a number, `t("sum.confirmMatched.dialog.confirmUnknown")` otherwise. It calls the existing confirm-matched mutation; disable it while the mutation is pending.
- **Toast on success.** Replace the success toast with `t("sum.confirmMatched.done", { confirmed: res.confirmed })`. When `res.skipped_rule` is a number above 0, append a space and `t("sum.confirmMatched.left", { n: res.skipped_rule })`. When `res.remaining` is a number above 0, append a space and `t("sum.confirmMatched.remaining", { n: res.remaining })`. Keep today's `onError` and today's query invalidation, so the badge refreshes from the new summary.

## 3. "Reject N shown" (the bulk bar in `RunWorkbench.tsx`)

The button keeps its label, its `N` and its targets (`bulkTargets`, rejectable rows). A click no longer calls the bulk mutation directly. It opens an `AlertDialog`:

- title: `t("wb.bulkReject.dialog.title.one")` when N is 1, `t("wb.bulkReject.dialog.title.many", { n: N })` otherwise;
- body: `t("wb.bulkReject.dialog.body")`;
- `AlertDialogCancel`: `t("wb.bulkReject.dialog.cancel")`;
- `AlertDialogAction`: `t("wb.bulkReject.dialog.confirm", { n: N })`, calling exactly today's bulk reject with the same ids; disable it while pending.

Freeze the ids when the dialog opens, so a filter change behind the dialog cannot change what is rejected.

## 4. Do not change

"Confirm N shown", every row's Reject / Confirm match / undo buttons, Downloads, Commit learnings, Publish, the decision calls themselves, and every count's meaning.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `sum.confirmMatched.none.tip` | No pair is clean enough to confirm in one click. Decide the open rows one at a time. | Nenhum par está limpo o bastante para confirmar com um clique. Decida as linhas abertas uma a uma. |
| `sum.confirmMatched.dialog.title.one` | Confirm 1 matched pair? | Confirmar 1 par conciliado? |
| `sum.confirmMatched.dialog.title.many` | Confirm {n} matched pairs? | Confirmar {n} pares conciliados? |
| `sum.confirmMatched.dialog.title.unknown` | Confirm the matched pairs? | Confirmar os pares conciliados? |
| `sum.confirmMatched.dialog.body` | Only exact pairs where the vendor agrees and no other charge claims the receipt. Everything else stays for you to decide. | Só pares exatos em que o fornecedor confere e nenhuma outra cobrança reivindica o recibo. Todo o resto fica para você decidir. |
| `sum.confirmMatched.dialog.undo` | Each one can be undone on its own row. | Cada um pode ser desfeito na própria linha. |
| `sum.confirmMatched.dialog.cancel` | Cancel | Cancelar |
| `sum.confirmMatched.dialog.confirm` | Confirm {n} | Confirmar {n} |
| `sum.confirmMatched.dialog.confirmUnknown` | Confirm | Confirmar |
| `sum.confirmMatched.done` | {confirmed} confirmed. | {confirmed} confirmados. |
| `sum.confirmMatched.left` | {n} left for you to decide. | {n} ficam para você decidir. |
| `sum.confirmMatched.remaining` | {n} more can be confirmed: press again. | Mais {n} podem ser confirmados: clique de novo. |
| `wb.bulkReject.dialog.title.one` | Reject 1 shown row? | Rejeitar 1 linha exibida? |
| `wb.bulkReject.dialog.title.many` | Reject {n} shown rows? | Rejeitar {n} linhas exibidas? |
| `wb.bulkReject.dialog.body` | Their receipts become free for other charges. Each row can be undone, one at a time. | Os recibos ficam livres para outras cobranças. Cada linha pode ser desfeita, uma de cada vez. |
| `wb.bulkReject.dialog.cancel` | Cancel | Cancelar |
| `wb.bulkReject.dialog.confirm` | Reject {n} | Rejeitar {n} |

## Checking it landed

Open the dialogs and press **Cancel** every time: these are Criss's live months, and confirming or rejecting writes her decisions.

1. August 2026 workbench (`/runs/074a7b8905d7`): "Confirm all matched" shows the live count from `summary.n_confirm_matched` (0 or 1 today). At 1, a click opens "Confirm 1 matched pair?" with the rule sentence and the undo line; Cancel closes it and nothing changes. At 0, the button is disabled and hovering it shows "No pair is clean enough to confirm in one click."
2. July 2026 workbench (`/runs/50622baec444`): the badge reads 0, the button is disabled, and the tooltip shows.
3. On a view with open rows, "Reject N shown" opens "Reject N shown rows?" naming the same N as the button; Cancel closes it and no row changes.
4. PT: the dialog reads "Só pares exatos em que o fornecedor confere e nenhuma outra cobrança reivindica o recibo."
````

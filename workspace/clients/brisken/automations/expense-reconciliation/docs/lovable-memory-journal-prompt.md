# Lovable prompt: say what a memory save will do, and let it be taken back

Paste into Lovable. Backend is live; every field below already exists on the
API. Two screens change: the month's Expenses page (the "Save corrections to
memory" button) and the Memory page (a new section).

## 1. The button says what it will save, before it saves

On the Expenses page, "Save corrections to memory" currently saves
immediately. Make it open a small dialog first.

When the button is pressed, call `GET /api/runs/{runId}/memory-plan` and show
the reply in the dialog:

- **Title:** "Save this month's corrections" / PT "Salvar as correções deste
  mês".
- **If `writes` is empty:** one line, "There is nothing new to save." / "Não
  há nada novo para salvar.", and the only button is Close. Do not call the
  save.
- **Otherwise** a compact table of `writes[]`, one row each:
  - column 1, what it is: map `table` to plain words.
    `merchant_category` → "Category" / "Categoria";
    `merchant_entity` → "Company" / "Empresa";
    `field_correction` → "Correction" / "Correção";
    `vendor_alias` → "Vendor name on the statement" / "Nome do fornecedor no
    extrato"; `merchant_fx` → "Exchange rate" / "Taxa de câmbio".
  - column 2, who it is about: `key.vendor_norm` (or `key.stmt_vendor_norm`
    for an alias), plus `key.legal_entity_id` beside it when it is not empty,
    and `key.field` for a correction.
  - column 3, `value`.
- **Below the table,** when `registry` is non-empty: "This also updates N
  merchants in the merchant list." / "Isto também atualiza N comerciantes na
  lista de comerciantes.", N = the number of keys in `registry`. Link the
  words "merchant list" to `/settings` (Merchants tab).
- **One sentence under that, always:** "Saved rules live on the Memory page,
  where you can edit or undo them." / "As regras salvas ficam na página
  Memória, onde você pode editá-las ou desfazê-las." Link "Memory page" to
  `/memory`.
- Buttons: Cancel, and "Save N rules" / "Salvar N regras" where N is
  `writes.length`. Save calls the existing
  `POST /api/runs/{runId}/commit-memory` unchanged.
- The success toast keeps its current text and gains, on a second line,
  "Undo on the Memory page" / "Desfazer na página Memória" linking `/memory`.

The plan call is read-only and safe to make on every open.

## 2. The Memory page gains a "Saves" section

New section at the TOP of `/memory`, above the existing Categories table.
Heading "Saves" / "Salvamentos", subtitle "Every time this month's
corrections were saved, and what each one taught." / "Cada vez que as
correções de um mês foram salvas, e o que cada uma ensinou."

Data: `GET /api/memory/commits`. Render `commits[]` newest first, one row
each:

| Column | From | Notes |
|---|---|---|
| Month | `label` | falls back to `run_id` when empty |
| When | `committed_at` | date and time, the page's existing date format |
| How | `trigger` | `publish` → "On publish" / "Ao publicar"; `button` → "Saved by hand" / "Salvo manualmente" |
| Taught | `learned` | one line, only the non-zero counts, e.g. "2 corrections, 1 category" |
| Rows | `n_rows` | plain number |
| | | the action cell, below |

The action cell: for the FIRST row that has an empty `reverted_at`, an
"Undo" / "Desfazer" button. Every other row shows either "Undone
{reverted_at}" / "Desfeito {reverted_at}" when it carries one, or nothing at
all. Only the newest un-undone save is undoable and the backend refuses the
rest, so do not render a button that will 409.

Undo calls `POST /api/memory/commits/{id}/undo`. Confirm first with
`window.confirm`, the way the existing delete does: "Undo this save? The
rules it taught go back to what they were before." / "Desfazer este
salvamento? As regras que ele ensinou voltam ao que eram antes."

On success, refetch the memory view and toast "Save undone: N rules
restored." / "Salvamento desfeito: N regras restauradas." using
`rows_restored`. On a 409 show the reply's `error` text directly; it is
already written for a reader in both languages by the backend's code table.

Expanding a row (the existing expander pattern) lists its `rows[]`: the same
plain-words table names as section 1, the key, and where it is managed, from
`surface` ("memory" → "Memory page" / "Página Memória").

## 3. What NOT to change

- Do not add an automatic save anywhere. Publish already saves; the button
  still saves; nothing else should.
- Do not hide the Categories, Aliases or FX tables; the Saves section sits
  above them.
- Do not compute what a save will do in the front end. The plan route is the
  only source; a second implementation would drift from the save.

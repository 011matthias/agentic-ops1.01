# Lovable prompt — Memory page: edit, delete, validate, guarded reset

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`.

Context: the Memory page's learned-categories table (103 entries) becomes
adjustable and reviewable. IMPORTANT contract note: `GET /api/memory` rows
name the entity `"entity"`, but every write endpoint below requires the key
`"legal_entity_id"` — map it when building request bodies.

## 1. Edit a learned category row inline

Categories rows now carry `validated` (date or "") and `validated_by`.
Add per-row Edit: category (dropdown; on a 400 the error body carries the
allowed list in `"categories"`) and Zoho account (free text).

`PUT /api/memory/categories` with:

```json
{ "legal_entity_id": "<row.entity>", "vendor": "<row.vendor>",
  "category": "...", "zoho_account": "..." }
```

- Send `zoho_account` ONLY when the user edited that field. Omitting the
  key preserves the stored account; sending `""` explicitly clears it.
- Editing a validated row clears its validated stamp on value change (by
  design: validation certifies what the human saw). After a successful
  edit, offer an inline "Validate" affordance so the reviewer can
  re-stamp in one tap.
- 200 echoes the stored row; refresh the table row from it.

## 2. Delete one learned row

`DELETE /api/memory/categories` with `{ "legal_entity_id", "vendor" }`
(JSON body on DELETE). Confirm first (EN "Remove this learned category?
Aliases and FX for the vendor stay." / PT "Remover esta categoria
aprendida? Apelidos e câmbio do fornecedor permanecem."). 404 = already
gone; just refresh.

## 3. Validate (the review-the-103 workflow)

- Per-row checkmark and a "Validate selected" bulk action:
  `POST /api/memory/categories/validate` with
  `{ "rows": [ { "legal_entity_id", "vendor" }, ... ] }` →
  `{ "ok": true, "validated": N, "requested": M }`.
- Validated rows show a check + the date (tooltip: `validated_by`).
- Add a filter toggle EN "Needs review" / PT "A revisar" that calls
  `GET /api/memory?unvalidated=1`. Note: `counts`/`total` in the reply
  stay WHOLE-STORE numbers even when filtered — badge counts should use
  `categories.length` for the filtered view.

## 4. Reset now requires confirmation (REQUIRED update — old button is broken)

`POST /api/memory/reset` WITHOUT `{"confirm": true}` no longer deletes
anything: it answers HTTP 200 with
`{ "ok": false, "confirm_required": true, "preview": {table: n, ...} }`.
The existing Reset button MUST be updated or it becomes a silent no-op
that looks successful:

- First call without confirm; show the preview counts in a dialog (EN
  "This permanently deletes N learned entries." / PT "Isto exclui
  permanentemente N entradas aprendidas.") with scope echoed.
- On user confirmation, call again with `"confirm": true` (plus the same
  `table` / `legal_entity_id` scope if one was chosen). Only an
  `"ok": true` reply means anything was deleted — never treat
  `confirm_required` as success.

Out of scope: aliases/FX/entity tables stay read-only this round (forget
and reset still cover them).

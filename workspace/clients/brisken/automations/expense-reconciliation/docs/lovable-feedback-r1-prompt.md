# Lovable prompt — expense-recon reviewer feedback, round 1

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`. Change only the three areas below; leave everything else
(reconciliation workbench, publish flow, upload) untouched.

The backend for these three is already deployed, so the API fields named below
are live now.

---

## 1. Legal entity: dropdown instead of free text, and allow blank

Today the legal entity is a free-text input. Replace it with a **select
dropdown** in two places:

**a) The "Start a new month" / create form.**
- Fetch the options from `GET /api/settings` → the `entity_options` array
  (e.g. `["Cloud Services", "Corporate Services"]`). It is now populated from
  the real entities; if it ever comes back empty, fall back to a free-text
  input so the form still works.
- The first option is a blank choice labelled **"Leave blank (resolve from
  card)"**. Submitting blank is valid and expected: the backend resolves the
  entity from the card on the statement. Do not require a selection.
- Submit the chosen value in the same `legal_entity` form field as today
  (empty string when blank).

**b) The per-expense entity picker on the expense grid.**
- The expense-batch response (`GET /api/expense-batches/{id}`) already returns
  an `entity_options` array. Use it as the dropdown for each row's entity,
  with the same blank option.
- Keep persisting a per-expense change with the existing
  `PUT /api/runs/{run_id}/expenses/{document_id}/entity` call (body
  `{ "legal_entity": "<value>" }`).

Do NOT hardcode the entity names; always read them from the API so new
entities appear automatically.

---

## 2. "Default currency": demote it, never force a currency

The reviewer flagged that a run-level "default currency" does not make sense:
currency belongs to each receipt.

- On the create form, **remove "default currency" as a prominent field.** If
  you keep it at all, move it under an "Advanced" disclosure and relabel it
  exactly: **"Fallback currency (only used when a receipt's currency cannot be
  read)"**, defaulting to **blank**.
- Never pre-fill or default it to USD or any currency.
- The field still posts to the same `default_currency` param when set; when
  blank, omit it. The backend already treats it as a last-resort only.

---

## 3. Category is a suggestion, not a lock

The reviewer needs the auto-assigned category to be easy to override; the same
vendor can legitimately land in different categories.

- On the expense grid, the category cell must always be an **editable
  dropdown** built from the `category_options` array in the batch response
  (the fixed 8 categories). Never render the category as read-only text.
- Show the provenance (`posting_category.source` = `registry` / `learned` /
  `llm` / `override`) only as a small, muted hint chip next to the dropdown,
  so the reviewer can see where the suggestion came from. The chip must not
  look like a lock or prevent editing.
- A reviewer change persists via the existing per-expense category edit call
  (unchanged).

---

## Out of scope for this prompt (backend work, do not attempt in Lovable)

These came up in the same feedback but need backend changes first, so leave
them for now:
- Reading the legal entity from a **column in the uploaded file** (per-row
  entities).
- **Deriving currency from vendor/location** when the receipt is ambiguous.
- Making one vendor map to **different categories by card / entity / receipt
  detail** (contextual categorization).

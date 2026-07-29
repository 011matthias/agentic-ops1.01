# Lovable prompt — Merchants registry editor + grid vendor hint

Paste into Lovable for `brisken-expense-recon-ui`. The Python FastAPI app is
the backend and the source of truth; **no Supabase**, call the external API.
All the fields below are already server-computed and shipped — the UI only
renders and edits them.

---

## 1. New settings section: "Merchants"

Add a **Merchants** editor to the Settings screen, styled exactly like the
existing **Card Accounts** / **Legal Entities** editors (same table, same
add / edit / remove affordances). It is backed by the same settings endpoint.

**Load:** `GET /api/settings` (bearer token). The response now includes:

```json
{
  "merchants": {
    "Uber": {
      "aliases": ["UBER *EATS", "UBER BV"],
      "category": "Travel & Transport",
      "zoho_account": "E100010 - Travel Expense"
    }
  },
  "categories": ["Travel & Transport", "Meals & Entertainment", ...]  // the fixed 8, read-only
}
```

**Table columns** (one row per merchant):

| Column | Field | Control |
|---|---|---|
| Canonical name | the object key | text input (this is the display vendor) |
| Aliases | `aliases` (string[]) | tag / chip input (add / remove strings) |
| Category | `category` (string or null) | dropdown of `categories` from the same response, plus a blank "— (let the tool decide) —" option |
| Zoho account | `zoho_account` (string or null) | text input |

**Save:** `PUT /api/settings` with `{"merchants": { ...whole map... }}`. This
is a **whole-map replace** (identical to `entities` / `card_accounts`):
send every merchant you want to keep; omitting one deletes it; an empty
`{}` clears the registry. Rules the server enforces (surface the 400 body's
`error` string inline on failure):

- a blank canonical name is dropped silently
- `aliases` are trimmed and de-duplicated server-side
- `category`, when set, must be one of the 8 `categories` (else HTTP 400)
- each merchant value must be an object (else HTTP 400)

Do not send the `categories` key back — it is read-only and ignored.

---

## 2. Grid: canonical vendor + a small provenance hint

The expense-grid vendor field changed shape. Each row's `vendor` is now an
**object**, not a string:

```json
"vendor": { "display": "Acme", "raw": "ACME COMERCIO LTDA", "source": "registry" }
```

- Render **`vendor.display`** as the vendor (was the bare string before).
- Keep the vendor cell **editable** exactly as today; the edit endpoint is
  unchanged: `PUT /api/runs/{runId}/expenses/{documentId}` with
  `{"field": "vendor", "value": "<new name>"}`. Editing feeds the
  self-improving registry (the raw name becomes an alias of the name you
  type), so no extra wiring is needed.
- Show a small muted **hint chip** next to the vendor driven by
  `vendor.source`:
  - `registry` → chip "registry" (this brand is in the Merchants registry)
  - `learned` → chip "learned" (auto-learned from a past correction)
  - `override` → chip "edited" (a reviewer typed this name)
  - `extraction` → no chip (as OCR read it)
- On hover / tooltip, show `vendor.raw` ("as printed: {raw}") so the reviewer
  can see the original OCR text behind a canonicalized name.

## 3. Grid: category provenance hint (optional, same pattern)

`posting_category.source` is now a coarse token in the same vocabulary:
`registry | learned | llm | override` (and `review` for uncategorized). If
you already show a category source, map these to the same chip styles as the
vendor hint (registry / learned as "trusted", llm as neutral, review as
"needs a look"). `posting_category.category` and `.zoho_account` are
unchanged.

---

Nothing else in the grid or settings contract changed. Ship the Merchants
editor and the vendor hint; the backend already canonicalizes, categorizes,
and learns from edits.

# Lovable prompt: Settings > Cards (the card registry)

Paste into Lovable for `brisken-expense-review`. Backend is LIVE (Cards R1):
the API below is deployed on `brisken-expense-recon.fly.dev`.

---

## What changes

The Settings screen's two card tables ("Card to legal entity" and "Card to
Zoho account") are replaced by ONE "Cards" section. A card is now a
first-class identity: it has a label, the digit numbers that identify it,
optional word aliases, its legal entity, an OPTIONAL Zoho account, and a
currency. Zoho is an attribute of a card, not its identity.

## API contract

- `GET /api/cards` -> `{"cards": [...], "entity_options": [...]}`.
  Each card: `{key, label, label_pt, digits: ["2838","1672"], aliases:
  ["CorpServ"], entity, zoho_account (string or null), currency, active,
  source: "settings"|"legacy"|"preset"}`.
  `GET /api/settings` also carries the same list as `cards_effective`.
- `PUT /api/settings` with `{"cards": {<key>: {label, digits, aliases,
  entity, zoho_account, currency, active}}}` — whole-map replace, same
  contract as `merchants`. Malformed digits (non-numeric, wrong length)
  answer 400 with `{"error": ...}`; show the message as a toast.

## The Cards section

Table columns:

| Column | Notes |
|---|---|
| Card | `label` (fall back to `key`); sub-line: `key`, muted |
| Numbers | `digits` as chips; editable list. Help text: "every number that identifies this card: the statement's card number and the last 4 digits printed on the plastic — they can differ" |
| Aliases | `aliases` as chips; editable list. Help: "distinctive words that name this card on receipts (e.g. CorpServ). Never generic words like Visa" |
| Legal entity | dropdown from `entity_options`, free text allowed |
| Zoho account (optional) | text input. Help: "only used by the Zoho export; leave empty if this card does not post to a Zoho bank account" |
| Currency | short text (e.g. USD) |
| Active | toggle; inactive cards never auto-resolve |

Row badge by `source`: none for "settings"; "from legacy maps" for
"legacy"; "from provisioning file" for "preset". Editing a legacy/preset
row PROMOTES it: the UI writes a `cards` entry under the row's `key`
carrying every composed field shown, then the edit. Saving sends the WHOLE
cards map (all settings rows), like the merchants editor.

"Add card" button: new row with a key generated from the label
(lowercase, dashes; e.g. "corporate-chase"), at least one digit required
in the form (the backend allows none, but a card with no digits and no
aliases can never auto-resolve — warn inline, do not block).

## Language (EN / PT)

Section title "Cards" / "Cartões". Help texts above need PT twins.
"Zoho account (optional)" / "Conta Zoho (opcional)". Keep receipt-side
data untranslated as always.

## Do not

- Do not remove the legacy tables' DATA path: the backend still reads the
  old maps (they show up here as `source: "legacy"` rows). Just remove the
  two old table UIs.
- Do not invent a per-card delete for legacy rows (they come from the
  legacy maps; deleting means editing those maps — out of scope this
  round; hide delete on `source != "settings"` rows).
- No em-dashes in UI copy.

## Verify after publish

Settings shows the Cards section; the seeded legacy rows appear with the
"from legacy maps" badge; adding digits "1672" to the corporate card and
saving round-trips (GET shows both digits).

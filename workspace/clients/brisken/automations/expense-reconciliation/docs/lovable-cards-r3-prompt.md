# Lovable prompt: entity-less batches + card review (Cards R3)

Paste into Lovable for `brisken-expense-review`. Backend is LIVE (Cards
R3) on `brisken-expense-recon.fly.dev`. Builds on the Cards editor from
`lovable-cards-prompt.md` (Settings > Cards).

---

## What changes

Starting a month no longer asks for a legal entity. The tool takes
receipts from ANY entity; each expense's entity now resolves from the
card that paid it. The batch page gains a card-review strip: unresolved
payment hints are laid out, the user assigns each to a card once, the
tool remembers. Nothing ever blocks on an unresolved card or entity; the
export ships with a visible placeholder and a later re-export folds the
assignment in.

## 1. "Start a new month" form

The legal-entity dropdown becomes OPTIONAL, labeled "Legal entity
(optional; leave empty when receipts mix companies)". Empty is the new
normal path; keep the dropdown for the single-entity case.

## 2. Expense grid: entity + card per row

Each row now carries:

- `legal_entity_id` — the RESOLVED entity (may be "").
- `entity_source` — one of `override` | `card` | `batch` | `learned` |
  `none`. Render as a muted sub-label under the entity value: "edited" /
  "from card" / "batch default" / "learned" / nothing for `none`.
- `payment_hint` — the raw card/tender text read off the receipt.
- `card` — `{key, label, entity, hint}` or `null`. When present, show a
  small chip with the card `label` in the row (tooltip: the hint).
- `review.reason_code` can now be `"needs_entity"` (state stays
  `check`): EN "No legal entity yet — assign the paying card or set the
  entity." / PT "Sem entidade legal — atribua o cartão pagador ou defina
  a entidade."

The per-row entity edit dialog is unchanged (`PUT
/api/runs/{id}/expenses/{doc}/entity`); an edit shows as
`entity_source: "override"`.

## 3. The card-review strip (batch page)

`GET /api/expense-batches/{id}` now returns `card_review`:

```json
{
  "unresolved_hints": [
    {"hint": "Visa ...1672", "n_rows": 4, "documents": [...],
     "generic": false}
  ],
  "resolved": [
    {"card": {"key": "corp-2838", "label": "Corporate card (Chase)",
      "entity": "Corporate Services", "zoho_account": "..."},
     "n_rows": 6, "hints": ["Visa ...1672", "2838"]}
  ],
  "n_resolved_rows": 6, "n_unresolved_rows": 5, "n_no_hint": 2,
  "n_needs_entity": 5
}
```

Render a strip above the grid when `unresolved_hints` is non-empty
(amber, like the set-aside strip): "N receipts name a card the tool does
not know yet." One line per hint: the hint text, `n_rows`, and an
"Assign to card…" control (dropdown of cards from `GET /api/cards` +
"New card…" opening the Settings-Cards add form inline). For
`generic: true` hints (e.g. "Visa", "Cartão de crédito"), add the note:
EN "Generic tender — applies to this month only, the tool will not
remember it." / PT "Meio de pagamento genérico — vale só para este mês."

Below the strip, a muted resolved summary line: "N receipts matched to
M cards." `summary.n_needs_entity` also becomes a stat tile ("Missing
entity" / "Sem entidade") when > 0.

## 4. Assigning

`POST /api/expense-batches/{id}/cards` with

```json
{"assignments": [{"hint": "Visa ...1672", "card": "corp-2838"}],
 "new_cards": {"my-card": {"label": "...", "digits": ["1234"],
   "entity": "..."}},
 "learn": true}
```

- `learn` is a checkbox in the assign control, default ON, labeled
  "Remember for future months" / "Lembrar para os próximos meses".
- Response: `{ok, results: [{hint, card, n_rows, learned, note?}],
  batch: <refreshed batch view>}` — re-render the grid + strip from
  `batch`. When `learned` is false and `note` present, show the note as
  an info toast (that is the generic-tender case).
- Errors are 400 `{"error": ...}` — toast.

## 5. Refresh master data (snapshot trap)

Batches snapshot the card registry at creation; a Settings > Cards edit
does NOT reach existing months. Add a "Refresh master data" action in
the batch page's overflow menu: `POST
/api/expense-batches/{id}/refresh-master-data` -> `{ok, changes: [...],
batch}`. Re-render from `batch`; when `changes` is empty, toast "Already
current" / "Já atualizado"; else "Master data refreshed" and list the
changed fields. Explain in the menu item's tooltip: EN "Apply the
current Settings (cards, accounts) to this month." / PT "Aplicar as
configurações atuais (cartões, contas) a este mês."

## 6. Export note

The Zoho CSV writes "(entity - assign)" in Legal Entity for unresolved
rows (mirrors "(paid-through - assign)"). Where the export dialog lists
caveats, mention: assignments made after an export are picked up by
simply downloading the export again.

## Do not

- Do not block the export button on unresolved cards/entities (owner
  ruling: placeholders, never block).
- Do not auto-assign generic tender hints client-side; the backend
  refuses to learn them by design.
- Do not translate receipt-side data (hints render verbatim).

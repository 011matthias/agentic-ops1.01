# Lovable prompt: person on the card, private-expense suggestions, and the server-grouped card strip

**NOT APPLIED. Drafted 2026-09-06 (R1: backend items 35 + 40 + 41). Gate:
paste only after the R1 backend deploys; verify by field name in the
published bundle (see "Verify after publish"). Person DATA ENTRY waits for
that verification: the settings cards map is whole-map replace, so a save
from a bundle that does not read and write `person` silently erases every
stored person.**

Paste into `brisken-expense-review` (production
`brisken-reconcile-dash.lovable.app`). One prompt, four surfaces: the
card-review strip (now grouped SERVER-side), the private-expense confirm
flow, the person column in Settings > Cards, and person in the Assign
control. Touches `CardReviewStrip` + the row grid in
`src/components/ExpensesReviewGrid.tsx`, the Cards editor in Settings, and
i18n (`src/lib/i18n.tsx`; every new string ships in EN AND PT).

## Why

Owner directives 2026-09-06: every expense must be attributed to a person,
THROUGH THE CARD ("each card is attributed to a name and therefore every
expense can be attributed to a person. Even the ones injected via email"),
and a payment method the system does not know "must be suggested to the
user as private expenses that will require reimbursement to the person who
expensed". The backend now ships both, plus the canonical card grouping
the 2026-08-28 strip prompt approximated client-side.

## 1. The strip renders the server's groups (replaces client-side grouping)

`card_review.unresolved_hints[]` entries are now grouped by the backend:
one entry per CARD NUMBER, with two new fields beside the existing ones:

- `digits`: string or null. The printed card run, leading zero kept
  ("0340"). Null = no card number readable in the hint.
- `spellings`: string[] — every member spelling, most frequent first.
  `hint` now carries the most frequent spelling; `n_rows` and `documents`
  cover the whole group.
- `suggested_private`: boolean (see section 2).
- `ambiguous` unchanged: two registered cards claim the hint.

Remove the client-side grouping regex from the 2026-08-28 prompt and
render the server's partition instead:

- Entries with `digits` non-null: "Card ending {digits}" / PT "Cartão
  final {digits}", "{n_rows} receipts, {spellings.length} spellings" /
  PT "{n_rows} recibos, {grafias}". "Show spellings" toggle lists
  `spellings[]` verbatim. ONE Assign per group: submit `assignments` =
  one `{hint, card}` entry PER member of `spellings[]` in a single
  `assignBatchCards` call (unchanged endpoint).
- Entries with `digits: null` and `generic: true`: the "No card number
  on the receipt" sub-strip, keeping the this-month-only note.
- Entries with `digits: null`, `generic` false: ungrouped single rows as
  today (assigning them CAN be remembered; no this-month-only note).

Defensive rendering per the api-contract rules: tolerate absent
`spellings` (fall back to `[hint]`), absent `digits` (treat as null),
absent `suggested_private` (false). A payload from an older backend must
render exactly as today.

## 2. Suggested private expenses (new review state + confirm flow)

New row review `reason_code: "suggested_private"` (state `check`), new
row fields `suggested_private` (bool), `private` (bool), `reimburse_to`
(string), `reimburse_to_prefill` (string), `person`, `person_source`
(`"card"` | `"private"` | `"none"`), and new counts
`summary.n_suggested_private`, `summary.n_private`,
`summary.n_needs_person` (also on `card_review`).

- Rows with `suggested_private: true` get a chip: EN "Suggested private
  expense" / PT "Sugerido como despesa particular", and the review cell
  falls back to the backend `reason` prose for unknown codes as always.
- Row action (menu + review cell button): EN "Confirm private expense" /
  PT "Confirmar despesa particular". Dialog copy: EN "No company card
  matches this payment method. If someone paid out of pocket, name who
  gets reimbursed." One text input "Reimburse" pre-filled from
  `reimburse_to_prefill` WHEN non-empty, labelled as a claim: EN helper
  "Pre-filled from the mail sender; change it if someone else paid." /
  PT mirror. Submit: `POST /api/runs/{batchId}/expenses/{documentId}/private`
  with `{"private": true, "reimburse_to": "<name>"}`. The 400 for a blank
  name renders inline.
- A confirmed row shows a "Private — reimburse {reimburse_to}" / PT
  "Particular — reembolsar {reimburse_to}" badge instead of the entity
  cell's MISSING ENTITY treatment, and its action flips to EN "Not
  private (undo)" / PT "Não é particular (desfazer)" →
  `{"private": false}`.
- In the sub-strip (section 1), entries with `suggested_private: true`
  add one line: EN "No card number readable; suggested as a private
  expense." / PT mirror. Assigning the entry to a card clears the
  suggestion; nothing else changes in the strip's controls.
- Stat row: add a "PRIVATE" tile only when `n_private > 0`; show
  `n_suggested_private` as a sub-count on the existing review tile
  ("{n} suggested private") rather than a new permanent tile.

## 3. Settings > Cards: the person column

The card editor gains a "Person" / PT "Pessoa" text field per card,
reading and writing the `person` key on each entry of the `cards` map
(same `PUT /api/settings` whole-map submit as every other card field;
`GET /api/cards` now returns `cards[].person`). Helper text under the
field: EN "Who this card's expenses belong to. Every expense on this card
is attributed to this person." / PT mirror. Empty stays allowed — the
backend then counts those rows under NEEDS PERSON.

CRITICAL: the editor must ROUND-TRIP `person` — include it in the map it
submits even for cards the user did not touch. The map replaces the
stored one wholesale; dropping the key erases stored persons.

## 4. Assign-with-person

In the strip's Assign control, the "New card..." creation form gains the
same "Person" field, submitted as `person` inside the `new_cards` entry.
Existing-card assignment does NOT ask for a person (the card already has
one or gets one in Settings).

## 5. Row + tile copy for needs_person

New review `reason_code: "needs_person"` (state `check`): localize EN
"No person owns this expense yet. Add a person to its paying card in
Settings > Cards." / PT mirror; fall back to backend `reason` for
unknown codes. Beside the MISSING ENTITY tile, render a NEEDS PERSON
tile from `summary.n_needs_person` when non-zero, linking to Settings >
Cards. Rows may also render `person` in the grid's card/entity cell
("{card label} · {person}") when present.

## Do not

- Do not infer a person from the mail sender anywhere outside the
  `reimburse_to_prefill` input described above. `submitted_by` stays a
  provenance display only.
- Do not re-implement grouping, genericity, or suggestion logic
  client-side; render the server's fields.
- Do not drop or rename any existing key in the cards map on save.
- Patch EN and PT in the same edit. No em-dashes in UI copy.

## Verify after publish (field-name grep, then drive)

1. Bundle grep (decisive): the settings chunk reads AND writes `person`;
   the grid chunk reads `suggested_private`, `reimburse_to_prefill`,
   `n_needs_person`, and `spellings`.
2. Drive: a batch with two spellings of one unregistered card shows ONE
   "Card ending" row; expanding lists both spellings; Assign submits
   both in one request (network tab: `assignments` length 2).
3. A row with an unknown payment method shows the suggested-private chip;
   confirming with a name turns it into "Private — reimburse {name}" and
   the MISSING ENTITY count does not include it; undo brings the
   suggestion back.
4. Enter a person on a card in Settings, save, re-open: the person
   SURVIVES a second unrelated save (the round-trip check), and rows on
   that card show the person after "Refresh master data".
5. Switch to PT and re-check every new string.

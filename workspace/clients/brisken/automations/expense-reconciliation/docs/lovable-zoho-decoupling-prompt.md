# Lovable prompt: Zoho decoupling copy + the two account dropdowns

Paste into Lovable for `brisken-expense-review`. Backend is LIVE (Cards
R2). Answers the 2026-08-21 feedback notes: "cards do not need zoho
accounts", "importance of zoho account is still not evident", and the two
"what is this option for / worth keeping?" dropdown notes.

## 1. Merchants editor (Settings > Merchants)

- Rename the "Zoho account" column to **"Zoho GL account (optional)"**
  (PT: "Conta Zoho (opcional)"). Help text under the header: "only used
  by the Zoho export; overrides the chart-derived account when a
  category is set" / PT twin.
- `GET /api/settings` now returns `merchants_inert`: a list of merchant
  names whose Zoho account is set but whose category is empty. Such an
  entry does nothing (the backend skips accounts without a category).
  Render an inline hint on those rows: "set a category for this account
  to take effect" / "defina uma categoria para esta conta ter efeito".

## 2. The expense grid's account dropdown (feedback note: "what is this
option for? is it useful? if not remove.")

The second select in the Category / Account cell picks the **Zoho GL
account** the expense posts to in the Zoho export. Two changes:

- When `account_options` is empty (no chart loaded), HIDE the account
  control entirely. Today it degrades to a bare free-text box, which is
  the mystery field the note flagged.
- When shown, give it a title/tooltip: "Zoho GL account for the export
  (optional)".

## 3. The Paid-through cell (feedback note: "explain value of this
second tab / dropdown")

Give the paid-through override control a tooltip: "which card or bank
account paid this; used as the export's Paid Through column". No
structural change this round: the card-assignment flow (next round)
replaces raw account picking.

## 4. Run-review setup warnings

The backend's setup advisories now carry `setting: "cards"` and per-card
wording ("Card '2838 - May 2026' has no Zoho paid-through account set
(optional: ...)"). If the warning list keys any copy or links off the old
`card_entities` / `card_accounts` setting values, key them to "cards" and
link to Settings > Cards.

## Do not

- No em-dashes in UI copy.
- Do not hide the paid-through override; only explain it.

## Verify after publish

Merchants editor shows the optional relabel + an inert hint on an
account-without-category row; the expense grid on a chartless batch shows
NO bare account text box; run-review warnings render the new per-card
wording.

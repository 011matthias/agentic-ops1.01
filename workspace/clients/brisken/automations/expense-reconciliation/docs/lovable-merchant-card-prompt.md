# Lovable prompt: a merchant's card (note item M2, backlog item 152)

Paste the block below into Lovable. It adds one field to the Merchants editor
in Settings, one read-only line beside it, and one new value in the card-source
label the expense rows already render.

---

## Background

Brisken pays some vendors from one card and one card only. Measured across the
live July, August and September 2026 months: of 60 vendors that appear, 34 were
paid from exactly one card, 5 from several (the AI vendors: Anthropic, OpenAI,
Lovable), and 21 carry no card at all. The backend now stores that fact on the
merchant entry and uses it as the LAST resort when a receipt prints no card
number: if the merchant is known to be paid from one card, the row takes that
card, and with it the company and the person, instead of landing in review.

The backend half is live. This prompt is the screen half: the editor must be
able to set the card, the page must show what the tool has learned by itself,
and the expense row must label the new source honestly.

## 1. Settings, Merchants editor: three new fields on each entry

`GET /api/settings` returns `merchants` as a map of canonical name to entry.
Each entry may now carry three extra keys. **All three are optional and absent
when unset** (not null), exactly like `cost_center` and `receipt_portal` today:

```json
{
  "merchants": {
    "Obsidian": {
      "aliases": ["Obsidian"],
      "category": "Software & Subscriptions",
      "zoho_account": null,
      "cost_center": "Tool work",
      "card_key": "card-2838",
      "card_key_learned": true,
      "cards_seen": ["card-2838"]
    }
  }
}
```

| Key | Type | Who writes it | Editable on screen |
|---|---|---|---|
| `card_key` | string | an editor, or the tool | **yes**, a card picker |
| `card_key_learned` | `true` or absent | the tool only | no, read-only |
| `cards_seen` | array of strings | the tool only | no, read-only |

**`card_key` — a card picker.** Offer the cards from `GET /api/cards` by their
label, plus an empty option meaning "not set". Send the card's `key` (for
example `card-2838`), never its label. The backend does not check the key
against the card registry on save, on purpose: merchants and cards are edited
independently, so the save must not fail because a card has not been defined
yet. A key that names no card simply resolves to nothing on the rows.

**`card_key_learned` — a small badge, not a control.** When `true`, show the
card field with a quiet badge reading `Learned` / `Aprendido` and a tooltip:
"The tool set this itself because every receipt of this merchant so far was
paid with this card. Editing it makes it yours, and the tool stops changing
it." When absent, show no badge: the key is the editor's own.

**`cards_seen` — one read-only line under the card field.** Render the card
LABELS (resolve each key through `GET /api/cards`; fall back to the raw key if
a card is not defined) as a comma-separated list, prefixed by the label below.
When the array is absent or empty, render nothing at all: an empty line is
noise.

## 2. The whole-map-replace warning (this is the part that breaks things)

`PUT /api/settings {"merchants": {...}}` **replaces the entire merchant map**.
Any key the editor does not send back is erased from the stored entry.

So when saving a merchant, the payload MUST carry `card_key`,
`card_key_learned` and `cards_seen` exactly as they were read, for **every**
merchant in the map, not only the one being edited. Two of the three are
written by the tool and can never be reconstructed from the screen: dropping
`cards_seen` throws away months of accumulated observation, and dropping
`card_key_learned` turns a key the tool may still withdraw into one it will
never touch again.

Keep the existing round-trip discipline the editor already uses for
`multi_category`, `cost_center` and `receipt_portal` and extend it to these
three. Send `card_key_learned` only when it was `true`; send `cards_seen` only
when it was non-empty; omit an unset `card_key` rather than sending `""`.

## 3. The expense row: one new card-source value

`expenses[].card_source` already renders on each row. It gains one value:

| `card_source` | EN | PT-BR |
|---|---|---|
| `merchant` | From this merchant's card | Do cartão deste fornecedor |

Existing values are unchanged: `override`, `hint`, `learned`, `settled_charge`,
`none`. Treat `merchant` like `learned` everywhere else on the row: it is a
remembered fact, not a decision about this receipt, so the "private card"
option stays available (`can_mark_private` is `true`, and the backend is the
authority on that flag; do not re-derive it).

## 4. Strings

| Key | EN | PT-BR |
|---|---|---|
| `settings.merchants.cardKey` | Paid with | Pago com |
| `settings.merchants.cardKey.none` | Not set | Não definido |
| `settings.merchants.cardKey.help` | The card this merchant is always paid from. A receipt of theirs that prints no card takes it. | O cartão com que este fornecedor é sempre pago. Um recibo dele que não mostre cartão passa a usá-lo. |
| `settings.merchants.cardKey.learned` | Learned | Aprendido |
| `settings.merchants.cardKey.learnedHelp` | The tool set this itself because every receipt of this merchant so far was paid with this card. Editing it makes it yours, and the tool stops changing it. | A ferramenta definiu isto sozinha porque todos os recibos deste fornecedor até agora foram pagos com este cartão. Ao editar, ele passa a ser seu e a ferramenta deixa de alterá-lo. |
| `settings.merchants.cardsSeen` | Seen on | Visto em |
| `expx.card.source.merchant` | From this merchant's card | Do cartão deste fornecedor |

## 5. Do not change

- Do not add Supabase or any other backend. Auth stays the bearer token.
- Do not validate `card_key` against the card list before saving, and do not
  block a save because a card is missing.
- Do not make `card_key_learned` or `cards_seen` editable, and do not add a
  control that clears `cards_seen`: it is the tool's own record.
- Do not touch the existing merchant fields (`aliases`, `category`,
  `zoho_account`, `multi_category`, `cost_center`, `receipt_portal`), the
  category precedence, or anything on the Memory page.
- Do not re-derive `can_mark_private`, `card`, or `card_source` on the client.

## 6. Checks before publishing

1. Open Settings, Merchants. Every existing merchant still shows its aliases,
   category, account and cost center, unchanged.
2. Set "Paid with" on one merchant, save, reload the page: the card is still
   there. Then open a DIFFERENT merchant that already had a cost center, save
   it without touching anything, reload, and confirm the FIRST merchant still
   has its card. That is the whole-map-replace check, and it is the one that
   matters.
3. A merchant the tool has learned shows the `Learned` badge and a "Seen on"
   line; a merchant you set by hand shows the card with no badge.
4. On a month, a row whose card came from the merchant shows "From this
   merchant's card" and still offers the private-card option.
5. Switch to Portuguese and repeat 3 and 4.

# Lovable prompt: the card-definition screen shows every card

Paste into Lovable against `brisken-reconcile-dash`. Backend shipped
2026-08-28; no deploy needed on our side.

## The problem this fixes

The Settings card screen lists only cards somebody already defined. On the
live data that is 2838 plus four cards carrying no charges, while 0340,
3645 and 4700 charge 53 of April's 94 rows and appear nowhere. Somebody
sitting down to define a card cannot see the card they need to define.

## What changed on the API

`GET /api/cards` now returns a third key beside `cards[]` and
`entity_options[]`:

```json
"seen_undefined": [
  { "key": "digits:3645",
    "suggested_key": "3645",
    "observed": "3645",
    "digits": ["3645"],
    "n_charges": 18,
    "months": ["April 2026"] }
]
```

Empty when every card the months charge is already defined. Guard the read
(`data.seen_undefined ?? []`); it is absent on older builds.

## 1. A second section on the card screen

Under the existing card list, when `seen_undefined` is non-empty:

> **Seen on your statements, not defined yet**

One row per entry, busiest first (the API already sorts):

`{suggested_key}` · `{n_charges} charges` · `{months.join(", ")}`

with a **Define this card** button on each row.

Show `observed` as muted secondary text only when it differs from
`suggested_key` (an account id rather than plain digits).

## 2. Define this card

The button opens the same card form the existing list uses, pre-filled:

- card key: `suggested_key`
- digits: `digits`
- entity: empty, for the person to choose from `entity_options`

Use `suggested_key` verbatim. Do not derive the key from `key` (it is the
internal `digits:`-namespaced match key) and do not strip leading zeros:
`0340` is the name on the statement, and a card defined as `340` is one
nobody recognizes.

## 3. Adding a card that is on neither list

The card screen also needs a plain **Add card** button, always visible, not
only when `seen_undefined` has rows. Same form, all fields empty. A card
that has never charged (a new one, a card whose statement has not been
loaded) has to be definable too.

## 4. Saving

Both paths save through the existing `PUT /api/settings` with `cards`.
That call REPLACES the whole map, so send the current `cards[]` plus the
new entry, never the new entry alone. After a successful save, re-fetch
`/api/cards`: the card moves into `cards[]` and drops out of
`seen_undefined` on its own.

A card saved with no entity is still defined and still leaves this list.
The missing entity belongs to the entity column, not here.

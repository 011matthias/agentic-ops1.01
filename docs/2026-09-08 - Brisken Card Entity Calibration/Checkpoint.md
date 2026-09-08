# Checkpoint: Brisken Card Entity Calibration

**Date:** 2026-09-08
**Status:** Entity half of backlog items 26/40 closed and live; person half and six data gaps asked, awaiting Criss/Dirk

---

## Summary

The owner's ALL BANKS BRISKEN GROUP list was calibrated into the live expense
tool: the card registry went from 6 cards to 15, Consulting was charted, and
unresolved rows across the three open batches fell from 30 of 40 to 28. The
round's most consequential output was not the data entry but a code reading
that overturned the plan's retirement premise before anything was written.

---

## What Was Done This Session

### Enumeration before any write
1. Pulled live `GET /api/cards` and `/api/settings` via the operator API, and
   the three open batches (September 12 rows, August 21, July 7).
2. Established a measurable baseline: 30 of 40 rows resolved no card and no
   entity; 6 resolved to card-9693, 4 to card-2838.
3. Read `cards.py` end to end for the retirement semantics, and
   `coa_provision.py` for where a chart can live.
4. Read `/data/coa-provision.json` and `/data/zoho-books-coa.json` off the Fly
   volume: charts exist for Corporate Services and Cloud Services only, but the
   chart FILE carries all eight Zoho orgs.
5. Sorted the list's 36 rows into 16 payment cards and 20 bank/brokerage
   accounts, and put the whole mapping table plus four decisions to the owner
   before touching anything.

### The registry write (after owner confirmation)
1. `PUT /api/settings` with a 14-entry `cards` map plus a `Consulting` entity;
   card-2838 deliberately omitted so its legacy composition stayed untouched.
2. Re-read `/api/cards` and verified all 15 cards field by field (entity,
   digits, active) against the confirmed table. All matched.
3. Ran `refresh-master-data` on all three open batches; each reported
   `cards 6 -> 15`, September and August each reported one row-entity change.
4. Diffed pre/post batch views on real rows: the two `Visa ...1176` rows now
   resolve to card-1176 with `entity_source: card`. No row lost a card or entity.

### Charting Consulting
1. Derived six scope groups from the live chart for org `808232536` under the
   documented 2026-07-01 exclusion rule; they come out identical to Cloud
   Services' six.
2. Proved rather than asserted: `load_entity_chart` over the live chart file
   resolves all six to real chart roots covering 60 accounts, and
   `coa_validation_from_settings("Consulting", ...)` builds an enabled block
   while `BRISKEN GmbH` correctly returns None.

### Documentation and comms
1. Rewrote backlog item 26 and extended item 40's person note (PR #727, merged).
2. Updated the existing `2026-09-08-card-gaps-criss-dirk.md` draft rather than
   creating a second, folding in the entity question, 9693, 2544, 9129, the
   6013-1042 pair, and the sharpened 3645 ask.

---

## Key Decisions Made

### Crossed-out cards are registered active, not `active: false`
- **Choice:** All five dead cards (2448, 7531, 1160, 3344, and the
  owner-marked-closed 1930) carry `active: true` with the retirement in the
  `label`.
- **Rationale:** `resolve_card` filters to `live = {k: c for k, c in
  cards.items() if c.active}` and `legacy_card_accounts` skips inactive cards,
  so deactivation means "never resolve" in BOTH directions. An inactive card
  does not resolve a historical receipt either, so the planned `active: false`
  would have left behaviour identical to today (absent resolves nothing) and
  bought only a Settings-screen entry. A cancelled card cannot be charged, so
  leaving one active carries near-zero risk. Owner confirmed.

### No backend round was needed
- **Choice:** Shipped the data entry directly; wrote no retirement code.
- **Rationale:** `active` already round-trips through all five card code points
  (`normalize_cards_setting`, `cards_to_setting`, `Card`/`_card_from_setting`,
  `card_to_dict`, the snapshot/refresh path). The planned "small backend round
  FIRST" was unnecessary; reading before building saved the whole round.

### Consulting is charted through settings, not the `/data` volume
- **Choice:** `settings["entities"]["Consulting"]` via the operator API.
- **Rationale:** `coa_validation_from_settings` prefers the settings registry
  over the file and falls back to the file's `chart_path`, and the volume chart
  already holds all eight orgs. Same API, same auth, reversible, no volume write.

### `Corporate Services` stays the entity label
- **Choice:** Treat the list's "Corp Service / LLC" as the same entity.
- **Rationale:** Renaming means re-keying the `/data` COA provisioning and
  re-stamping live rows. Owner confirmed.

### card-7531 registered with no entity
- **Choice:** Left the entity blank pending Dirk.
- **Rationale:** "Cloud Solutions" matches no Zoho org. The owner reads it as a
  second name for Cloud Services but asked for confirmation, so the tool holds
  the card without filing it anywhere.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | Items 26 + 40 rewritten (PR #727, merged `0e16e610`) |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | One line: the entity half of 26/40 is no longer open |
| `workspace/clients/brisken/context/drafts/2026-09-08-card-gaps-criss-dirk.md` | edit | Folded in the entity question and four newly found gaps (gitignored) |
| live `settings["cards"]` | write | 6 cards to 15, via operator API |
| live `settings["entities"]` | write | Consulting chart (org 808232536, six scope groups) |

---

## Current Status

Registry holds 15 cards across four entities (BRISKEN GmbH, Cloud Services,
Consulting, Corporate Services). Consulting is charted and its gate block
builds; GmbH is deliberately chartless. The three open batches carry 28 of 40
rows with no card, down from 30, and every remaining one is blocked on data
only Criss or Dirk has. brisken platform ops status: unknown plan, last
assessed unknown. Comms log touched 1 day ago.

No deploy happened and none was needed: the whole round is data through the
operator API against the running app.

---

## Next Steps

1. Send the card-gaps draft to Criss and Dirk; every remaining gap is in it.
2. On reply: enter persons (start with 4921/5126, which two sources already
   name), 0340's entity, and 3645. Persons are safe to write since the
   2026-09-07 SPA gate cleared.
3. If Dirk confirms Cloud Solutions is Cloud Services, set card-7531's entity;
   if it is a real separate entity, it needs its own chart decision.
4. Consider whether the registry should carry a first-class retired-but-still-
   resolving state instead of the label convention this round used.
5. The p2 status files (lead-gen-general, onepilot-site, outreach, product-decks,
   rome, targeting) are 47-79 days stale. Not this session's workstream; flagged
   for whoever picks p2 back up.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 26 + 40)
- `workspace/clients/brisken/context/expense-reconciliation/all-banks-brisken-group-2026-09-08.md`
- `workspace/clients/brisken/context/drafts/2026-09-08-card-gaps-criss-dirk.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cards.py`

### Open Questions
- Is "Cloud Solutions" a second name for Cloud Services, a separate entity, or
  BRISKEN Holding under another name? card-7531 waits on this.
- Is 3645 a Corp Services card of Dirk's? An August Obsidian receipt prints
  `CorpServ & DN ••3645`, which is a merchant's rendering, not the owner's record.
- Is `6013 - 1042` one card with two digit identities, like 2838/1672?
- Is 9693 still in use? It is in the registry but absent from the list.
- What are 2544 and 9129, the two cards that paid Google in August?
- Should GmbH get a chart, and if so, on what scope? Its Zoho chart is flat
  German with no operating-subtree structure to mirror.

### Working Notes
- **The retirement finding is the reusable one.** The tool has no "retired but
  still resolves historically" state. `active: false` is direction-blind. The
  label convention used here is a convention, not a constraint: nothing stops a
  future edit from dropping the "(retired)" text, and nothing warns on a fresh
  charge against a card labelled retired.
- **1672 is still not registered.** `cards.py` uses "the 2838 statement marker
  and the 1672 plastic are one card" as its worked example in the module
  docstring, but the live card-2838 carries `digits: ["2838"]` only, composed
  from the legacy maps. The documented example is not the deployed state.
- **`entity_options` is derived and read-only**, unioning the `/data` COA
  provisioning, `settings["entities"]`, and every card's entity target. Adding a
  card with a new entity adds that entity to the picker for free; there is no
  separate entity-list write.
- **An inactive card still contributes its entity to `entity_options`** (the
  union has no active filter). Not load-bearing here, but surprising.
- **The `cards` and `entities` settings maps are whole-map replace.** A partial
  PUT deletes everything omitted. Pre-edit snapshots for this round are in the
  session scratchpad (`cards-snapshot-preedit.json`, `settings-snapshot-preedit.json`).
- **Batch snapshots insulate history.** Each batch snapshots the registry at
  creation, so a settings edit reaches an existing batch only through an explicit
  `refresh-master-data`. That is why retiring a card cannot corrupt a closed month
  either way, and why the refresh had to be run explicitly on all three.
- **`has_coa` stayed false on all three batches after the refresh**, and that is
  correct: those batches carry no batch-level `legal_entity_id`, so there is no
  entity to provision against. The Consulting chart fires on a batch created with
  that entity, which is why it was proved through the loader instead.
- Zoho knows two cards the list omits: GmbH 1940 (Firma) and Holding Wise Visa
  4872. Holding does not appear on the list at all.
- `flyctl ssh sftp get` needs `MSYS_NO_PATHCONV=1` on this machine, and it writes
  to the CWD, ignoring a destination argument.

### Reference Materials
- App: `https://brisken-expense-recon.fly.dev` (operator code in the gitignored
  `workspace/clients/brisken/context/.env`; `POST /api/login` returns a bearer)
- PR #727: https://github.com/011matthias/agentic-ops1.01/pull/727
- `workspace/clients/brisken/context/expense-reconciliation/zoho-entity-card-map.md`

---

## How to Continue

Read backlog item 26 for the full state. If Criss or Dirk have replied, the
answers map one-to-one onto the open questions above; each is a
`PUT /api/settings` on the `cards` map (whole-map replace, so re-read
`/api/cards` first and send the complete map), followed by
`refresh-master-data` on any open batch and a pre/post row diff to confirm the
resolution actually moved.

---

## Strategic Feedback

### What Worked Well This Session
- Reading `cards.py` before writing overturned the plan's central premise. The
  session was briefed to build a retirement state "FIRST" as a backend round with
  tests, mutation proof, CI and a Fly deploy; the field already existed, and its
  semantics were the opposite of what retirement needed. The enumeration step
  paid for the entire round.
- The baseline row-count (30 of 40 unresolved) taken BEFORE the write made the
  verification a measurement rather than an assertion. "Two rows flipped, none
  regressed" is a claim that can be wrong; without the baseline it would have
  been unfalsifiable.
- Proving the Consulting scope groups through the production loader against the
  live chart caught the class of failure where a plausible group name silently
  resolves to zero accounts and the gate validates against nothing.

### Suggestions
- The registry deserves a real retired state: a card that resolves historical
  receipts, refuses to be the target of a new assignment, and renders as retired.
  The label convention used here works but encodes an important fact as prose,
  which is exactly the shape of drift the tool's own `merchants_inert` surface
  exists to prevent elsewhere.

### System Health
- The `all-banks` transcription being gitignored and read by path worked, but the
  session had to be told where it was. A note in item 26 pointing at the
  transcription would have made the file discoverable from the backlog alone; it
  now carries one.
- Autonomy score: 1 human intervention, and it was the mandated one. The live-write
  protocol required owner confirmation of the mapping table before any write, so
  the single AskUserQuestion round was the gate working rather than a deferral.
  Everything else, including the retirement finding and the charting decision, ran
  without a prompt.

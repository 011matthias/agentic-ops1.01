# Checkpoint: Brisken Recon Entity Order

**Date:** 2026-09-17
**Status:** Item 92 live and verified (backend v146, SPA rounds 1 and 2 published); one owner-side data mismatch open

---

## Summary

Criss asked to reorder the legal entities she has saved. The tool now stores an operator-owned `entity_order`, every entity picker follows it, and the Settings list reorders by press-hold-drag. All of it is deployed, published and driven cold on the live app; an order is already saved there.

---

## What Was Done This Session

### Q&A and scoping
1. Explained "account picks" (per-entity shortlist of `code name` GL labels; empty = the entity's scoped chart) in plain language after the first answer read too technical.
2. Started the Settings-tabs request (bundle audit of the live Settings screen, a partial-PUT isolation test). The owner redirected: another chat owned tabs (it shipped as item 91, #969). The tabs test was backed out of the shared tree.

### Item 92 backend (PR #971, Fly v146)
1. `settings['entity_order']` added to `SETTINGS_DEFAULTS` and `SETTINGS_WRITABLE_KEYS`; PUT validates a list, trims, dedupes, keeps stale names.
2. `service.available_entities` returns the named entities first in order, the rest A-Z, stale names ignored. `entity_options` carries it to the settings payload, `GET /api/cards` and every batch grid with no per-caller change.
3. Tests: 5 unit (ordering, unnamed, stale/repeat/blank, run default, no-order), 4 route (round-trip, 400, stale save, grid route follows), contract sample. `regress_check.py` on the ordering line: 4 red incl. the grid-route test, restored green. Full module suite 2014 passed, 2 skipped.
4. api-contract, backlog item 92.

### SPA prompts
1. `lovable-entity-order-prompt.md` (round 1): list renders `entity_options`, one row opens at a time, native drag + Move up/down saving `{entity_order}` alone with the `applied` check and rollback.
2. `lovable-entity-order-r2-prompt.md` (round 2, owner ask): dnd-kit with Mouse/Touch sensors on a hold delay, keyboard reorder on a focusable grip, DragOverlay, arrows removed, save contract unchanged.

### Deploy and verification
1. On the owner's "done and published" the PR was green but unmerged; merged, deployed v146 from a detached origin/main worktree.
2. Live API: `entity_order` served; differential probe with no write (`"x"` answers "must be a list", control key answers "unknown settings key").
3. Round 1: bundle read (keys, save payload, no local sort) + cold headless drive (8 rows in API order, row expands, month dropdown matches; only `POST /api/login`).
4. Round 2: bundle carries dnd-kit (`DndDescribedBy`, `DndLiveRegion`), arrows and native drag gone; cold drive: 0 arrows, 8 grips in API order, quick click toggles, press-hold lifts into a shadow overlay, Escape cancels with no request, an immediate move does not lift. The saved order is non-alphabetical, which closes round 1's "order equals A-Z" verification limit.
5. PROMPT-STATUS Applied rows for both rounds (#977, #984).

---

## Key Decisions Made

### Order as a separate list, not a field per registry entry
- **Choice:** `entity_order: [names]` beside `entities`.
- **Rationale:** 3 of the 8 live entities exist only as card targets, outside the registry; a per-entry field could not order them.

### Stale names kept on save, ignored on read
- **Choice:** no existence check in the PUT; `available_entities` skips unknown names and appends unnamed entities.
- **Rationale:** an entity leaving the card map must not refuse the operator's save, and the picker must never hide an entity a charge needs.

### No live writes during verification
- **Choice:** probes that refuse before writing, drives that open rows and cancel drags, never drop or save.
- **Rationale:** `feedback_recon_no_live_writes_criss_acts`; the order is Criss's data.

### Round 2 adds a library
- **Choice:** dnd-kit, reversing round 1's "no drag library".
- **Rationale:** native HTML drag cannot lift on hold, shift rows live, or work on touch.

---

## What Did NOT Work (and why)

- **Merging #971 "on green" after ending the turn:** the turn closed with CI running; nothing merged it, and the owner published the SPA prompt against a backend that rejected `entity_order` until the next turn's merge + deploy. Now caught by `warn-stop-merge-left-pending`.
- **Editing in the shared primary clone:** a sibling session was editing `service.py` in the same tree; my hunks had to be backed out by hand and the work redone in a worktree.
- **Claiming the live registry was empty:** repeated from a stale docstring without querying; the live registry holds 5 entries. Corrected in the backlog (#977); the docstring in `available_entities` still carries the old claim.
- **`git rebase` on the pushed prompt branch:** would have needed a force push (B6 floor); reset to the remote and merged `origin/main` instead.
- **Playwright 1.55 default launch:** wanted `chromium_headless_shell-1187`, cache has 1223-1234; launched via `executable_path` to `chromium-1234`.
- **First drive locators:** the feedback widget popover intercepted clicks (hidden with an injected style); a forceMounted hidden combobox matched `[aria-expanded]`; round-2 row headers are `div[role=button]`, not `button`.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/{store,app,service}.py` | Edit | `entity_order` key, PUT validation, ordering (#971) |
| `.../tests/test_master_data_settings.py`, `test_web_expense_settings.py`, `test_settings_put_contract.py` | Edit | ordering + route + contract tests (#971) |
| `.../docs/api-contract.md` | Edit | `entity_order` contract (#971) |
| `.../docs/lovable-entity-order-prompt.md` | Create | round 1 SPA prompt (#971) |
| `.../docs/lovable-entity-order-r2-prompt.md` | Create | round 2 press-hold-drag prompt (#980) |
| `.../docs/PROMPT-STATUS.md` | Edit | both rounds Applied with evidence (#977, #984) |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | item 92, correction, card-name finding |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | item 92 element row (this PR) |
| `.claude/patterns/warn-stop-merge-left-pending.md` | Create | stop-event rule for a merge left pending (this PR) |

---

## Current Status

Item 92 is closed on both halves. Fly `brisken-expense-recon` v146 serves `entity_order`; the SPA reorders by press-hold-drag and a non-alphabetical order is saved. Brisken ops status: `infrastructure.yaml` has no platform section (unknown plan).

The open item is data, not code: all 9 cards point at `Corporate Services` / `Cloud Services` / `Consulting`, while org id, default paid through and account picks sit under `Brisken Corp Services, LLC` / `Brisken Cloud Services, LLC` / `Brisken Consulting, LLC`. `entity_from_settings` matches names exactly (case-insensitive), so those settings do not reach the cards' charges.

---

## Next Steps

1. Owner or Criss decides the canonical entity names; the recommended fix is pointing each card at its LLC name in the Cards tab (the three short rows then drop out). No code.
2. Correct the stale docstring line in `service.available_entities` ("the real Brisken case, where `settings['entities']` is empty").
3. The Legal entities tab count reads the registry (5) while the list shows 8; fold into the next Settings prompt if it confuses anyone.
4. `p2-product-decks.md` (56d) and `p2-targeting.md` (57d) status files are stale; update or delete them in a p2 session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 92
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (item 92 rows)

### Open Questions
- Which entity names are canonical: the LLC names in the registry or the short names on the cards?

### Working Notes
- Live read-only verification recipe for the recon SPA: API login with `EXPENSE_RECON_OPERATOR_CODE` from `context/.env`; Playwright python with `executable_path` to `ms-playwright/chromium-1234/chrome-win64/chrome.exe`; inject `[data-fb-widget]{display:none!important}` after login; scope locators to visible elements (Settings panels are forceMounted).
- Differential-probe shape for a new settings key with no write: send an invalid value; new code answers the key's own validation error, old code answers "unknown settings key(s)".
- `deploy-consumer-gate` closed its marker on `ls $LOCALAPPDATA/ms-playwright` (path contains "playwright"): same class as the open 2026-09-17 system verification-theater row.

### Reference Materials
- PRs #971 (backend), #977 (applied r1), #980 (r2 prompt), #984 (applied r2)
- Fly `brisken-expense-recon` v146

---

## How to Continue

Nothing is in flight for item 92. Start from the Next Steps; step 1 needs an owner decision before any write to Criss's card settings.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the published bundle before writing the prompts: it showed both pickers render `entity_options` unsorted, so the dropdown needed no SPA change, and it surfaced that 3 of 8 entities live outside the registry, which set the data model.
- Differential probes that refuse before writing verified the live backend without touching Criss's settings.

### Suggestions
- `deploy-consumer-gate` should match browser-tool invocations as commands (`agent-browser`, `browser_*`, a Playwright launch), not substrings anywhere in a Bash line; it closed on an `ls` of the Playwright cache this session.

### System Health
- Autonomy: 2 human interventions (plain-language re-ask; redirect off the tabs work, owned by a sibling chat).
- The shared primary clone ran five concurrent sessions; the SessionStart sibling warning fired and was not acted on until a real collision. The worktree-first habit held for every later step.

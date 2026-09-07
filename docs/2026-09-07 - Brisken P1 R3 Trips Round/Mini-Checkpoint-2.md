# Mini-Checkpoint: Brisken P1 R3 Trips Round

**Date:** 2026-09-07
**Status:** R3 shipped + deployed (Fly v105); owner-side alias gate open
**Type:** mini

---

## Summary
R3 of the item-38 program (one of four parallel chats): trip entity, declared
batch_type, and travel-alias mail routing built, adversarially reviewed (10
findings fixed pre-PR), merged THIRD per program order (PR #688), and deployed
as Fly v105 with server + SPA-drive verification. The travel alias ships
UNSET; the feature activates owner-side.

## What Was Done
- Trip entity: trips table + CRUD at `/api/trips`; batch materializes on
  first join (create-with-receipt), one batch per trip under an in-process
  creation slot that also closes the delete-during-create window.
- `batch_type` declared at creation ("company-month" | "trip"); absent reads
  company and an undeclared create stores no marker; month routing, claiming,
  replay, re-ingest and item 39's materializer are all structurally blind to
  trips (even month-parsing trip names).
- Travel routing: `intake.travel_alias` (unset default; PUT edge refuses
  "receipts" + person-alias collisions), base-local matching (travel+tag@ is
  travel, receipts+travel@ is not, Cc-both = travel, all pinned), travel mail
  RESTS with an exactly-one-covering-trip suggestion, joining is
  `POST /api/inbound/{archive}/join-trip` (provenance carried; failures
  return the mail to the pool). receipts@ behavior pinned field-identical
  with and without the alias, pooled AND direct-ingest halves.
- Roster-mismatch flag on trip rows via R1's person field
  (`expenses[].roster_mismatch` + `n_roster_mismatch`, trip-only presence).
- Two rebases (post-R1, post-R2) with owned conflict resolution; the one
  cross-round interplay pinned by test: item 39's materializer skips
  `pool_kind: travel` (added at rebase — R2's backfill would otherwise seed a
  month from a travel receipt).
- Contract: api-contract.md updated per change; `trip.travelers[]` pinned;
  `lovable-trips-prompt.md` written (§5 Settings field ships FIRST) +
  PROMPT-STATUS not-applied row; status roll-up row closed via PR #689.
- Verification: final merged tree suite 1478 passed / 2 skipped, calibrate
  gate OK, ruff E9/F clean on the diff, eight RED-proofs via regress_check;
  deploy verified by /healthz + authenticated API reads
  (`/api/trips` = `{"trips": []}`, `n_pooled_travel: 0`) + Playwright drive
  of /months and /inbound (real labels, no "Arriving", no error boundary).

## Current Status
Live app is Fly v105 (2026-09-07) carrying R1+R2+R3. brisken platform:
unknown plan (pre-flight); live pool at drive time: 24 pooled, 0 held,
0 months open, 0 trips. R3's feature is inert until the owner picks the
travel alias. R4b (trip-spanning settlement) unblocks on this merge.

## Next Steps
1. OWNER GATE: paste `lovable-trips-prompt.md` (§5 Settings travel-alias
   field FIRST — intake object is whole-object-replace; a stale SPA save
   would erase the alias), verify §5 by field name in the bundle, then enter
   the chosen alias local-part in Settings.
2. After the alias is set: full `TEST -` drill — create a TEST trip, mail
   the alias, verify rest + suggestion + join, remove all fixtures to zero.
3. R4 chat: R4b may start (R3 merged); R4 merges fourth and owns the next
   shared-surface conflicts.

## Files to Read First
- workspace/clients/brisken/status/p1-expense-reconciliation.md (R3 row)
- workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-trips-prompt.md
- workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md
  (batch_type + trip, travel pool, roster_mismatch sections)

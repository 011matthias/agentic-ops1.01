# Mini-Checkpoint: Brisken Recon Zoho Decoupling + Cards R4

**Date:** 2026-08-22
**Status:** Both rounds merged and deployed; Cards R4 has one piece left
**Type:** mini

---

## Summary

The owner answered the five open questions, which unblocked the last wave
round and opened a bigger one: cut every tie to Zoho. Layer 1 of that (the
live connection) and the Cards R4 export half both shipped and are live.

## What Was Done

- **PR #579 — the live Zoho connection is gone.** Deleted the Books API
  client, the idempotent journal poster, `expense-recon zoho-post`, the
  `coa_source: "api"` live chart pull, and the `seed-zoho` importer: ~1,600
  lines plus 65 tests. Nothing hosted used them (no `ZOHO_*` env on Fly, the
  web layer never imported the client), so hosted behavior is unchanged.
  `tests/test_no_zoho_connection.py` keeps them gone; all four tests were
  proven red against the pre-deletion tree. Doctor gained a real fix: it
  rejected `coa_source: "none"`, which is the default.
- **PR #580 — Cards R4 export half.** The ruling (one file, entity as a
  column) already worked after R3, so it is pinned by tests. The find was
  beside it: `CoaGate` assumed one entity per run and provisioning looked up
  that one entity, so every entity-less batch exported with no chart
  validation at all. `MultiEntityCoaGate` now gates each row against its own
  entity's chart, and provisioning injects one entry per known entity when a
  batch targets none.
- Owner answers recorded in backlog item 10; the Zoho program is item 23 with
  its four layers and why three of them wait.

## Current Status

Suite 1163 passed / 2 skipped, calibrate green. Deployed twice more today
(four deploys total); `/healthz` 200, six batches intact, April still reads
36 rows and 35 categorized, the export still generates.

`has_coa` is snapshotted at batch creation, so the new per-entity gate
applies to batches created from now on; the April batch still reads
`has_coa: false` until it is re-run. That is the existing snapshot rule, not
a regression.

## Next Steps

1. **Item 19 — build the re-ingest action** for attachment mail stranded by a
   deleted month. The owner said build it; this session ran out of pressure
   budget before starting it.
2. **Zoho layers 2 and 3:** rename `zoho_account` (parallel field + Lovable
   prompt) and give the chart gate a non-Books chart source.
3. **Zoho layer 4 needs one answer:** which accounting system the exported
   CSV gets imported into now. Keeping today's headers costs nothing and
   still works; changing them blind would be guesswork.
4. Cards R4 leftovers: persisted cards migration, intake dropdown unification.
5. The January credit notice still needs one click in the app (the sandbox
   classifier blocks state-changing calls from this session); my call was to
   book it.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 10, 19,
  23)
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_no_zoho_connection.py`

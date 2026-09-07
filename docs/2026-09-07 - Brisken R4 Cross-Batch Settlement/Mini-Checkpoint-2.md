# Mini-Checkpoint: Brisken R4 Cross-Batch Settlement

**Date:** 2026-09-07
**Status:** R4 shipped, deployed (v106), live-verified; 2026-09-06 owner program CLOSED
**Type:** mini

---

## Summary
R4 (item 38's deep half) shipped in two phases on one branch and closed the four-round owner program: the `receipt_claims` registry makes one-receipt-one-charge a global invariant across batches, a month's statement pool spans overlapping trips, provenance ships as `settled_by` on both payloads, and a trip's report sections per person.

## What Was Done
- **R4a (built before R3 merged):** `receipt_claims` table (PK receipt_run_id+document_id), advisory read + commit-lock re-check + UNIQUE backstop in `rematch_month`, decision sync (reject releases, re-pick moves, cross-run steal 409s), delete cascades. Load-bearing pin proven: with zero trips the machinery is inert (machinery-on vs stubbed builds byte-compare equal).
- **R4b (after R3 merged):** `trip_pool_for_month` spans the pool over date-overlapping trips (private-confirmed, foreign-claimed, id-colliding docs excluded); borrowed receipts ride the snapshot as copies only; cross-month rematch triggers on trip-batch create and gradual add; per-person trip report (`sections` in the PDF builder, roster order, off-roster flag, continuous numbering).
- Merged LAST per program order (#685, after #686/#687/#688), conflicts on shared surfaces resolved; suite 1496/2, calibrate Gate OK; six RED-proofs via `tools/regress_check.py` all bit.
- Deployed v106 from a detached worktree; live TEST- drill: trip receipt settled a month charge, second month could NOT re-settle it, trip report rendered (title/range/roster/person section), Playwright drove the published SPA workbench (settled row rendered, "TEST R4 WB TAXI" @99%, no fallbacks); all fixtures deleted, live back to 0 batches / 0 trips.
- Program close: loop brief re-ranked to post-program state (#691); Lovable prompt `lovable-r4-settled-by-prompt.md` + PROMPT-STATUS row shipped with #685.

## Current Status
Live app v106; suite baseline 1496 passed / 2 skipped. All four program rounds merged + deployed. Everything visible now waits on owner-side applies: four pending Lovable prompts (R1 gates person data entry; R3 §5 gates alias entry), the travel-alias decision, two Hostinger dismissals gating the R2 flag flip (`EXPENSE_RECON_AUTO_MATERIALIZE` still OFF). Brisken ops status: platform plan/last-assessed unknown in infrastructure.yaml.

## Next Steps
1. Owner pastes the four Lovable prompts; re-run `prompt_ledger.py`, update PROMPT-STATUS.md.
2. R2 staged flip after the two Hostinger dismissals (protocol in backlog item 39).
3. Resume the pre-program queue: item 27, item 23's remaining layers (gated on GL-codes call), 24, overlay routes.

## Files to Read First
- workspace/clients/brisken/status/p1-recon-loop-prompt.md (post-program ranking)
- workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md (Cross-batch settlement section)
- workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md

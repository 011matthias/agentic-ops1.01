# Checkpoint: Brisken P1 Receipts Drop Page

**Date:** 2026-09-08
**Status:** Backend shipped + deployed + live-drilled; SPA consumer drive OPEN (browser tooling down)

---

## Summary

Built and shipped the owner's 2026-09-08 directive: receipt entry is
decoupled from month creation. `POST /api/receipts` is the one manual
entrance (each dropped file routes to the month printed on it), company
months are created empty, and the create route now refuses files. PR #709
merged on green CI and deployed to Fly; the live drop drill filed a TEST
receipt into a self-created June 2026 month and the fixture was removed.
The Lovable prompt is written and unapplied.

---

## What Was Done This Session

### The decision (answered before building)

1. The owner asked whether receipt injection should leave "create a new
   month". Answered yes, with the reasoning that decided the design: the
   create-month upload slot was the last surface filing receipts by
   OPERATOR CONTEXT rather than by what the receipt says, which is the
   class that put Dirk's August receipts in the April batch.
2. Named the pairing that makes removal viable: empty months must become
   legal, or Criss cannot open a month at all (statement-first is her real
   workflow; January was 78 of 80 charges with no receipt).

### Backend (PR #709, merged, Fly-deployed)

1. `POST /api/receipts` + `route_dropped_receipts`: per-FILE routing
   through the same `resolve_receipt_month` brain mail uses, month
   materialization when absent (`created_by: "drop"`, unconditional),
   pool claim after a create, per-file ledger on a new `jobs.result`
   column (idempotent migration, COALESCE so a later status write cannot
   blank it).
2. Create route: company months refuse files (400) and create empty via
   opt-in `allow_empty`; trip creates unchanged. `allow_empty` never
   sanctions an all-rejected upload, so the mail materializer's floor
   survives.
3. `needs_month` resting state for unreadable dates (no arrival-month
   guess), `month` override believed like a typed date, zips refused.

### Tests

1. New `tests/test_receipts_drop.py` (12 tests) covering both halves.
2. 31 existing modules' create fixtures converted to
   create-empty-then-add by four parallel agents, file-disjoint, with a
   strict contract (identical mock budgets, no weakened assertions).
   Retired create-contract tests were rewritten against the surfaces the
   surviving journey populates.
3. Suite 1496 → **1508 passed / 2 skipped**; ruff clean; six RED-proofs
   each green→red→green.

### Live

1. Deployed to Fly (build context must be the recon DIRECTORY, not just
   `--config`), `/api/receipts` drill: TEST- PDF printing 2026-06-11 →
   filed to a self-created "June 2026" (`created_by: drop`), expense read
   at 18.90 EUR. Fixture deleted; live state back to 3 real months, pool 0.

---

## Key Decisions Made

### Remove receipt injection from month creation

- **Choice:** Remove it, paired with legal empty months.
- **Rationale:** One routing brain for every entrance. Leaving the slot
  would leave two filing policies, one of them the one already replaced.

### The drop materializes months unconditionally

- **Choice:** No `EXPENSE_RECON_AUTO_MATERIALIZE` gate on the drop path.
- **Rationale:** That flag exists to stop a STRANGER's mail minting
  months; an operator dropping a file on the page is the opposite of the
  risk it guards.

### An unreadable date rests instead of guessing

- **Choice:** `needs_month` + an explicit operator override, rather than
  falling back to the arrival month the way MAIL does.
- **Rationale:** A silent month guess is exactly what item 29's routing
  rebuild removed; mail has no operator present to ask, the page does.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| web/app.py | edit | `/api/receipts` route, drop job runner, create-route refusal + `allow_empty` |
| web/intake_mail.py | edit | `route_dropped_receipts`, `valid_month_key` |
| web/service.py | edit | `create_expense_batch(allow_empty=...)` |
| web/store.py | edit | `jobs.result` column + migration + COALESCE write |
| tests/test_receipts_drop.py | create | 12 tests, both halves |
| 31 test modules | edit | create fixtures → create-empty-then-add |
| docs/lovable-receipts-drop-prompt.md | create | the SPA half (unapplied) |
| docs/api-contract.md, docs/PROMPT-STATUS.md | edit | drop contract + Not-applied row |
| status/p1-expense-reconciliation.md, status/p1-improvement-backlog.md | edit | round row + backlog item 44 |

---

## Current Status

Live on Fly, verified through the API: 3 real months (Sept/Aug/July),
0 trips, pool 0, held 0. The drop endpoint works end to end on real
vision. The SPA does NOT yet have the Receipts page: the prompt is
written and unapplied, and the create-month form still shows an upload
area that the server now 400s (loud error, no corruption).
brisken platform: unknown plan (no platform section in
infrastructure.yaml for the fastapi orchestrator).

---

## Next Steps

1. **Finish the consumer drive** (the one thing this session could not
   close): re-run a TEST drop, then drive the published SPA's `/months`
   with a browser and assert the drop-created month RENDERS with a real
   label (not a blank cell / "Unknown"), then remove the fixture. Both
   Playwright MCP (CDP :9222 refused) and agent-browser (`open` hung
   past 100s twice, even after `close --all`) were unavailable; try a
   fresh terminal, `agent-browser install`, or start Edge with
   `--remote-debugging-port=9222` first.
2. Hand the owner `docs/lovable-receipts-drop-prompt.md` to paste, then
   re-audit the bundle by field names and update PROMPT-STATUS.
3. Item-26/40 data entry (person per card, 0340 entity, 3645/1672) is
   still the open owner-side item from 2026-09-07; the card-list ask was
   sent 2026-09-07 and is awaiting reply.
4. p2 status files are 47-79d stale (6 files) — out of scope for p1
   sessions, refresh when a p2 session next opens.

---

## Context for Next Session

### Files to Read First

- workspace/clients/brisken/status/p1-improvement-backlog.md (item 44 is
  this round's design record)
- workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-receipts-drop-prompt.md
- workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md
  ("The receipts drop")

### Open Questions

- None on this round. The GL-codes-vs-categories call and the Consulting
  entity's cards remain open from earlier rounds.

### Working Notes

- **Fly deploy of this app needs the DIRECTORY as build context:**
  `flyctl deploy "<abs path to expense-reconciliation>" --app
  brisken-expense-recon`. Passing only `--config <fly.toml>` validates
  and then dies with "app does not have a Dockerfile".
- The drop's mock-budget rule for tests: an EMPTY create consumes zero
  extractions; the add consumes what the create used to. Where a batch
  claims pooled mail, the claim now happens during the (empty) create,
  i.e. BEFORE the seed add — two intake tests had to swap queue order
  for that reason.
- Operator-API helper + drill scripts live in this session's scratchpad
  (`recon_api.py`, `drop_drill.py`); trivially re-derivable, not durable.
- `tools/regress_check.py --test ... --file ... --replace ... --with ...`
  is the fastest way to prove a guard bites; six mutations took ~4 min
  total.

### Reference Materials

- https://brisken-expense-recon.fly.dev (API), https://brisken-reconcile-dash.lovable.app (SPA)
- PR #709 (merged)

---

## How to Continue

`/resume brisken` → step 1 of Next Steps (the consumer drive), then hand
the Lovable prompt.

---

## Strategic Feedback

### What Worked Well This Session

- Answering the design question BEFORE building, and naming the pairing
  (empty months) that the removal depended on: the directive as literally
  stated would have bricked month creation.
- Four file-disjoint agents converted 31 test modules under one written
  contract; each reported its judgment calls rather than quietly
  weakening assertions, and the one contract gap they found (upload
  validation moving from the create payload to `expense_ingest`) came
  back as a documented finding.

### Suggestions

- The RED-proof sweep tripped the "same command 3x" hard-limit hook,
  which is calibrated for fix-then-test spirals. A verification sweep is
  the opposite shape (every run green→red→green, nothing being fixed);
  worth teaching the hook to distinguish a `regress_check.py` invocation
  from a bare pytest retry.

### System Health

- Autonomy: 1 human intervention (the design question, which was the
  user's to answer) plus one interrupt on the stuck browser tooling.
- Browser automation was unavailable through BOTH paths this session
  (Playwright CDP refused, agent-browser `open` hung). That blocks the
  deploy-consumer gate for any SPA-facing round, so it is infrastructure
  worth fixing before the next one.

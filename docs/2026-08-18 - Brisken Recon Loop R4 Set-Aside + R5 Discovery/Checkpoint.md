# Checkpoint: Brisken Recon Loop R4 Set-Aside + R5 Discovery

**Date:** 2026-08-18
**Status:** Loop rounds 4+5 complete; proactive loop PAUSED → reactive

---

## Summary

Round 4 shipped the set-aside strip + one-click restore (PR #538, deployed
Fly, live-verified incl. a created-then-deleted UTIL batch e2e; owner
published the Lovable strip UI). Round 5 ran the two genuinely untested
material sets and found zero money defects (PR #539, docs-only), so the
loop switched from scheduled rounds to evidence-driven reactivation.

---

## What Was Done This Session

### Round 4 — set-aside strip + restore (PR #538, merged + deployed)

1. Quarantined uploads become first-class snapshot `set_aside` entries
   (file, display, reason code, stored extraction); both write paths
   (batch creation via `ReconcileResult.set_aside_receipts`, mid-month
   add inline). Mid-month exclusions now survive later adds.
2. `build_expense_view` exposes `view.set_aside` + `summary.n_set_aside`;
   legacy runs derive entries from the quarantine parse warnings.
3. `POST /api/expense-batches/{id}/set-aside/restore`: stored extraction
   reused (no fresh vision call), memory + registry + categorize pass,
   entry flagged `restored`; deny-by-default guards.
4. 5 regression tests (proven to fail on pre-fix src); suite 1068/2.
   Deployed to Fly from clean origin/main worktree; live-verified:
   healthz 200, 401 gate, strip fields on all batches, restore refusal
   path, and a full e2e (UTIL batch with a statement page → strip
   populated with reason `statement` → deleted after).
5. Lovable prompt authored + handed (`docs/lovable-set-aside-prompt.md`
   in the module); owner applied and published the UI.

### Round 5 — discovery pass over untested material (PR #539, docs-only)

1. Set 6 first-ever run (13 receipts: Uber email-forwards, MBTA, DB
   tickets, BRL invoices) with the live 28-merchant book pulled via
   `/api/settings`: 18 rows; every spot-checked sum exact vs source PDFs
   (3 Uber totals to the cent, DB 6.65 EUR). Misses were vendor names
   only ("CIV" for DB AG, "Uber Receipts" for Uber).
2. May fresh-read pair (2026-08-13 vs 2026-08-18, local config has no
   cache): 20/20 rows identical amount/currency/date; quarantine 7/7
   both times; text-only drift incl. one bank-read-as-vendor flip
   (ANNADA ROUEN → CREDIT AGRICOLE NORMANDIE).
3. Smoke10 R7 byte-identical to R6 (third identical run) — item-4
   category-flip watch has still never fired on pinned inputs.
4. Backlog: +item 6 (vendor = merchant, never the acquiring bank —
   prompt fix queued to ride with the next code round), +item 7 (drift
   evidence record), merchant-seed note extended with DB AG/CIV, Uber,
   Enilive. Runbook: loop switched to reactive.

---

## Key Decisions Made

### Loop goes reactive after round 5

- **Choice:** No more scheduled iterations; a code round fires only on
  evidence (Criss's real usage, the item-4 watch, the item-2 decision).
- **Rationale:** Rounds 1–4 each killed a recurring defect; round 5's
  discovery pass over ALL remaining untested material found zero money
  defects. Remaining known issues need human answers (split rows,
  multi-category vendors) or owner data entry (merchant book); iterating
  further would optimize against our own taste, not her workflow.

### Restore reuses the stored extraction

- **Choice:** The set-aside entry carries the excluded receipt's full
  extraction; restore never re-reads the photo (legacy entries without
  stored extraction re-extract from disk as fallback).
- **Rationale:** Free + instant for the normal case, and the human's
  "this is a receipt" verdict overrides the model's classification
  (`document_type` forced back to receipt with a provenance note).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `...expense-reconciliation/src/expense_recon/cli.py` | edit | split returns excluded; `ReconcileResult.set_aside_receipts` |
| `...expense-reconciliation/src/expense_recon/web/service.py` | edit | set-aside entries, view exposure, `restore_set_aside_file` |
| `...expense-reconciliation/src/expense_recon/web/app.py` | edit | restore endpoint |
| `...expense-reconciliation/tests/test_document_type_quarantine.py` | edit | 5 regression tests |
| `...expense-reconciliation/docs/lovable-set-aside-prompt.md` | new | owner UI handoff (applied + published) |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 1 → shipped; +items 6/7; watch notes (PRs #538/#539) |
| `workspace/clients/brisken/status/p1-recon-loop-prompt.md` | edit | rounds 4/5 state; reactive mode; material table |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | iter-4 element row (PR #538) |
| `.scratch/criss-recon-set6/` | new | set-6 fixture: config + merchants snapshot + pinned cache + output |
| memory `project_brisken_expense_recon_usability_loop.md` | edit | rounds 4/5 + reactive state |

---

## Current Status

Rounds 1–5 done: 4 shipped fixes live on Fly (quarantine, honest labels,
extraction cache + CLI registry, set-aside strip + restore) + strip UI
published by owner; round-5 discovery clean on money. brisken platform:
unknown plan, ~?/? ops/mo (no platform section for the FastAPI app —
expected). p1 status file current on origin/main; the five stale p2
status files belong to p2 sessions, untouched here.

---

## Next Steps

1. Owner: ask Criss the item-2 split-row question (two rows per
   multi-account receipt, or one).
2. Owner: Merchants editor — add DB AG (+ "CIV" alias), Uber (+ "Uber
   Receipts" alias), Enilive (+ "Enimove"); plus the existing MEGA
   CENTER dup/category cleanup.
3. Criss's next real month = the live proof; watch for strip usage and
   any defect → that evidence reactivates the loop (paste
   `status/p1-recon-loop-prompt.md` into a fresh chat).
4. Next code round (whenever it fires) carries backlog item 6 (vendor ≠
   acquiring-bank prompt line; bumps cache fingerprint).

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the
  re-entry brief; states reactive mode)
- `workspace/clients/brisken/status/p1-improvement-backlog.md`

### Open Questions

- Item 2: split receipts — one row or two? (Criss/Dirk call.)
- Zoho "Tax Amount" semantics on split Uber rows: sums are exact, but
  whether Zoho treats the Tax Amount column as included-in-amount on
  import has not been confirmed against a real Zoho import.

### Working Notes

- Restore endpoint answers synchronously with the refreshed `batch`
  view — the SPA replaces state directly, no second GET.
- May local config deliberately has NO extraction cache: each run is a
  fresh read, which is what makes it the drift instrument. Do not "fix"
  that by adding a cache path.
- The May drift pair evidence: `expenses-QUARANTINE-20260813.csv` vs
  `expenses.csv` in `.scratch/criss-recon-may/`.
- Lovable publish verification was cut short on owner instruction
  ("don't check, just explain") — strip render on the published SPA is
  owner-attested, not DOM-probed.

### Reference Materials

- PRs: #538 (feature), #539 (round-5 docs)
- `automations/expense-reconciliation/docs/lovable-set-aside-prompt.md`

---

## How to Continue

Paste `workspace/clients/brisken/status/p1-recon-loop-prompt.md` into a
fresh chat when evidence arrives (defect from Criss, watch fires, or the
item-2 decision lands). No scheduled work remains.

---

## Strategic Feedback

### What Worked Well This Session

- The loop's own discipline (run → diff → source-verify → backlog)
  produced a defensible "stop iterating" answer: the stagnation question
  was answered with a discovery round's data (source-exact sums, an
  identical 20-row money diff) instead of a hunch.
- Proving the 5 regression tests fail on pre-fix src (checkout
  origin/main -- src, run, restore) caught the burden of proof cheaply
  without stash.

### Suggestions

- The stop-b1-gate keeps catching the same closing-offer habit (6th
  session-row since 2026-07-24). The primer helps next-turn but the
  authoring habit persists; consider a draft-time self-check phrase ban
  ("If you want, I can…") in the response-authoring guidance rather
  than another post-hoc layer.

### System Health

- Autonomy: 1 human intervention (owner redirected a verification
  detour to an explanation — logged as intent-misalignment).
- Gates: B1:1 B2:5 B3:1 skipped:0. Register at 400 KB → archive split
  run with this checkpoint.

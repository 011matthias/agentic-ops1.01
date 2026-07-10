# Checkpoint: Brisken Recon Strategy Removal + Doc Refresh

**Date:** 2026-06-16
**Status:** Complete — both PRs merged to main, deployed to Fly (v8), verified live

---

## Summary
Removed the mistakenly-embedded lead-gen Strategy deck from the Brisken
expense-reconciliation tool, then refreshed the served Guide and How-it-works
docs to match the tool's current code/routes/CLI. Shipped as two PRs (#188
removal, #189 content), merged on green CI, and deployed the new build to Fly.

---

## What Was Done This Session
### PR #188 — Remove Strategy (merged)
1. Dropped the `Strategy` nav tab in `templates/base.html`.
2. Deleted the `GET /strategy` route + `strategy()` handler in `web/app.py`,
   and removed `/strategy` from the module docstring route list.
3. Deleted the embedded `web/guides/strategy.html`.
4. Removed `test_strategy_deck_served_verbatim` + the `/strategy` nav assertion
   in `tests/test_web_guides.py`.
5. Left the standalone lead-gen deck deliverable in place (separate artifact).

### PR #189 — Refresh Guide + How-it-works (merged)
Read the actual code/routes/CLI first (B4), then updated both served docs:
1. **Statement input:** named the Chase PDF path (multi-card, per-charge
   foreign amount + currency read from the PDF, no column map / no card name)
   alongside the CSV / Excel column auto-detect path.
2. **Matching:** card-scoping (a receipt paid on a named card only reconciles
   against that card); exact-FX first (a foreign receipt matches the
   statement's captured original amount euro-to-euro, deterministically, no
   estimate and no AI) with the implied-rate band as the fallback; unknown
   receipt currency flagged, never defaulted to USD.
3. **Outputs:** corrected "two files" to three — xlsx review report, flat
   reconciled CSV (`/runs/{id}/reconciled.csv`), Zoho Books journal CSV.
4. **Form / workbench:** legal entity derived from the paying account
   (account to entity map); receipts-currency-blank flags unknowns; added the
   Unknown currency counter + the Reconciled data (.csv) download.
5. Refreshed the automated-check count (346 to 392). User Guide updated across
   all three languages (EN / DE / PT).
6. Re-synced the two tracked standalone deliverable copies
   (`expense-recon-*-2026-06-16.html`) byte-for-byte to the served docs.

### Deploy (Band-3, on explicit user order)
1. `flyctl deploy --ha=false --remote-only` from merged main.
2. Verified: release v8 live; `/healthz` 200; `/` 303 to `/login`.

---

## Key Decisions Made
### Standalone deliverable copies: sync the tracked ones, leave the WIP alone
- **Choice:** Re-synced the two **tracked** `expense-recon-*-2026-06-16.html`
  deliverables to the served docs; did not touch the two **untracked** WIP
  copies (`tool-flow-2026-06-16.html`, `user-guide-2026-06-16.html`).
- **Rationale:** The tracked copies were byte-identical mirrors of the served
  docs; leaving them stale would create client-facing drift (a sent copy
  contradicting the in-tool doc). The untracked copies are excluded WIP per the
  PR-flow rule.

### Cited a concrete test count (392) in the docs
- **Choice:** Updated the "automated checks behind it" stat to 392 (the current
  passing suite) rather than dropping the number.
- **Rationale:** The existing docs already committed to the pattern; 392 is
  verifiable at publish time and PR #189 added no tests, so it stays accurate.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../web/templates/base.html` | Modified | Drop Strategy nav tab |
| `.../web/app.py` | Modified | Remove /strategy route + docstring entry |
| `.../web/guides/strategy.html` | Deleted | Embedded lead-gen deck removed |
| `.../tests/test_web_guides.py` | Modified | Drop strategy test + nav assertion |
| `.../web/guides/user-guide.html` | Modified | Refresh content (EN/DE/PT) |
| `.../web/guides/tool-flow.html` | Modified | Refresh content (How it works) |
| `.../deliverables/expense-recon-user-guide-2026-06-16.html` | Modified | Re-sync standalone copy |
| `.../deliverables/expense-recon-tool-flow-2026-06-16.html` | Modified | Re-sync standalone copy |

All paths under `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/`.

---

## Current Status
Both PRs merged to `main`. Fly app `brisken-expense-recon` is on **release v8**
(built from merged main @ `c77f71b`): the Strategy tab/route are gone and the
refreshed Guide + How-it-works are live. App is gated by
`EXPENSE_RECON_ACCESS_CODE`, scales to zero, Frankfurt region.

The recon subtree is NOT in CI; the local gates are the source of truth
(pytest + calibrate, run before each PR). The repo's own CI (platform / spell /
playwright / hooks) still runs on each PR and was green for both.

---

## Next Steps
1. None outstanding for this work. The tool is current and deployed.
2. (Standing) Confirm with Dirk the persisted OpenAI key is the rotated one
   (carryover from prior sessions; not touched here).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/app.py` (routes)
- `.../src/expense_recon/web/guides/user-guide.html` + `tool-flow.html` (served docs)
- `.../src/expense_recon/matching/deterministic.py` (card-scoping + exact-FX + FX band)
- `.../src/expense_recon/ingest/statement_pdf.py` + `ingest/expense_csv.py` (inputs)

### Open Questions
- None for this work.

### Working Notes
- Work happened in the `agentic-ops1-recon-main` worktree (off main), per the
  recon subtree convention. Untracked WIP in that worktree (deliverables WIP
  `*-2026-06-16.html`, `recon-web-data/`, `brisken-onepilot-website-*`) must
  never be staged.
- The Strategy deck was embedded by PRs #185/#186 earlier the same day; this
  session reverted just the tool embedding. The standalone lead-gen deck
  (`workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html`)
  is unrelated and was left untouched.
- Fly does NOT auto-deploy on merge (unlike Vercel). Served docs ship inside
  the wheel, so any served-doc/template change needs an explicit `flyctl deploy`
  to go live. This was the cause of the "Strategy still showing" screenshot
  (live app was on v7, pre-removal).
- Login gate is off locally unless `EXPENSE_RECON_ACCESS_CODE` is set, so a
  local `expense-recon-web --no-open` run can render `/guide` + `/how-it-works`
  without auth for verification.

### Reference Materials
- PR #188: https://github.com/011matthias/agentic-ops1.01/pull/188
- PR #189: https://github.com/011matthias/agentic-ops1.01/pull/189
- Live app: https://brisken-expense-recon.fly.dev/ (gated)

---

## How to Continue
The work is complete and deployed. To pick up further recon work, resume in the
`agentic-ops1-recon-main` worktree off main, run the two local gates
(`pytest` + `calibrate`) before any PR, and remember Fly needs an explicit
`flyctl deploy` for served-doc/template changes to go live.

---

## Strategic Feedback

### What Worked Well This Session
- The "read the actual code first, then write" instruction (B4) was explicit in
  the task and paid off: every capability claim in the refreshed docs traces to
  a verified code path (exact-FX, card-scoping, three outputs, unknown-currency
  flagging), with zero invented features.
- Splitting into removal-then-content PRs kept each diff small and reviewable;
  both merged on green with no rework.

### Suggestions
- For non-Vercel deploy targets (Fly), it's worth a standing habit: when a
  client-facing change merges, state plainly that the live app is unchanged
  until `flyctl deploy`. Done here, but the "why is it still there" screenshot
  shows the gap between merge and deploy is an easy place for a client to be
  surprised.

### System Health
- The recon subtree being outside CI means the two local gates
  (pytest + calibrate) are the only behavior check before merge; the repo CI
  green-lights the PR without exercising recon. This is a known, documented
  arrangement and held fine, but it puts the verification burden entirely on
  agent discipline. No drift this session.
- Autonomy score: 0 — fully autonomous session (the deploy authorization was
  the expected Band-3 gate, not a friction intervention).

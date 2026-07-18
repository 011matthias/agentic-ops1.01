# Checkpoint: Optimize Onboarding + Brisken Match Labeling

**Date:** 2026-07-17
**Status:** SHIPPED — PRs #261 (multi-project oversight) + #262 (label fixture builder) merged; architecture corrected to CSV-statement + ER-PDF production shape

---

## Summary

Operator onboarding session for the optimize-loop (live worktree demo with the
page-weight scorer, tamper test, revert path), then two shipped increments: the
multi-project oversight layer (`optimize_overview.py` + RECIPES convention) and
Block 1 of the first real target — the Brisken expense-recon match ground-truth
labeling module. Owner corrected the target architecture at the end: production
statements are CSV; the Zoho Expense ER PDF is the side that gets enriched.

---

## What Was Done This Session

### Optimize-loop operator onboarding (teach, throwaway)
1. Live demo in an isolated worktree at origin/main: manifest -> `start`
   (baseline 26145) -> KEEP round (-720) -> deliberate-regression DISCARD ->
   `stop`; worktree + branches deleted, nothing shipped.
2. Tamper test: an Edit to `tools/scorers/page-weight.py` in the WORKTREE was
   NOT blocked by scorer-lock-gate (hook covers the primary checkout); the
   engine's `resume` dirty-tree recovery wiped it and the hash checks would
   have refused any round. Finding logged (see friction).
3. CRLF lesson: `core.autocrlf` re-expanded line endings on checkout ->
   REPRODUCIBILITY MISMATCH caught by the engine; ~510 B of the demo win was
   phantom.

### Multi-project oversight (PR #261, merged `237d5d6`)
1. Convention in `docs/optimize/RECIPES.md` "Many projects, one oversight
   surface": manifests carry `project: <slug>`, tags slug-prefixed and unique
   forever, one worktree per concurrent run, lifecycle = shipped | dead-end.
2. `tools/optimize_overview.py` — derived fleet view (journaled runs grouped by
   project, ACTIVE runs via worktree run.json scan, WARNINGS for interrupted /
   summary-less runs). 4 subprocess behavior tests; first CI push was red
   (test imported yaml; hooks CI env is dep-free) — rewrote to the
   test_optimize_run subprocess pattern, green, auto-merged.

### Brisken p1 match labeling (PR #262, merged `f1444cf`)
1. `expense_recon/labeling.py` + `expense-recon label propose|accept|check`:
   ground-truth pairing fixture builder. Evidence independent of the matcher
   (E1 bank-printed original amount, E2 same-currency exact, E3 Zoho
   base-amount, E4 reference hit); AUTO only conclusive + mutually unique;
   ambiguity excluded by the human, never guessed. 11 tests; package suite
   440 passed / 21 skipped.
2. Ran `propose` on all 6 real month-bundles: CSV-bridge bundles are
   evidence-starved (4 AUTO / 218 receipts). PDF-statement variant on 2026-03:
   29/45 AUTO via E1 (and the 2026-04-04 statement cycle empirically covers
   the March ER; the 2026-03-04 one scored zero).
3. Status file `status/p1-expense-reconciliation.md` bumped (new element row).

---

## Key Decisions Made

### Production shape: CSV statement + enriched ER PDF (owner correction)
- **Choice:** The scored/optimized pipeline consumes Chris's Chase CSV export
  plus Zoho Expense ER PDFs enriched by `ingest/expense_report_pdf.py` (which
  already extracts Ref#, payment_mode, zoho_category, exchange_rate,
  base_amount). Statement PDFs are OFFLINE label-truth corroboration only.
- **Rationale:** Owner: "the point is for the statement to be CSV but the zoho
  expense will be PDF that we have to enrich and improve before merging."
  My statement-PDF push was an over-rotation on a demo win (friction row).

### Labels may use richer evidence than the scored pipeline
- **Choice:** Truth-building uses ALL available evidence (incl. statement
  PDFs); the matcher under test only ever sees production-shape inputs.
- **Rationale:** Standard truth/test separation; keeps labels maximally
  correct without leaking non-production signal into the metric.

### Multi-project oversight is derived, not indexed
- **Choice:** No hand-maintained run index; `optimize_overview.py` derives
  from run dirs + worktree state each call.
- **Rationale:** A derived view cannot rot; an index file would.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| tools/optimize_overview.py (+ INDEX.md row) | Created (PR #261) | fleet view across projects |
| tools/tests/test_optimize_overview.py | Created (PR #261) | 4 subprocess behavior tests |
| docs/optimize/RECIPES.md | Modified (PR #261) | `project:` field + Many-projects section |
| workspace/.../expense_recon/labeling.py | Created (PR #262) | label propose/accept/check |
| workspace/.../expense_recon/cli.py | Modified (PR #262) | `label` subcommand dispatch |
| workspace/.../tests/test_labeling.py | Created (PR #262) | 11 tests incl. CLI round-trip |
| workspace/clients/brisken/status/p1-expense-reconciliation.md | Modified (PR #262) | labeling element row |
| context/.../by-month/*/labels-proposed*.csv + run-pdf-*.json | Created (gitignored) | proposal state for the accept pass |

---

## Current Status

main at `f1444cf`. Optimize infra: engine + locks + pins + fleet overview all
shipped; page-weight is still the only pinned scorer. Brisken match-accuracy
path: labeling tool shipped and proven on real data; no labels.csv accepted
yet; bundles still CSV-bridge shape. Local main checkout was 2-4 commits behind
origin through the session (sibling session held the tree; all work ran in
worktrees off origin/main).

---

## Next Steps

1. **Source the six ER PDFs** (ER-00214/00215/00216/00194/00181/00183) — not in
   local context; only CSV derivatives are. Try the recon app's intake archive
   on the Fly volume, else SharePoint/Zoho via read-only Graph.
2. **Rebuild the 6 bundles production-shape** (statement.csv + ER-PDF receipts
   via `expense_report_pdf` source), rerun `label propose` — expect E3/E4 to
   carry the FX months.
3. **Accept pass**: review AUTO evidence, decide PICK/NONE rows, `label accept`
   -> labels.csv per month; statement PDFs as offline corroboration.
4. **Block 2**: MatchConfig (incl. the hardcoded 0.55/0.30/0.15 blend weights,
   deterministic.py:266) loadable from a config file — the optimize asset.
5. **Block 3**: `tools/scorers/recon-match-accuracy.py` (maximize, fixture
   checksum self-check, held-out floor guard) — needs the user's explicit
   `SCORER_LOCK_ALLOW=1` at pin time.
6. Then manifest `project: brisken`, tag `brisken-match-accuracy-v1`, worktree,
   mode continuous.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/labeling.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/expense_report_pdf.py`
- `docs/optimize/RECIPES.md` (constructed-metric protocol + multi-project section)
- `.claude/rules/rule_optimize_loop.md`

### Open Questions
- Where do the six bundle-month ER PDFs live? (Fly volume intake archive vs
  SharePoint vs Zoho export — first task next session.)
- 2024/2025 historic months have no statement PDFs: accept lower AUTO coverage
  there, or drop them to held-out-only roles?

### Working Notes
- Bundle home: `workspace/clients/brisken/context/expense-reconciliation/expense-reports/csv/by-month/`.
  Each dir: statement.csv + receipts.csv + run.json (+ new labels-proposed*.csv,
  run-pdf-*.json experiments; supersede when bundles are rebuilt).
- Statement-cycle mapping is empirical: the 20260404 PDF covers the March ER.
- `expense_report_pdf.py` already extracts everything E3/E4 need; "enrich and
  improve" = quality/coverage of THAT extractor (also the natural second
  optimize target: extraction-field accuracy vs the same labeled months).
- Worktree runs rely on engine-layer locks; Write/Edit-layer hooks cover the
  primary checkout only (friction row; structural fix = resolve repo root from
  the target file path in the gates).
- CI hooks job is dep-free (`uv run --no-project --with pytest`): drive tools
  as subprocesses in tests, never import PEP-723 deps directly.

### Reference Materials
- PR #261 https://github.com/011matthias/agentic-ops1.01/pull/261
- PR #262 https://github.com/011matthias/agentic-ops1.01/pull/262
- Prior checkpoint: `docs/2026-07-17 - Optimize-Loop Autoresearch Infrastructure/Checkpoint.md`

---

## How to Continue

Open a Brisken-scoped session (`/resume brisken`), start at Next Steps 1-2 (ER
PDF sourcing + bundle rebuild). The fresh-chat prompt written at the end of this
session's transcript carries the full brief.

---

## Strategic Feedback

### What Worked Well This Session
- The teach-by-doing demo (real engine, throwaway worktree) surfaced two real
  findings a doc walkthrough never would: the worktree hook-coverage gap and
  the CRLF phantom-win class.
- Enumerate-before-build paid twice: `calibrate` + `expense_report_pdf`
  already contained most of what the scorer needs; the labeling module reused
  loaders instead of reinventing ingestion.

### Suggestions
- The production-shape correction came AFTER the statement-PDF experiment.
  For pipeline-shaped targets, confirm the production input shape as part of
  the fit check itself, before choosing what to enrich (added to working
  notes; candidate line for comd_optimize Step 1).

### System Health
- Enforcement hooks assume the primary checkout while the optimize workflow
  standardizes on worktrees; that mismatch is now a named structural gap with
  a known fix. Until closed, worktree runs are engine-enforced only.
- Autonomy score: 1 human intervention this session (architecture correction).

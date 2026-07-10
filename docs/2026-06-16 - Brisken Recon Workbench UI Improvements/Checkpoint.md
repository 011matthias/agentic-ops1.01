# Checkpoint: Brisken Recon Workbench UI Improvements

**Date:** 2026-06-16
**Status:** Complete — all 7 PRs merged to `main`, verified live

---

## Summary
Shipped 7 independently-mergeable PRs (#165–171) improving the Brisken
expense-reconciliation review workbench (FastAPI local web, Path A). Each
went feature-branch → CI-green → squash-merge from the
`agentic-ops1-recon-main` worktree off `main`.

---

## What Was Done This Session
### Workbench UI features (one PR each)
1. **PR A (#165) Review speed** — server-side "Confirm all matched" batch
   route, j/k/c/r/e keyboard triage with row highlight, sticky "Ready to
   post?" bar (live undecided count / unreconciled-by-currency / unmapped
   lines) gating the report download until undecided == 0.
2. **PR B (#166) Manual match** — assign/steal a receipt by hand;
   `apply_decisions` rewritten as a conflict-safe two-pass resolver
   (confirmed-first, latest-confirm wins a contested receipt via a new
   `Decision.updated_at`); `build_view` now renders from the same resolved
   outcome as the export so screen and export can't disagree.
3. **PR E (#167) Zoho CSV download** — `GET /runs/{id}/zoho.csv` +
   `regenerate_zoho` mirroring `regenerate_report`; gated download button.
4. **PR C (#168) Memory legibility** — "Auto-filled (memory)" stat,
   LEARNED-only row filter, per-line "This was wrong" → JSON `/forget` +
   reopen reclassify dropdown.
5. **PR D (#169) Match transparency** — amount/date/vendor sub-scores
   stored on `Match` (serialized), expandable on the candidate; nearest
   free-receipt hint for unmatched charges.
6. **PR F (#170) Run progress** — background the pipeline + `/jobs/{id}`
   status-poll page; `create_run` split into `prepare_run` (fast, validates)
   / `execute_run` (slow, backgrounded); `EXPENSE_RECON_WEB_SYNC` test seam.
7. **PR G (#171) Compare runs** — `/compare` view: summary deltas +
   per-charge bucket changes, mirroring the CLI `diff` (unioned ids).

### Verification
- Full suite on merged `main`: **341 passed, 2 skipped** (was 321 at start).
- `calibrate` exit 0 on every PR (invariant OK, no double-binding,
  categorization gate OK).
- Live Playwright smoke on merged `main`: async run → running page → poll →
  workbench; confirm-all opened the gate; keyboard reject live-updated the
  bar; manual steal moved a receipt and freed the former charge (invariant
  held); expandable sub-scores + near-miss; Zoho/report links; compare page.

---

## Key Decisions Made
### PR F: full background + status poll (not just a spinner)
- **Choice:** background the run via FastAPI BackgroundTasks + a polling
  page, with a sync env-var seam for tests.
- **Rationale:** user picked the fuller option; the seam preserved the
  ~30 existing web tests' immediate-303 contract via `tests/conftest.py`.

### PR B: allow re-assigning (stealing) an already-matched receipt
- **Choice:** a manual match can take a receipt held elsewhere; the former
  charge falls back to unmatched.
- **Rationale:** user picked it; required the two-pass resolver to keep the
  one-receipt-one-transaction guarantee under manual edits.

### PR D: store sub-scores on `Match` (vs recompute in the view)
- **Choice:** add `amount_score`/`date_score`/`vendor_score` to `Match`.
- **Rationale:** single source of truth in the matcher; defaults keep old
  snapshots + reviewer-built matches valid.

---

## Files Modified
All under `workspace/clients/brisken/automations/expense-reconciliation/`.

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/service.py` | Modified | build_view refactor (resolved-outcome render), confirm-all, manual-match validate, memory/near-miss/compare, prepare/execute split |
| `src/expense_recon/web/app.py` | Modified | confirm-matched, manual-match, zoho.csv, forget(JSON), compare, jobs + background run routes |
| `src/expense_recon/web/store.py` | Modified | `Decision.updated_at` |
| `src/expense_recon/web/serialize.py` | Modified | serialize Match sub-scores |
| `src/expense_recon/web/templates/{workbench,index,base}.html` | Modified | ready bar, keyboard, manual-match, memory, sub-scores/near-miss, submit feedback, Compare nav |
| `src/expense_recon/web/templates/{running,compare}.html` | Created | poll page; compare view |
| `src/expense_recon/matching/{types,deterministic}.py` | Modified | Match sub-score fields, set in match_one |
| `tests/test_web_*.py` (+`conftest.py`) | Created/Modified | 17 new tests; sync seam |

Memory written: `reference_repo_tooling_gotchas.md` (gh slug + playwright upload sandbox).

---

## Current Status
All work merged to `origin/main` (#165–171). No platform/Make/n8n
infrastructure for this client (local Python tool — no `infrastructure.yaml`,
ops/MCP/infra-reconciliation checks N/A). The `agentic-ops1-recon-main`
worktree is on a local `recon-ui-verify` branch pointing at merged `main`.

---

## Next Steps
1. (Optional) CoA upload on the run form so PR E's Zoho export resolves real
   account names instead of `Card: {account_id}` placeholders.
2. (Optional) Delete the `recon-ui-verify` local branch in the worktree.
3. Nothing blocking — series is done.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (the hub: build_view, apply_decisions, prepare/execute, compare)
- `.../src/expense_recon/web/app.py` (all routes)
- `.../BLUEPRINT.md` (Slice 9 cross-run learning context)

### Open Questions
- None blocking. CoA-on-the-form is the only natural follow-up.

### Working Notes
- **Worktree:** all p1 finance work was done in `agentic-ops1-recon-main`
  (off `main`), NOT the main clone (which is on `client/brisken/lead-gen-onepilot`).
  The web module lives only on `main`, never on the lead-gen branch.
- **CI does not run the recon subtree** — the pytest suite + `calibrate` are
  LOCAL pre-ship gates; run both green before every PR.
- **Test seam:** `EXPENSE_RECON_WEB_SYNC=1` (set suite-wide in
  `tests/conftest.py`) makes POST /runs synchronous (303) so legacy tests
  pass; PR-F async tests delete it per-request.
- **Gotchas (now in memory):** GitHub slug is `agentic-ops1.01`; playwright
  upload needs lowercase `c:` and rejects sibling-worktree paths.

### Reference Materials
- PRs https://github.com/011matthias/agentic-ops1.01/pull/165 … /171

---

## How to Continue
The series is complete. For a follow-up, `/resume brisken`, then work in the
`agentic-ops1-recon-main` worktree off `main` (branch `client/brisken/<desc>`),
run `uv run --extra dev --extra web pytest -q` + `uv run --extra web
expense-recon calibrate --config examples/run.example.json` before each PR.

---

## Strategic Feedback

### What Worked Well This Session
- The upfront design-fork gate (one `AskUserQuestion` after orienting,
  before any code) locked PR F/B/D direction once, so no mid-build rework.
- Splitting into 7 small PRs kept each CI run fast and each merge low-risk;
  the worktree-off-main pattern let the lead-gen branch stay untouched.

### Suggestions
- The Brisken recon tool now has a rich web layer but no `infrastructure.yaml`;
  a tiny one (even just recording "local Python tool, no orchestrator") would
  stop future checkpoints from re-deriving that it has no platform section.

### System Health
- The recon subtree is invisible to CI by design, so its 341-test suite +
  `calibrate` gate rely entirely on agent discipline. A `local-gates`
  pre-push reminder (or a thin CI job that runs just `calibrate` on the
  subtree) would harden that without pulling the whole suite into CI.
- Autonomy score: 0 human interventions this session — fully autonomous
  build (the one `AskUserQuestion` was a planned design gate, not an
  unblock). 2 minor self-detected slow-paths (gh slug, playwright upload),
  both resolved to memory.

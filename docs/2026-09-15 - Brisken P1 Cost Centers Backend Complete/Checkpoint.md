# Checkpoint: Brisken P1 Cost Centers Backend Complete

**Date:** 2026-09-15
**Status:** Backlog item 47 backend shipped (PR #834 merged, Fly v120 live, consumer-driven). Lovable half written, not applied.

---

## Summary

Steps 3 and 5 of the cost-centers build landed this session: the month report partitions its listing per cost center, and `GET /api/cost-centers/totals` rolls spend up across batches. With steps 1 and 2 already on the branch, the backend is complete; PR #834 merged on CI green and v120 serves it, proven by an authenticated live probe and a cold SPA drive.

---

## What Was Done This Session

### Step 3, the month report grouped by cost center
1. `build_expense_report_pdf` sections accept a generic `caption` / `label` beside item 38's `person` / `on_roster`, plus `sections_heading` / `sections_note` rendered once above the partition.
2. `build_expense_report` partitions a company month on the resolved cost center whenever the chain resolves or flags a row; named centres in name order captioned `Name (kind)`, unassigned rows as the final section, the stated limit as `COST_CENTER_SCOPE_NOTE`. Trip reports unchanged. The route passes live settings.
3. Five route-level tests through the PDF route plus one builder test; three mutation points proven, including the empty-registry short-circuit reddening the flat-listing test THROUGH the report.

### Step 5, the cross-month totals
1. `build_cost_center_totals(store, date_from, date_to)` scans every expense batch (months and trips), takes the export's own rows, resolves through the same chain, excludes confirmed private rows, emits per-centre buckets, an explicit unassigned bucket, `n_batches` / `n_rows` / `n_undated`, and the note verbatim.
2. Route `GET /api/cost-centers/totals?from=&to=` with inclusive ISO bounds; malformed or inverted range is a 400 with prose.
3. Refresh-master-data now emits `row_cost_centers`, a step-2 gap the spec promised and writing the Lovable prompt exposed.
4. Seven route-level tests plus one refresh test; four mutation points proven.

### Step 6 written, contract, ship
1. `docs/lovable-cost-centers-prompt.md` promoted out of item 47, registered in PROMPT-STATUS as not applied with the whole-map-replace sequencing gate.
2. `docs/api-contract.md` re-pinned: report subsection, totals subsection, carriers bullet.
3. Merged origin/main into the branch (three append-only docs conflicts), suite 1628 green on the merged tree, PR #834 opened, merged on CI green, deployed as v120 from a detached origin/main worktree.
4. Deploy verified by behaviour: authenticated totals returns the real book (6 batches, 125 rows, all unassigned, `n_undated` 1); a live month's payload carries the new keys silently and its PDF stays flat; agent-browser cold drive through the login gate rendered the June 2026 grid with no fallback strings.

---

## Key Decisions Made

### The report's partition gate derives from the chain, never from the registry
- **Choice:** partition when any row resolves or flags; no `if registry:` in the report.
- **Rationale:** the empty-registry contract has exactly one home. A second guard would make neither load-bearing; the mutation test proves the report goes flat only because `resolve` is silent.

### Undated rows always count in the totals
- **Choice:** a range cannot exclude a row with no date; it is counted and declared in `n_undated`.
- **Rationale:** silently dropping it would understate a project; naming it keeps the figure honest. The live book has one such row today.

### An empty registry makes the roll-up all-unassigned, not silent
- **Choice:** `cost_centers: []` plus everything in `unassigned`.
- **Rationale:** the roll-up states a fact; the row-level review flag is what must stay silent, and it does.

### The split-receipt route test was dropped, not faked
- **Choice:** slice alignment is pinned at builder level only.
- **Rationale:** a two-account receipt through the route needs mock classification responses that no existing API-level test wires; adding that plumbing is its own change.

### Deploy proof by behaviour, not release number
- **Choice:** authenticated probe plus SPA drive.
- **Rationale:** a sibling session shipped v119 one minute before v120, and the unauthenticated 401 probe turned out blind (auth precedes routing on the live app), so neither the version nor the status code could prove the tree.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/src/expense_recon/cost_centers.py` | edit | `COST_CENTER_SCOPE_NOTE`, one constant for both surfaces |
| `.../output/month_report_pdf.py` | edit | generic section caption/label, partition heading and note |
| `.../web/service.py` | edit | report partition, `build_cost_center_totals`, `row_cost_centers` |
| `.../web/app.py` | edit | report route passes settings; totals route |
| `.../tests/test_cost_center_report.py` | new | 5 tests through the PDF route |
| `.../tests/test_cost_center_totals.py` | new | 7 tests through the totals route |
| `.../tests/test_cost_center_resolution.py` | edit | refresh count test |
| `.../tests/test_month_report_pdf.py` | edit | captioned-section builder test |
| `.../docs/api-contract.md` | edit | report and totals subsections, carriers bullet |
| `.../docs/lovable-cost-centers-prompt.md` | new | step 6, pasteable after deploy |
| `.../docs/PROMPT-STATUS.md` | edit | not-applied row with its gate |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | steps 3 and 5 recorded |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 47 Lovable half repointed to the prompt doc |

---

## Current Status

Item 47 backend is live on `brisken-expense-recon` v120 (commit ef121c23 on main). The registry is empty in production, so every new field is inert until the owner defines a cost center, and nothing in the SPA changes until the Lovable prompt is pasted. Module suite 1628 passed, 2 skipped on the merged tree; ruff clean on every file this branch touched (12 pre-existing errors on main in untouched files). Ops status line from pre-flight: platform unknown plan, no comms-log on file. Project status: p1 files current; p2-lead-gen-general (86d), p2-product-decks (54d), p2-rome (55d), p2-targeting (55d) stale.

---

## Next Steps

1. Owner-side: paste `lovable-cost-centers-prompt.md` sections 1 and 2 first, publish, prove the settings bundle round-trips `cost_centers` and `default_cost_center` (bundle grep of the save payload) before anyone types a cost center; then the rest of the prompt; re-audit PROMPT-STATUS.
2. Owner-side data entry once the bundle proves round-trip: define the cost centers; the review flag starts firing only then.
3. July receipts: 19 PDFs in the primary clone's `.scratch/recon-july/criss-receipts/` await the app's OCR; ingest into Criss's live July month `50622baec444` is invasive and needs a per-action go including the route (direct ingest vs forwarding to expenses.brisken.com).
4. Item 50 open half: a probe that records machine state when "Failed to fetch" fires.
5. Refresh or retire the four stale p2 status files.
6. Read-only look at the one live row with no date (`n_undated: 1` in the totals); it is a review exception somewhere in the six months.
7. Small cleanup PR for the 12 ruff errors on main (8 auto-fixable), none in cost-center files.
8. Prune worktree `agentic-ops1-cc` and the merged remote branch when nothing else needs them.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (the cost-centers row carries every decision)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`, the cost-centers section and its two subsections
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-cost-centers-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`, items 47 to 54

### Open Questions
- Which route for the July ingest (direct vs mail forward), owner decision.
- Whether the empty-registry roll-up (all unassigned) is the shape the owner wants on the cross-month screen, or whether the screen should hide the table until one centre exists; the prompt renders it as a fact with explanatory copy.

### Working Notes
- `tools/regress_check.py` spawns the test outside Git Bash: `--test` and `--file` need `C:/` paths, `/c/` fails with "system cannot find the path". Same for any path inside `python -c`.
- `agent-browser wait --load networkidle` never returns on the live SPA; open, sleep a few seconds, snapshot. Playwright MCP here is CDP to the user's Edge on :9222 and was not listening; a named agent-browser session (`--session <name>`) worked cold through the login gate.
- The live API answers 401 before routing, so an unauthenticated status probe cannot distinguish a present route from an absent one; log in via `POST /api/login` with the operator code from the local vault (entry labelled matthias) and probe with the Bearer token.
- Live totals at deploy time: BRL 3,922.51, EUR 19,102.47, USD 34,105.62 across 6 batches and 125 rows, all unassigned.
- The heredoc guards fire above 80 lines or on a triple-quoted block; write scripts to the scratchpad with the Write tool and run them.
- Merge conflicts with the parallel round were docs-only append hunks (PROMPT-STATUS rows, api-contract summary rows and appended sections, backlog frontmatter date); the resolver kept both sides.

### Reference Materials
- PR #834: https://github.com/011matthias/agentic-ops1.01/pull/834
- Live API: https://brisken-expense-recon.fly.dev (v120); SPA: https://expenses.brisken.com

---

## How to Continue

The backend is done; nothing on the branch is half-wired. Next work is owner-gated (Lovable paste, data entry, July ingest go) or unrelated to cost centers (item 50 probe, p2 status refresh, ruff cleanup). Start from the p1 status row, then the backlog items 48 to 54 for the other open defects.

---

## Strategic Feedback

### What Worked Well This Session
- `regress_check.py` at every wiring point (eight this session, fifteen across the item) turned "the suite is green" into "the suite bites"; the empty-registry mutation reddening a test through the report route is the proof the contract has one home.
- Taking the deploy probe's baseline BEFORE deploying exposed that the 401 probe was blind, so the verification switched to an authenticated read and a cold SPA drive instead of a confident nothing.

### Suggestions
- A PreToolUse hook that flags a `/c/...` POSIX path inside a `python -c` body, a `--test`, or a `--file` argument on Windows: third recurrence of the class (2026-09-11 twice, today), each time one wasted call and a retry.

### System Health
- Autonomy: 0 human interventions, fully autonomous session.
- The session header block was not output at session start (skipped-gate, self-detected at checkpoint).
- The parallel round means a Fly release number no longer identifies a tree; deploy verification has to be behavioural every time.

# Checkpoint: Brisken Expense-Recon Usability Loop R1-R2

**Date:** 2026-08-13
**Status:** Rounds 1+2 shipped + deployed (Fly v58); round 3 designed, not built

---

## Summary

First two rounds of the receipt-first test-and-fix loop shipped and
live-verified: non-receipt uploads (statement pages, report summary sheets)
are now quarantined instead of becoming phantom expenses (PR #516), and the
literal string "null" can no longer appear as an Expense Account (PR #518).
Improvement tracking was centralized into one backlog file on owner
directive; the next round (vendor-drift / extraction cache) is designed and
queued there.

---

## What Was Done This Session

### Round 1 — non-receipt quarantine (PR #516)
1. Resolved the brief's open money question: `receipt_01` is page 7 of a
   Zoho ER, a summary page carrying BOTH disputed totals (8,796.35 BRL
   column total, $1,837.51 USD summary). Not a money bug; a missing
   document-type concept.
2. Vision extraction now classifies every file (`document_type`: receipt |
   statement | report_summary | other; whitelisted; defaults "receipt" so
   exclusion must be earned). `generate_expenses` + the web incremental add
   exclude non-receipts as warning ParseIssues (grid `parse_issues`, ingest
   `issues`, CLI print). `reconcile()` untouched.
3. Verified failure-first (test failed on unfixed code), then live with
   gpt-4o-mini: smoke10 (summary page excluded, money fields stable vs prior
   run) and Criss's real May folder (7/7 Chase statement PDFs excluded,
   20/20 receipts kept, zero leakage).

### Round 2 — "null"-string labels (PR #518)
1. gpt-4o-mini intermittently returns the STRING "null" for
   category/zoho_account; truthy, so it reached the CSV as a literal `null`
   account. `_opt_label` collapses sentinel spellings to None at both
   ClassificationResult parse sites; rows show `(uncategorized - assign)`.
2. Tested via `_opt_label` matrix + end-to-end through the real
   `OpenAIClient.classify_line_items` parse with a stubbed SDK response.

### Ship + deploy
1. Suite 1024 → 1043 passed, 2 skipped. PRs #516/#518 merged on green CI
   (three transient GitHub 502s absorbed by a retry loop).
2. Fly deploy from the refreshed detached `agentic-ops1-deploy` worktree;
   verified live: healthz 200, `/api/expense-batches` 401 not 404 (flag
   intact), release v58 complete.

### Central improvement tracking (owner directive this session)
1. `workspace/clients/brisken/status/p1-improvement-backlog.md` — THE one
   list: 5 ranked open items in plain language + shipped history (PR #529).
2. `workspace/clients/brisken/status/p1-recon-loop-prompt.md` — paste-in
   runbook for the next round, pointing at the backlog (PR #529).
3. Status file row + memory `project_brisken_expense_recon_usability_loop`
   updated to point at the backlog; frontmatter `state:` fix (PR #531).

---

## Key Decisions Made

### Exclusion must be earned, never defaulted
- **Choice:** only an explicit non-receipt classification excludes a file;
  absent/junk classification stays "receipt".
- **Rationale:** a phantom row is visible and deletable; a silently dropped
  real receipt is money lost without a trace.

### Quarantine, not auto-routing
- **Choice:** set non-receipts aside loudly; do NOT auto-feed statement
  pages into Mode B.
- **Rationale:** statement-attach flow is not in daily use yet; speculative
  routing risks touching behavior Criss depends on. Recorded as backlog
  item 5 for later.

### Fix "null" at the parse layer, not the export
- **Choice:** sanitize in `llm/client.py` where payloads become
  ClassificationResults, not in `_debit_account_and_note`.
- **Rationale:** every consumer (grid, learning, both exports) sees a clean
  no-category; an export patch would leave the poisoned string in the run.

### One central backlog in `status/`
- **Choice:** all improvement suggestions live in
  `p1-improvement-backlog.md`; chat reports and checkpoints only point at it.
- **Rationale:** owner correction — suggestions scattered in chat get lost;
  the loop runbook now instructs appending new ideas there in-session.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/llm/client.py` | edit | document_type in schema/prompt/parse; `_opt_label` sentinel sanitizer |
| `.../src/expense_recon/matching/types.py` | edit | `Receipt.document_type` field |
| `.../src/expense_recon/ingest/receipts_folder.py` | edit | carry classification into Receipt |
| `.../src/expense_recon/web/serialize.py` | edit | snapshot round-trip + legacy default |
| `.../src/expense_recon/cli.py` | edit | `split_non_receipt_documents` + partition in `generate_expenses` + CLI issue printing |
| `.../src/expense_recon/web/service.py` | edit | incremental-add quarantine via `NON_RECEIPT_LABELS` |
| `.../tests/test_document_type_quarantine.py` | new | 17 tests, failure-first, incl. 2 web-layer |
| `.../tests/test_categorize_llm.py` | edit | null-label regression tests |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | loop row + `updated:` (PR #520) |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | new | central improvement list (PRs #529/#531) |
| `workspace/clients/brisken/status/p1-recon-loop-prompt.md` | new | next-iteration runbook (PRs #529/#531) |
| memory `project_brisken_expense_recon_usability_loop.md` | new | loop state + central-tracking pointer |

---

## Current Status

Fly v58 live and verified (healthz 200, receipt-first surface gated 401).
Suite 1043 passed / 2 skipped. Backlog has 5 open items; item 1 (extraction
cache) + item 2 (CLI registry) are the designed next round. Brisken
platform ops status: unknown plan, ~?/? ops/mo, last assessed ? (no
`platform` section data — FastAPI/Fly client, no orchestrator ops to
audit). PR #531 (frontmatter `state:` keys) merging this session.

---

## Next Steps

1. Run the next loop round: paste
   `workspace/clients/brisken/status/p1-recon-loop-prompt.md` into a fresh
   chat (targets backlog items 1+2: per-image extraction cache + registry
   on CLI runs).
2. Hand the owner a Lovable prompt for backlog item 3 (set-aside files
   strip in the review screen, PT reason + override).
3. Owner/Criss conversation for backlog item 4 (split rows vs one row per
   receipt) — five-line change either way once decided.
4. Stale p2 status files flagged by the sweep (p2-lead-gen-general 53d,
   p2-outreach 53d, p2-rome/p2-targeting/p2-onepilot-site 22d) belong to
   the live p2 sessions; not touched here to avoid cross-session collisions.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`
- memory `project_brisken_expense_recon_usability_loop`

### Open Questions
- Split rows (backlog item 4): does Criss expect one row per receipt?
- When does the owner want the Lovable set-aside strip (item 3)?

### Working Notes
- Money fields verified stable run-to-run on identical code; ALL observed
  drift is text (vendor spellings, reference numbers, tax labels,
  line-item descriptions) at temperature 0. Evidence preserved in set 3's
  `expenses-BASELINE/-NEW/-NEW2/-QUARANTINE-RUN3.csv`.
- KI-MASSA receipt legitimately split 47.50 → 41.30 + 6.20 (two accounts,
  same Reference#); categorization drift makes the split appear/disappear
  between runs — cosmetic, feeds backlog item 4.
- CLI `_run_expense_generation` passes `registry=None`, `expense_memory=None`
  — web path is the only registry consumer (backlog item 2).
- GitHub API threw 502s mid-merge twice; a 5×15s retry loop around
  `gh pr merge` + state check absorbed it (pattern worth reusing).
- Do NOT loosen the learned-store exact match to fuzzy (cross-wires
  merchants); ruled out in backlog item 1.

### Reference Materials
- PRs #516, #518, #520, #529, #531; Fly release v58
- `.scratch/criss-recon-may/` + `.scratch/criss-recon-runs/05d3db59b225/`
  (test sets with kept outputs)

---

## How to Continue

Paste `workspace/clients/brisken/status/p1-recon-loop-prompt.md` into a
fresh chat. It carries the run recipe, traps, known facts, and points at
the backlog for target selection.

---

## Strategic Feedback

### What Worked Well This Session
- Looking at the actual image resolved in one Read what two sessions of
  CSV-diffing framed as a "currency flip bug": the input was never a
  receipt. Ground-truth the artifact before theorizing about the pipeline.
- Failure-first testing caught its worth immediately: the quarantine test
  demonstrably failed on unfixed code, so the later green meant behavior,
  not wiring.

### Suggestions
- The improvement backlog pattern (one ranked file per workstream, chat
  reports only point at it) is worth adopting for other long-running
  workstreams (lead-desk, outreach engine) — same failure mode exists
  there: suggestions scattered across checkpoints.

### System Health
- Autonomy: 1 human intervention (owner redirected improvement-suggestion
  tracking to a central file + plainer language — logged as
  strategic-gap, fixed structurally with the backlog + runbook).
- Gates: B1:0 B2:4 B3:1 skipped:0. Register >200 KB advisory handled via
  `archive-register` in this checkpoint's docs PR.

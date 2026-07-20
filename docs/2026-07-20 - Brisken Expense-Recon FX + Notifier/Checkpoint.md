# Checkpoint: Brisken Expense-Recon FX + Notifier

**Date:** 2026-07-20
**Status:** Shipped — PR #285 (Tier-1 FX) + PR #288 (notifier) merged to main, verified on Criss's real files

---

## Summary
Two Brisken expense-recon fixes shipped this session: the Tier-1 correctness build (statement sign canonicalization + a refunds bucket + deterministic reference-rate FX + PDF-first doctor/advisory), which took a no-LLM run of Criss's real April month from 0/36 to 29/36 matched; and a notifier fix so an operator "run now" upload actually fires an email to the dev.

---

## What Was Done This Session

### Tier-1 FX correctness build (PR #285, merged)
1. Sign canonicalized at ingest (purchase = positive, credit = negative): CSV parser reads a mapped `type` column (Chase `Sale`-prints-negative) or infers the flip from a ≥3-negative majority with a warning; the Chase statement PDF sets `is_credit` on its negative prints.
2. `MatchOutcome.refunds` bucket + `Transaction.is_credit`: credits partition out **before** candidate generation, so no purchase receipt ever pair-matches a credit (LD-5 A5). A blind `abs()` was rejected for this reason. Carried the bucket through every invariant reader (calibrate, report Summary/Unmatched/Explain, web summary + workbench section + `apply_decisions`, serialize round-trip, runlog).
3. Deterministic reference-rate FX (`MatchingConfig.fx_reference_rates`, via `matching.tuning_path`) ahead of the band/LLM path: ≤3% deviation = clean `FX_REFERENCE`, 3–13% = match+review, >13% falls through to the implied-rate band / `FX_JUDGMENT`. Exact-FX PDF short-circuit still runs first.
4. PDF-first: `doctor` accepts `.pdf` statements + the `expense_report_pdf`/`expense_csv` receipt sources; `doctor` and the web run summary both advise when a foreign-heavy receipt set meets a non-PDF statement. `calibrate` honors `matching.tuning_path` and reports refunds + a purchase-based match rate.

### Notifier fix (PR #288, merged)
1. `operator_state` now returns an `operator_runs` list (every run + `n_transactions`/`n_matched`/`match_rate` + `published`). Run rows exist only after the pipeline finishes, so the summary is always populated.
2. `brisken-recon-notify.py` gained `diff_runs` + `seen_runs`: a new operator run pings the dev once with the match result, whatever its publish state; a `baseline_new_run_tracking` migration keeps an existing state file from mass-mailing the run backlog.

---

## Key Decisions Made

### Refunds get a bucket, not an abs()
- **Choice:** Partition `is_credit` transactions into `MatchOutcome.refunds` before matching, rather than `abs()`-ing the amount to make the sign work.
- **Rationale:** LD-5 A5 says negatives are refunds; a blind `abs()` would let a credit pair-match a purchase receipt and corrupt refund handling. The candidate-finder sign guards stay; credits never reach them.

### Reference-rate FX is config-driven, not learned
- **Choice:** The deterministic FX converter reads `fx_reference_rates` from `config/match-tuning.json`, not the learned `merchant_fx`.
- **Rationale:** Reference rates are monthly operator input (derived from the statement PDFs: BRL≈0.1924, EUR≈1.1623 for April). Learned `merchant_fx` keeps its existing score-only role and never decides bucket membership, preserving the reconciliation guarantee.

### Notifier surfaces all runs, announces once
- **Choice:** `operator_runs` carries every run; the notifier tracks `seen_runs` and announces a run once (to the dev) regardless of published state.
- **Rationale:** An operator "run now" upload creates an unpublished run that was invisible. Announcing once on first sight (not on publish) means the separate published→user "ready" ping still fires later without re-announcing to the dev.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/matching/types.py` | Modified | `Transaction.is_credit`, `MatchOutcome.refunds`, `FX_REFERENCE` type |
| `.../matching/deterministic.py` | Modified | refunds partition in `match_month`; reference-rate FX in `match_one`; config fields |
| `.../ingest/_common.py` · `ingest/statement_csv.py` · `ingest/statement_pdf.py` | Modified | sign canonicalization (Type column, majority inference, PDF `is_credit`) |
| `.../doctor.py` · `calibrate.py` | Modified | `.pdf` + `expense_report_pdf`/`expense_csv` support; foreign-heavy advisory; tuning-path + refunds metrics |
| `.../output/report_xlsx.py` · `web/serialize.py` · `web/service.py` · `web/templates/workbench.html` · `runlog.py` | Modified | refunds bucket + statement-source advisory across every invariant reader |
| `.../web/app.py` | Modified | `operator_runs` in `/api/operator/state` |
| `tools/brisken-recon-notify.py` | Modified | `diff_runs`, `seen_runs`, migration guard, dev email on new run |
| `config/match-tuning.json` | Modified | `fx_reference_rates` scaffold + thresholds |
| tests (`test_statement_csv/pdf`, `test_deterministic_matching`, `test_doctor`, `test_web_app`, `tools/tests/test_recon_notify_diff`) | Modified | sign/refunds/FX + operator_runs + notifier diff coverage |

---

## Current Status
Both PRs merged to `main`, all CI checks green. No-LLM reconciliation on Criss's exact April files: **0/36 → 29/36** deterministic (20 clean + 9 DCC-band review), 4 held for FX judgment (>13% DCC), 1 unmatched (a 2025 year-typo receipt date); invariant OK, no double-binding. Cross-check on the March statement PDF + ER-00214: 28 exact-FX matches, 5 real payment credits partitioned to refunds. Module suite 617 green; hooks preflight `--full` clean (535 hook tests).

Platform: brisken-expense-recon.fly.dev, Fly (gated). No Make/n8n platform section in `infrastructure.yaml` for this client (it's a FastAPI/Fly app), so no ops-audit applies.

Sibling Tier-2 chat merged receiptless-charge categorization (PR #287) the same day — the two bodies of work now both live on main.

---

## Next Steps
1. **User action (schtasks):** register a recurring (~15 min) Windows task running `uv run tools/brisken-recon-notify.py --once --env-file workspace/clients/brisken/context/.env`. The notifier code fix only fires when the notifier runs; it is not scheduled on the dev box. Agent cannot `schtasks`.
2. Optional: populate `fx_reference_rates` in `config/match-tuning.json` per month from the statement PDFs when the activity CSV (no original-amount detail) is the only statement source; the statement PDF path needs no rates (exact-FX).
3. Set `EXPENSE_RECON_NOTIFY_USER` so the published→user "ready" ping reaches Criss, not just the dev copy.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` — "Using-the-data revision (2026-07-20)" + LD-5 (the authority)
- `workspace/clients/brisken/automations/expense-reconciliation/ANNEALING.md` — A5 (refunds), A1 (FX)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` — the roll-up

### Open Questions
- Whether to keep the activity-CSV path at all, or make the statement PDF mandatory for foreign-heavy months (the advisory nudges toward PDF; exact-FX needs it).

### Working Notes
- Reference rates for April derived from the Mar/Apr Chase statement PDFs via `parse_statement_pdf_tolerant` (fx_rate field): BRL mean 0.1924 (n=79), EUR mean 1.1623 (n=2). These are the values in the local `match-tuning-tier1.json` calibration config (gitignored `context/.../by-month/01-04-2026_ER-00215/`).
- The 4 FX-judgment holdouts on April are genuine >13%-DCC charges (Mega Center BRL 1358 implied 0.2176, etc.), not tool gaps. The 1 unmatched receipt is dated 2025 (manual year typo) — correct to leave unmatched.
- Criss's raw uploads pulled from Fly `/data/runs/b67133b8df98/` (activity CSV + ER-00215.pdf) into the gitignored `context/.../by-month/01-04-2026_ER-00215/`; kept per the documented no-cost testing loop.
- The FX-branch worktree directory (`agentic-ops1-fx`) was left on disk after merge — its git registration was pruned but a Windows process held a file lock; cosmetic, deletable once the lock clears.

### Reference Materials
- PR #285 (Tier-1 FX), PR #288 (notifier), PR #287 (Tier-2 receiptless categorization — sibling)
- Memory: `project_brisken_expense_recon_testing_loop` (updated this session — sign+FX fixed, notifier code-fixed, scheduling still open)

---

## How to Continue
Both fixes are merged and live in code. To exercise the combined pipeline (FX + receiptless categorization), sync `main` and run `expense-recon calibrate --config <run.json>` on Criss's files with a `matching.tuning_path` pointing at reference rates. To activate notifications, the user must register the schtasks task (step 1 above).

---

## Strategic Feedback

### What Worked Well This Session
- Two directive, well-scoped tasks with clear ownership boundaries (the FX brief explicitly named which files were mine vs the Tier-2 sibling's) — zero cross-session collision, both merged clean.

### Suggestions
- The `schtasks` scheduling gap has now blocked the notifier twice (the code is right, but nothing runs it). Registering the task once removes a recurring dead-end; worth doing in the next hands-on window.

### System Health
- The isolated-worktree-per-task discipline held cleanly: two feature branches + one docs branch, no shared-tree contention with two live sibling sessions. The one rough edge is Windows file locks on `git worktree remove` after a merge — the git registration prunes fine, but the directory lingers. Not worth automating around.

- Autonomy score: 0 — fully autonomous session.

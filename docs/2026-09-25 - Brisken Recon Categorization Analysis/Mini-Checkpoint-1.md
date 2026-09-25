# Mini-Checkpoint: Brisken Recon Categorization Analysis

**Date:** 2026-09-25
**Status:** Builds split across five parallel sessions; prompts handed to the owner; no build started
**Type:** mini

---

## Summary

After the full checkpoint (PR #1430), the owner asked for prompts that run beside the main build prompt. Four parallel prompts were handed over, each owning a disjoint set of files so five sessions can build the item-216 root causes at once.

## What Was Done

- Split the five structural builds by file ownership, so no two sessions edit the same code in the same window:

| Session | Build | Owns | Must not touch |
|---|---|---|---|
| main | 1 corrections land; 2 code half (model is a suggester, no parent picks, source-of-answer counts) | `web/service.py` category/override paths, `web/app.py` field PUT, `_gl_model_result`, `categorize_charges.py`, `sheet_writeback` / report / PDF labelling | the registry resolver, intake routing |
| A | 5 reproducible score | `tools/recon-categorization-score.py`, its test, its `tools/INDEX.md` row | anything under `src/expense_recon/` |
| B | 2 data half: account map from Criss's 24-month history, Dirk's one message, the write plan | gitignored `context/expense-reconciliation/account-map-*`, `context/drafts/` | module code; no settings write this session |
| C | 4 wire/bank-transfer invoices leave the card queue | `resolve_receipt_month` + drop path, `intake_mail.py` payment_mode stamping, `month_readiness.py` waits-for-statement, the new Bills-path module, the duplicate key for same invoice number | category code; asks the owner the destination (a Bills section in the month recommended) before coding |
| D | 3 canonical merchant identity | `merchant_registry.py`, `vendor_names.py`, `learning/consult.py`, the alias learner in `learning/capture.py`, `_recall_for` / `_registry_account` | measures now, opens its PR only after Build 1 merges (shared `categorize.py`, `capture.py`) |

- Coordination rules written into every prompt: own worktree and branch off `origin/main`; never `git stash`; one prefetch of only the months needed (15 s apart, 45 s brake, replay from disk); `git merge origin/main` and claim the backlog number right before committing; one deploy at a time, checked against `flyctl status` and `/healthz` `server.commit` (no deploy if a sibling deployed in the last 15 minutes); the SESSION LOOP section verbatim.
- p1 status file's item-216 row updated to name the five-session split.

## What Did NOT Work (and why)

None

## Current Status

Nothing built yet. The four parallel prompts and the main continuation prompt exist only in this conversation's replies; a resume that needs them regenerates each from the ownership table above plus the item-216 Next Steps in `Checkpoint.md`. brisken ops status: platform unknown plan; comms-log none. The one no-auto-commit candidate (merge of #1430 asked while CI was pending) was the gate working: the watcher merged on green.

## Next Steps

1. Owner starts the sessions: main (Build 1 first), A, B, C now; D measures now and lands after Build 1's PR merges.
2. Session C's destination question (Bills section vs separate queue vs mark-and-hide) goes to the owner before any routing code.
3. Session B's draft for Dirk (split vendors, 7 questions, parent-account policy) goes to the owner to send; the settings write waits for Dirk's answers and a per-action yes.
4. After all five land: rerun session A's score tool on a fresh prefetch and a Zoho re-pull once August and September are booked; today's open-row figure is 1/23.

## Files to Read First

- `docs/2026-09-25 - Brisken Recon Categorization Analysis/Checkpoint.md` (Next Steps = the five causes)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (item-216 row)

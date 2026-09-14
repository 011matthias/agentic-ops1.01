# Checkpoint: Expense-Recon Parallel Round Setup

**Date:** 2026-09-15
**Status:** Void-list rounds 1-3 shipped (items 57, 58, 59, 56, 60; Fly v117). Ten open items handed to ten simultaneous sessions under one protocol; nothing of theirs has landed yet.

---

## Summary

Closed the 2026-09-11 void-list brief (five of ten items shipped across three rounds, each with route-level tests, regress proofs, CI-green merge, Fly deploy and an SPA drive; the receipt-taken Lovable prompt handed as text), then opened the next ten: items 61-68 plus the untracked operator notes 16 and 17, one session each. The enabling work was a single protocol file on `main` and four new backlog numbers carved out of item 49, so the ten prompts stay short and identical in discipline.

---

## What Was Done This Session

### Void-list rounds 1-3 (detail in the three mini-checkpoints of this folder's siblings)
1. Round 1 (#811, v115): `summary.month_health` refuses readiness on a zero-match month with exact pairs in the pool; every `rematch_month` commit records a `rematch_log` event and the notifier mails one line per event.
2. Round 2 (#815/#818, v116): a charge's entity resolves through ITS card (`stamp_charge_entities`, blank when the registry cannot name it); an invoice+receipt duplicate pair is one matcher candidate (`collapsed_duplicate_copies`). Both owner-ruled via `AskUserQuestion`. The predicted 77-row entity gap on August did not exist: `coverage[].known` is the batch's upload-time snapshot, not the live registry.
3. Round 3 (#820, v117): `rows[].candidates[].held_by` names the charge holding a contested receipt; `summary.n_charges_receipt_taken`. The reported instance no longer reproduced (round 2 had removed it), so the fixture was constructed through `POST /manual-match`. `tools/lovable-bundle-audit.py` (#821) promoted from a scratch script that had reported a confident false negative.

### The parallel round (this segment)
4. Handed the receipt-taken Lovable prompt as pasteable text (the Stop hook had blocked an offer to do so).
5. `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md` on `main` (#824, `c798b899`): own worktree per item, append-only edits to the seven shared files, merge-not-rebase after a push, probe the live API for your field before deploying (a sibling's deploy carries your merge), own `agent-browser --session`, Lovable prompt as text, checkpoint on a fresh `docs/` worktree, and a cleanup block ending in three outputs that must be empty. It also states outright that CI does not run the module suite.
6. Backlog items 65-68 carved out of item 49 (float totals + silent drop; lock-bypass writes; one bad receipt 500s the month report; coverage overstated + the two reports disagree) so each session owns a number a Shipped row can close.
7. Ten prompts handed in the reply, one per item: 61, 62, 63, 64, 65, 66, 67, 68, 16, 17. Each names its siblings, its worktree and browser session, the live read to do first, the exact build shape with function and line pointers, whether a ruling is needed (only 62: does a settled-outside receipt still print in the expense report; recommend yes), the Lovable half or "none", and the done criterion.

---

## Key Decisions Made

### One protocol file instead of ten long prompts
- **Choice:** land the shared rules on `main` first and point every prompt at the file.
- **Rationale:** ten sessions on one `service.py` beside a live item-47 sibling; the rules that keep them from colliding (append-only, merge-not-rebase, probe-before-deploy, repair the session log) have to be identical, and a rule repeated ten times drifts.

### Which ten
- **Choice:** the four remaining voids (61-64), the four standalone defects inside item 49 (65-68), and the two untracked operator notes (16, 17).
- **Rationale:** the backlog's own ranking rule (wrong money first, then what stops the tool learning, then what Criss hand-fixes monthly). Items 42, 35 and 36 were already shipped; 10-residual, 23 layers 2-4, 47 and 48 are too large for a one-round session.

### 67 and 68 share the report builder
- **Choice:** 67 owns per-file render failures, 68 owns the disagreement between the two reports and the Receipt column, and 68 calls whatever 67 exposes; whoever lands second merges main and re-runs.
- **Rationale:** both need "does this receipt have a page in the report"; one owner for the probe, two consumers.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md` | created (#824) | the one protocol the ten prompts point at |
| `status/p1-improvement-backlog.md` | edited (#824) | items 65-68 + the round header; `updated: 2026-09-15` |
| `status/p1-expense-reconciliation.md` | edited (this checkpoint, client PR) | one row: the parallel round is open |
| memory `project_brisken_expense_recon_usability_loop.md` | edited | 2026-09-15 paragraph + description |
| `docs/INDEX.md`, `docs/sessions/2026-09-15.md`, `docs/friction-register.md` | scaffold | ledger |

Rounds 1-3 files are listed in their mini-checkpoints.

---

## Current Status

Live: Fly v117 on `brisken-expense-recon.fly.dev`, both months healthy on all three new readiness/entity/held_by counts, which is why none of the three SPA renderers has a live case. Lovable: month-health and charge-entity prompts applied (bundle audit 48 files); receipt-taken prompt handed, pending the owner's paste. `origin/main` at `c798b899`. This session's own worktrees and branches removed; the ten sessions have not started.

Ops status (from `pre`): brisken platform unknown plan; no comms-log for this project; status files current except the p2 set (86d / 54d / 55d / 55d), which belongs to a p2 session.

---

## Next Steps

1. Launch the ten prompts (or 61-65 first, then the rest when two have merged, to halve contention on `service.py`).
2. After the owner pastes the receipt-taken prompt: `uv run tools/lovable-bundle-audit.py`, move the PROMPT-STATUS row to Applied.
3. Pull the main checkout once its dirty `meji-media/status/enquiry-automation.md` is committed by its sibling, so the scheduled `BriskenReconNotify` task runs the round-1 notifier code.
4. The three renderers without a live case (blocked readiness bar, "Card not defined" chip, `held_by`) need a TEST-namespaced batch in production to be seen; that is an invasive mutation and waits for a per-action yes.
5. CI does not run the expense-recon module suite (`ci.yml`: hooks, platform, spell, Playwright, lead-desk only). Worth a `lead-desk`-shaped job; not scheduled.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 61-68, 16, 17; Shipped rows 32-34)
- `docs/2026-09-15 - Expense-Recon Void List Round 3/Mini-Checkpoint-2.md`
- memory `project_brisken_expense_recon_usability_loop.md`

### Open Questions
- Item 62 ruling: does a receipt settled outside the card still print in the monthly expense report? (Recommendation: yes, captioned.)
- Whether to add the module suite to CI now that ten PRs a day will land against it.

### Working Notes
- `coverage[].known` answers "did THIS BATCH know the card", never "is the card defined"; `/api/settings` `cards_effective` answers the second. All nine live cards carry an entity.
- A charge that loses its receipt keeps the candidate on display (raw outcome) and falls to `unmatched` truthfully (effective outcome). Two identical charges competing for one receipt is NOT that case: the loser lands in `unmatched_transactions` with no candidates. The reassignment path (`POST /manual-match`) is.
- A regress mutation must change behaviour. `x = None or f()` reported TEST BITES and proved nothing; `if reconciling:` -> `if False:` is the shape.
- `.pdf` fixture names with JPEG bytes skip vision; use `.jpg`.
- `gh pr checks` can return the previous run's results before the new run registers.
- A squash-merged branch cannot take further commits without conflicting; `format-patch` + `git am` onto a fresh branch.
- The bundle audit is only evidence when its control fields are found; the v1 crawl of 16 chunks reported `ready_to_post` absent.
- `git show origin/main:<path>` survives MSYS mangling most of the time and not always; `MSYS_NO_PATHCONV=1` every time.

### Reference Materials
- Live months: August `074a7b8905d7`, July `50622baec444`; operator code in vault "Expense Recon App".
- `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, `docs/lovable-receipt-taken-prompt.md` (module `docs/`).
- `tools/regress_check.py`, `tools/lovable-bundle-audit.py`, `tools/brisken-recon-notify.py`, `tools/repair-session-log.py`.

---

## How to Continue

`/resume brisken`, then paste one of the ten prompts per fresh session. Each session's final reply carries its PR, Fly release, regress line, the Lovable prompt in full, and the three empty cleanup outputs; the checkpoint after the round is the roll-up of those replies.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the live months before every diagnosis changed the build twice: the entity gap was a stale snapshot, and the held_by symptom had already been removed by the previous round. Both fixes still shipped, on constructed fixtures, with the gap stated in the backlog instead of papered over.
- Refusing to believe an instrument until it found something known-present (the bundle audit's control block) turned a false "not applied" into a tool that cannot produce one.

### Suggestions
- Add the expense-recon module suite to `ci.yml` as a `lead-desk`-shaped job. Ten PRs a day against a suite that only runs on the author's machine is the exact gap the protocol has to paper over in prose.

### System Health
- Autonomy: 1 correction (the prompt was offered instead of handed; Stop hook caught it, owner repeated the ask) + 3 rulings the brief required; every ship chain, deploy and cleanup ran without an order. The `[CONSUMER NOT DRIVEN]` marker fired on a docs-only push in this segment and closed itself one call later; the deploy it referred to (v117) had been driven before compaction. Gates: B1:3 B2:12 B3:4 skipped:1.

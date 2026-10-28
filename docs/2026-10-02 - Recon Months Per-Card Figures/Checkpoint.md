# Checkpoint: Recon Months Per-Card Figures

**Date:** 2026-10-02
**Status:** Items 236 + 238 LIVE (backend deployed, SPA prompt published by the owner and driven)

---

## Summary
On `/months`, picking a card now shows that card's own Receipts, Needs category and Set aside per month, and the chips lost their number (item 236). The All row's Needs category now equals each month page's count (item 238), so cards plus No card add up to it in every month.

---

## What Was Done This Session

### Item 236: the months table follows the card filter
1. Answered the owner's question first: the chip number was item 193's "needs a category, all months, own card only". It was consistent across chips, but it sat beside whole-month table figures.
2. Backend: set-aside (quarantined) files now carry `set_aside[].card_section`, resolved by the unheld-receipt chain (`report_receipt_cards`, else No card). `n_set_aside` was added to `receipt_months[]`, `no_card.months[]` and the card and no-card totals. Receipts and Needs category already existed per card and month.
3. SPA prompt `docs/lovable-months-card-figures-prompt.md`: chip badges removed, `BatchRow` reads the picked card's month entry, both captions reworded (EN + PT). The owner published it; it was driven cold.
4. PR #1505 (renumbered 231 → 232 → 236 across three merges as siblings claimed numbers), Fly `1fa8bf67`; record PR #1517.

### Item 238: the months list's Needs category = the month page's
1. Found while checking item 236 live: on the GL months the list read 4 fewer than the pages (September 34 vs 38). The owner chose the fix via AskUserQuestion.
2. Root cause, measured on the 2026-09-25 SharePoint backup with a local API: `_stale_suggestion` (front 3 steps 4-5) re-reads model suggestions stored before today's refusals (`E500010` parent, `E500010-10` vendor-specific) as refusals on the page. The list counted the stored code.
3. `grid_posting` (service.py) now holds the page's steps once (live merchant accounts, overrides with the row's company, chart gate). `build_expense_view` and `batch_list_summary` both call it.
4. The list cost rose 4x (0.12 → 0.53 s locally), so `GET /api/expense-batches` keeps its body under the card roll-up's data key (`CardStatusMemo`): rebuilt on the first read after any write.
5. PR #1526, Fly `7e5dd03c`; record PR #1527.

### System
1. Pattern rule `warn-jq-not-installed` (no `jq` on this machine; a CI watch piped into it stayed silent for 30 minutes).
2. Memory `reference_repo_tooling_gotchas.md`: the jq fact plus `gh run watch` / full-SHA `gh run list`.

---

## Key Decisions Made

### An account counts only its own rows
- **Choice:** with 2838 picked, the table shows 2838's rows, not 3876 / 3645 / 0340.
- **Rationale:** the owner's ruling, the same as the item 193 chip and the month page opened with `?card=2838`.

### A set-aside file belongs to the card its reading names
- **Choice:** the same chain as an unheld receipt; a file that names no card (and a legacy entry with no reading) goes to No card.
- **Rationale:** a quarantined file is held by no charge, so it files exactly where an unheld receipt would; no second rule.

### The list counts through the page's code, kept in memory
- **Choice:** one shared helper plus a write-invalidated memo, instead of a second copy of the page's steps or a background warm-up.
- **Rationale:** copies drift (that was the bug). The memo key (SQLite commit counters + top-level files) covers everything the list reads, so the next read after an edit is fresh.

---

## What Did NOT Work (and why)
- **Monitor watching PR #1505's CI:** it piped `gh ... --json` into `jq`. No jq binary exists here, so every poll failed silently and the watch expired after 30 minutes with 0 events while all 8 checks were green.
- **Merging PRs #1505 and #1517 on the first green CI:** each time a sibling had landed backlog or PROMPT-STATUS edits during the 6-14 minute module suite, so the merge was refused for conflicts (3 times on #1505, 2 on #1517). Backlog item numbers 231 and 232-235 were also claimed mid-CI.
- **First explanation of the list gap ("the chart check blanks the account"):** given from code reading. The backup diff showed the gate changes nothing on those rows; the live merchant read's stale-suggestion refusal does.
- **Running the chart gate locally on the backup as stored:** run configs point `chart_path` and `work_dir` at `/data/...`, so the gate silently built as None until both were rewritten on the local copy.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` | Modified | set-aside card stamping, `n_set_aside`, `grid_posting`, list count through the grid chain |
| `.../expense-reconciliation/src/expense_recon/web/app.py` | Modified | months list body kept in `CardStatusMemo` |
| `.../expense-reconciliation/tests/test_months_card_figures_item_236.py` | Created | 5 route-level tests, 3 red with the stamping off |
| `.../expense-reconciliation/tests/test_months_list_needs_category_item_238.py` | Created | 4 route-level tests, red under both mutations |
| `.../expense-reconciliation/tests/test_card_status_receipt_months_item_190.py` | Modified | shape pins name `n_set_aside` |
| `.../expense-reconciliation/docs/lovable-months-card-figures-prompt.md` | Created | SPA half of item 236 (published) |
| `.../expense-reconciliation/docs/api-contract.md`, `PROMPT-STATUS.md` | Modified | field contract; prompt moved to Applied |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Modified | items 236 + 238 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | element row + dated line |
| `.claude/patterns/warn-jq-not-installed.md` | Created | pattern rule |

---

## Current Status
Both items are live and verified: 7 of 7 months reconcile on all three columns (live API), and the cold browser drive of 2838, 3876 and No card shows exactly their `GET /api/cards/status` entries. Brisken ops status: `infrastructure.yaml` has no `platform` block ("unknown plan"); the recon app is FastAPI on Fly, outside that assessment.

---

## Next Steps
1. Trips list (`trip_view`) calls `batch_list_summary` without the learning store, so remembered cards do not reach a trip's list count. Fix only if a trip month shows a mismatch.
2. Status files `p2-lovable-rebuild.md` and `p2-onepilot-site.md` are 22 days stale (flagged by `pre`). They're not this session's workstreams; refresh them in a p2 session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 236, 238)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-months-card-figures-prompt.md`

### Open Questions
- None open with the owner from this session.

### Working Notes
- Local bench recipe that worked: newest backup via `expense_recon.web.backup.GraphDrive` (site `brisken.sharepoint.com:/sites/MARKETING`, folder `ExpenseTool`) into a short `.scratch/src`, then rewrite `/data/` to the local path in `runs.config` / `runs.work_dir` and `coa-provision.json`'s `chart_path`. Without the rewrite the chart gate is None and GL behavior differs.
- On the 2026-09-25 backup, 29 / 11 / 11 rows (September / August / July) read differently under the two rules, net 23 / 9 / 9 more needing a category on the page; live on 09-27 the net gap was 4 per month.
- The months list cold build is ~1.2 s live; repeat reads come from the memo.

### Reference Materials
- PRs #1505, #1517, #1526, #1527

---

## How to Continue
Nothing pending on these items. For any further months-list change, verify with the per-month reconciliation (cards + No card vs the list, all three columns) on the live API, GET-only.

---

## Strategic Feedback

### What Worked Well This Session
- A differential instrument before trusting a negative: the old tree on the backup copy showed 3 months differing, so the "0 after" on the new tree carried weight. The same diff overturned the first guess at the cause before it reached the docs.

### Suggestions
- Backlog numbers are claimed by whichever sibling merges first, and each loss costs a renumber plus a conflict cycle against a 6-14 minute CI. Claim the number at merge time: write the item as `### NNN.` placeholder and have a small tool assign the next free number during the final `merge origin/main`.

### System Health
- The stop-event warn on "PR left waiting on CI" fired twice this session and only after the turn had ended; the chain was finished on the next turn each time. A pre-stop check that blocks a closing message while an own PR is open and unmerged would catch it before, not after.
- Autonomy: 2 human interventions (two tool-call rejections early on, both about pacing: answer first, then build).

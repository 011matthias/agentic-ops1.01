# Checkpoint: Brisken P1 Edits Stick, Card List, Scorer Repin, Matching Round A

**Date:** 2026-09-15
**Status:** Item 70 live on Fly v129; items 71 + scorer re-pin merged; matching round A built and reviewed, fix pass in flight

---

## Summary

The owner reported two defects in plain words ("users can click and change things in a month and they stay unchanged", "the card list at the top of a month makes everything harder to see"); both were real, neither was in the backlog, and the first turned out to be Criss's own untriaged 2026-09-14 feedback. Item 70 shipped and deployed, item 71's prompt and the scorer re-pin merged, and matching round A (item 69) is built, reviewed by five lenses and being fixed.

---

## What Was Done This Session

### The two reported defects, audited before anything was built
1. Two read-only audit agents enumerated every control on both month pages and every block above the first work row, against the live app and a DB copy. Three causes behind "changes do not stick", one bug plus a layout finding behind the card list.
2. Criss's feedback of 2026-09-14 06:57 UTC on July ("coloco a categoria certa, nao acontece nada... permanece sem categoria mesmo dando refresh") had never been triaged; the DB copy holds the 16 category changes she saved that morning, 6 of them on review rows that still showed ASSIGN.

### Item 70 (PR #870, Fly v129): a change made in a month sticks
1. A needs-review row resolves `posting_category` from the candidate the Confirm would take, flagged `posting_category_proposed` (parallel, absent elsewhere). 12 July + 3 August rows.
2. The five expense-edit routes accept edits on a statement month again (the never-scheduled "overlay-route round"); an edit that can move a pairing re-matches off the event loop, result or error under `rematch`.
3. `rematch_month` bakes from `baseline_receipts(run)` instead of the already-baked pool: measured first, a cleared edit had stayed in the matcher's pool (grid 42.50, pool 99.99).
4. Reclassify with no `line_index` covers every line and a changed category no longer keeps the old account.
5. Suite 1724 -> 1746; nine regress proofs RED first; live-data replay old-vs-new identical on both months (26/16 and 11/3 pairs, same pool), so nothing moves until someone edits.

### Item 71 (PR #869): the card list leaves the top of the month
1. `docs/lovable-card-chips-prompt.md`: coverage table becomes filter chips, statements box one line, a banner only when something needs action, card-review strip collapsed. Every field read off the live payloads first.
2. Found on the way: the Card filter counts every option as the month total (`countWith(patch, skip)`, shipped in today's SPA publish), and the strip prints "card ending 42463153" for a masked BIN.
3. PROMPT-STATUS re-audited against the live bundle: view-receipt, settled-outside and the API host switch are live since the owner's 13:41-13:47 UTC publish; the receipt viewer was browser-driven (PDF renders on the workbench; still locked on the expense list until item 70's prompt lands).

### Scorer re-pin (PR #871, owner-ordered)
1. `rapidfuzz==3.14.5` added to the pinned scorer's and the guard's inline deps, re-pinned under `SCORER_LOCK_ALLOW=1`; both run standalone again and reproduce the floor exactly (train 49.8, holdout 15.7, all 65.5, 55/95, 0 wrong, guard 4/4).

### Matching round A (item 69), built + reviewed, NOT merged
1. Commit `404c07da` on `client/brisken/p1-matching-round-a`: second duplicate key (normalized reference + total + currency), `basis: "reference"` parallel field, collapse of the new groups, and `inherit_card_from_copies` before the card chain in `rematch_month`, the grid and the export setup.
2. Measured on both live months: August's 3 wrong auto-matches -> 0 (Lovable 50 / Anthropic 100 stop taking BASE44 charges, the Anthropic 51.38 copy matches its own charge), `matched_unverifiable` 1 -> 0, undetected copies 2 -> 0 on both months, July unchanged at 26 clean / 0 wrong. Suite 1746 -> 1785, four regress proofs.
3. Five review lenses (matcher, theater, numbers, contract, production) ran the code rather than reading it and returned 8 findings that survived their own evidence bar; a fix workflow is applying them.

---

## Key Decisions Made

### Full fix for the edit defect, not just the visible half
- **Choice:** Reopen the five edit routes on statement months with a re-match, rather than only fixing what the page shows.
- **Rationale:** Owner picked it; cost centers shipped the same day and both live months have statements, so no row cost center could be set anywhere.

### Card list becomes filter chips plus an action-only banner
- **Choice:** Chips in the filter bar, empty cards folded away, banner only when a card is unknown / has receipts but no charges / charges lack a company.
- **Rationale:** Owner picked it over one collapsed section; the numbers become navigation and the filter-count bug gets fixed in the same prompt.

### The July Google duplicate ruling stands
- **Choice:** Owner ruled: leave the reviewer's "duplicate" ruling on 0036/0037.
- **Rationale:** Owner's call; consequence recorded (one GOOGLE 71.64 charge stays unmatched).

### Scorer re-pin ordered
- **Choice:** Owner ordered the `SCORER_LOCK_ALLOW=1` maintenance edit.
- **Rationale:** The instrument could not run outside the module venv; the hash diff ships in the PR for review.

### Round A ships only after the review findings are applied
- **Choice:** Do not merge `404c07da` as reviewed; apply 8 findings first.
- **Rationale:** One is a silent lost match (an account id in `detected_reference` can twin two different purchases), one is that the bundle/scorer evidence never executed the changed code.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/app.py` | edit | five edit routes reopened, `_expense_edit_reply`, whole-receipt reclassify (#870) |
| `src/expense_recon/web/service.py` | edit | bake from baseline, proposed posting category, account rule, `EXPENSE_MATCH_FIELDS` (#870); reference groups + inheritance (round A) |
| `src/expense_recon/duplicates.py` | edit | reference key, `basis`, `inherit_card_from_copies` (round A) |
| `tests/test_month_edits.py` | add | 21 route-level tests (#870) |
| `tests/test_reference_duplicates.py` | add | 38 tests (round A) |
| `docs/lovable-month-edits-prompt.md` | add | SPA half of item 70 |
| `docs/lovable-card-chips-prompt.md` | add | SPA half of item 71 |
| `docs/PROMPT-STATUS.md` | edit | three prompts moved to Applied, two registered Not applied |
| `docs/api-contract.md` | edit | reopened routes + `rematch`, `posting_category_proposed`, `basis` |
| `tools/scorers/recon-match-accuracy.py`, `tools/recon-accuracy-guard.py`, `PINS.json`, `guard-pins.json` | edit | rapidfuzz re-pin (#871) |
| `status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md` | edit | items 70, 71, round A |
| `tools/recon-match-attribution.py` | edit | mirrors the app's pool assembly (round A) |

---

## Current Status

Fly **v129** serves item 70 (verified: 12/12 July and 3/3 August review rows carry a category; the live page shows "Meals & Entertainment EDIT" where ASSIGN was). Three PRs merged today from this session (#869, #870, #871). `brisken` platform ops status: unknown plan / unassessed in `infrastructure.yaml`; the recon app is Fly, not an orchestrator, so no `/ops-audit` action falls out of it.

Round A sits at `404c07da` on `client/brisken/p1-matching-round-a` (worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-matching`), with the fix workflow mid-run and uncommitted edits in that tree. Round B is specified and queued (script at `<scratchpad>/round-b-workflow.js`).

Two Lovable prompts wait on the owner: month-edits first, card-chips second (both touch `ExpensesReviewGrid.tsx`).

---

## Next Steps

1. Let the round-A fix workflow finish; verify its regress proofs and the re-measured attribution, then merge `client/brisken/p1-matching-round-a` and deploy.
2. Live re-match July + August through `POST /api/expense-batches/{id}/refresh-master-data` after that deploy (`<scratchpad>/live_rematch.py --go`), then drive one changed row in the SPA.
3. Run round B from the queued script (spoken-for rivals, vendor dominance, masked-BIN `_card_keys`), then stop per the 3-receipts-a-month floor.
4. Owner: paste the two Lovable prompts in order; then run the four browser checks in the card-chips prompt and the item-70 checks.
5. Log the brisken comms conversations if any (comms-log 7 days stale).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 69 (round A paragraph), 70, 71
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `<scratchpad>/round-b-workflow.js` (the queued round-B spec)
- Memory: `project_brisken_recon_matching_program`, `project_brisken_expense_recon_usability_loop`

### Open Questions
- Does the persisted-vs-effective split (new backlog item 72) need its own round, or does round B's spoken-for rule close the live instance?
- Should `load_bundle` permanently run the pool assembly, making the six bundles a real regression surface for pool-layer rounds?

### Working Notes
- **The main clone is 68 commits behind origin/main** and its `pre` output (stale status files) reflects that, not reality: both p1 status files carry `updated: 2026-09-15` upstream.
- **A no-LLM local re-match blanks receiptless charge categories on any code tree.** Diff old-code vs new-code, never before-vs-after on one tree; the first probe of item 70 looked like 74 changed rows and was an artifact.
- **The live DB copy recipe:** `flyctl ssh console -C "python3 -c sqlite3.backup to /tmp"` then `MSYS_NO_PATHCONV=1 flyctl ssh sftp get` with a Windows-form local path. Today's copies: `<scratchpad>/fly/recon-web-copy.sqlite` (labels' baseline, 12:12) and `recon-web-1720.sqlite` (17:20 live state).
- **agent-browser's first `open` in a session hangs past 120s;** stop the call and re-open, the second works. The grid's controls are disabled by `<fieldset disabled>`, which the accessibility tree reports as `disabled` while the DOM shows `disabled:0` on the buttons themselves.
- Round A review findings not yet applied at checkpoint time are listed verbatim in the fix workflow's prompt (`<scratchpad>` workflow script `recon-round-a-fix-*.js`).

### Reference Materials
- Live: `https://expenses.brisken.com`, API `https://brisken-expense-recon.fly.dev` (read-only helper `%TEMP%/claude/recon-probe/api.py`)
- PRs: #869 (card chips), #870 (item 70), #871 (scorer re-pin)

---

## How to Continue

Open the round-A worktree, confirm the fix workflow's commit, re-run the attribution tool on both live months plus the six bundles and the standalone scorer, then ship per B6 and deploy. Round B follows from its queued script; do not start it before round A is merged, because both touch the same worktree.

---

## Strategic Feedback

### What Worked Well This Session
- Auditing both reported defects with read-only agents before proposing anything turned a vague complaint into three named causes and surfaced Criss's untriaged feedback, which no backlog item covered.
- Five review lenses over a committed change caught a silent-lost-match class the build agent had reasoned past, and caught its own evidence being vacuous (the bundles and the pinned scorer never execute pool-layer code).

### Suggestions
- Cap adversarial fan-out per workflow: 69 agents hit the account session limit and killed 52 of them mid-flight, costing the whole verify+fix phase. Two sequential workflows of ~20 would have finished.

### System Health
- Autonomy: 2 human interventions, both decision blocks this session raised (`AskUserQuestion`), zero corrections.
- The friction register is 221 KB with nothing archivable inside the sanctioned window; it will need a wider `--days` next time it crosses a checkpoint.

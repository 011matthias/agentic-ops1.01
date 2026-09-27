# Mini-Checkpoint: Expense-Recon Front 4 Step 6 And Item 227

**Date:** 2026-09-27
**Status:** Front 4 closed (item 223 all steps shipped); item 227 shipped; both live on Fly v270
**Type:** mini

---

## Summary
Item 223 step 6 (the intake records an invoice and its receipt from one mail, `submitted_by.twin_of`, ladder rung 0 `intake_twin`) and item 227 (gpt-5-mini priced, cached input billed at its rate) shipped as PRs #1496 and #1500, deployed together as Fly v270 (`987e0b52`); live read-only checks matched the prediction of zero moves.

## What Was Done
- Predicted step 6 per row before building: the step-4 A/B readings (both passes agreeing) joined to the live mails (archive, or arrival stamp + address on pre-item-106 rows) find 10 pairs, July 1 / August 1 / September 8, all Lovable Labs, every one already a single live copy group (charge-held invoice counted in 3, receipt in 7); five Anthropic mails read the invoice number on one pass of two only.
- Built step 6 in `duplicates.py` (`intake_twins`, `stamp_intake_twins`, `twin_links`, `intake_twin_pairs`, rung 0, `twins=` threaded through find/decide/lending/inherit) and `web/service.py` (stamp in the add path and in a mail-created month, `stored_intake_twins` read in `duplicate_decisions` and the list screen, a month move drops `twin_of`). 16 route-level + rule tests, contract pin, three regress proofs all TEST BITES.
- Built item 227 in `llm/cost.py` / `llm/client.py`: price verified the same day on developers.openai.com/api/docs/pricing (0.25 / 0.025 / 2.00 per 1M), cached-input rates for every priced model, `prompt_tokens_details.cached_tokens` passed through, a source scan that fails on any configured model without a price. 5 tests, two regress proofs.
- Shipped Rows 154 (step 6) and 155 (item 227); siblings took 152 (#1495) and 153 (#1497) while #1496 sat in CI, so #1496 merged origin/main twice and #1500 once, both sides kept each time.
- Deployed via `deploy.py` from a detached origin/main worktree: /healthz on `987e0b52`, release v270. Live against a read taken right before the deploy: July 21 / August 6 / September 24 duplicate groups, per-row counting, totals and copies unchanged, 0 `intake_twin` groups, 0 `twin_of` rows. Cold SPA drive rendered September USD 5,241.09 and July USD 31,882.49.
- Record PR #1508 (Fly v270 + live checks into the Shipped rows and the status file). `docs/lovable-copies-kind-prompt.md` gained the `intake_twin` label; sibling #1507's reason-gate prompt already carries it.

## What Did NOT Work (and why)
- **Full module suite from PowerShell:** 7 failures, all `tests/test_smtp_starttls.py`, because `ensure_cert` needs an `openssl` binary on PATH and PowerShell has none; the same file passes 10/10 from Git Bash (`/mingw64/bin/openssl`). Run the suite from Bash.
- **The prediction keyed on the mail archive alone:** it found 5 pairs, not 10, because July/August provenance predates the archive key; the shipped rule's arrival-stamp + address fallback was missing from the script until re-run.
- **`.scratch/recon-cold-drive-months.py` as committed by the earlier session:** it hardcoded September's total (5,202.08) and read `rendered=False` once September had grown to 93 rows (live 5,241.09); the figure was updated in the scratch script.

## Current Status
Front 4 has no open step. Owner-pending: whether to run step 7's reapply per month (September's invoice-over-receipt swaps; July 0076 / 0083 / 0054). SPA: `lovable-duplicate-reasons-gate-prompt.md` (#1507, sibling) and the copies-kind trigger key are not pasted, so `reference_digits` / `misread_digit` / `body_twin` / `intake_twin` groups read "Decided by the tool". Eight new feedback notes (#99-#106, 20:28-20:33 UTC) are not itemized. Nothing waits on Criss.

## Next Steps
1. Read notes #99-#106 from `/feedback.jsonl` with their anchors and itemize them in the backlog (check `git worktree list` and open PRs first: a sibling may hold them).
2. Merge record PR #1508 on green if still open.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 223, 227, Shipped rows 154-155)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("The intake decides once", "AI cost figures include the vision model")

---

## Continuation prompt

`````
/comd_resume brisken

# Feedback notes #99-#106 (owner, 2026-09-27 20:28-20:33 UTC): itemize, then build

## Where it stands
Front 4 is closed. This session shipped item 223 step 6 (PR #1496: the intake records an invoice and its receipt from one mail as `intake_provenance[doc].twin_of`, served as `submitted_by.twin_of`; ladder rung 0 `intake_twin`, re-checked on every read) and item 227 (PR #1500: gpt-5-mini priced 0.25 / 0.025 cached / 2.00 per 1M, cached input billed at each model's rate, a test that fails on any configured model without a price). Both deployed together as Fly v270 (`987e0b52`) via deploy.py. Live, against a read taken just before the deploy: July 21 / August 6 / September 24 duplicate groups, per-row counting, totals and copies unchanged, 0 `intake_twin` groups, 0 `twin_of` rows (the prediction: 10 July-September mails would pair, all already one copy group). Cold SPA drive rendered September USD 5,241.09 and July USD 31,882.49. Shipped rows 154 (step 6) and 155 (item 227); record PR #1508 (merge on green if still open).
- Pending paste (owner): `docs/lovable-duplicate-reasons-gate-prompt.md` (sibling #1507: the SPA's `BASIS_KEYS` gate hides `reference_digits` / `misread_digit` / `body_twin` / `intake_twin`; 12 live groups read "Decided by the tool"), and the `mh.rematch.trigger.duplicates_reapply` key in `docs/lovable-copies-kind-prompt.md`.
- Owner decision: whether to run item 223 step 7's reapply per month (September's invoice-over-receipt swaps; July's 0076 / 0083 / 0054 leave the count).
- Nothing waits on Criss.

## Queue, in order
1. Notes #99-#106 (8 notes, 2026-09-27 20:28:59-20:33:03 UTC, not in the backlog): #99 "compressed to just display the cards 4 ending digits", #100/#101 "more evident", #102 "remove first 2 sentences here", #103 "a dropdown button labelled 'View all Statements loaded'", #104 "a dropdown: 'View cards with no statement for this month'", #105/#106 "format this so that it is more visible". Read each from `GET /feedback.jsonl` (bearer from `POST /api/login`, vault "Expense Recon App" `operator_code:`) WITH its anchor (page, section, clicked element) before deciding anything; most read as SPA-only (Lovable prompt), so grep the SPA source (`gh api repos/011matthias/brisken-expense-review/contents/...`) for the anchored component and check who owns each sentence (backend `reason` vs SPA i18n) before building. Itemize them in `status/p1-improvement-backlog.md` (next item numbers after the highest on origin/main at merge; siblings claim numbers mid-CI), then build or write the prompt. Before claiming: `git worktree list` and open PRs, a sibling may already hold these notes.

## How to work
Protocol: workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md on origin/main (own worktree off origin/main, append-never-reflow on shared files, merge origin/main after any push and re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session). Siblings merge into main every few minutes: before `gh pr merge`, read `gh api repos/011matthias/agentic-ops1.01/pulls/N -q .mergeable_state` (dirty = merge origin/main, keep both sides, renumber backlog items / Shipped rows a sibling claimed; this session renumbered twice); run `gh pr merge` as its own Bash call; conflict-resolver scripts run under `set -e`. Inside a REBASE the conflict sides flip (the first block is main, the second is yours). Module suite ~13-15 min today, no xdist: run it from GIT BASH (PowerShell has no `openssl` on PATH and `test_smtp_starttls.py` fails 7), redirect to a log and read pytest's summary line. Live-check scripts in the main clone's .scratch: `recon-reapply-dryrun.py` (login + route probe + dry runs) and `recon-cold-drive-months.py` (raw CDP, headless Chrome :9361, month route /expenses/{run_id}, non-GET aborted; its per-month totals are hardcoded, update them from `summary.totals_by_ccy` before trusting a `rendered=False`). flyctl in PowerShell cannot find its token: export `FLY_API_TOKEN` from `~/.fly/config.yml` in Bash. An extraction schema or prompt change needs the A/B (the pin test's protocol); cost it at list price (item 227 now makes the tracker right for calls from v270 on).

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
`````

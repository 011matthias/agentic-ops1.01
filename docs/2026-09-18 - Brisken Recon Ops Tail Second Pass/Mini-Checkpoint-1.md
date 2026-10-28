# Mini-Checkpoint: Brisken Recon Ops Tail Second Pass

**Date:** 2026-09-18
**Status:** Item 123's alert path fixed and live (PR #1106); items 125, 127, 128, 129 unchanged; the 10-minute cron has still not fired
**Type:** mini

---

## Summary

Second of the four parallel p1 sessions' ops tail. The queue's three watch items had nothing to act on, and the fourth turned up the session's one real defect: the uptime monitor built yesterday detected a dead app correctly and then alerted nobody, because GitHub's `bash -e` aborted the probe step on the DOWN exit and skipped the notifier. Fixed, guarded by a test that drives the workflow's own step text, and re-rehearsed live. Separately, no scheduled run has fired since the workflow landed on main, so the cron itself is still unproven.

## What Was Done

- **Item 123, the defect.** The first outage rehearsal (dispatch 35361771075, `api_override=https://127.0.0.1:9`, dry run) printed `summary: DOWN: api` and then `Process completed with exit code 1`; the Notify step was skipped by its implicit `success()` condition, so no issue and no mail. GitHub starts a `run:` block as `bash -e {0}`, and the step's own `set -uo pipefail` does not undo the `-e` it was launched with, so the shell aborted on the probe's exit 1 before reaching the `rc=$?` line that classifies 1 as "the app is down, tell the notifier". All 19 of the probe's own tests passed throughout: the defect sat in the three lines of YAML between them and the alert, which is the same shape as the September blank-page and pooled-status incidents (the tested half was not the wired half).
- **Item 123, the fix (PR #1106, merged c8b9d8e6).** `|| rc=$?` on the probe line, so a DOWN app leaves the step green and the notifier runs, while exit 2 (the probe itself broke) still fails the job. `tools/tests/test_recon_uptime_workflow.py` guards the caller rather than the script: it lifts the step's real text out of the YAML and runs it under `bash -e` with a stub `uv` whose exit code is the dial, asserting green on 0 and 1, red on 2, that `probe.json` lands where Notify reads it, and that Notify carries no `if:`. Red-proven by hand, with the pre-fix line restored the DOWN test fails with `rc=1`, the live run's exact outcome; restored byte-identical, 6 pass. `preflight-hooks --full`: 1968 passed, 1 skipped, ruff clean. PR CI green on all six jobs.
- **Item 123, verified live.** Post-merge rehearsal 35363507882 (same override, dry run) finished `success` with Notify running and naming what it would do: open `expenses.brisken.com is down (2026-09-18 15:37 UTC)`, send one mail to the `BRIEFING_TO` address, and append the three-line probe table. No `recon-uptime` issue is open.
- **Item 123, the cron.** Zero `schedule`-event runs for the workflow since it landed on main at 14:12Z, confirmed by API (`total_count = 0`, re-read at 16:07Z) and by a poll every three minutes from 15:18Z to 16:04Z, 16 of 16 reading zero. That is 115 minutes and roughly 11 missed 10-minute boundaries. The workflow is `active`, Actions is enabled with `allowed_actions: all`, the repo is public and not a fork, and the cron reads `*/10 * * * *`. The repo's three other scheduled workflows have been `disabled_manually` since 2026-06-27 (owner's "make it stop" on the morning briefing), so there is no second cron to compare against and no evidence either way about the repo's scheduler.
- **Item 125, second leg: nothing to report yet.** No mail-sourced receipt has arrived since v187. The newest mail provenance in the live store is 2026-09-09 (August batch `074a7b8905d7`, 23 `submitted_by` blocks, `transport_tls` absent on every one), which is what `intake_mail._provenance_entry` predicts: the key is written only when the archive meta carries it, so a pre-2026-09-18 archive leaves it absent and "not recorded" reads apart from "delivered in the clear". Today's April batch `0603bb0e6f38` (created 11:23Z, 34 expenses) is upload-sourced, `submitted_by` null throughout.
- **Item 125, first leg re-verified.** Read-only EHLO against `mx.expenses.brisken.com:25` on the machine serving now (`7843d54b579598`, started 14:46Z): `starttls` advertised, `220 Ready to start TLS`, TLS 1.3 with `TLS_AES_256_GCM_SHA384`, 845-byte certificate. No MAIL FROM, no RCPT, nothing delivered.
- **Item 129: not pasted.** The live SPA bundles carry the pre-existing toast keys (`rematch.open`, `rematch.done`, `rematch.failed`, `rematch.nothingNew`, `rematch.noStatement`) and no `mh.rematch.last`, so the Not-applied row in `PROMPT-STATUS.md` stands and the August header has nothing new to drive.
- **Feedback log: unchanged.** 70 lines, same as the handover. No note from Criss. #70 is still the owner's (2026-09-18 10:19Z, run `af8936c6b05a`, section "Add more receipts"): "add receipts function just opens receipt view in new tab but does not really add it". Untriaged and outside this fence.

## What Did NOT Work (and why)

- **The monitor's own first rehearsal.** It was run to prove the alert path and proved the opposite: probe DOWN, step red, Notify skipped, nobody told. That failure is the session's finding rather than a detour, but the plan it broke was "item 123 is shipped and only needs watching".
- **Guessing the PR number before opening the PR.** The docs went in citing `#1105`, which a sibling session's checkpoint took first; the real number is #1106, corrected in a follow-up commit on the same branch. Write the number after `gh pr create` returns it.
- **`git show origin/main:<path>` in Git Bash.** MSYS rewrites the colon pathspec into a Windows path list, so the command fails with "unknown revision"; `MSYS_NO_PATHCONV=1` then breaks `git -C /c/...` instead, since the POSIX root stops resolving. Reading through the worktree, or through the PowerShell tool, avoids both.
- **Closing the session without the confirm line.** The checkpoint ran end to end and merged as PR #1108, and the closing reply never said so, so it read as not having happened and the user re-asked for it. Step 9 of the skill exists for exactly this: the work is not reported until the saved path is in the reply.
- **`gh run list -w <file> --limit N` as the cron instrument.** It answers "runs of this workflow", not "scheduled runs", so the first read looked like a throttle question; `gh api .../runs?event=schedule` returning `total_count = 0` is the reading that actually settles it.

## Current Status

brisken platform: unknown plan (no `platform` section in `infrastructure.yaml`). Fly **v187** still live and healthy (status ok, disk 79 percent free, machine `7843d54b579598` up since 14:46Z); this session deployed nothing, since PR #1106 is repo-side only. Main is green after the merge. Backlog item 123 carries the follow-up paragraph and Shipped row 97; `status/p1-expense-reconciliation.md` names the fix and the cron gap. Worktrees `agentic-ops1-ops-123b` and `agentic-ops1-ops-ckpt2` are this session's.

## Next Steps

1. **Item 123 cron.** No `schedule` run has appeared at all, so the monitor runs only when dispatched by hand and the choice is the owner's: keep waiting on GitHub's best-effort scheduler, add a redundant local runner (precedent: the `MejiWeeklyReview` Windows task), or point a free external monitor at `/healthz` as the item originally proposed.
2. **Item 123 real alert path.** The issue-plus-mail leg has still never run for real. Deliberately not fired unattended: the mail's subject reads `expenses.brisken.com is down`, which would reach the owner as a false alarm. One command when they want it: `gh workflow run expense-recon-uptime.yml -f api_override=https://127.0.0.1:9`, then re-run with no override to close the issue and send the recovery mail.
3. **Item 129.** Owner pastes `docs/lovable-rematch-visible-prompt.md`; then drive the August header cold in EN and PT-BR and move the row to Applied.
4. **Item 125.** On the next real mail arrival, read `submitted_by.transport_tls` on that month's batch; a `false` names a sender still delivering in the clear.
5. **Owner note #70** (add-receipts opens the viewer instead of adding) needs an owner or a session assigned to it.

## Files to Read First

- `.github/workflows/expense-recon-uptime.yml` (the probe step) and `tools/tests/test_recon_uptime_workflow.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 123's follow-up paragraph and Shipped row 97
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (the 129 Not-applied row)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` line 274 (the uptime row)

## Open Questions (outside this fence, not fixed here)

- Owner note #70: "add receipts" opens the receipt view in a new tab instead of adding. Untriaged, and the SPA is not this fence.
- `status/p2-product-decks.md` (57 days) and `status/p2-targeting.md` (58 days) are flagged stale by the SessionStart sweep; both are p2 lead-gen, another frame.
- The repo's morning-briefing, eod-capture and weekly-review workflows have been disabled since 2026-06-27, so the uptime cron is the only scheduled workflow and there is no baseline for whether this repo's scheduler fires at all.

---

## Prompt handed over 2026-09-18 (second pass)

### Paste into a fresh Claude Code chat: ops tail, third pass

````
/comd_resume brisken

You are one of FOUR parallel sessions on the Brisken expense-reconciliation tool (p1). The other three are already running and have their own frame. Your entire job is the operations tail nobody else is touching.

## SCOPE FENCE — read this before anything else

**YOURS, and nothing else:** backlog items **123, 125, 127, 128** and the UI prompt for **129**.

**NOT YOURS. Do not open, edit, test, deploy, or write docs about these, even if you spot a defect in them:**
- The **M-series** (branch `client/brisken/p1-memory-m1`) — another session owns memory work end to end.
- The **T-series** (branch `client/brisken/p1-trace-t2`) — another session owns trace work end to end.
- **match-description** (branch `client/brisken/p1-match-description`) — another session owns the matcher's descriptions.
- **Items 130, 131 and 132** — all three sit inside those frames.
- The **matcher itself** (`src/expense_recon/matching/**`). Item 127 is about RUNNING the accuracy scorer in CI, never about changing how matching works. If your work would edit a file under `matching/`, you have left your lane: stop and say so.

If you find something broken outside your fence, write ONE line in your checkpoint's Open Questions naming it. Do not fix it. A second session fixing the same file is the one failure mode this split exists to prevent.

**Already shipped, do not rebuild:** items 98, 104, 144, 146, 147, 148, and the prompt halves for 109 and 130. Read the backlog heading before starting any item; a `SHIPPED` marker means it is done.

## Where it stands (2026-09-18, after the second pass)

All five fenced items are SHIPPED. The first pass shipped 123 (PR #1098), 127 (#1099), 128 (#1100), 125 (#1101) and 129's backend (#1103), all live on Fly **v187**.

The second pass found and fixed the one live defect, **PR #1106 (merged `c8b9d8e6`)**: item 123's monitor detected a dead app and then alerted nobody. GitHub starts a `run:` block as `bash -e {0}`, and the step's own `set -uo pipefail` does not undo that `-e`, so the probe's DOWN exit (1) aborted the step before the `rc=$?` line that hands 1 to the notifier; the Notify step was skipped by its implicit `success()` condition. Live proof, run 35361771075: `summary: DOWN: api` then `Process completed with exit code 1`, Notify skipped. The fix is `|| rc=$?` on the probe line, guarded by `tools/tests/test_recon_uptime_workflow.py`, which lifts the step's real text out of the YAML and runs it under `bash -e` with a stub probe (green on 0 and 1, red on 2). Re-rehearsed after the merge, run 35363507882: `success`, Notify ran and named the issue it would open and the one mail it would send. PR #1106 is repo-side only, so **no deploy**; Fly is still v187.

**The cron has still never fired.** `gh api .../actions/workflows/361424780/runs?event=schedule` returns `total_count = 0`, polled every three minutes from 15:18Z to 16:04Z (16 of 16 polls zero, API re-read at 16:07Z), against a workflow that landed on main at 14:12Z with `*/10 * * * *`. The workflow is `active`, Actions is enabled (`allowed_actions: all`), the repo is public and not a fork. The repo's other three scheduled workflows (morning-briefing, eod-capture, weekly-review) have been `disabled_manually` since 2026-06-27, so there is no second cron to compare against. Checkpoint: `docs/2026-09-18 - Brisken Recon Ops Tail Second Pass/Mini-Checkpoint-1.md`.

## Your queue, in order

1. **Read `GET /feedback.jsonl` first** (70 lines through 2026-09-18 15:00Z, unchanged across both passes; #70 is the OWNER's note on run `af8936c6b05a`: "add receipts function just opens receipt view in new tab but does not really add it", untriaged and outside the fence unless the owner assigns it). A new note from Criss outranks everything below.
2. **Item 123 cron.** `gh api "repos/011matthias/agentic-ops1.01/actions/workflows/361424780/runs?event=schedule&per_page=1"`. If `total_count` is still 0, GitHub's scheduler is not running this monitor and the monitor only works when dispatched by hand, which is the owner's call between three options: keep waiting on the best-effort scheduler, add a redundant local runner (precedent: the `MejiWeeklyReview` Windows scheduled task, and memory `feedback_agent_can_register_scheduled_tasks`), or point a free external monitor at `/healthz` as backlog item 123 originally proposed. Do not build one unasked. If it HAS fired, check the runs are green and no `recon-uptime` issue is open; a red run for a probe error (exit 2) is yours to fix, a DOWN is the app.
3. **Item 123 real alert path.** The issue-plus-mail leg has still never run for real; only the dry run has. It was deliberately not fired unattended, because the mail's subject reads `expenses.brisken.com is down` and would reach the owner as a false alarm. When the owner wants it: `gh workflow run expense-recon-uptime.yml -R 011matthias/agentic-ops1.01 -f api_override=https://127.0.0.1:9` (opens the issue, sends one mail), then re-run with no override to close it and send the recovery mail.
4. **Item 129 paste check.** Fetch `https://expenses.brisken.com/` and grep its `/assets/*.js` for `mh.rematch.last`. Today it carries only the old toast keys (`rematch.open`, `rematch.done`, `rematch.failed`, `rematch.nothingNew`, `rematch.noStatement`), so the prompt is unpasted and `docs/PROMPT-STATUS.md` stays Not-applied. Once it is live, drive the August header cold in EN and PT-BR and move the row to Applied.
5. **Item 125 second leg.** Read the newest mail-sourced receipt on `GET /api/expense-batches/{id}` and report `submitted_by.transport_tls`; a `false` names a sender still delivering in the clear. Nothing has arrived by mail since the deploy: the newest mail provenance in the live store is 2026-09-09 (August `074a7b8905d7`, 23 `submitted_by` blocks, the key absent on all of them, which is what `intake_mail._provenance_entry` predicts for a pre-2026-09-18 archive), and the April batch `0603bb0e6f38` the owner created on 09-18 at 11:23Z is upload-sourced with `submitted_by` null on all 34 rows. Leg 1 re-verified live on machine `7843d54b579598`: EHLO advertises `starttls`, `220 Ready to start TLS`, TLS 1.3 `TLS_AES_256_GCM_SHA384`, 845-byte cert, read-only (no MAIL FROM).
6. Nothing else is in the fence. Residues are recorded in the backlog under each item and are the owner's call: 127's per-month verdict tally, 128's reader-version stamp, 129's per-file "matched with X" line, 125's CA certificate, 123's Brisken-mailbox recipient.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open`, `git worktree list`, and grep recently modified transcripts in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/*.jsonl` for the item number. A number another session is holding is not yours, even if it is in your list.

## Staying out of the other three sessions' way

All four of you share ONE clone, so these are not style preferences:

- **Your worktrees are prefixed `agentic-ops1-ops-`** (e.g. `agentic-ops1-ops-127`). Your branches are `client/brisken/p1-ops-<item>-<slug>` and `docs/ops-<topic>`. Never create a branch or worktree outside those namespaces, and **never remove a worktree you did not create** — `git worktree list` is full of other sessions' live work. This pass's `agentic-ops1-ops-123b` and `agentic-ops1-ops-ckpt2` are merged and may be removed.
- **Never `git stash`.** The stash is shared across every worktree in the clone; a sibling will pop yours. Commit on a branch instead.
- **Never `git add -A`.** Stage explicit paths only.
- **Use a session-unique checkpoint payload**: `.scratch/checkpoint-payload-ops.json`, never the bare `.scratch/checkpoint-payload.json`.
- **Ledger files go through a `docs/ops-...` PR only** (`docs/INDEX.md`, `docs/friction-register.md`, `docs/sessions/*.md`). Never commit one on a feature branch.
- **The Shipped table in `p1-improvement-backlog.md` is the #1 collision point.** Main's table already carries two legacy rows numbered 37, so never dedupe the whole table. After merging origin/main, rebuild the table as origin/main's rows verbatim plus your row numbered max+1 on top (the second pass added row 97), and drop a merge-duplicated `### N.` heading (the copy without the SHIPPED suffix). Expect every merged sibling PR to turn yours DIRTY: merge main again, rebuild, push, wait for CI.
- **For `api-contract.md` and `PROMPT-STATUS.md`, keep main's sections first and append yours.** If your section makes an earlier sentence false, fix that sentence in place. (The second pass did exactly that to item 123's "the 10-minute cron is live" claim.)
- **Never write a PR number into docs before `gh pr create` returns it.** #1105 was taken by a sibling session mid-session; the correction cost an extra commit.
- **Deploys are serialized whether you like it or not.** Always read the version back with `flyctl releases` and never infer it from your own deploy.

## How to work

- **The API host is `https://brisken-expense-recon.fly.dev`.** `expenses.brisken.com` serves only the SPA; the SPA calls `api.expenses.brisken.com`. **Python's default urllib User-Agent is refused by Cloudflare** (`403 error code: 1010`); send a browser UA on every request. `MSYS_NO_PATHCONV=1` for every `/api/...` arg in Git Bash, but NOT on a `git -C /c/...` call, where it stops the POSIX root resolving. Windows Python cannot open `/c/...` paths: pass `C:\...`. The operator code is vault entry "Expense Recon App", field `operator_code` (`python C:\Users\neuma_p1qrsic\vault.py get "Expense Recon App"`); never print it or a token. Everything except `/api/login` and `/healthz` needs `Authorization: Bearer <token>` from `POST /api/login {"code": ...}`.
- **`git show origin/main:<path>` fails in Git Bash** (MSYS rewrites the colon pathspec). Read the file through a worktree, or run the command through the PowerShell tool.
- **No writes to Criss's live months, ever.** Read-only API calls only. Never probe publish. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes: never fetch it live.
- **Parallel builder subagents work well**: one worktree per item, a `general-purpose` Agent per worktree in the background with a self-contained brief (hard rules, measurement, docs, commit on the branch, do NOT push), `uv run tools/bg_watch.py watch` per builder. Tell every builder: report anything in the brief that turned out to be WRONG. Builders share your scratchpad directory: name their scratch files by item.
- **Never chain a mutating git command through a pipe** (`git merge ... | tail && git push`): the pipe hides the conflict exit and the push runs anyway. Use `if git merge ...; then ...; else ...; fi`.
- **`tools/regress_check.py` is unusable.** Prove every wiring point BY HAND: `cp` the source aside, disable it with a single-line change, run the targeted pytest, read the FAILED lines, `cp` back, confirm byte-identical. A red proof that does not go through the real caller does not bite. The second pass's proof is the model: the test lifts the CALLER's own text (a workflow step) and runs it, so unwiring the fix turns it red with the live run's exact exit code.
- **A green suite is not a wired feature.** Item 123's 19 probe tests passed for a day while the alert path was dead, because every one of them called the script and none of them called the step that calls the script. Ask what sits between the test and the effect.
- **The negative-case fixture is where defects come from.** Name the specific absent row class in every brief.
- **Patch CRLF sources in BYTE mode.** Python heredocs with triple quotes are blocked by a hook: write scripts with the Write tool. A bare persistent `cd` is blocked: use `( cd X && ... )` or `git -C`. Never `git checkout --` to restore a backup; use `cp`.
- **Full module suite in the FOREGROUND before any PR:** `uv run --extra dev --extra web pytest -q -p no:cacheprovider` from the module root (~5 min, ~2547 tests). For a change under `tools/`, `.claude/hooks/` or `tools/tests/`, `uv run tools/preflight-hooks.py --full` is the CI-equivalent (~6 min, 1968 tests). Deploy with `flyctl deploy . -a brisken-expense-recon --remote-only` from a clean detached origin/main worktree (pre-authorized).
- **After a deploy:** a live API probe of the changed field, then a cold consumer drive (headless Playwright `channel="chrome"`: fresh context, goto, set localStorage `brisken.lang`, fill the first input with the operator code, Enter, goto the route, read `body` inner text, record non-GET requests, which must be none besides login). Dismiss the feedback widget first (`[data-fb-widget] [role=dialog]`, its "Got it" button via JS `click()`). Say plainly what the drive covered.
- In the same PR, update the backlog item's heading and its Shipped row, plus `status/p1-expense-reconciliation.md`.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine and with four sessions live it will usually be someone else's; trust its `context=` ONLY when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl`. Keep a small script for it in your scratchpad. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check costs about 45k; a builder-run item costs you 30-60k because the builder burns its own window; a matcher-scale item with before/after measurement costs about 225k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries you registered.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/ops-...` worktree off origin/main and `--root <that worktree>` BEFORE the `finalize` subcommand (it is a global flag); use `.scratch/checkpoint-payload-ops.json`; write the checkpoint prose after `finalize` or rename your file to the number it prints; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; the SCOPE FENCE section verbatim; where it stands (what shipped with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with exact code pointers and live evidence; the "Staying out of the other three sessions' way" and "How to work" sections; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session (labelled as such), and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````

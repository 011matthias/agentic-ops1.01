# Mini-Checkpoint: Repo Layout Execution Batch 1

**Date:** 2026-10-28
**Status:** First execution batch of the layout plan shipped; queue continues at W1-14
**Type:** mini

---

## Summary
First session executing `docs/2026-10-28 - Repo Layout Audit/PLAN.md`: the permission probe answered, eight owner decisions recorded, the eight stranded ledger PRs re-landed, and four mechanical items merged (W1-1, W1-2 pending CI at write time, W1-3, W1-13).

## What Was Done
- **W1-0 (PR #1654):** a hook `ask` is a real prompt under `auto`. git-stash-gate logged ASK at 14:53:28 and the probe's first line ran at 17:13:02, a 2 h 19 min hold, although `.claude/settings.json` allows `Bash` wholesale. All 40 recent transcripts ran `permissionMode: auto`; none ever ran `bypassPermissions`. Floor gates are real; no deny conversion.
- **Owner decisions (AskUserQuestion, PR #1655):** D1 retire the Trigger.dev/Railway lane now; D2 handoff repos under UnpauseAI's GitHub (not the recommended client-owned repo); D3 all of (a)-(g); D4 the whole list incl. the repo-sweep remote-delete pre-authorization; D16 leave the backups and executions.json out; D17 backup only, Jochen code stays untracked; D18 private context repo, secrets excluded; W1-0 allow-list prune dropped. D5 waits for W1-24's dry-run table (the prune tool does not exist yet).
- **W1-4:** (a) #1638, #1226, #1198, #1178, #1161, #1073, #970, #955 all merged, serially, each after a local `merge origin/main` (union drivers) and session-log normalize; the p1 status file and the register archive took main's version as planned; the WW Hero checkpoint is on main with its INDEX row. (b) `fetch.prune=true` on the primary. (c) the 10 husk dirs removed (Repo entries 107 to 97). (d) NOT done: three live sibling sessions on the primary at every check.
- **W1-3 (PR #1656):** `merge_verdict` reads `gh pr view --json mergeable,statusCheckRollup` via new `.claude/hooks/_gh.py` (repo-sweep imports `classify_rollup` from it); CONFLICTING asks with the merge-main remedy and is not cleared by a merge-anyway override. regress_check bites on both wiring points.
- **W1-1 (PR #1657):** platform.yml (quality, spell, smoke with a Playwright browser cache) and lead-desk-tests.yml split out, path-filtered; ci.yml keeps hooks + secrets; concurrency on all four keyed on workflow name. Verified: docs PR #970 listed only secrets + hooks, exit 0.
- **W1-13 (PR #1659):** repo-sweep skips a parked primary (live dry run printed `skip: primary parked on client/meji-media/status-current-10-09`), vets every untracked file through file-placement-gate.py, skips token/snapshot shapes, lists leftovers in the PR body; `test_root_layout.py` pins the committed root. regress_check bites on three wiring points. `_placement.py` not factored (no second consumer); CREDENTIAL_PATTERNS kept.
- **W1-2 (PR #1660):** the full pytest step gated by dorny/paths-filter; ledger + root-layout tests stay unconditional. Filter extended beyond the plan with `workspace/projects/vinted-reselling/**` (four tests import its code) and the whole expense-recon app folder.

## What Did NOT Work (and why)
- **Six `gh pr merge` calls sent in parallel:** three merged, three then failed `Pull Request has merge conflicts`, because each merge moves INDEX.md and GitHub's merge does not run the union drivers. Ledger PRs must merge one at a time, each after a local re-merge of main.
- **`gh pr merge` inside a for-loop:** blocked by pattern rule `block-merge-chained-after-any-command` (the CI gate reads once per command); one merge per call.
- **`MSYS_NO_PATHCONV=1` with `git -C /c/...`:** the suppression also stopped the `/c/` path from converting, so git found no directory; use `C:/...` paths when the variable is set.
- **`rmdir $R/$h`:** refused by the built-in removal check (an unset variable could expand to `/`); `"${R:?}"/"${h:?}"` passes.
- **Gate tests run alone:** `KeyError: '_gh'`, because the in-process gate import needs the hooks dir on sys.path; the first green run passed only because test_repo_sweep imported `_gh` first. Fixed in the test file.

## Current Status
Ops status: not applicable (system scope, no infrastructure.yaml). Open PRs not this session's: #1650 (sibling WW checkpoint, today) and #1649 (the sweep's commit onto the parked primary's branch, held by a live session). Primary clone still parked on client/meji-media/status-current-10-09 with live siblings. Worktrees this session: ao1-layout-1, ao1-layout-2, ao1-layout-docs, ao1-tmp-1198 (all removable once their branches merge). Context at checkpoint: about 380k.

## Next Steps
1. W1-4(d) when the primary is free; then W1-14 (pii_scan + push gate) with W1-35 (gitleaks config), W1-31 (100 `text=True` calls lack `encoding=`: 50 in tools/.claude/hooks, 50 in tools/tests).
2. W1-16 .. W1-20, then execute D1, D3, D4, D18 (D17 folds into D18) in that order; then the WW migration prompt may run.
3. W1-24 builds the prune tool, then ask D5 with its dry-run table.

## Files to Read First
- docs/2026-10-28 - Repo Layout Audit/PLAN.md (Status lines current as of this checkpoint)
- this file

## Continuation prompt

````
/comd_resume system

(System scope, no client. If resume asks you to pick a project folder, answer "system" and carry on with this prompt; the context YAML has a `system` entry from the 2026-10-28 checkpoints.)

## Where it stands

The repo layout plan is the queue: `docs/2026-10-28 - Repo Layout Audit/PLAN.md` on origin/main (read it from a fresh worktree; the primary clone is parked on a merged meji branch with live sibling sessions). Its Status lines are current; `docs/2026-10-28 - Repo Layout Execution Batch 1/Mini-Checkpoint-1.md` has this batch's notes.

Shipped 2026-10-28 (batch 1): W1-0 PR #1654 (a hook `ask` is a real prompt under `auto`, the mode every session runs in; floor gates are real); owner decisions PR #1655 (D1 retire now, D2 handoff repos under UnpauseAI's GitHub, D3 all of (a)-(g), D4 whole list incl. the sweep pre-authorization, D16 leave both out, D17 backup only and the code stays untracked, D18 private context repo with secrets excluded, allow-list prune dropped); W1-4 (a)(b)(c) (all eight stranded ledger PRs merged, fetch.prune, 10 husks removed); W1-3 PR #1656 (merge gate reads mergeability via `.claude/hooks/_gh.py`); W1-1 PR #1657 (platform.yml and lead-desk-tests.yml split, concurrency); W1-13 PR #1659 (sweep skips a parked primary, vets untracked files through the placement gate, test_root_layout.py); W1-2 PR #1660 (hooks pytest gated by paths-filter; confirm it merged and that the next docs PR shows the pytest step skipped).

Waits on the owner: D5 (asked after W1-24 builds tools/worktree_prune.py and its dry-run table exists); D6 .. D15 and D19; the D3(g) remote-branch deletions need a fresh explicit order in the session that runs them; gh `delete_repo` scope for 011matthias/agentic-ops1; the Brisken-Oct1-Invoice-And-Retainer task outcome.

## Queue, in order

1. Read PLAN.md's "Client-ops guard" section first (owner, 2026-10-28): any item whose changed paths reach a live surface in its table needs a read-only before-check, the owner's yes for THAT item at execution time (AskUserQuestion, surface named; earlier D approvals do not cover it) and the same check after. W1-4(d) is done (primary on main since 22:29). The Brisken notifier IPv4 fix is on branch client/brisken/recon-notify-ipv4: confirm its PR merged and that `.scratch/recon-notify-runs.log` in the primary shows exit=0 on the runs since.
2. W1-14 (pii_scan.py + pii-push-gate.py + repo-sweep wiring + CI job) together with W1-35 (`.gitleaks.toml` after the differential probe against commit 57415748 and a scratch file in the WW .env shape). repo-sweep's plan() already takes a placement classifier and skips `??` files through `secret_shape`; hook the pii scan in beside it.
3. W1-31 (rescoped under the guard: NO global `PYTHONUTF8=1`, it would change how session-launched client scripts decode files): one `encoding="utf-8", errors="replace"` helper in `.claude/hooks/_shell.py`; 50 non-test and 50 test `text=True` calls lack `encoding=`; project_status.py:341 is the crash site; doctor.py marks a Traceback tail not-ok; a CI leg that can go red.
4. W1-16 (infrastructure.yaml loader), W1-17 with W1-36 (mcp_config, MCP fleet), W1-18 (client homes), W1-19 (WW tests in CI, n8n test mode; follow the W1-1 path-filtered workflow shape), W1-20 (WW import pre-flight).
5. Execute the approved D1, D3, D4, D18 in that order (D2's CLAUDE.md change rides with D1; D17 is covered by D18). D3(a) also touches akkton/unpauseai-web via its content/<slug> publish path; D3(f) deletes the two root PNGs and must drop the TEMPORARY exemption in tools/tests/test_root_layout.py in the same change.
After step 5 the WW migration prompt may run in its own session. The rest continues in parallel or after:
6. Always-loaded context: W1-5 .. W1-12.
7. W1-15, W1-21 .. W1-30, W1-32 .. W1-34 (W1-24 builds the prune tool, then ask D5 with its dry-run table; W1-26 should also cover the git-stash-gate false positive on a commit message that quotes `git stash push`, seen 2026-10-28), then D6 .. D15 and D19 as the owner answers, X1 .. X8 when their triggers fire.

Each item's Verify line is the acceptance criterion; a green suite alone is not.

## How to work

- Work in a fresh worktree off origin/main, never in the primary clone (shared by sibling sessions, parked on a merged branch): `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b sys/layout-<item> C:\Users\neuma_p1qrsic\Repo\ao1-layout-<n> origin/main`. Gitignored client context/ exists only in the primary clone; read it by absolute path when an item needs it. Remove this batch's ao1-layout-1, ao1-layout-2, ao1-layout-docs and ao1-tmp-1198 once their branches are merged.
- One PR per item on a `sys/layout-<item>` branch; the B6 chain runs without asking: commit, push, `gh pr create`, merge on CI green, one `gh pr merge` per Bash call, never in a loop or in parallel. Ledger PRs merge strictly one at a time: GitHub's merge ignores the union drivers, so every merge to main re-conflicts the other ledger PRs on INDEX.md until each is re-merged locally. Ledger edits (INDEX, register, session logs, checkpoint folders, PLAN.md Status lines) go on `docs/...` branches only. For changes under tools/, .claude/hooks/ or tools/tests/: `uv run tools/preflight-hooks.py` (`--full` when tools/tests change) before the push, and prove each fix with `uv run tools/regress_check.py` from the worktree that holds the change. Tests that load a hook in-process must put `hooklib.HOOKS` on sys.path themselves.
- Owner decisions only through AskUserQuestion with the recommendation first; never an open offer. The owner can be away for hours: a hook `ask` held a call for 2 h 19 min on 2026-10-28, so avoid triggering floor gates speculatively.
- The repo is public by owner decision (2026-09-16); never re-raise it. Never push a file carrying real addresses, rosters or secrets; count PII, never print values. Test fixtures build secret-shaped strings at runtime so gitleaks has no literal to flag. Nothing of WW is pushed until W1-20's scan is clean and the owner has seen the public file list.
- Hero, n8n and mail writes in any client tenant need a per-action yes; never touch the held R1 test on HUK-106488.
- Client operations come first (owner, 2026-10-28: "i cannot risk this jeopardizing any ongoing client operations"). Every merge to main reaches the Brisken notifier within 15 min (its clone fast-forwards each run); the Meji tasks and the notifier read the primary's gitignored context/ by path. PLAN.md's Client-ops guard table is the map; check it before every item.
- PLAN.md is the only queue: update its Status lines in your checkpoint's docs PR. When an item touches a client's status/ workstream, bump that status file in the same session.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume system`; where it stands (what shipped this session with PR numbers, what is in flight and why, what waits on the owner); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any other paste-ready prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no PLAN.md item is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner.
````

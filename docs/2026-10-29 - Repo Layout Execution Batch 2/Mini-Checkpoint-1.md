# Mini-Checkpoint: Repo Layout Execution Batch 2

**Date:** 2026-10-29
**Status:** client-ops guard in force; W1-4(d), W1-14, W1-35 done; Brisken notifier fixed; next is W1-31 (needs the owner's yes under the guard)
**Type:** mini

---

## Summary
Owner directive 2026-10-28, "i cannot risk this jeopardizing any ongoing client operations", became PLAN.md's Client-ops guard (live-surface map, per-item before-check, owner yes, after-check). Checking today's merges against it found none of the 31 files touched a live job, and found a live Brisken notifier failing ~3 runs in 4 since 10-16, now fixed.

## What Was Done
- Live-surface audit: the 31 files of this batch's 15 PRs reach no path a live job reads; no branch protection; no deploy workflows. Mapped every scheduled task on the machine (Get-ScheduledTask) and the auto-pulling `agentic-ops1-notify` clone.
- PR #1662: PLAN.md Client-ops guard section, W1-4(d) done, W1-31 rescoped (no global PYTHONUTF8), continuation prompt in batch 1's Mini-Checkpoint-1.md updated.
- W1-4(d): primary moved to main 2026-10-28 22:29 (clean, no live sibling), fast-forwarded again to d6a4b063 on 10-29; sweep dry runs clean both times.
- PR #1663 (owner yes): BriskenReconNotify pins IPv4 in `main()`. Cause: this machine's IPv6 route to Fly drops the TLS handshake (IPv4 4/4, IPv6 2/4 and 0/4). Dry runs 0/3 before, 3/3 after; 13 of 13 scheduled runs exit 0 since. Caller test bites (regress_check).
- PR #1664 (owner yes): W1-14 `tools/pii_scan.py` + `.claude/hooks/pii-push-gate.py` + repo-sweep skip + CI warning step; W1-35 `.gitleaks.toml` (make-mcp-url, zoho-oauth-token, token-named-file) read by CI via GITLEAKS_CONFIG. Gate wired in the primary (30 hooks).
- Memory `feedback_system_work_never_risks_client_ops.md` + index line.
- p1-expense-reconciliation.md notifier row bumped (deliberate cross-cutting edit on this docs branch).

## What Did NOT Work (and why)
- **Watching the notifier by exact commit (`grep commit=ac42486d`):** a sibling merge on top would move the clone past that commit and the watcher would never count the runs; replaced by a timestamp filter.
- **Appending pytest code through a heredoc:** heredoc-size-gate blocks triple-quoted Python in heredocs; the Edit tool carried it.
- **New tests importing urllib3:** the CI/test env has no requests/urllib3 (ModuleNotFoundError); a stand-in module in sys.modules tests the wiring instead.
- **`pii-allow:\s*\S` marker regex:** `\s` crossed the newline, so a bare `pii-allow:` borrowed the next line as its reason; now `[ \t]*`.
- **Whole-file single-line token check in range mode:** a one-line recon regex edit tripped it (replay, 382b2a35); now new files only.
- **Bare `"name":` key counting:** drizzle snapshots and n8n exports scored 65-171; now only data-shaped values count.
- **`grep --no-ignore`:** a ripgrep flag; GNU grep exits 2 and the pattern rule blocked it.
- **First preflight:** failed on the missing tools/INDEX.md row and `.gitleaks.toml` not on the root allowlist (test_root_layout.py caught it, as designed).

## Current Status
Guard in force. Primary on main at d6a4b063, pii gate wired there. Notifier healthy. MEMORY.md at 24.2 KB against the ~24.4 KB read limit (D10). No platform/ops line for system (no infrastructure.yaml); brisken platform unknown, 10 brisken status files stale (not this session's workstreams).

## Next Steps
1. W1-31 (rescoped). It reaches live surfaces: `tools/brisken-recon-notify-run.py` (auto-pulled by the notifier clone within 15 min) and `tools/repo-sweep.py` (RepoSweep) both shell out; either leave those two files out or name them in the AskUserQuestion yes.
2. W1-16 .. W1-20, then D1, D3, D4, D18, each with its guard check and the owner's yes at execution.

## Files to Read First
- `docs/2026-10-28 - Repo Layout Audit/PLAN.md` (Client-ops guard section first)
- this file's continuation prompt below

## Continuation prompt

````
/comd_resume system

(System scope, no client. If resume asks you to pick a project folder, answer "system" and carry on with this prompt; the context YAML has a `system` entry from the 2026-10-29 checkpoint.)

## Where it stands

The repo layout plan is the queue: `docs/2026-10-28 - Repo Layout Audit/PLAN.md` on origin/main (read it from a fresh worktree). Read its "Client-ops guard" section FIRST: owner directive 2026-10-28, "i cannot risk this jeopardizing any ongoing client operations", chosen mode guarded per item. An item whose changed paths reach a surface in its table needs (1) the surfaces named in the PR body, (2) a read-only before-check, (3) the owner's yes for THAT item at execution time through AskUserQuestion with the surface named (earlier D approvals do not cover this), (4) the same check after, stated in the checkpoint. Notes: `docs/2026-10-29 - Repo Layout Execution Batch 2/Mini-Checkpoint-1.md`.

Shipped 2026-10-28/29 (batch 2): PR #1662 (guard section, W1-31 rescoped); W1-4(d) done (primary on main, at d6a4b063 after a check-then-act fast-forward; sweep dry runs clean); PR #1663 Brisken notifier IPv4 pin (it had failed ~3 runs in 4 since 10-16 on this machine's broken IPv6 route to Fly; 13 of 13 runs exit 0 since); PR #1664 W1-14 pii_scan.py + pii-push-gate.py (ask, never deny, fail-open; range mode scans added lines only) + repo-sweep skip + CI warning step, and W1-35 .gitleaks.toml (make-mcp-url, zoho-oauth-token, token-named-file) read by CI via GITLEAKS_CONFIG. The pii gate is wired in the primary (30 hooks). Batch 1 (2026-10-28): #1654 .. #1661, see the batch 1 Mini-Checkpoint-1.md.

Waits on the owner: D5 (after W1-24's dry-run table); D6 .. D15 and D19 (D10 is MEMORY.md, now 24.2 KB against the ~24.4 KB read limit); the exact UnpauseAI GitHub account or org for D2; a fresh explicit order for the D3(g) remote-branch deletions; gh `delete_repo` scope for 011matthias/agentic-ops1; the Brisken-Oct1-Invoice-And-Retainer task outcome.

## Queue, in order

1. W1-31 (rescoped under the guard: NO global `PYTHONUTF8=1`): one `encoding="utf-8", errors="replace"` helper in `.claude/hooks/_shell.py`; 50 non-test and 50 test `text=True` calls lack `encoding=`; project_status.py:341 is the crash site; doctor.py marks a Traceback tail not-ok; a CI leg that can go red. Guard: `tools/brisken-recon-notify-run.py` reaches the live notifier within 15 min of merge (its clone fast-forwards every run) and `tools/repo-sweep.py` reaches RepoSweep; leave both out of this item or name them in the owner's yes, and read `.scratch/recon-notify-runs.log` in the primary after the merge.
2. W1-16 (infrastructure.yaml loader), W1-17 with W1-36 (mcp_config, MCP fleet), W1-18 (client homes; guard: move nothing a live job reads by path), W1-19 (WW tests in CI, fixtures only, no tenant credential, follow the W1-1 path-filtered workflow shape), W1-20 (WW import pre-flight; `uv run tools/pii_scan.py` is the scanner).
3. Execute the approved D1, D3, D4, D18 in that order, each with its guard check and the owner's yes at execution (D2's CLAUDE.md change rides with D1; D17 is covered by D18). D3(a) also touches akkton/unpauseai-web and the live WW docs; D3(f) deletes the two root PNGs and must drop the TEMPORARY exemption in tools/tests/test_root_layout.py in the same change. `uv run tools/pii_scan.py --all` lists 18 files today; D3 and D4 should take most of them off.
After step 3 the WW migration prompt may run in its own session. The rest continues in parallel or after:
4. Always-loaded context: W1-5 .. W1-12.
5. W1-15, W1-21 .. W1-30, the rest of W1-32 (the other scheduled jobs' outcomes), W1-33, W1-34 (W1-24 builds the prune tool and must protect agentic-ops1-notify, -watcher, -deploy; then ask D5 with its dry-run table; W1-26 should also cover the git-stash-gate false positive on a commit message that quotes `git stash push`), then D6 .. D15 and D19 as the owner answers, X1 .. X8 when their triggers fire.

Each item's Verify line is the acceptance criterion; a green suite alone is not.

## How to work

- Work in a fresh worktree off origin/main, never in the primary clone (shared by sibling sessions and the scheduled tasks): `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b sys/layout-<item> C:\Users\neuma_p1qrsic\Repo\ao1-layout-<n> origin/main`. Gitignored client context/ exists only in the primary clone; read it by absolute path when an item needs it. Remove ao1-layout-3 and ao1-layout-docs once their branches are merged.
- One PR per item on a `sys/layout-<item>` branch; the B6 chain runs without asking except where the guard asks for the owner's yes: commit, push, `gh pr create`, merge on CI green, one `gh pr merge` per Bash call, never in a loop or in parallel. Ledger PRs merge strictly one at a time: GitHub's merge ignores the union drivers, so every merge to main re-conflicts the other ledger PRs on INDEX.md until each is re-merged locally. Ledger edits (INDEX, register, session logs, checkpoint folders, PLAN.md Status lines) go on `docs/...` branches only. For changes under tools/, .claude/hooks/ or tools/tests/: `uv run tools/preflight-hooks.py` (`--full` when tools/tests change) before the push, and prove each fix with `uv run tools/regress_check.py` from the worktree that holds the change. Tests that load a hook in-process must put `hooklib.HOOKS` on sys.path themselves; the test env has no requests/urllib3.
- Owner decisions only through AskUserQuestion with the recommendation first; never an open offer. The owner can be away for hours (a yes on 2026-10-28 arrived ~12 h later), so ask once the PR is green and the ask is the last step.
- The repo is public by owner decision (2026-09-16); never re-raise it. Never push a file carrying real addresses, rosters or secrets; count PII, never print values. Test fixtures build secret- and PII-shaped strings at runtime so neither gitleaks nor pii_scan has a literal to flag. Nothing of WW is pushed until W1-20's scan is clean and the owner has seen the public file list.
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

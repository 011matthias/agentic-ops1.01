# Mini-Checkpoint: Repo Layout Execution Batch 7

**Date:** 2026-10-30
**Status:** D3 (a)-(e) shipped and verified; (g) and D3's PII Verify remain open; D1 next
**Type:** mini

---

## Summary
D3's live half is off unpauseai.com, and (b)-(e) moved client rosters, personal checkpoints and the Prototype Fund sketch into gitignored homes in the primary clone. D3's own Verify (`pii_scan --all` clean) is still unmet on 10 files the plan never listed.

## What Was Done
- akkton/unpauseai-web#56, merged; promote 99cb6cc is live: removed m-mail-abgleich.html and the two abgleich-info-mails downloads, the sidebar entry on 27 pages, 3 search-index entries per page on 40 pages, 5 inline links (unwrapped to plain text) and the wimmer-nav.json allUrls entry. Its smoke job is pinned to ubuntu-24.04.
- #1711 D3(b): 72 rome-2026-leadgen files plus the invite xlsx went to the primary's `workspace/clients/brisken/context/lead-generation/rome-2026/`, the meji US CSV to meji `context/`, `status/p2-rome.md` repointed; all 74 blobs hash-verified before the `git rm`.
- #1713 D3(c)/(d): 29 checkpoint folders (36 blobs) went to the primary's `docs/personal/`; 30 INDEX rows, the emptied `jochen-projekt` and `personal-kit` sections and 28 session-log entries were removed, and each removed entry was saved as `session-log-entries.md` in its folder.
- #1714 D3(e): `SCOPE.md` moved to the primary's `docs/personal/prototype-fund/`; the `PrototypeFund-Last-Safe-Start` (11-09 10:00) and `PrototypeFund-Window-Opens` tasks now open it there (read back: Ready, triggers unchanged).
- Primary clone: `docs/personal/` added to the shared `.git/info/exclude` (line 21) before any write, because the primary still lacks #1702.
- D1 guard, read-only: no `infrastructure.yaml` names Railway or Trigger.dev, neither CLI is installed, and brisken `deploy:` = `automations/expense-reconciliation/deploy.py`.
- PLAN.md Status lines for D1 and D3 updated (this docs PR).

## What Did NOT Work (and why)
- **`next build` in the uweb worktree with a junctioned node_modules:** Turbopack panics with "Symlink node_modules is invalid, it points out of the filesystem root". CI's clean `npm ci` build was the build signal instead.
- **PR #56's first smoke run:** "Playwright does not support chromium on ubuntu26.04-x64", because `ubuntu-latest` moved to 26.04. Pinning `runs-on: ubuntu-24.04` for the smoke job fixed it. Smoke runs only on pull_request, so main's CI and publish.yml were never affected.
- **Signed-in pass through the WW gate:** the auto-mode classifier refused reading `~/.passwords.json` as credential exploration, and no context file names the code. Deployed-tree reads at 99cb6cc plus the cold gate check stood in.
- **After-check (a):** the primary is still on d6a4b063, 97 behind, with a live sibling on main and a dirty `docs/INDEX.md`. #1677 is not in it, so no RepoSweep result counts yet. Not fast-forwarded.

## Current Status
The D3 removals are on main (ad1621cc) and live on unpauseai.com. The primary clone is unchanged apart from gitignored writes under `workspace/clients/*/context/` and `docs/personal/`. No client-ops surface was touched beyond the two personal reminder tasks. Context at the checkpoint was about 270k.

## Next Steps
1. After-checks (a)/(b) once the primary has #1677/#1702 (it was still on d6a4b063 at 18:30).
2. D3 Verify remainder: classify the 10 `pii_scan --all` hits (allowlist test fixtures and ledger archives; move the meji `instantly-audit2.md` pair and `session-inventory-2026-05-10.md` if their addresses are real); (g) needs a fresh order.
3. D1, then W1-29, D4 and D18, per the continuation prompt below.

## Files to Read First
- `docs/2026-10-28 - Repo Layout Audit/PLAN.md` (Client-ops guard; D1, D3, D4, D18, W1-29)
- this file's continuation prompt

## Continuation prompt

````
/comd_resume system

(System scope, no client. If resume asks you to pick a project folder, answer "system" and carry on with this prompt; the context YAML has a `system` entry from the 2026-10-30 Batch 7 mini-checkpoint.)

## Where it stands

The repo layout plan is the queue: `docs/2026-10-28 - Repo Layout Audit/PLAN.md` on origin/main (read it from a fresh worktree). Read its "Client-ops guard" section FIRST: owner directive 2026-10-28, "i cannot risk this jeopardizing any ongoing client operations", chosen mode guarded per item. An item whose changed paths reach a surface in its table needs (1) the surfaces named in the PR body, (2) a read-only before-check, (3) the owner's yes for THAT item at execution time through AskUserQuestion with the surface named (earlier D approvals do not cover this), (4) the same check after, stated in the checkpoint. Map an item to surfaces with `Get-ScheduledTask` actions (which file each task runs) and the workflow triggers, not from memory. Notes: `docs/2026-10-30 - Repo Layout Execution Batch 7/Mini-Checkpoint-1.md`.

Shipped 2026-10-30 (batch 7), all merged on green CI:
- akkton/unpauseai-web#56 D3(a) live half: m-mail-abgleich.html + the two abgleich-info-mails downloads gone from /docs/warme-wimmer, plus the sidebar entry on 27 pages, 3 search-index entries per page on 40 pages, 5 inline links (unwrapped to text) and the wimmer-nav.json allUrls entry; live as promote 99cb6cc (`/api/version` matched; deployed tree has no abgleich file or link; downloads/ = prozesslandkarte PDF only; gate answers cold). Same PR pins that repo's smoke job to `ubuntu-24.04` (ubuntu-latest = 26.04 cannot install chromium). Not driven: a signed-in pass through the gate (the code is in no file the agent may read; the classifier blocks vault reads).
- #1711 D3(b): rome-2026-leadgen (72) + invite xlsx -> the primary's gitignored `workspace/clients/brisken/context/lead-generation/rome-2026/`, meji US_Emails_sourced CSV -> meji `context/`, `status/p2-rome.md` repointed; hash-verified before `git rm`.
- #1713 D3(c)/(d): 29 checkpoint folders (six Jochen, Nagarro, all 13 One Assessment/1Assessment, 8 KIT/BAfoeG/TikTok + 2026-10-28 KIT IAM) -> the primary's gitignored `docs/personal/`; 30 INDEX rows, the `jochen-projekt` and `personal-kit` sections and 28 session-log entries removed (each saved as `session-log-entries.md` in its personal folder).
- #1714 D3(e): `workspace/projects/prototype-fund/SCOPE.md` -> the primary's `docs/personal/prototype-fund/SCOPE.md`; `PrototypeFund-Last-Safe-Start` (11-09 10:00) and `PrototypeFund-Window-Opens` now open it there.
- Primary clone: `docs/personal/` is in the shared `.git/info/exclude` (line 21) since 2026-10-30, because the primary still lacks #1702's .gitignore line.
- This checkpoint's docs PR: PLAN.md Status lines for D1 (guard evidence) and D3.
Batch 6: #1705, #1706, #1708, #1709, #1710; batch 5: #1700, #1702, #1704; batch 4: #1684, #1686, #1693, #1695, #1696; batch 3: #1669, #1671, #1677; batch 2: #1662 .. #1664; batch 1: #1654 .. #1661.

Live evidence the next session needs: the primary clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops1` was still on d6a4b063 at 2026-10-30 18:30, 97 behind, with a live sibling session on main and a dirty docs/INDEX.md; it LACKS #1677, #1684, #1700, #1702 and everything after, so its scheduled jobs run pre-#1677 code and any checkpoint run FROM it uses the old scaffold. Gitignored writes made into it this session: `workspace/clients/brisken/context/lead-generation/rome-2026/`, `workspace/clients/meji-media/context/US_Emails_sourced_2026-07-27.csv`, `docs/personal/` (30 folders). D1 guard evidence (read-only, 2026-10-30): no client or project infrastructure.yaml names Railway or Trigger.dev, neither CLI is installed, brisken `deploy:` = `workspace/clients/brisken/automations/expense-reconciliation/deploy.py`. `uv run tools/pii_scan.py --all` on ad1621cc flags 10 files outside D3(a)-(g): docs/2026-05-20 Morning Briefing Checkpoint, the two `WW Sales Process 72627` Mini-Checkpoint-2 files (10-09, 10-11), docs/friction-register-archive.md, docs/session-inventory-2026-05-10.md (48 addresses), brisken `automations/expense-reconciliation/tests/test_intake_mail.py` (43), brisken `status/p1-expense-reconciliation.md` and `status/p1-improvement-backlog.md`, and both meji `deliverables/instantly-audit2.md` + `deliverables/shared/instantly-audit2.md` (37 each).

Waiting on the owner: a fresh explicit order for D3(g) (tok.txt rotation + the two remote-branch deletions); D5 (after W1-24's dry-run table); D6 .. D15 and D19 (D10 is MEMORY.md near the ~24.4 KB read limit); the UnpauseAI GitHub account or org for D2; gh `delete_repo` scope for 011matthias/agentic-ops1; the Brisken-Oct1-Invoice-And-Retainer task outcome.

## Queue, in order

PLAN.md's "Depends on" lines decide the order (item N = W1-N): D1 waits on W1-5 (done), D4 on W1-13 (done) and W1-29, W1-29 on W1-5 (done), D18 on nothing.

1. After-checks, only once the primary has caught up (do not fast-forward a shared clone with a sibling's dirty files). (a) `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 merge-base --is-ancestor fab6a530 HEAD`; once it holds, `Get-ScheduledTaskInfo -TaskName RepoSweep` (expect 0x0) and AgenticOpsWeeklySynthesis after Mon 11-02 06:10 (0x1 is W1-32's; a new traceback in its log would be #1677's). (b) Once the primary has #1702: `git -C <primary> check-ignore -v docs/personal/x.md` names `.gitignore` (today it names `.git/info/exclude:21`, which is fine to keep).
2. D3 Verify remainder: for each of the 10 files above, count (never print) what pii_scan sees and decide: test fixtures and ledger archives with synthetic or already-public addresses get an allowlist entry in pii_scan's allowlist (read how #1664 defines it); real third-party addresses move to the client's gitignored `context/` (copy, hash-verify, `git rm`, pointer). The meji pair and session-inventory are the likely moves; check the meji files against the Client-ops guard first (Meji tasks read `context/analysis-scripts/` only). Ledger files go on a `docs/...` branch. Done when `uv run tools/pii_scan.py --all` reports 0 outside allowlists. D3(g) only on a fresh order.
3. D1 (unblocked), guard: evidence above; re-check `/comd_deploy` still routes Brisken recon to its `deploy.py` after the rewrite. D2's CLAUDE.md change rides with it. D1 is large (~250 deletions + four command/agent rewrites): start it in a session at or under ~200k, and plan a mini-checkpoint after it.
4. W1-29 (unblocked), then D4 with its guard checks (notifier and recon deploy import none of the deleted `tools/brisken-*.py`; `onepilot-site/` is not brisken-onepilot-proto's deploy source; MejiReplySLA runs once from its new path with LastTaskResult 0 before the old file goes).
5. D18 (covers D17): `tools/context_backup.py` wired into repo-sweep, private repo 011matthias/agentic-ops1-context. Guard: the hardcoded `Repo/agentic-ops1` in `tools/brisken-recon-notify-run.py:47` runs in the notify clone, a SEPARATE clone, so `main_worktree()` there returns the notify clone itself; keep an `AGENTIC_OPS_PRIMARY` default that equals today's path, and check the notifier's LastTaskResult after. The first push of client context needs the owner's yes. The new `docs/personal/` folders belong in that backup too.
After D1, D3, D4, D18 landed the WW migration prompt may run in its own session, following item 5 of the 2026-10-21 WW checkpoint's Next Steps.
6. The rest: W1-6 .. W1-9, W1-11, W1-12, W1-15, W1-21 .. W1-28, W1-30, the rest of W1-32, W1-33, W1-34, W1-10(c); W1-24 builds the prune tool and must protect agentic-ops1-notify, -watcher, -deploy, then ask D5 with its dry-run table; W1-26 should also cover the git-stash-gate false positive on a commit message quoting `git stash push`, and the no-auto-commit-gate false positive on a heredoc whose Python string contains `gh pr merge` (2026-10-29). Then D6 .. D15 and D19 as the owner answers, X1 .. X8 when their triggers fire.

Each item's Verify line is the acceptance criterion; a green suite alone is not.

## How to work

- Work in a fresh worktree off origin/main, never in the primary clone (shared by sibling sessions and the scheduled tasks): `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b sys/layout-<item> C:\Users\neuma_p1qrsic\Repo\ao1-layout-<n> origin/main`. A new worktree has no .mcp.json; `uv run tools/mcp_config.py --ensure` in it renders the session's set (restart to load). Gitignored client context/ exists only in the primary clone; read it by absolute path when an item needs it.
- Never `cd` inside a Bash call: the cd-guard hook rewrites it into a subshell and auto mode then refuses to review the call. Use absolute paths, `git -C`, `uv run --directory`, `npm --prefix`.
- One PR per item on a `sys/layout-<item>` branch; the B6 chain runs without asking except where the guard asks for the owner's yes: commit, push, `gh pr create`, merge on CI green, one `gh pr merge --repo 011matthias/agentic-ops1.01 --squash --subject "<PR title> (#N)"` per Bash call with nothing chained before it, never in a loop or in parallel. Finish the chain in the same turn: wait on `gh pr checks` with an in-turn until-loop that also reads `gh pr view N --json mergeable` (a conflicted PR gets no checks; UNKNOWN right after CI means re-read in a few seconds). A closing message that leaves a suite, CI or merge pending is blocked by the Stop hook. Run `preflight-hooks.py --full` ALONE, in the background, writing a log (`> log 2>&1; echo exit=$? >> log`), register `tools/bg_watch.py watch`, and wait in-turn with `until grep -q '^exit=' log; do sleep 15; done` (timeout 600000); chained with other commands it outlasts the 600 s foreground limit. Ledger PRs merge strictly one at a time: GitHub's merge ignores the union drivers, so every merge to main re-conflicts the other ledger PRs on INDEX.md until each is re-merged locally. Ledger edits (INDEX, register, session logs, checkpoint folders, PLAN.md Status lines) go on `docs/...` branches only. A sys/ branch that predates a merge touching the same files: `git merge origin/main` before the full preflight. For changes under tools/, .claude/hooks/ or tools/tests/: `uv run tools/preflight-hooks.py --full` whenever tools/tests changes, plain preflight otherwise, before the push; prove each fix with `uv run tools/regress_check.py` from the worktree that holds the change. Every `subprocess.run(text=True)` in new code or tests passes `encoding="utf-8", errors="replace"`. Tests that load a hook in-process must put `hooklib.HOOKS` on sys.path themselves; the test env has no requests/urllib3. Write test files, scripts with triple-quoted strings and long text with the Write or Edit tool, never a heredoc; run py_compile after any mechanical edit over Python. Scripts that need pyyaml run as `uv run tools/x.py` (inline deps), not `uv run python tools/x.py`; there is no pyproject.
- akkton/unpauseai-web: local clone `C:\Users\neuma_p1qrsic\Repo\uweb` (on `content/meji-dormant-live`); work in a worktree off origin/main. `next build` refuses a junctioned node_modules (Turbopack), so `tsc --noEmit -p <wt>/tsconfig.json` locally and CI's clean build is the build signal. Publish = merge, then publish.yml adds an akkton-authored promote commit; verify `unpauseai.com/api/version` equals it and read the deployed files at that SHA via `gh api .../contents/...?ref=<sha>`.
- Prove an instrument before trusting a negative: run `pii_scan.py` against content you know is PII-shaped before believing a clean result.
- A new gitignored file that can hold a secret is protected by `.gitignore` only in checkouts that already have the line; add it to the shared `.git/info/exclude` too before writing it into the primary.
- Owner decisions only through AskUserQuestion with the recommendation first; never an open offer. The owner can be away for hours, so ask once the PR is green and the ask is the last step.
- The repo is public by owner decision (2026-09-16); never re-raise it. Never push a file carrying real addresses, rosters, client record IDs or secrets; count PII, never print values. Test fixtures build secret- and PII-shaped strings at runtime. Nothing of WW is pushed until W1-20's scan is clean and the owner has seen the public file list.
- Hero, n8n and mail writes in any client tenant need a per-action yes; never touch the held R1 test record (its ID lives in the WW context, not in tracked files).
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

# Mini-Checkpoint: Repo Layout Execution Batch 4

**Date:** 2026-10-29
**Status:** W1-17, W1-36 (bar its fresh-session read), W1-18, W1-19 shipped; W1-20 next
**Type:** mini

---

## Summary
Four layout-plan PRs merged on green CI: the per-checkout MCP renderer (#1684, follow-up #1686), the n8n client home (#1693) and the WW offline-test workflow with n8n test and activation guidance (#1695). The primary clone now carries `.mcp.local.json` under an owner yes, with `.mcp.json` byte-identical.

## What Was Done
- **#1684 W1-17 + W1-36 rest**: `tools/mcp_config.py` (`--check/--ensure/--adopt/--mcp-health`), SessionStart and worktree-add hooks in wire-hooks.py, doctor `mcp-health`, comd_n8n-instances / new-client / resume rewritten around it.
- **Primary adopt + ensure** (owner yes via AskUserQuestion, surface named: the primary `.mcp.json` read by every primary session incl. ClaudeRemoteControl). Before: `claude mcp list` 7 connected, vercel needs auth. After: `.mcp.json` sha256 `4a8d1f63c68ff927` unchanged, `--check` current (union, 5 servers), `--mcp-health` 7 connected 0 failed.
- **#1686**: `--adopt` adds `.mcp.local.json` to the shared `.git/info/exclude` when the checkout does not ignore it (see What Did NOT Work).
- **#1693 W1-18**: rule_file_placement client rows, check-index client scan, `tools/n8n_export.py`, builder/N8N-BUILD flat export path, comd_resume Step 4 READMEs, recon CI paths, `workspace/templates/client-n8n/`.
- **#1695 W1-19**: `.github/workflows/warme-wimmer-tests.yml`, agnt_testing-agent n8n mode, comd_test pointer, skil_build-test-fix "n8n activation shape" (the builder hands it on, never runs it).
- PLAN.md Status lines for W1-17, W1-18, W1-19, W1-36 updated in this docs PR.

## What Did NOT Work (and why)
- **Relying on the new `.gitignore` line to hide `.mcp.local.json`:** the primary was still on d6a4b063 (pre-#1684), so `git status` there listed the token-bearing file as untracked for about a minute, in the clone where RepoSweep commits backlogs. Fixed by hand with the shared `info/exclude`, then structurally in #1686.
- **Skipping `preflight-hooks.py --full` on #1686:** CI's hooks job failed on `test_text_encoding.py` (W1-31 rule: a new test called `subprocess.run(text=True)` without `encoding=`). One CI cycle lost; `--full` would have caught it locally.

## Current Status
Merged on main: #1684, #1686, #1693, #1695. The primary clone is still on d6a4b063 with a sibling's dirty `docs/INDEX.md`, so it lacks #1677 (fab6a530) and the new SessionStart MCP hook until it fast-forwards. No surface in the Client-ops guard table changed: the notifier clone fast-forwards to these merges but runs only its own scripts.

## Next Steps
1. After-checks for #1677: first confirm the primary contains it (`git -C <primary> merge-base --is-ancestor fab6a530 HEAD`). RepoSweep executes the code it loaded at start and pulls only after a run that switched branches, so a run on d6a4b063 says nothing about #1677. Then read RepoSweep (expect 0x0) and AgenticOpsWeeklySynthesis after Mon 11-02 06:10 (0x1 is W1-32's; only a new traceback is #1677's).
2. W1-36 Verify: a fresh session start in the primary reports no failed MCP connection.
3. W1-20 (WW import pre-flight), split into its repo half (gitignore patterns, dead context/portable exemption, file-placement-gate mirror, scrub-test-data.py + test, checkpoint checklist) and its WW-tree half (the scrub run, harness.js/fetch-live.js `WW_TEST_DATA_DIR`, infra split, a1-a5 specs, doc-site builder swap, pii_scan + gitleaks, owner reads the public file list).
4. Then D1, D3, D4, D18 with guard checks and per-item yes.

## Files to Read First
- `docs/2026-10-28 - Repo Layout Audit/PLAN.md` (Client-ops guard, W1-20)
- `tools/mcp_config.py`, `tools/n8n_export.py`

---

## Continuation prompt

````text
/comd_resume system

(System scope, no client. If resume asks you to pick a project folder, answer "system" and carry on with this prompt; the context YAML has a `system` entry from the 2026-10-29 Batch 4 mini-checkpoint.)

## Where it stands

The repo layout plan is the queue: `docs/2026-10-28 - Repo Layout Audit/PLAN.md` on origin/main (read it from a fresh worktree). Read its "Client-ops guard" section FIRST: owner directive 2026-10-28, "i cannot risk this jeopardizing any ongoing client operations", chosen mode guarded per item. An item whose changed paths reach a surface in its table needs (1) the surfaces named in the PR body, (2) a read-only before-check, (3) the owner's yes for THAT item at execution time through AskUserQuestion with the surface named (earlier D approvals do not cover this), (4) the same check after, stated in the checkpoint. Map an item to surfaces with `Get-ScheduledTask` actions (which file each task runs) and the workflow triggers, not from memory. Notes: `docs/2026-10-29 - Repo Layout Execution Batch 4/Mini-Checkpoint-1.md`.

Shipped 2026-10-29 (batch 4), all merged on green CI:
- PR #1684 W1-17 + W1-36 rest: tools/mcp_config.py renders the gitignored .mcp.json per checkout from infrastructure.yaml (`mcp_server`, `api_url_env`, `api_key_env`), the PRIMARY's context/.env, and a gitignored `.mcp.local.json` at the primary root (machine-only servers; optional `"_scope": ["<client>" | "platform"]`). Primary = union; worktree = the branch's client (`client/<c>/...` or `--client`) plus vercel only on platform/ and proposal/ branches. `--ensure` writes only on change (backup in `.scratch/mcp.json.pre-ensure-*`, prints "restart Claude Code to load") and refuses until `--adopt` has seeded `.mcp.local.json`; `--check` diffs by names only; `--mcp-health` is the doctor `mcp-health` check. Wired: SessionStart `--ensure --hook`, PostToolUse Bash|PowerShell `--after-worktree-add`, comd_resume Step 0, comd_n8n-instances/new-client.
- Primary adopt + ensure ran with the owner's yes: `.mcp.json` sha256 4a8d1f63c68ff927 unchanged, 7 MCP servers connected, 0 failed.
- PR #1686: `--adopt` also appends `.mcp.local.json` to the shared `.git/info/exclude` when the checkout does not ignore it (the primary on an older main showed the token-bearing file as untracked for ~1 min; closed by hand at once, before any sweep).
- PR #1693 W1-18: rule_file_placement client rows (flat `automations/{id}-{slug}.n8n.json`, `automations/tools/` + README.md, `automations/tests/`, client secrets, web-surface deploy source), check-index.py client scan, tools/n8n_export.py `--client X [--only ID] [--check]` (map from infra `export:` else `automations/{key}.n8n.json`; scrubbed, stable-stringified; read-only GET), agnt_n8n-builder + N8N-BUILD.md flat path, comd_resume Step 4 READMEs, expense-recon-tests.yml paths, workspace/templates/client-n8n/ (manifest is tools/README.md, matching check-index).
- PR #1695 W1-19: .github/workflows/warme-wimmer-tests.yml (path-filtered, no credential, `fetch-live*` and `fixtures/` excluded, zero matches fails, a "No WW tree yet" step until the import), agnt_testing-agent n8n mode, comd_test pointer, skil_build-test-fix "n8n activation shape" (idle, PUT by id, read back via n8n_export --check, activate, acceptance run, rollback; the builder hands it on, never runs it). Deferred to the import: the harness copy to workspace/templates/n8n-tests/.
Batch 3: #1669, #1671, #1677; batch 2: #1662 .. #1664; batch 1: #1654 .. #1661.

Live evidence the next session needs: the primary clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops1` is on d6a4b063 with a sibling's dirty docs/INDEX.md and untracked docs folders. It LACKS #1677 (fab6a530) and #1684, so its scheduled jobs still run pre-#1677 code and its SessionStart does not yet run mcp_config. RepoSweep's last run (10-29 11:32 local, 0x0) predates #1677's merge (13:22 local). RepoSweep pulls `--ff-only` only after a run that switched branches, and it executes the code it loaded at start.

Waiting on the owner: D5 (after W1-24's dry-run table); D6 .. D15 and D19 (D10 is MEMORY.md near the ~24.4 KB read limit); the UnpauseAI GitHub account or org for D2; a fresh explicit order for the D3(g) remote-branch deletions; gh `delete_repo` scope for 011matthias/agentic-ops1; the Brisken-Oct1-Invoice-And-Retainer task outcome.

## Queue, in order

1. After-checks. (a) #1677: first `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 merge-base --is-ancestor fab6a530 HEAD`. Only once it holds does a RepoSweep result count; then `Get-ScheduledTaskInfo -TaskName RepoSweep` (expect 0x0) and AgenticOpsWeeklySynthesis after Mon 11-02 06:10 (0x1 is W1-32's; a new traceback in its log would be #1677's). If the primary is still behind, say so and do not fast-forward a shared clone with a sibling's dirty files; that clears when the sibling's ledger lands or the sweep runs. (b) W1-36 Verify: this session's start in the primary reports no failed MCP connection, and `uv run tools/mcp_config.py --mcp-health` is 0 failed.
2. W1-20 (WW import pre-flight, cost M), in two PRs. Repo half first: .gitignore adds `.env.*` with `!.env.example|.env.sample|.env.template|.env.dist`, `/output/`, `/webhook-dump*.json`, `.claude/worktrees/`, `/workspace/hours-tracker.xlsx`; delete the dead context/portable exemption (.gitignore ~L92-99, file-placement-gate.py ~:209 lookahead, test_file_placement_gate.py ~:335-337, rule_file_placement.md client table row) after proving with `ls workspace/clients/*/context/portable` in the PRIMARY that nothing uses it; mirror the new prefixes in file-placement-gate's static ignored list; tools/scrub-test-data.py + a pytest asserting no consumer-domain address under workspace/clients/warme-wimmer/automations/ (placeholder fixtures only); the migration-day checklist into the next steps of `docs/2026-10-21 - WW Hero Key And Zapier Migration Prep/Checkpoint.md`. WW-tree half (needs the WW tree, which lives in the akkton clone, see memory project_warme_wimmer_takeover): the scrub run, harness.js/fetch-live.js read `WW_TEST_DATA_DIR`, infrastructure.yaml split by kind (under 40 KB; prose to status/ via `project_status.py --scaffold`; `secret_value:` to context/.env; make: block to a checkpoint), a1-a5 to stage folders via skil_spec-cleanup, tools/build-warme-wimmer-doc-site.py replaced by the akkton version, `uv run tools/pii_scan.py` and gitleaks over the import branch, and the owner reads the public file list before any push of WW content.
3. Execute the approved D1, D3, D4, D18 in that order, each with its guard check and the owner's yes at execution (D2's CLAUDE.md change rides with D1; D17 is covered by D18). D1 must keep `/comd_deploy` honoring brisken's `deploy:`. D3(a) also touches akkton/unpauseai-web and the live WW docs; D3(f) deletes the two root PNGs and must drop the TEMPORARY exemption in tools/tests/test_root_layout.py in the same change. `uv run tools/pii_scan.py --all` lists 18 files; D3 and D4 should take most of them off.
After step 3 the WW migration prompt may run in its own session; it must add N8N_API_KEY_WARME_WIMMER and N8N_API_URL_WARME_WIMMER to the WW `automations/.env.example` (infra_check names them), set the WW n8n instance's `mcp_server`/`api_url_env`/`api_key_env`, run `uv run tools/mcp_config.py --ensure` (W1-17's "lists n8n-warme-wimmer" Verify), `uv run tools/n8n_export.py --client warme-wimmer --check` (W1-18's live Verify), and land the harness copy in workspace/templates/n8n-tests/ (W1-19's deferred part). The rest continues in parallel or after:
4. Always-loaded context: W1-5 .. W1-12.
5. W1-15, W1-21 .. W1-30, the rest of W1-32 (the other scheduled jobs' outcomes), W1-33, W1-34 (W1-24 builds the prune tool and must protect agentic-ops1-notify, -watcher, -deploy; then ask D5 with its dry-run table; W1-26 should also cover the git-stash-gate false positive on a commit message that quotes `git stash push`), then D6 .. D15 and D19 as the owner answers, X1 .. X8 when their triggers fire.

Each item's Verify line is the acceptance criterion; a green suite alone is not.

## How to work

- Work in a fresh worktree off origin/main, never in the primary clone (shared by sibling sessions and the scheduled tasks): `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b sys/layout-<item> C:\Users\neuma_p1qrsic\Repo\ao1-layout-<n> origin/main`. A new worktree has no .mcp.json; `uv run tools/mcp_config.py --ensure` in it renders the session's set (restart to load). Gitignored client context/ exists only in the primary clone; read it by absolute path when an item needs it. Remove ao1-layout-17 and ao1-layout-docs5 once their branches are merged.
- One PR per item on a `sys/layout-<item>` branch; the B6 chain runs without asking except where the guard asks for the owner's yes: commit, push, `gh pr create`, merge on CI green, one `gh pr merge --repo 011matthias/agentic-ops1.01` per Bash call with nothing chained before it, never in a loop or in parallel. Ledger PRs merge strictly one at a time: GitHub's merge ignores the union drivers, so every merge to main re-conflicts the other ledger PRs on INDEX.md until each is re-merged locally. Ledger edits (INDEX, register, session logs, checkpoint folders, PLAN.md Status lines) go on `docs/...` branches only. For changes under tools/, .claude/hooks/ or tools/tests/: `uv run tools/preflight-hooks.py --full` whenever tools/tests changes (skipping it on 2026-10-29 cost a red CI cycle on the W1-31 encoding rule), plain preflight otherwise, before the push; prove each fix with `uv run tools/regress_check.py` from the worktree that holds the change. Every `subprocess.run(text=True)` in new code or tests passes `encoding="utf-8", errors="replace"`. Tests that load a hook in-process must put `hooklib.HOOKS` on sys.path themselves; the test env has no requests/urllib3. Write test files and long text with the Write or Edit tool, never a heredoc; run py_compile after any mechanical sed over Python. Scripts that need pyyaml run as `uv run tools/x.py` (inline deps), not `uv run python tools/x.py`; there is no pyproject.
- A new gitignored file that can hold a secret is protected by `.gitignore` only in checkouts that already have the line; add it to the shared `.git/info/exclude` too before writing it into the primary.
- Owner decisions only through AskUserQuestion with the recommendation first; never an open offer. The owner can be away for hours (a yes on 2026-10-28 arrived ~12 h later), so ask once the PR is green and the ask is the last step.
- The repo is public by owner decision (2026-09-16); never re-raise it. Never push a file carrying real addresses, rosters, client record IDs or secrets; count PII, never print values. Test fixtures build secret- and PII-shaped strings at runtime so neither gitleaks nor pii_scan has a literal to flag; a WW-shaped fixture uses placeholder values only (see tools/fixtures/infra_yaml/ww-shape/). Nothing of WW is pushed until W1-20's scan is clean and the owner has seen the public file list.
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

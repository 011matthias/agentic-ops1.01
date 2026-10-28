# Checkpoint: Repo Layout Audit

**Date:** 2026-10-28
**Status:** Audit complete and verified; plan published in PLAN.md beside this file; execution not started

---

## Summary
Ten-lens, adversarially verified audit of whether the repo layout fits the work ahead (Brisken p1 product loop, the Waerme Wimmer n8n migration, Meji, Upwork independence), delivered as PLAN.md (37 mechanical items, 19 owner decisions, 8 deferrals, 12 verified critic gaps) plus the continuation prompt at the end of this file. Earlier in the same session: README restructure merged (PR #1647) and the owner's decision that WW moves into this repo with code public and data private.

---

## What Was Done This Session
### Audit
1. Fact base on origin/main 711961b3: sizes of the always-loaded context (20 rules 174,593 B, CLAUDE.md 6.4 KB, MEMORY.md 23.5 KB), CI job runtimes, a transcript census of command and skill use, worktree, branch and PR state.
2. Workflow run wf_6956c984-be3: 10 lenses (fit, ctx, harness, ledger, homes, ci, exposure, machine, truth, onboard) produced 123 findings; each got an evidence refuter and a value refuter; a synthesis agent merged them into waves; a completeness critic listed what no lens covered. 36 agents, 9.3M tokens, 1,209 tool calls, 16 h wall-clock. Verdicts: 24 confirmed, 99 partly (claim right, size or fix adjusted), 0 refuted, 0 unverified.
3. The 12 critic gaps checked live (PLAN.md section G): a live client app whose code is gitignored (Jochen Projekt), the 800 MB Brisken context/ existing only in the primary clone, a 20,332-line service.py, three red scheduled tasks, the status sweep dying with a UnicodeDecodeError and exiting 0, no gitleaks config, dead MCP entries, a dangling plugin enable, doctor.py never run, 843 MB of .scratch and an 18 MB hook log.
4. Independent spot-checks confirmed the highest-severity findings: the WW customer-mail export tracked under platform/public/docs/warme-wimmer since 2026-07-17 (PR #268, world-readable since the repo went public on 2026-09-16; 0 forks, 0 watchers), tok.txt on two pushed branches, n8n-nodes-hero-software unpushed (9 commits), 44 worktrees with merged PRs, the brisken p1 status pair at 1.5 MB, all 8 open PRs CONFLICTING.

### Earlier in the session
1. README restructured and merged (PR #1647, squash 711961b3).
2. WW migration decided (move here, code public, data private) and a WW continuation prompt handed over; recorded in memory project_warme_wimmer_takeover.
3. Dead repo 011matthias/agentic-ops1: owner chose delete; blocked on the gh token lacking the delete_repo scope, so the owner runs the command.

---

## Key Decisions Made
### Layout items gate the WW migration
- **Choice:** PLAN.md items W1-13, W1-14, W1-35, W1-16 .. W1-20, D1 .. D4, D16 .. D18 land before the WW migration prompt (issued 2026-10-27) runs.
- **Rationale:** A straight import publishes 79 addresses, ten live Hero snapshots and 24 screenshots into a public repo; "code public, data private" has no enforcement today, and the n8n client home (export naming, automations/tools, tests, secrets) is undefined.

### PLAN.md is the queue
- **Choice:** Each item carries a Status line updated in the docs PR of the session that lands it; no second tracker.
- **Rationale:** W1 no-file-bloat; a parallel list drifts within a week.

### Critic gaps folded into the plan, no second audit round
- **Choice:** W1-0, W1-31 .. W1-36 and D17 .. D19 were written from one-command verifications.
- **Rationale:** Every gap was confirmable in one read; the open parts are owner decisions, not more agents.

---

## What Did NOT Work (and why)
- **`git show origin/main:<path>` in Bash loops:** MSYS converted `origin/main:` into a Windows path; fixed with `export MSYS_NO_PATHCONV=1`, which memory reference_repo_tooling_gotchas already records.
- **`du` over 80 worktrees in the foreground:** exceeded the 120 s tool timeout; ran in the background instead.
- **Transcript census with `rg` on `<command-name>`:** matched nothing; the tool-call JSON needs `grep -a -o '"name":"Skill","input":{"skill":"..."'`.
- **Claim "CLAUDE.md's templates/ reference is stale":** wrong; workspace/templates exists (124 files, 6 referrers). The real finding is unused Trigger.dev/FastAPI-era boilerplate (PLAN D1).
- **150-line heredoc for the plan additions:** blocked by heredoc-size-gate (cap 80 lines); the Write tool carried it.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| docs/2026-10-28 - Repo Layout Audit/PLAN.md | created | the plan and queue (rendered from the workflow result, gap verifications and additions written in) |
| docs/2026-10-28 - Repo Layout Audit/Checkpoint.md | created | this file, continuation prompt appended |
| docs/INDEX.md, docs/friction-register.md, docs/sessions/2026-10-28.md | scaffold | ledger rows |
| memory: project_repo_layout_audit_plan.md (new), MEMORY.md, project_warme_wimmer_takeover.md | edited | pointer to the plan and the WW ordering constraint |
| README.md | PR #1647 (earlier) | restructure |

---

## Current Status
Audit complete; nothing of PLAN.md executed. Ops status: not applicable (system scope; no infrastructure.yaml). Primary clone parked on client/meji-media/status-current-10-09, 56 commits behind origin/main, two sibling sessions live in it at compaction time; the audit worktree agentic-ops1-audit (detached at 711961b3) is removed at the end of this session, the ckpt-layout worktree after this PR merges. Context at checkpoint: 247k tokens (below the 300k moderate band).

---

## Next Steps
1. Owner pastes the continuation prompt below into a new session; its queue starts with the permission probe (W1-0) and the decision batches D1 .. D4, D16 .. D18, D5.
2. Owner's own actions: `gh auth refresh -h github.com -s delete_repo; gh repo delete 011matthias/agentic-ops1 --yes`; confirm the Brisken-Oct1-Invoice-And-Retainer task outcome (refused by the scheduler on 2026-10-02, on battery); tell Nico about the WW move when ready.
3. The WW migration prompt runs only after the queue's step 6 (PLAN.md ordering line).

---

## Context for Next Session
### Files to Read First
- docs/2026-10-28 - Repo Layout Audit/PLAN.md
- this file
- memory: project_repo_layout_audit_plan.md, project_warme_wimmer_takeover.md, project_repo_public_by_decision.md

### Open Questions
- Does a hook `ask` produce a prompt under the project's bypassPermissions mode (W1-0)? If not, the floor gates have been theater since May.
- Owner answers to D1 .. D19.

### Working Notes
- Measured baselines the plan's Verify lines compare against: docs/client PR wall-clock 2:50-3:35 (12:00 outliers); hooks job 2:40 of which 2:32 is the 1,739-test suite; expense-recon job 6:49 serial over 3,604 tests; a Brisken /comd_resume about 170k tokens; rules 174,593 B (about 44k tokens, loaded about 4x per session with subagents); 80 worktrees (44 dead, 22 unmerged, 12 detached), 10 husk dirs, 436 remote / 442 local branches with 415 / 423 merged; register 295,695 B; MEMORY.md 23.5 KB / 185 lines against a 25 KB / 200-line cap.
- The 123 raw findings with evidence paths are in the workflow journal, one JSON line per agent: `C:\Users\neuma_p1qrsic\.claude\projects\c--Users-neuma-p1qrsic-Repo-agentic-ops1\72731354-fb8c-4937-b3cd-2b12e64ff826\subagents\workflows\wf_6956c984-be3\journal.jsonl`. PLAN.md carries the merged version; read the journal only when an item's evidence needs the original file:line.
- Friction candidates this session: 10, all gate firings; 7 were false positives of no-auto-commit-gate and instantly-invasive-gate on read-only commands that quoted gate source or printf'd hook payloads (folded into W1-26's scope).

### Reference Materials
- Workflow script: `C:\Users\neuma_p1qrsic\.claude\projects\c--Users-neuma-p1qrsic-Repo-agentic-ops1\72731354-fb8c-4937-b3cd-2b12e64ff826\workflows\scripts\layout-audit-wf_6956c984-be3.js`
- Workflow result: `C:\Users\NEUMA_~1\AppData\Local\Temp\claude\c--Users-neuma-p1qrsic-Repo-agentic-ops1\72731354-fb8c-4937-b3cd-2b12e64ff826\tasks\w2o9nhww6.output` (1.4 MB JSON; temp, may be gone)

---

## How to Continue
Paste the continuation prompt below into a new Claude Code session. Work in a fresh worktree off origin/main, one PR per item, PLAN.md Status lines updated in each checkpoint's docs PR.

---

## Strategic Feedback

### What Worked Well This Session
- Two refuters per finding plus a completeness critic: 0 findings refuted, 99 of 123 resized, and the critic found the twelve largest gaps (an untracked live client app, no backup of the only client record, silently failing monitors), none of which any lens's frame contained. Independent spot-checks run while the verifiers worked confirmed every sampled claim before the synthesis landed.

### Suggestions
- Wire doctor.py and the scheduled-task results into the nightly sweep (W1-32, W1-33): four of the twelve gaps were the class "a signal exists and nobody reads it".

### System Health
- Autonomy: 1 human intervention (a "continue" nudge after the model switch); otherwise fully autonomous. Gates: B1:1 B2:3 B3:3 skipped:0.
- The SessionStart status sweep has been crashing on Windows with a decode error and exiting 0, so the harness reported it as healthy; fail-open hides exactly the failures a health check exists to show.

---

## Continuation prompt (pasted into the new session)

````
/comd_resume system

(System scope, no client. If resume asks you to pick a project folder, answer "system" and carry on with this prompt; the context YAML has a `system` entry from the 2026-10-28 checkpoint.)

## Where it stands

The repo layout audit is done and verified; the plan is the queue. Read it first: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\docs\2026-10-28 - Repo Layout Audit\PLAN.md` (on origin/main; the primary clone is parked 56 commits behind on a merged branch, so read it from the fresh worktree described under How to work). `Checkpoint.md` beside it has the session notes and measured baselines.

Shape of the plan: 37 mechanical items (W1-0, W1-1 .. W1-36), 19 owner decisions (D1 .. D19), 8 deferrals (X1 .. X8), each with Action / Why / Verify / Files and a `Status:` line you update. Behind it: 123 findings from 10 lenses, two refuters each (24 confirmed, 99 partly, 0 refuted), and 12 critic gaps checked live on 2026-10-28.

Already done in the audit session: README restructured (PR #1647 merged); the owner decided the Waerme Wimmer (WW) client moves into this repo with code public and data private, and a WW migration continuation prompt was handed over on 2026-10-27. That prompt must not run before the items below that define where WW files land and the gate that keeps personal data out of the public tree.

## Queue, in order

1. W1-0: the hook-ask-under-bypassPermissions probe (ten minutes). Write the answer into your checkpoint; it decides whether the floor gates are real.
2. Owner decisions through AskUserQuestion, recommendation as the first option, consequence stated, up to four questions per call. Batch 1: D1 retire the Trigger.dev/Railway lane, D2 client-handoff convention, D3 public-data removals from HEAD (the WW mail export under platform/public/docs/warme-wimmer, lead rosters, personal checkpoint folders, the two root PNGs, the tok.txt branches plus token rotation), D4 supersession deletions. Batch 2: D16 WW import content, D17 Jochen Projekt code tracked, D18 context/ backup mechanism, D5 machine clean-up (show the dry-run table first). Write each answer into the item's Status line. Execute no D item before its yes; D3(g), D5's branch deletions and repo setting, and anything that deletes a remote are Band-3 and need the owner's explicit order in that session.
3. W1-4: re-land the 8 conflicting ledger PRs, `fetch.prune`, remove the 10 husk directories, move the primary clone to main (only when `git status --porcelain` is empty there and `uv run tools/session_registry.py --check` shows no live sibling).
4. W1-3 (ci_is_green reads mergeability), then W1-1 and W1-2 (CI split and path filters).
5. W1-13 (sweep placement gate, skip when parked), W1-14 (pii push gate), W1-35 (gitleaks config after the differential probe against commit 57415748), W1-31 (PYTHONUTF8 and subprocess encoding).
6. W1-16 (infrastructure.yaml loader), W1-17 with W1-36 (mcp_config and the MCP fleet), W1-18 (client homes: automations/*.n8n.json, automations/tools with a manifest, automations/tests, context/.env plus a tracked .env.example), W1-19 (WW tests in CI, n8n test mode), W1-20 (WW import pre-flight), D16.
7. Execute the approved D1, D3, D4, D17, D18 in that order.
After step 7 the WW migration prompt may run in its own session. The rest continues in parallel or after:
8. Always-loaded context: W1-5 (CLAUDE.md and the always-loaded truth fixes), W1-6 (rules: path scoping, trims, budget ratchet), W1-7 (resume brief), W1-8 (project_status ceilings and digest), W1-9 (memory audit), W1-10 (INDEX normalize, private checkpoints), W1-11 (register rotation), W1-12 (dead PreCompact hook).
9. W1-21 .. W1-30, W1-32 .. W1-34, then D5 .. D15 and D19 as the owner answers, X1 .. X8 when their triggers fire.

Each item's Verify line is the acceptance criterion; a green suite alone is not.

## How to work

- Work in a fresh worktree off origin/main, never in the primary clone (shared by sibling sessions, parked on a merged branch): `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b sys/layout-1 C:\Users\neuma_p1qrsic\Repo\ao1-layout-1 origin/main`. Gitignored client context/ exists only in the primary clone; read it by absolute path when an item needs it.
- One PR per item on a `sys/layout-<item>` branch; the B6 chain runs without asking: commit, push, `gh pr create`, merge on CI green. Ledger edits (INDEX, register, session logs, checkpoint folders, PLAN.md Status lines) go on `docs/...` branches only. For changes under tools/, .claude/hooks/ or tools/tests/: `uv run tools/preflight-hooks.py` (`--full` when tools/tests change) before the push, and prove each fix with `uv run tools/regress_check.py` so the suite is seen to go red when the fix is unwired.
- Owner decisions only through AskUserQuestion with the recommendation first; never an open offer.
- The repo is public by owner decision (2026-09-16); never re-raise it. Never push a file carrying real addresses, rosters or secrets; count PII, never print values. Nothing of WW is pushed until W1-20's scan is clean and the owner has seen the public file list.
- Hero, n8n and mail writes in any client tenant need a per-action yes; never touch the held R1 test on HUK-106488.
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

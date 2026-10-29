# Repo layout audit: plan

Date: 2026-10-28. Source: Workflow run wf_6956c984-be3 (10 audit lenses over origin/main at 711961b3, 123 findings, two refuters per finding, one synthesis agent, one completeness critic; 36 agents, 9.3M tokens, 1,209 tool calls). Verdicts: 24 confirmed, 99 partly confirmed (claim right, size or fix adjusted), 0 refuted, 0 unverified.

## How to use this file

- Every item carries a `Status:` line. The session that lands an item sets it to `done PR #N` (or `dropped: <reason>`) in the same docs PR as its checkpoint. This file is the queue; do not keep a second list.
- Wave 1 (W1-1 .. W1-30, plus W1-0 and W1-31 .. W1-36 from section G; the synthesis summary's '29' is a miscount, the list has 30): mechanical, no owner decision, one PR each, ordered by what every session or PR pays first. Wave 2 (D1 .. D16): owner decisions, each with a recommendation and consequence; ask with AskUserQuestion, recommendation first. Wave 3 (X1 .. X8): deferred. Section G (G1 .. G12): gaps the completeness critic raised after the lenses, each with the 2026-10-28 live verification; the additions they produced are W1-31 .. W1-36, W1-0 and D17 .. D19 at the end.
- Ordering that matters: W1-13, W1-14, W1-35, W1-16 .. W1-20, D1 .. D4, D16, D17 and D18 land BEFORE the Waerme Wimmer migration prompt (already issued on 2026-10-27) is executed, because they define where WW files land and the gate that keeps personal data out of the public tree.

## Client-ops guard (owner, 2026-10-28)

Owner, verbatim: "i cannot risk this jeopardizing any ongoing client operations." Chosen mode (AskUserQuestion, 2026-10-28): guarded per item. This outranks the queue order and every earlier approval.

An item whose changed paths reach a surface in the table runs only after (1) its PR body names the surfaces it reaches, (2) a read-only before-check of each, (3) the owner's yes for THAT item at execution time, through AskUserQuestion with the surface named (a D item's earlier approval does not cover this step), and (4) the same check after the merge or deploy, stated in the checkpoint. An item that reaches none of them runs as before.

Surfaces, read 2026-10-28 from Get-ScheduledTask, the workflow triggers on main and the jobs' own code:

| Surface | Runs from | Reads by path | How a repo change reaches it |
|---|---|---|---|
| BriskenReconNotify, every 15 min (Criss's "result ready" + dev pings) | the separate clone `Repo/agentic-ops1-notify` | its own `tools/brisken-recon-notify*.py`; the PRIMARY's `workspace/clients/brisken/context/.env` and `.scratch/recon-notify-state.json` | the clone fast-forwards to origin/main every run: a merge is live within 15 min; moving the primary's brisken `context/` or `.scratch/` breaks it at once |
| MejiReplySLA (daily 08:05), MejiWeeklyReview (Mon 05:17) | gitignored scripts in the primary's `workspace/clients/meji-media/context/analysis-scripts/` (uv `--directory`) | that folder | moving the folder or retargeting the task (D4 moves `meji_reply_sla_daily.py`) |
| RepoSweep (02:30), AgenticOpsWeeklySynthesis, ClaudeRemoteControl | tracked code in whatever branch the primary has checked out | the primary's git state | the primary's branch: an old branch brings back old sweep code |
| Fly apps: brisken-expense-recon (api.expenses.brisken.com), Lead Desk, one-assessment-demo, brisken-onepilot-proto | deployed by hand from their source dirs under `workspace/clients/` | the source dir at deploy time | a merge deploys nothing; the next deploy ships what main holds, and a deleted source dir leaves the app running but undeployable |
| Scheduled Actions: expense-recon-uptime (10 min), morning-briefing, eod-capture, weekly-review | main's workflow files | the tools they call | any merge to main |
| Client tenants: WW n8n + Hero (held R1 test on HUK-106488), Meji Make + Instantly, Brisken M365 | nothing in this plan writes to them | | only a test, activation or send, each already under its per-action yes |
| unpauseai.com gated client docs (`/docs/warme-wimmer`) | akkton/unpauseai-web | | D3(a) removes files from the live site |

Per-item checks:
- W1-14 pii-push-gate: `ask` with fail-open, never `deny`, so an urgent client fix can still push; calibrate on the current tree first.
- W1-18 client homes: rename or move nothing a row above reads by path, or migrate that reader in the same PR and check it after.
- W1-19: CI runs fixtures only, holds no tenant credential and never calls n8n or Hero; the new n8n test mode and activation shape are not exercised against WW in this item.
- W1-24: the protected roots it already names (`agentic-ops1-notify`, `-watcher`, `-deploy`) are part of its Verify.
- W1-31: no global `PYTHONUTF8=1`; it would change how every session-launched client script decodes a file opened without `encoding=` (a cp1252 bank CSV, an Excel export). Ship the per-call helper only.
- D1: enumerate Railway and Trigger.dev live before deleting the lane; `/comd_deploy` must still route Brisken recon to its `deploy.py`.
- D3(a): remove from the public tree first; remove from the live site only after confirming WW no longer uses `m-mail-abgleich.html` and the downloads.
- D4: confirm the notifier and the recon deploy import none of the deleted `tools/brisken-*.py`; confirm `onepilot-site/` is not brisken-onepilot-proto's deploy source; MejiReplySLA runs once from its new path with LastTaskResult 0 before the old file goes.
- D17, D18: copy only. No `context/` path changes, because the notifier and the Meji tasks read those paths.

## Summary (synthesis agent)

123 verified findings merged into 29 Wave-1 PRs (mechanical, ordered by what every session or PR pays first), 16 Wave-2 owner decisions (each with a recommendation and consequence), and 8 deferrals. Settled conflicts: path-scope all three platform rules (unpauseai.com is edited in its own checkout, which loads its own rules; the voice bans stay unconditional in rule_anti_slop); keep comd_test and a thin comd_deploy router, delete the Trigger/Railway agents, and put the n8n activate/verify steps in agnt_n8n-builder + skil_build-test-fix (harness-1 vs onboard-8/10); repo-sweep skips when the primary is parked instead of branching off a feature HEAD (exposure-1); pii_scan thresholds recalibrated per exposure-4's verifier. Sequencing that matters for the WW migration next session: items 16-19 (n8n client shape, export/test/CI conventions, import pre-flight) and 14 (pii push gate) land first; item 4 re-lands the stranded WW Hero checkpoint PR #1638 so /comd_resume can find it.

## Wave 1: mechanical, one PR each, ordered by leverage

No owner decision; cost S or M; each item has a named test or measurement. Items 1-4 touch every PR or every resume; 5-12 cut the fixed per-session load; 13-15 close the public-exposure gates before the WW import; 16-20 define the n8n client shape the migration needs on day one; 21-29 are harness hygiene.

### W1-1 [ci-1, ci-7, ci-12] cost S

Status: done PR #1657 (2026-10-28): platform.yml + lead-desk-tests.yml path-filtered, concurrency on all four workflows (group keyed on workflow name). Verified: docs PR #970 listed only secrets + hooks, exit 0; #1657 itself ran every split job.

Depends on: none

Action: Split ci.yml: move quality+spell+smoke to .github/workflows/platform.yml with `on.pull_request.paths: [platform/**, .github/workflows/platform.yml]` (cache ~/.cache/ms-playwright keyed on @playwright/test); move the lead-desk job to lead-desk-tests.yml path-filtered like expense-recon-tests.yml; keep `secrets` (gitleaks) and `hooks` unconditional in ci.yml so `gh pr checks` never returns 'no checks'. Add `concurrency: {group: ci-${{ github.event.pull_request.number || github.ref }}, cancel-in-progress: ${{ github.event_name == 'pull_request' }}}` to ci.yml and expense-recon-tests.yml. Keep the push:main run.

Why: Every docs/client PR waits 2:50-3:35 (12:00 outliers) on jobs that cannot fail on its diff; re-pushes run a second full matrix; main has no branch protection so a filtered-out workflow blocks nothing.

Verify: Open a docs-only PR: `gh pr checks` lists only secrets+hooks, exit 0, green under 3 min; push twice to one branch and `gh run list --branch` shows the first run cancelled; `gh run view` on a platform/ PR shows platform.yml ran.

Files: `.github/workflows/ci.yml`, `.github/workflows/platform.yml`, `.github/workflows/lead-desk-tests.yml`, `.github/workflows/expense-recon-tests.yml`

### W1-2 [ci-2] cost M

Status: done PR #1660 (2026-10-28): pytest step gated by dorny/paths-filter; ledger + root-layout tests unconditional. Filter extended with workspace/projects/vinted-reselling/** (four tests import its code) and the whole expense-recon app folder. Skip path verified on the batch-1 checkpoint docs PR.

Depends on: item 1

Action: In ci.yml make `lint` unconditional (ruff, check-index, pattern lint, `pytest tools/tests/test_validate_output_slop.py -k friction_register` with the same --with deps) and gate the pytest step of `hooks` with a dorny/paths-filter step on tools/**, .claude/**, pytest.ini, ruff.toml, .github/workflows/**, docs/optimize/**, workspace/clients/brisken/status/p1-improvement-backlog.md and the expense-recon src/tests. Job-level or step-level `if:` only, never workflow-level paths.

Why: 2:32 of the 2:40 hooks job is the 1,739-test suite whose inputs change in a minority of PRs; after item 1 it is the whole wait for a docs PR.

Verify: Docs PR: pytest step shows 'skipped', PR green in under 50 s, `gh pr checks` exit 0; a PR touching .claude/hooks runs the full suite; push:main still runs it.

Files: `.github/workflows/ci.yml`

### W1-3 [ci-4] cost S

Status: done PR #1656 (2026-10-28): merge_verdict reads mergeable + statusCheckRollup via .claude/hooks/_gh.py (repo-sweep imports classify_rollup from it); CONFLICTING asks with the remedy, not cleared by merge-anyway. regress_check bites on both wiring points.

Depends on: none

Action: ci_is_green in no-auto-commit-gate.py reads `gh pr view <sel> --json mergeable,statusCheckRollup`; CONFLICTING -> ask with reason 'CONFLICTING: merge origin/main locally (union drivers apply), push, auto-merge fires on green'; green/red/pending from the rollup via classify_rollup moved into .claude/hooks/_gh.py and imported by tools/repo-sweep.py. Keep the NO_AUTO_COMMIT_GATE_CI seam and the named-override path for zero checks.

Why: #1638 is CONFLICTING yet `gh pr checks` exits 0, so the gate allows a merge GitHub refuses; the richer state already exists in repo-sweep.

Verify: New cases in tools/tests/test_no_auto_commit_gate.py (conflicting-with-green, zero-checks) proven with `uv run tools/regress_check.py`; `uv run tools/preflight-hooks.py`.

Files: `.claude/hooks/no-auto-commit-gate.py`, `.claude/hooks/_gh.py`, `tools/repo-sweep.py`, `tools/tests/test_no_auto_commit_gate.py`

### W1-4 [machine-4, machine-9, machine-3, machine-5] cost M

Status: partly done 2026-10-28: (a) all eight PRs merged (#1638 #1226 #1198 #1178 #1161 #1073 #970 #955), serially, because GitHub's merge ignores the union drivers and each merge re-conflicts the rest on INDEX.md; (b) fetch.prune=true; (c) 10 husks removed (Repo 107 -> 97 entries). Done 2026-10-28 22:29: (d) the primary moved to main in one check-then-act (porcelain empty, session_registry "no live sibling"), 0 behind; `repo-sweep.py` dry run from it: all three repos clean.

Depends on: none

Action: (a) Re-land the 8 open PRs: in each existing worktree `git fetch origin main && git merge --no-edit origin/main` (union drivers resolve INDEX/register/sessions), take main's version of workspace/clients/brisken/status/p1-expense-reconciliation.md (#1226/#955/#1198), docs/friction-register-archive.md (#1198), .claude/patterns/warn-tail-task-output-file.md (#1161); `uv run tools/repo-sweep.py --normalize-sessions docs/sessions/<date>.md`; `uv run tools/check-index.py`; commit, push; CI auto-merges. #1198 needs a temp worktree. (b) `git -C C:/Users/neuma_p1qrsic/Repo/agentic-ops1 config fetch.prune true`. (c) rmdir the 10 empty husks (agentic-ops1-c9-3-log, -ckpt-c9-3, -ckpt-c9-3b, -ckpt-c9-5, -ckpt-vendorhist, -ckpt-ww, -d3docs, -docs-endings, -reread240, ao1-memory-pt). (d) Move the primary to main (approved 2026-09-09), check-then-act in one command: `[ -z "$(git -C $P status --porcelain)" ] && uv run --directory $P tools/session_registry.py --check | grep -q 'no live sibling' && git -C $P checkout main && git -C $P pull --ff-only`.

Why: Seven checkpoints incl. the WW Hero/Zapier migration prep are invisible to /comd_resume; the primary is 50 commits behind and the nightly sweep would commit onto its parked branch.

Verify: `gh pr list --state open` shows 0 docs PRs; 'docs/2026-10-21 - WW Hero Key And Zapier Migration Prep/Checkpoint.md' exists on origin/main and INDEX.md has its row; `git -C $P branch --show-current` = main, 0 behind; `ls C:/Users/neuma_p1qrsic/Repo | wc -l` drops by 10.

Files: `docs/INDEX.md`, `docs/friction-register.md`, `docs/sessions/*.md`

### W1-5 [truth-1, fit-9, truth-8, truth-11, ctx-10, truth-9, truth-12, harness-10, homes-10, truth-2, truth-14, truth-10, ctx-4, harness-6] cost S

Status: todo

Depends on: none

Action: One docs PR on the always-loaded files. CLAUDE.md: replace lines 28-61 with the README's comd_* five-line loop plus one sentence 'spec-driven n8n/Make builds use /comd_build-automation, /comd_test [mode], /comd_deploy'; fix line 72 (/comd_help-system) and 117; replace the Structure block with README's Layout block (adds hooks/, patterns/, status/, deliverables/, projects/, workflows/, drops platform/src/app/proposals, scripts/ pending item 2-D4); Primitives rows for Hooks (33 files, 29 wired) and Patterns (36 rules + README) with anneal-metrics compute_drift extended to count them; reword line 71 to 'credentials and bulk client data live in context/; a rule or tool may name the stable identifiers it enforces'; Git Workflow: one author, branch families client/ docs/ sys/ local-web/ uwi/ leadgen/, 'one worktree per concurrent session', drop the Vercel-preview sentence; move the Platform section to workspace/projects/platform/context/README.md with a one-line pointer; drop the Proposals/Delivery groups and the Git Subtree block (truth-4 decision text replaces it); Python section: 'uv everywhere; each service under clients/<c>/automations/<service>/ is its own uv project'. rule_behaviors.md: delete the ship-gate vercel-force-deploy sentence and the Platform-merge-is-not-live sub-clause; move the AI-model line into workspace/templates/client-automation/app/config.py docstring; retire the [MERGE-NOT-LIVE] arm of post-action-gate.py and its 9 tests; comd_new-proposal.md:380 points at the akkton/unpauseai-web publish path. rule_session-start.md:5/17, rule_session-pressure.md:40/59, DECISION-TREE.md, COMMS-LOG.md: comd_ names; replace '128 files / 659 KB' in rule_session-start:13 and comd_resume:168 with 'run `uv run tools/memory_audit.py`'; delete the brand.md references in rule_deliverables.md:20, rule_session-start.md:15, comd_resume.md:178-193 (point at rule_platform_standards §1). comd_help-system.md: replace the hand table with a `!` preprocessor roster over .claude/commands/comd_*.md (stem, argument-hint, description) and fix the three rule file names. README: add 'Lead Desk tests, plus path-filtered suites', 'most with their own README', workflows/ in the .claude tree. comd_morning-briefing.md: neumath4@icloud.com -> BRIEFING_TO, drop the two-proposals directive, first step `gh workflow view` stop-if-disabled. CI test tools/tests/test_doc_command_refs.py: fail on a fixed deny-list of legacy short names (resume, checkpoint, build-automation, test-dev, test-production, status-check, deploy, draft, new-client, help-system, system-dev, review, publish, client-handoff, export-client-docs, new-proposal, proposal-status, publish-proposal) appearing as backticked `/name` tokens in CLAUDE.md, README.md, .claude/rules, .claude/commands, .claude/agents, skil_* SKILL.md, and on any `/comd_x` without a comd_x.md.

Why: CLAUDE.md is loaded into every session and subagent and names 19 commands that do not exist, a deploy path the same file forbids, a second developer and a brand file that never existed; continuation prompts are authored from it.

Verify: test_doc_command_refs.py green; `uv run tools/anneal-metrics.py` reports 0 drift for all six counts; test_post_action_gate.py green after removing the arm; a fresh session shows CLAUDE.md under 4.5 KB (was 6,548 B).

Files: `CLAUDE.md`, `README.md`, `.claude/rules/rule_behaviors.md`, `.claude/rules/rule_session-start.md`, `.claude/rules/rule_session-pressure.md`, `.claude/rules/rule_deliverables.md`, `.claude/commands/comd_help-system.md`, `.claude/commands/comd_resume.md`, `.claude/commands/comd_new-proposal.md`, `.claude/commands/comd_morning-briefing.md`, `.claude/hooks/post-action-gate.py`, `tools/anneal-metrics.py`, `tools/tests/test_doc_command_refs.py`, `tools/tests/test_post_action_gate.py`, `.claude/skills/skil_meta-builder/modules/DECISION-TREE.md`, `.claude/skills/skil_client-comms/modules/COMMS-LOG.md`

### W1-6 [ctx-1, ctx-2, ctx-3, ctx-9] cost M

Status: todo

Depends on: item 5

Action: Rules PR. (a) `paths:` frontmatter, no renames: rule_platform_standards, rule_client_page_structure, rule_gated_access -> `platform/**`; rule_optimize_loop -> `docs/optimize/**, tools/scorers/**, tools/optimize_run.py, tools/pin_scorer.py, .claude/commands/comd_optimize.md`; rule_instantly_invasive -> `workspace/clients/meji-media/**` (instantly-invasive-gate.py stays unconditional); rule_brisken_graph_first -> `workspace/clients/brisken/**, tools/brisken-*, tools/recon*, tools/send_email.py`; keep rule_brisken_graph_send_by_id unconditional (the send-by-id discipline has no hook). Add one line to rule_anti_slop: 'unpauseai.com and platform/ copy: rule_platform_standards loads on platform/** reads; read it first for the sibling akkton/unpauseai-web checkout'. CLAUDE.md:79 'Always-on' -> 'loaded at launch or on matching paths'. (b) In every hook-backed rule replace incident narrative with one line 'Source: register YYYY-MM-DD; history in .claude/hooks/<hook>.py WHY THIS EXISTS'; hookless rules move their Why into docs/references/rule-provenance.md; instrument-validity's three shapes become three short bullets; Enforcement sections become one line 'Enforced by: <hook>.py (<event>); tests: tools/tests/<file>.py' with a test that every named hook is in wire-hooks.py CANONICAL_HOOKS and every named test file exists; state the em-dash ban once (rule_anti_slop) and B4 once (rule_behaviors); keep the anchor strings test_voice_ban_consistency.py and test_validate_output_slop.py parse. (c) tools/tests/test_rules_budget.py as a ratchet: pinned per-file bytes and unconditional total in tools/rules-budget.json, fail only on growth past the pin; delete the stale 'budget: 250' lines in skil_system-digest.

Why: 53 KB (~13.3k tokens) of client/surface rules and ~55 KB of narrative+enforcement restatement load into every session and every custom subagent (~4 loads per session); nothing stops regrowth.

Verify: `claude --debug` on a Meji session shows the five scoped rules absent from launch and rule_platform_standards loading on a platform/ Read; `uv run tools/session_state.py --status` at session start drops by >= 15k tokens for a non-Brisken session; test_rules_budget, test_voice_ban_consistency, test_validate_output_slop green; `uv run tools/anneal-metrics.py` shows 0 rule files over 250 lines.

Files: `.claude/rules/*.md`, `docs/references/rule-provenance.md`, `tools/tests/test_rules_budget.py`, `tools/rules-budget.json`, `.claude/skills/skil_system-digest/SKILL.md`, `.claude/skills/skil_system-digest/modules/OVERVIEW-TEMPLATE.md`, `CLAUDE.md`

### W1-7 [fit-3, ctx-8, ledger-6, fit-6, truth-16, ctx-12, harness-10] cost M

Status: todo

Depends on: item 8, item 16

Action: Add `checkpoint_scaffold.py resume --client X` printing a bounded brief (cap 24 KB): the WHAT NOT TO RETRY block; the client's newest docs/INDEX.md row (sections merged case-insensitively) and its Checkpoint.md path; the client's context-YAML entry via main_worktree(); per status file frontmatter, byte size and only Elements rows whose State is not done/live/paused (via project_status.py --digest, item 8); the repo_freshness line; infrastructure.yaml instances through tools/infra_yaml.py (item 16); `automations/*/fly.toml` app names; the pack path. Rewrite comd_resume.md: run it through the `!` preprocessor at the top and read only what it names; Step 1 reads the INDEX section, not `ls -d docs/*/`; Step 2 skips specs/README.md when status/ exists; Step 3 'read context/README.md and the files the digest names'; delete the duplicated memory paragraph; renumber so memory load sits outside the Step-0 skip; scope codes bris, meji, ww, uwi, plat, vint, loc, sys; drop trigger-dev rows, add `fastapi -> the app's automations/<app>/BLUEPRINT.md` to 5.7. finalize renders a `## Next-session prompt` section (next_steps, open_questions, not_worked, open Elements rows, links to the rules holding standing constraints; version from the deploy record, never a GET) appended to the Checkpoint.md and printed as pasteable text; `not-worked` falls back to the newest INDEX-linked checkpoint when no YAML exists. comd_checkpoint.md:51 rule-miner spawn -> `subagent_type: Explore` with its one rule restated.

Why: The resume command cannot be followed literally (1.6 MB status/, 296 KB register, 'Cost ~1-2K tokens' for 90 KB logs) and its folder fallback lists zero checkpoints; a measured Brisken start is ~170k tokens; the loop prompt that actually starts p1 sessions is hand-maintained and contradicts a safety rule.

Verify: `uv run tools/checkpoint_scaffold.py resume --client brisken` in a fresh worktree (no context YAML) prints under 24 KB and names the 2026-10-21 Recon checkpoint; new tests in tools/tests/test_checkpoint_scaffold.py (resume brief, not-worked fallback, next-prompt section); `session_state.py --status` after /comd_resume brisken under 70k tokens.

Files: `tools/checkpoint_scaffold.py`, `.claude/commands/comd_resume.md`, `.claude/commands/comd_checkpoint.md`, `tools/tests/test_checkpoint_scaffold.py`, `workspace/clients/brisken/status/p1-recon-loop-prompt.md`

### W1-8 [fit-1, ctx-6, fit-8, fit-2, truth-16] cost S

Status: todo

Depends on: none

Action: tools/project_status.py: roll-up ceiling 32 KB / 400 lines ('roll-up exceeded') applied only to files without `kind:` or kind: status; `--digest {client}` printing frontmatter + Elements + Open-decisions tables; add not-started to NON_DECAYING_STATES and the rule/template enum; a 90-day window for state: live; one summary line per client in the sweep; per-client consistency block: spec `stage` disagreeing with an active/live status, infrastructure.yaml newest date older than the newest status `updated:`. tools/spec-staleness.py: 'spec behind status' row (spec `updated:` trailing its status file's by > 60 d) plus tools/tests/test_spec_staleness.py. Content: u1-cold-email-infra.md -> dormant.

Why: The once-per-day sweep flags 14 of 27 files and sessions scroll past it; the two p1 files (283 KB, 1.24 MB) have no size guard; brisken's spec/status drift is invisible to every tool.

Verify: tests in tools/tests/test_project_status.py (ceiling, kind exemption, not-started, live window, consistency) and test_spec_staleness.py; `--sweep-stale` output for upwork-independence drops from 8 flagged files to 5.

Files: `tools/project_status.py`, `tools/spec-staleness.py`, `tools/tests/test_project_status.py`, `tools/tests/test_spec_staleness.py`, `.claude/rules/rule_project_status.md`, `.claude/skills/skil_project-status/SKILL.md`, `workspace/projects/upwork-independence/status/u1-cold-email-infra.md`

### W1-9 [ctx-5, ctx-7] cost S

Status: todo

Depends on: none

Action: tools/memory_audit.py: per-line ceiling 155 chars, headroom warning at 20 KB / 170 lines, 'closed-marker' bucket (CLOSED/COMPLETE/DISABLED/paused/DORMANT/RETIRED), 'file > 10 KB' bucket, 'ledger in memory' bucket (project_* whose slug matches a tracked status/ workstream); wire into the wire-hooks.py SessionStart list with --once-per-day.

Why: MEMORY.md sits at 23.6 KB / 185 lines against the 25 KB / 200-line load cap; four project files of 33-92 KB duplicate status/ and checkpoints and cost a Brisken session ~117k tokens under the 'read the FULL file' rule.

Verify: tools/tests/test_memory_audit.py cases for each bucket; the SessionStart advisory prints once per day; `uv run tools/memory_audit.py` lists the 18 over-long lines and the 4 ledger files.

Files: `tools/memory_audit.py`, `tools/tests/test_memory_audit.py`, `tools/wire-hooks.py`

### W1-10 [ledger-1, ledger-7, exposure-7] cost S

Status: todo

Depends on: item 4

Action: (a) insert_index_row normalizes `section` (lower-case, validated against workspace/clients/*, workspace/projects/*, {system, platform, personal}; refuse the literal 'system/platform'); one-time merge of `## Brisken` into `## brisken` and `## system/platform` into `## system`; list the 59 dead rows in the PR body. (b) `private: true` in the checkpoint payload (comd_checkpoint sets it for section personal / scope `me`): finalize writes the Checkpoint.md under gitignored docs/personal/{date} - {topic}/, skips the INDEX row, session-log entry and register rows, merges the context YAML as today; add docs/personal/ to .gitignore and to file-placement-gate's static ignored-prefix list; comd_resume scope `me` reads docs/personal. (c) `index --rebuild|--check` generator (order-insensitive check) is a follow-up PR after item 4.

Why: Free-text sections produced duplicate client headings and a placeholder heading; every personal session (KIT, BAfoeG, TikTok) is committed to the public ledger because the scaffold has no private path.

Verify: tests in test_checkpoint_scaffold.py (section normalize, placeholder refused, private routing writes no tracked file); `grep -c '^## ' docs/INDEX.md` shows no case-duplicate headings; a `private: true` finalize leaves `git status --porcelain` empty.

Files: `tools/checkpoint_scaffold.py`, `.claude/commands/comd_checkpoint.md`, `.claude/commands/comd_resume.md`, `docs/INDEX.md`, `.gitignore`, `.claude/hooks/file-placement-gate.py`, `tools/tests/test_checkpoint_scaffold.py`

### W1-11 [ledger-3, ledger-4, ledger-10] cost M

Status: todo

Depends on: none

Action: Register: 7-column header; `archive-register --days 90 --all-rows` (age-only) replacing the 200 KB ladder and its advisory; `reconcile` (flip rows whose Fix cell names a backticked hook/tool that exists on main) then `expire` writing `Yes (aged out, no recurrence by <date>)`; friction-watch.py, anneal-metrics.py build_metrics, weekly_synthesis.py read_register and cmd_pre's regression grep read `docs/friction-register*.md`; friction-watch stale list newest-first with `--since 30d` and per-type counts for older rows; weekly_synthesis persists last week's backlog figure and prints the delta. comd_system-dev Phase 0/1 and comd_review Step 1 consume `friction-watch --format json`, `anneal-metrics --format json`, skill_stocktake and memory_audit with the comd_checkpoint line-8 ban on full reads; comd_review stays as a thin wrapper (its docs/reviews cadence message in friction-watch.py:213 unchanged).

Why: 443 of 456 rows are unresolved so the file can never shrink, the regression convention is unobservable, the daily advisory has shown the same five March rows for months, and the two loop-closing commands cannot run as written (0 runs, 49-day cadence breach).

Verify: test_checkpoint_scaffold.py archive/expire/reconcile cases; test_friction_watch.py render/stale cases; test_anneal_metrics.py reads two files; `archive-register --dry-run` now reports rows to move; `friction-watch` text shows October rows first.

Files: `tools/checkpoint_scaffold.py`, `tools/friction-watch.py`, `tools/anneal-metrics.py`, `tools/weekly_synthesis.py`, `docs/friction-register.md`, `.claude/commands/comd_system-dev.md`, `.claude/commands/comd_review.md`, `.claude/commands/comd_checkpoint.md`, `tools/tests/test_checkpoint_scaffold.py`, `tools/tests/test_friction_watch.py`, `tools/tests/test_anneal_metrics.py`

### W1-12 [ledger-11] cost S

Status: todo

Depends on: none

Action: Delete the PreCompact entry from .claude/settings.json (keep the SessionStart `compact` restore entry); rewrite rule_session-pressure 'Compaction Awareness' so it no longer promises an emergency hook; add a settings.json shape assertion (hook keys limited to SessionStart) to tools/tests/test_hooks_registry.py.

Why: The matcher `auto` never fired in eight months (all 23 compactions manual) and its prompt writes an unnumbered file and hand-edits ledgers the scaffold owns.

Verify: test_hooks_registry.py shape case; `uv run tools/wire-hooks.py --ensure` reports no drift.

Files: `.claude/settings.json`, `.claude/rules/rule_session-pressure.md`, `tools/tests/test_hooks_registry.py`

### W1-13 [homes-11, exposure-2, exposure-1, exposure-11, machine-5, machine-8] cost M

Status: done PR #1659 (2026-10-28): parked-primary skip (live dry run printed it), untracked files vetted through the real placement gate, token/snapshot shapes skipped, leftovers in the PR body, test_root_layout.py. (c) _placement.py not factored (no second consumer; tests use load_hook); CREDENTIAL_PATTERNS kept (stricter, covers the push-policy repos). regress_check bites on three wiring points.

Depends on: none

Action: tools/repo-sweep.py: (a) for policy pr, if original_branch not in (main, master) log 'skip: primary parked on <branch>' and return; (b) plan() runs every `??` file through .claude/hooks/file-placement-gate.py as a synthetic Write payload (classifier injected for tests), skipping deny/ask with a reason, plus a content-shape deny for single-line high-entropy files and basename patterns `tok*`, `*.tok`, `*.token`, `*.live.json`, `*snapshot*`; drop CREDENTIAL_PATTERNS in favour of the gate's NEVERCOMMIT_RE; pass the skipped list as `gh pr create --body`; (c) factor the gate's constants into .claude/hooks/_placement.py re-exported by the hook; (d) tools/tests/test_root_layout.py asserting `git ls-tree HEAD` root names are in ROOT_ALLOWLIST, seeded with a temporary allowlist for `--full-page`/`--fullpage` until Wave-2 D3 deletes them; retarget test_plan_excludes_credentials_and_oversize to docs/notes.md.

Why: The one unattended committer bypasses every placement rule: two client screenshots, a personal sketch and tok.txt reached public refs this way, and a parked primary would receive the next sweep commit.

Verify: tests in tools/tests/test_repo_sweep.py (root PNG, *-export.csv, unknown top dir, tok.txt shape, parked branch) proven with regress_check; `uv run tools/repo-sweep.py` dry-run from a parked worktree prints the skip line.

Files: `tools/repo-sweep.py`, `.claude/hooks/file-placement-gate.py`, `.claude/hooks/_placement.py`, `tools/tests/test_repo_sweep.py`, `tools/tests/test_root_layout.py`

### W1-14 [exposure-4, exposure-6, exposure-8] cost M

Status: done PR #1664 (2026-10-29, owner yes under the client-ops guard). Range mode scans only ADDED lines (old ledgers and removals stay silent); the token check fires on whole new files only (a one-line recon regex edit had tripped it). CI step warns, never fails. Calibration `--all`: 18 files, not the predicted 5: the predicted ones plus the 10-09 WW and 05-20 Morning Briefing checkpoints, the Rome roster + build-master-v2.py, the WW m-mail-abgleich page, two meji Instantly audits (named mailboxes), and personal addresses (likely the owner's) in two brisken status files and test_intake_mail.py. Replay of 200 merges: asks on 2, both WW checkpoints. confidential-names.txt does not exist for any client yet, so that detector is inert until seeded. After-check: primary fast-forwarded to d6a4b063, gate wired (30 hooks), sweep dry run clean.

Depends on: item 13

Action: tools/pii_scan.py (pure Python): consumer-domain addresses >= 3 distinct per added file (or >= 8 occurrences of <= 2 addresses, the 10-09 checkpoint shape), any-domain >= 20 distinct, IBAN, DE phone, JSON name/email/phone key density >= 50, single-line high-entropy file, and a docs/-scoped confidential-names list seeded from each client's context/confidential-names.txt; allowlist tools/tests/, */fixtures/, .claude/skills/**, *.example.*; inline `pii-allow: <reason>` marker. Wire: .claude/hooks/pii-push-gate.py (PreToolUse Bash|PowerShell on `git push`, range from ruff-push-gate's pushed_files, permissionDecision ask listing paths and counts, never values); repo-sweep plan() on every `??` text file; a CI job over base..head. Rewrite .gitignore L152-153 to a neutral comment.

Why: gitleaks runs after the push is already public and knows only secret shapes; nothing looks for addresses, rosters or names; the WW import brings 582 context files and real-data test material into a public repo.

Verify: tools/tests/test_pii_scan.py with negative cases as the contract; calibration run over the tree lists exactly docs/session-inventory-2026-05-10.md, friction-register-archive.md, the 10-11 WW and 09-24 BAfoeG checkpoints and the platform WW export; a push adding a 3-address CSV asks, an ordinary checkpoint push is silent.

Files: `tools/pii_scan.py`, `.claude/hooks/pii-push-gate.py`, `tools/repo-sweep.py`, `.github/workflows/ci.yml`, `tools/wire-hooks.py`, `tools/tests/test_pii_scan.py`, `.gitignore`

### W1-15 [homes-3, exposure-5] cost S

Status: todo

Depends on: none

Action: file-placement-gate.py: delete the `not rl.startswith('workspace/clients/')` clause (gitignored paths are already exempt), extend EXPORT_RE with roster|contacts|attendees|profiles|prospects|emails?[-_]sourced, sniff CSV headers (email/first_name/last_name -> ask) and .md/.html writes under tracked client paths containing linkedin.com/in or 3+ addresses (advise).

Why: The PII advisory skips the whole clients tree, so the roster writes that landed 25+ named third parties under deliverables/ could not have fired.

Verify: new cases in tools/tests/test_file_placement_gate.py (tracked client roster.csv advises; context/ path silent) proven with regress_check.

Files: `.claude/hooks/file-placement-gate.py`, `tools/tests/test_file_placement_gate.py`

### W1-16 [harness-2, onboard-2, onboard-3, onboard-1, onboard-12, fit-5, harness-5] cost M

Status: done PR #1671 (2026-10-29). tools/infra_yaml.py + infra_check.py (CI hooks job, `--all`); builder agents, comd_resume, skil_build and n8n-pack read through the loader. The WW shape is a synthetic fixture (tools/fixtures/infra_yaml/ww-shape). Deviation: brisken got `deploy: .../expense-reconciliation/deploy.py` beside `orchestrator: fastapi`, because agnt_deployer maps FastAPI to `railway up`; D1 must keep honoring `deploy:`. Against the real WW file infra_check names N8N_API_KEY/URL_WARME_WIMMER missing from its .env.example: the migration adds them. PLATFORM-FEASIBILITY lives in skil_make-mcp-tools-expert/modules (the only copy), not skil_make-pack.

Depends on: none

Action: tools/infra_yaml.py: one loader normalizing `instances:` lists and top-level `n8n:`/`make:` blocks (walking nested `workflows:` maps) into {instances(type, name, url, api_url_env, api_key_env, mcp_server), credentials, workflows(id -> name, n8n_workflow_id, status, trigger, export, test)}; tools/infra_check.py --client X (mcp_server == n8n-{client}, export paths exist, test scripts exist, token_env names in automations/.env.example, advisory when the file exceeds 40 KB or any scalar 500 chars) in the hooks job. agnt_make-builder Step 8 ('init' -> 'add') and agnt_n8n-builder Steps 2/7 read and write through the loader; comd_resume Step 5 likewise. Detection order in skil_build/SKILL.md, modules/DETECTION.md and skil_n8n-pack: top-level `orchestrator:` -> instance `type:` -> file checks; .mcp.json answers only 'credentials wired on this machine'; add `orchestrator:` to brisken (fastapi) and meji-media (make) infrastructure.yaml. comd_new-client: default n8n (also DETECTION.md:3), deliverables/ in the tree, Step 4 MCP entry delegated to `/comd_n8n-instances add`, Step 2.5/6.5/Step 8 dead paths fixed (skil_make-pack, skil_client-comms/templates, drop The Crucible symlink and both reference/README.md stubs), Step 9 -> B6 Band-1 chain; same dead PLATFORM-FEASIBILITY path in comd_ops-audit.md:69 and comd_convert-proposal.md:74; comd_new-proposal.md:414/422 `/proposal-retro` -> `/comd_proposal-status`.

Why: Both builder agents BLOCK on an infrastructure.yaml shape no client file has, n8n detection reads a gitignored file worktrees lack, and three incompatible n8n schemas exist; WW's 127 KB file arrives next session.

Verify: tools/tests/test_infra_yaml.py loads meji-media's file and a fixture copy of the WW shape; test_infra_check.py; `uv run tools/infra_check.py --client meji-media` exits 0; `uv run tools/check-skill-map.py` OK.

Files: `tools/infra_yaml.py`, `tools/infra_check.py`, `.claude/agents/agnt_make-builder.md`, `.claude/agents/agnt_n8n-builder.md`, `.claude/commands/comd_resume.md`, `.claude/commands/comd_new-client.md`, `.claude/commands/comd_ops-audit.md`, `.claude/commands/comd_convert-proposal.md`, `.claude/commands/comd_new-proposal.md`, `.claude/skills/skil_build/SKILL.md`, `.claude/skills/skil_build/modules/DETECTION.md`, `.claude/skills/skil_n8n-pack/SKILL.md`, `workspace/clients/brisken/infrastructure.yaml`, `workspace/clients/meji-media/infrastructure.yaml`, `tools/fixtures/agnt_n8n-builder/infrastructure.yaml`, `tools/tests/test_infra_yaml.py`, `tools/tests/test_infra_check.py`

### W1-17 [onboard-4] cost M

Status: done PR #1684 + follow-up #1686 (2026-10-29): tools/mcp_config.py renders .mcp.json from infra + the primary's context/.env + a gitignored `.mcp.local.json` (`_scope` tags); primary = union, worktree = branch client (+ vercel on platform/proposal); `--ensure` writes on change only, refuses until `--adopt`; SessionStart + worktree-add hooks; comd_n8n-instances/new-client/resume read through it. Owner yes (AskUserQuestion): adopt + ensure ran in the primary, `.mcp.json` sha256 unchanged, `claude mcp list` 7 connected 0 failed. #1686: `--adopt` also writes `.git/info/exclude`, because the primary (on an older main) showed the token-bearing local file as untracked for ~1 min. Verified: 15 tests, regress_check bites, `--check` on a fresh worktree renders brisken without make-meji-media and meji-media with it. Open: the "lists n8n-warme-wimmer" half waits for the WW import; the primary needs a fast-forward before its SessionStart runs the new hook.

Depends on: item 16

Action: tools/mcp_config.py --ensure|--check: render .mcp.json for the current root from each client's tracked infrastructure.yaml (mcp_server, api_url_env, api_key_env) plus the gitignored context/.env, with a `local:` passthrough block for machine-only servers; run --ensure at SessionStart, after `git worktree add` (PostToolUse) and from comd_resume Step 0; print 'restart Claude Code to load' only when the rendered file changed; comd_n8n-instances shrinks to 'edit infra + .env, run --ensure'.

Why: The per-client MCP server lives in one gitignored file; worktree sessions have none, and the WW key is duplicated in .env and .mcp.json (the 2026-09-13 25-hour outage shape).

Verify: tools/tests/test_mcp_config.py renders from a fixture infra + .env; `--check` in a fresh worktree reports the diff; after --ensure a worktree session lists make-meji-media and n8n-warme-wimmer servers.

Files: `tools/mcp_config.py`, `tools/wire-hooks.py`, `.claude/commands/comd_n8n-instances.md`, `.claude/commands/comd_new-client.md`, `.claude/commands/comd_resume.md`, `tools/tests/test_mcp_config.py`

### W1-18 [homes-8, onboard-7, onboard-9, onboard-5, fit-5, homes-1, homes-4] cost M

Status: done PR #1693 (2026-10-29): rule_file_placement client rows, check-index client scan (README.md per automations/tools/), tools/n8n_export.py (infra-derived map, scrubbed stable export, `--check`), builder + N8N-BUILD flat export path, comd_resume Step 4 READMEs, recon CI paths, workspace/templates/client-n8n/. Template manifest is tools/README.md (not INDEX.md) to match check-index. Verified: tests + regress_check on both wirings, preflight --full 2154 passed. Open: `n8n_export.py --client warme-wimmer --check` against live after the import.

Depends on: item 16

Action: rule_file_placement §2 client table gains rows: `automations/{id}-{slug}.n8n.json` (scrubbed exports, owner-set flat naming), `automations/tools/` (client scripts + README.md manifest in INDEX-row format), `automations/tests/`, 'client secrets: context/.env, names carry the client token, tracked automations/.env.example names only', 'client web-surface deploy source: {client}/<dir>/ with a README naming the deploy target'. tools/check-index.py: second scan over workspace/clients/*/automations/tools/*.{py,mjs,js,cjs} against that dir's README.md. comd_resume Step 4 reads automations/README.md and automations/tools/README.md when present. agnt_n8n-builder L185/212/225/269 and N8N-BUILD.md:3 -> the flat export path. tools/n8n_export.py --client X [--only ID] [--check] deriving the id->file map from infra (item 16) with a stable-stringified repo-vs-live diff. expense-recon-tests.yml `paths` gains tools/recon*, tools/brisken-recon-notify*, tools/lovable-bundle-audit.py and their tools/tests files. Templates: minimal workspace/templates/client-n8n/ (README, tools/INDEX.md, tests/README) as the copy source.

Why: WW lands next session with ~100 scripts, exports and two test harnesses and no defined home; brisken's client tools at tools/ top level are the opposite convention; the id-to-file map is kept in three places.

Verify: test_check_index.py client-scan case; a fixture client dir without README makes `check-index.py` exit 1; `uv run tools/n8n_export.py --client warme-wimmer --check` (after import) exits 0 against live; expense-recon PR runs its suite on a tools/recon* change.

Files: `.claude/rules/rule_file_placement.md`, `tools/check-index.py`, `tools/n8n_export.py`, `.claude/commands/comd_resume.md`, `.claude/agents/agnt_n8n-builder.md`, `.claude/skills/skil_build/modules/N8N-BUILD.md`, `.github/workflows/expense-recon-tests.yml`, `workspace/templates/client-n8n/`, `tools/tests/test_check_index.py`, `tools/tests/test_n8n_export.py`

### W1-19 [ci-12, onboard-8, onboard-10] cost S

Status: done PR #1695 (2026-10-29) except the harness template: warme-wimmer-tests.yml (path-filtered, no credential, fetch-live*/fixtures excluded, zero matches fails, a 'No WW tree yet' path until the import), agnt_testing-agent n8n mode, comd_test pointer, skil_build-test-fix n8n activation shape (builder hands it on, never runs it). Verified: synthetic tree run (decoys skipped, pass 1), the PR's own run took the no-tree path. Deferred to the WW import: the harness copy to workspace/templates/n8n-tests/ (the harness exists only in the WW tree).

Depends on: item 18

Action: .github/workflows/warme-wimmer-tests.yml path-filtered on workspace/clients/warme-wimmer/** (setup-node, npm ci, `node --test` in automations/tests; fetch-live.js never invoked). agnt_testing-agent and comd_test gain an n8n mode: run each infrastructure.yaml `test:` command, then `n8n_executions` readback per POST-EXECUTION-VERIFICATION.md. agnt_n8n-builder's closing phase and skil_build-test-fix gain the activation shape: activate via the client's n8n MCP `activateWorkflow` or the client's release script, read back active=true, name ww-vertrieb-release-72627.mjs as the reference (idle -> PUT by id -> readback hash -> activate -> acceptance run -> rollback). A reusable harness copy goes to workspace/templates/n8n-tests/, never tools/.

Why: The 145+ offline WW assertions run only when someone remembers the command; /comd_test and the builder have no n8n path; the harness in tools/ would break the subtree handoff.

Verify: The workflow runs on a PR touching the WW tree and not on a docs PR; `node --test` passes in CI with live-snapshots absent (skip path); agnt_testing-agent n8n section cites real MCP tool names from skil_n8n-pack.

Files: `.github/workflows/warme-wimmer-tests.yml`, `.claude/agents/agnt_testing-agent.md`, `.claude/agents/agnt_n8n-builder.md`, `.claude/commands/comd_test.md`, `.claude/skills/skil_build-test-fix/SKILL.md`, `workspace/templates/n8n-tests/`

### W1-20 [exposure-8, onboard-6, onboard-11, onboard-12, homes-2, exposure-10] cost M

Status: todo

Depends on: item 14, item 18

Action: WW import pre-flight PR (lands before the migration branch is pushed): .gitignore adds `.env.*` with `!.env.example|.env.sample|.env.template|.env.dist`, `/output/`, `/webhook-dump*.json`, `.claude/worktrees/`, `/workspace/hours-tracker.xlsx`; delete the dead context/portable exemption (.gitignore L92-96, L98-99; file-placement-gate.py:209 lookahead; test at test_file_placement_gate.py:335-337; rule_file_placement.md:37); mirror the new prefixes in file-placement-gate's static ignored list; tools/scrub-test-data.py rewriting addresses in ww-* scripts to example.com fixtures plus a pytest scoped to workspace/clients/warme-wimmer/automations/ asserting no consumer-domain address; harness.js/fetch-live.js read WW_TEST_DATA_DIR (default `../../../context/test-data`) and skip when absent; migration-day checklist written into docs/2026-10-21 WW checkpoint's next steps: live-snapshots, fixtures, output/ and handoff bundles to context/; infrastructure.yaml split by kind (identifiers + per-workflow {n8n_workflow_id, status, trigger, export, test} stay; prose to status/ files via `project_status.py --scaffold`; `secret_value:` to context/.env; make: block to a checkpoint); a1-a5 to stage folders via skil_spec-cleanup; replace tools/build-warme-wimmer-doc-site.py with the akkton version (WEBSITE_REPO kept, INDEX row updated) pointing at ../unpauseai-web/docs/publishing.md; run `uv run tools/pii_scan.py` and gitleaks locally before the first push; the owner reads the public file list.

Why: A straight `git mv` publishes 79 addresses, ten live Hero snapshots and 24 screenshots under the handoff subtree; the owner decision is 'code public, data private' and nothing enforces the second half.

Verify: `git check-ignore -v` confirms each new pattern; test_file_placement_gate.py green without the portable case; the WW scrub test green on the import branch; `pii_scan.py` over the import branch reports 0 hits outside allowlisted fixtures; `ls workspace/clients/warme-wimmer/status/` shows the scaffolded files and infrastructure.yaml is under 40 KB.

Files: `.gitignore`, `.claude/hooks/file-placement-gate.py`, `tools/tests/test_file_placement_gate.py`, `.claude/rules/rule_file_placement.md`, `tools/scrub-test-data.py`, `tools/build-warme-wimmer-doc-site.py`, `tools/INDEX.md`, `docs/2026-10-21 - WW Hero Key And Zapier Migration Prep/Checkpoint.md`

### W1-21 [ci-9] cost S

Status: todo

Depends on: none

Action: Single-source the lint scope in ruff.toml (`include` + `extend-exclude`, so `ruff check .` is the whole scope incl. the lead-desk tree and later automations/tools/); ci.yml, tools/preflight-hooks.py, ruff-push-gate.py (PY_SCOPE + RUFF_ARGS) and .pre-commit-config.yaml read it; one-time cleanup of lead-desk findings; a test that the four mirrors agree.

Why: Three local mirrors stopped at the pre-#862 scope, so recon lint errors pass every local gate and fail in CI after 2:40; the WW tree would be a fifth list.

Verify: tools/tests/test_lint_scope_mirrors.py; `ruff check .` clean; `uv run tools/preflight-hooks.py` matches the CI command byte for byte.

Files: `ruff.toml`, `.github/workflows/ci.yml`, `tools/preflight-hooks.py`, `.claude/hooks/ruff-push-gate.py`, `.pre-commit-config.yaml`, `tools/tests/test_lint_scope_mirrors.py`

### W1-22 [ci-5, machine-5, ci-7] cost S

Status: todo

Depends on: item 4

Action: tools/repo_freshness.py: `--open-prs` (one `gh pr list --author @me --state open --json number,headRefName,mergeable,mergeStateStatus,statusCheckRollup`, 5 s timeout, fail-open) printing DIRTY/red/>2-day PRs with the remedy; `[PRIMARY-PARKED]` when the main worktree is on a merged non-main branch with a clean tree, performed by `doctor.py --heal` only with check-then-act in one step and no sibling heartbeat; 'main CI red at <sha>' from `gh run list --branch main --workflow ci.yml --limit 1`; `--once-per-day` copied from friction-watch. post-action-gate.py: after a merge whose head equals the main worktree's branch, emit [PRIMARY-PARKED] re-surfacing like the not-live marker.

Why: Nothing looks at open PRs or at main's CI; seven checkpoints sat unmerged for six weeks and the primary parked twice.

Verify: tools/tests/test_repo_freshness.py with a PATH-shimmed gh; test_post_action_gate.py parked case; a SessionStart prints the open-PR line once per day.

Files: `tools/repo_freshness.py`, `tools/doctor.py`, `.claude/hooks/post-action-gate.py`, `tools/tests/test_repo_freshness.py`, `tools/tests/test_post_action_gate.py`

### W1-23 [ci-3, machine-4] cost M

Status: todo

Depends on: item 3

Action: tools/pr_land.py <pr|branch>: read mergeable + rollup; on CONFLICTING run the local union merge in a temporary `git worktree add` when the branch is not checked out, normalize sessions, push; wait with repo-sweep's decision table; merge; assert `gh pr view --json state` == MERGED regardless of the merge command's exit code. no-auto-commit-gate.py allows `pr_land.py` on a non-main branch as its own band (CI-green gate held inside the tool) with a test proven by regress_check; comd_checkpoint step 9 and rule_no_auto_commit name it; repo-sweep.py calls the same function and generalizes self_heal_conflict to docs/* heads. Retire the four warn-* chained-merge patterns and tools/gh-merge.sh; keep the two block-* patterns.

Why: No command owns push-wait-merge-verify; six pattern rules police the improvised chain; ledger PRs that lose the race to main rot because only the sweep's own branch gets healed.

Verify: test_pr_land.py (conflicting -> healed -> merged, red -> leaves open); test_no_auto_commit_gate.py band case; `uv run tools/pr_land.py <next docs PR>` lands it in one call.

Files: `tools/pr_land.py`, `.claude/hooks/no-auto-commit-gate.py`, `tools/repo-sweep.py`, `.claude/commands/comd_checkpoint.md`, `.claude/rules/rule_no_auto_commit.md`, `.claude/patterns/`, `tools/gh-merge.sh`, `tools/tests/test_pr_land.py`, `tools/tests/test_no_auto_commit_gate.py`

### W1-24 [machine-1, machine-2, machine-6, homes-12, machine-7, machine-10, machine-9] cost M

Status: todo

Depends on: item 14

Action: tools/worktree_prune.py (dry-run default): inputs `git worktree list --porcelain`, cached `gh pr list --state merged --limit 2000` and open PRs, session_registry records (live pid, not only heartbeat age), protected roots from Get-ScheduledTask actions and junction targets (fail-closed for --execute; tracked fallback allowlist agentic-ops1-watcher, agentic-ops1-notify, agentic-ops1-deploy as the one refreshable deploy seat). PROTECTED: live pid or heartbeat, task root, junction target, newest mtime within 24 h, dirty (CRLF-only is clean); DEAD: merged PR or ahead==0; HOLD: open PR or ahead>0 (print pushed/unpushed; push unpushed branch worktrees older than the quiesce after a credential/pii scan, never a PR). --execute: `git worktree remove` (never --force), `branch -D` for DEAD, `worktree prune`, rmdir empty agentic-ops1-*/ao1-* without .git; `--remote-merged` dry-run listing merged remote heads. Wire after sweep_repo() in repo-sweep.py. tools/scheduled_tasks.py --check (Windows-only, --once-per-day at SessionStart, doctor CHECK home_clone_only) with a registry tools/fixtures/scheduled-tasks.json seeded from weekly_synthesis --print-registration and lead-desk/worker/install-task.ps1; weekly_synthesis close-candidate exclusion uses the protected-roots helper. recon-accuracy-deploy-gate.py SANCTIONED text: 'refresh agentic-ops1-deploy, do not add a tree per deploy'. sibling-session-gate.py:76 advises `../ao1-<name>`. Rewrite memory reference_repo_root_layout.md from the live listing and correct the sweep time to 02:30 StartWhenAvailable.

Why: 78 worktrees (55 dead, 6-7 GB), 10 stale detached snapshots, nine scheduled tasks pinned to three checkouts that no tool knows about (three red today), four generators and zero collectors; the memory-only fix failed once already.

Verify: tools/tests/test_worktree_prune.py matrix (merged-clean DEAD, open-PR HOLD, dirty/heartbeat/task-root PROTECTED, CRLF-only clean, ahead>0 HOLD, deploy seat exempt); dry-run table lists ~56 DEAD, 8 HOLD, watcher PROTECTED; test_scheduled_tasks.py with a stubbed PowerShell call; `--execute` stays for Wave-2 D5.

Files: `tools/worktree_prune.py`, `tools/scheduled_tasks.py`, `tools/fixtures/scheduled-tasks.json`, `tools/repo-sweep.py`, `tools/weekly_synthesis.py`, `tools/doctor.py`, `tools/wire-hooks.py`, `.claude/hooks/recon-accuracy-deploy-gate.py`, `.claude/hooks/sibling-session-gate.py`, `tools/tests/test_worktree_prune.py`, `tools/tests/test_scheduled_tasks.py`, `tools/INDEX.md`

### W1-25 [harness-7] cost S

Status: todo

Depends on: item 23

Action: Delete .claude/patterns/warn-merge-chained-after-checks-watch.md (identical pattern) and warn-merge-chained-after-any-command.md (disabled); widen block-merge-chained-after-any-command's separator class to include newline, then delete warn-chained-checks-watch-and-merge.md; `pattern_rules.py lint`: duplicate (event, pattern) = FAIL, `enabled: false` older than 14 d = advisory; translate warn-send-output-truncated.md to English.

Why: One chained merge fires two warnings and a block; the dead rule is read by every lint.

Verify: tools/tests/test_pattern_rules_gate.py cases; `uv run tools/pattern_rules.py lint` = 34 rules, 0 findings.

Files: `.claude/patterns/`, `tools/pattern_rules.py`, `tools/tests/test_pattern_rules_gate.py`

### W1-26 [harness-8, ctx-11] cost S

Status: todo

Depends on: none

Action: Move executed_view (split_segments, MENTION_PROGRAMS, INLINE_CODE_FLAG) from deploy-consumer-gate.py into .claude/hooks/_shell.py; add for/[/test/do/done as mention words; post-action-gate.py:253 matches `vercel-force-deploy\.sh` against that view; negative cases (loop header, `[ -e path ]`, grep) in both test modules. cd-guard REWRITE_NOTE shortened to one line (adjust test_cd_guard.py assertions). deploy-consumer-gate PostToolUse arm: suppress the advisory for subagent payloads (agent_id/agent_type, fallback transcript_path recorded in the marker) and rate-limit the re-advise per marker. Minimal test for reference-anchor-gate.py; delete auto-approve-protected.py and drop it from CANONICAL_HOOKS/EXPECTED_HOOK_SCRIPTS (redundant under bypassPermissions).

Why: A file-existence check cleared the platform marker and opened a consumer-drive marker; cd-guard repeats 330 chars on every cd (~6k tokens per 300-call session); two wired hooks have no test.

Verify: test_post_action_gate.py, test_deploy_consumer_gate.py (subagent payload sees parent marker), test_cd_guard.py, new test_reference_anchor_gate.py, test_hooks_registry.py green; regress_check on the loop-header case.

Files: `.claude/hooks/_shell.py`, `.claude/hooks/deploy-consumer-gate.py`, `.claude/hooks/post-action-gate.py`, `.claude/hooks/cd-guard.py`, `.claude/hooks/auto-approve-protected.py`, `tools/wire-hooks.py`, `tools/tests/test_post_action_gate.py`, `tools/tests/test_deploy_consumer_gate.py`, `tools/tests/test_cd_guard.py`, `tools/tests/test_reference_anchor_gate.py`, `tools/tests/test_hooks_registry.py`

### W1-27 [harness-9] cost S

Status: todo

Depends on: none

Action: wire-hooks.py resolves the interpreter once at wire time (`uv python find`) and emits `<abs python> <abs script>` instead of `uv run --directory`, after confirming no gate depends on cwd beyond REPO-from-__file__.

Why: Each Bash call spawns 12 hook processes and each Write/Edit 9; roughly half of a 176-422 ms gate is the uv launcher.

Verify: Time the 12-hook Bash chain with the same minimal payload before and after (expect >= 1 s saved sequential); test_hooks_registry.py green; `wire-hooks.py --ensure` idempotent.

Files: `tools/wire-hooks.py`, `tools/tests/test_hooks_registry.py`

### W1-28 [ci-8] cost M

Status: todo

Depends on: item 1

Action: Trial `pytest -n auto` (pytest-xdist in the dev extra) on expense-recon-tests.yml; mark test_smtp_listener_e2e.py, test_smtp_starttls.py and sleep-dependent tests `@pytest.mark.serial` and run them in a second step with `-m serial`; keep the push:main run (it is the only full-suite pass over the merged tree); fallback a two-way directory matrix.

Why: The 6:49 serial recon job is the real critical path for the p1 loop (37 commits/month) and grows with every item.

Verify: Two consecutive PR runs of expense-recon-tests.yml under 4 min with 3,604 tests collected; no new flakes across five runs.

Files: `.github/workflows/expense-recon-tests.yml`, `workspace/clients/brisken/automations/expense-reconciliation/pyproject.toml`, `workspace/clients/brisken/automations/expense-reconciliation/tests/`

### W1-29 [harness-4, harness-12, harness-11] cost M

Status: todo

Depends on: item 5

Action: Move the 11 stub skills' modules into skil_n8n-pack/modules and skil_make-pack/modules with namespaced basenames (JS-/PY- prefixes for the three colliding names); rewrite both pack tables to local links; delete the stub dirs; fix agnt_make-builder.md:104, agnt_build-orchestrator.md:176, comd_status-check.md:113; drop CROSS_SKILL_MODULE_REF and test C1. Rename the five vendored copies (skil_email-html-mjml, skil_web-design-guidelines, skil_mcp-builder, skil_sales-do, skil_owasp-security) to drop skil_ and add lock entries; `FIRST_PARTY_EXTRA = {"brisken-design"}`; anneal-metrics first-party basis = 'skill dirs absent from skills-lock.json'. Extend check-skill-map.py to walk .claude/commands and .claude/agents resolving `/name` tokens (pass on comd_{name} or skil_{name}) and add it to the CI hooks job; fix the four dangling refs (/proposal-retro x2 -> item 16, /verify-live x2 -> `/comd_test verify`); align the handoff path to `.claude/handoffs/{client}-{session}/` in comd_build-automation, agnt_build-orchestrator and CLAUDE.md.

Why: Eleven roster entries say they are not skills, the pack's own agent points at a modules path that 404s, the lock cannot hash five vendored skills, and no checker covers command/agent references.

Verify: `uv run tools/check-skill-map.py` OK over skills, commands and agents; test_check_skill_map.py updated; CLAUDE.md Skills line regenerated and anneal-metrics drift 0.

Files: `.claude/skills/skil_n8n-pack/`, `.claude/skills/skil_make-pack/`, `.claude/skills/`, `skills-lock.json`, `tools/check-skill-map.py`, `tools/anneal-metrics.py`, `.github/workflows/ci.yml`, `.claude/agents/agnt_make-builder.md`, `.claude/agents/agnt_build-orchestrator.md`, `.claude/commands/comd_status-check.md`, `.claude/commands/comd_build-automation.md`, `CLAUDE.md`, `tools/tests/test_check_skill_map.py`

### W1-30 [homes-5, truth-16, fit-2, homes-9, fit-11, ledger-12] cost S

Status: todo

Depends on: item 10

Action: Brisken/orphan tidy with no deletions beyond W1 supersession: dedupe the 14 root duplicates in brisken/deliverables (diff the 5 divergent .md pairs, keep the themed copy), place the 7 unsorted files and 3 session/deck dirs, record themes linkedin/sap-assets/youtube/sessions in FILE-PLACEMENT.md, add lead-desk and the four site dirs to FILE-PLACEMENT.md and PROJECT-BOUNDARIES.md, drop brisken's automations/blueprints/.gitkeep; run skil_spec-cleanup brisken (p1 -> specs/4-live, stage: live, orchestrator: fastapi; p2.ops1 decided in the pass); rewrite brisken/specs/README.md in the comd_new-client Step 5 shape with p1 live and pointers to PROJECT-BOUNDARIES.md and status/; add a0 to meji's specs/README.md; rename 'workspace/projects/Automation services' -> automation-services; move the three workspace/docs checkpoints into docs/ with INDEX rows and delete workspace/docs; tools/client_placement_check.py (reads a client's FILE-PLACEMENT.md theme table, flags flat deliverables/ root files) in doctor's battery.

Why: The client-level rule written to stop the flat pile has regrown it by duplication; every full-path resume reads a May-2026 account of p1 as unstarted.

Verify: `git ls-files workspace/clients/brisken/deliverables | awk -F/ 'NF==5'` returns 0 root files; `uv run tools/validate-spec.py` green on the moved spec; test_client_placement_check.py; docs/INDEX.md gains three February rows under their client sections.

Files: `workspace/clients/brisken/deliverables/`, `workspace/clients/brisken/FILE-PLACEMENT.md`, `workspace/clients/brisken/PROJECT-BOUNDARIES.md`, `workspace/clients/brisken/specs/`, `workspace/clients/meji-media/specs/README.md`, `workspace/projects/automation-services/`, `workspace/docs/`, `docs/INDEX.md`, `tools/client_placement_check.py`, `tools/doctor.py`, `tools/tests/test_client_placement_check.py`

## Wave 2: owner decisions, each with a recommendation and consequence

Deletions, repo settings, convention changes and anything the verifiers flagged as an owner call. Presented as decisions, not offers; D1-D4 unblock the WW migration and the public-exposure clean-up and should be answered in the first session.

### D1 [harness-1, harness-3, truth-3, fit-4, truth-15, homes-8, truth-5, onboard-1, harness-5] cost M

Status: approved 2026-10-28 (owner, AskUserQuestion): retire now, one PR before the WW migration.

Depends on: item 5, item 16

Decision and recommendation: Recommendation: retire now, in one PR before the WW migration. Consequence: ~250 tracked files gone (history keeps them); the build flow becomes resume -> build (Make/n8n builder or Python service) -> PR -> deploy router -> checkpoint; anyone wanting Trigger.dev later restores from git. Saying no keeps 60 KB of agent prose that misroutes every onboarding and deploy request.

Action: D1 Retire the Trigger.dev / Railway lane. Delete agnt_implementation-agent, agnt_deployer, agnt_testing-agent, agnt_bug-fixer, comd_publish, comd_client-handoff, comd_fix-bugs, comd_status-check, comd_convert-proposal, comd_publish-proposal, comd_proposal-status, skil_trigger-pack (17 files), the 6 TRIGGER-DEV-* + FASTAPI-BUILD modules, .agents/ (16 files), workspace/templates/client-trigger-dev (14), client-automation (42) and api-clients (63; retarget skil_api-boilerplate, skil_api-docs-fetcher, agnt_api-fetcher, comd_fetch-api to workspace/clients/{client}/automations/<pkg>/), DELIVERY-GUIDE.md (+ ROOT_ALLOWLIST entry), .claude/handoffs/herbox-1768492413 (+ gitignore handoffs/*/). Rewrite comd_build-automation + agnt_build-orchestrator in place (Make/n8n routing, intent review, Make ops gate; Phases 5-6 replaced by the builder's own activate/verify). comd_deploy becomes a thin router (n8n: MCP activate + readback; Make: MCP; Python services: the app's deploy.py); comd_test keeps its modes. comd_new-proposal rewritten to the akkton/unpauseai-web content/<slug> flow. Sweep the dangling references (comd_new-client -> client-handoff, comd_morning-briefing -> convert-proposal, agnt_intent-reviewer -> implementation-agent, rule_session-pressure -> /comd_deploy, tools/spec-staleness.py docstring, tools/INDEX.md -> comd_publish, meji handoff-package.md) and regenerate CLAUDE.md counts.

Why: No client runs Trigger.dev or Railway, both live Brisken products are FastAPI on Fly, the owner chose n8n for new builds; the lane has 0 runs since September and steers the WW session into a non-existent stack.

Verify: `uv run tools/check-skill-map.py` OK; test_doc_command_refs.py green; `/comd_build-automation meji-media a1` reaches agnt_make-builder in a dry run; CLAUDE.md counts match anneal-metrics.

Files: `.claude/agents/`, `.claude/commands/`, `.claude/skills/skil_trigger-pack/`, `.claude/skills/skil_build/`, `.agents/`, `workspace/templates/`, `DELIVERY-GUIDE.md`, `.claude/handoffs/`, `.gitignore`, `CLAUDE.md`, `.claude/hooks/file-placement-gate.py`, `.claude/rules/rule_file_placement.md`

### D2 [truth-4] cost S

Status: decided 2026-10-28 (owner): handoff repos live under UnpauseAI's GitHub, created at handoff and transferred to the client later (not the recommended client-owned repo). The Action's 'repo the client owns (org parameterised)' becomes 'a repo under the UnpauseAI account, transferable'.

Depends on: item 5

Decision and recommendation: Decide the repo owner for client handoff repos (recommendation: a repo under the client's own GitHub account, created at handoff time with `gh repo create`, subtree split once) before the WW code lands. Consequence: the WW import does not need a handoff repo now; CLAUDE.md line 88 and the Lead Desk/recon OWNERSHIP-HANDOFF stay the model.

Action: D2 Client handoff convention. Replace the CLAUDE.md subtree story with: 'each client's automations/<service> is self-contained; handoff = OWNERSHIP-HANDOFF.md plus a one-time `git subtree split` push to a repo the client owns (org parameterised)'; agnt_deployer's 'cannot deploy without subtree' goes with D1; the no-auto-commit subtree-push guard stays.

Why: The documented handoff pushes to the other developer's GitHub org and has never run; the WW code (today under akkton) lands next session.

Verify: CLAUDE.md names no akkton remote; `grep -r 'agentic-ops--' .claude CLAUDE.md` = 0.

Files: `CLAUDE.md`, `workspace/clients/brisken/OWNERSHIP-HANDOFF.md`

### D3 [exposure-3, homes-3, exposure-5, exposure-6, exposure-7, ledger-7, homes-9, machine-8, exposure-1, homes-11, exposure-2] cost M

Status: approved 2026-10-28 (owner): all of (a)-(g). (g)'s two remote-branch deletions were ordered in the 2026-10-28 session; a later session executing (g) needs a fresh explicit order. Rotation: hand the owner only the step that needs their login.

Depends on: item 10, item 14

Decision and recommendation: Recommendation: approve all of (a)-(g) now, history purge later as its own force-push decision. Consequence: the public tree stops carrying client PII and personal admin; GitHub history still serves it until a purge; one Band-3 branch deletion and one rotation are the owner's own actions.

Action: D3 Public-data removals from HEAD (history stays until a separate purge order). (a) platform/public/docs/warme-wimmer/ (downloads + m-mail-abgleich.html, 579 addresses) and the same files in akkton/unpauseai-web via the content/<slug> publish path; (b) brisken rome-2026-leadgen task-2..7 output and the invite xlsx -> context/lead-generation/rome-2026/, meji US_Emails_sourced CSV -> context/, pointers in status/p2-rome.md; (c) the six Jochen, the Nagarro and the One Assessment checkpoint folders -> gitignored docs/personal (scores, submission ids and a third-party email are in the bodies); (d) the 8 KIT/BAfoeG/TikTok checkpoint folders, their INDEX rows and session-log entries -> docs/personal; keep the 13 Vinted folders; (e) workspace/projects/prototype-fund/SCOPE.md -> a gitignored home, retarget the two PrototypeFund notepad tasks; (f) `git rm --full-page --fullpage`; (g) tok.txt: identify the service from the 2026-08-23 deckgen transcript, rotate, then `git push origin --delete client/brisken/deckgen-native parking/primary-clone-wip-2026-08-25` and `git branch -D parking/...` after a diff --stat review; enable GitHub secret-scanning non-provider patterns.

Why: Hundreds of third-party consumer addresses, named lead rosters, a confidential assessment's results, the owner's address and a credential-shaped file are world-readable today.

Verify: `uv run tools/pii_scan.py --all` reports 0 hits outside allowlists; `git ls-tree HEAD` root has no `--full*`; `gh api repos/akkton/unpauseai-web/contents/public/docs/warme-wimmer/downloads` 404; `git branch -r --contains 57415748` empty.

Files: `platform/public/docs/warme-wimmer/`, `workspace/clients/brisken/deliverables/rome-2026-leadgen/`, `workspace/clients/meji-media/deliverables/US_Emails_sourced_2026-07-27.csv`, `docs/`, `docs/INDEX.md`, `workspace/projects/prototype-fund/`, `--full-page`, `--fullpage`

### D4 [homes-2, homes-4, homes-6, homes-7, truth-13, ledger-12, truth-6, fit-11, exposure-9] cost M

Status: approved 2026-10-28 (owner): whole list as one order, including the one-time repo-sweep pre-authorization to close and delete the REMOTE head of a red/conflicting/no-checks sweep PR (local branch kept).

Depends on: item 13, item 29

Decision and recommendation: Recommendation: approve the whole list as one order; two PRs (brisken branch, docs branch). Consequence: ~40 files and three directories leave HEAD; the recon Fly deploy, scheduled tasks and client surfaces are untouched; anything needed later is in history.

Action: D4 Supersession deletions (W1 §4). brisken: tools/brisken-mailbox-watch.py, brisken-dirk-draft-loader.py, brisken-website-inquiries.py, build-hours-tracker.py, sync-hours.py (+ INDEX rows; reference_dirk_outlook_com_drafts.md trimmed to the conventions the rule still cites); onepilot-site/ and the root duplicate deliverables/brisken-onepilot-website-prototype.html; rome-hub/ once the 301 lands; MICROSOFT-GRAPH-IT-REQUEST.md and lead-desk/PHASE2-IT-REQUEST.md; OWNERSHIP-HANDOFF.md and TARGET-ARCHITECTURE.md -> docs/references/ with the 19 relative links rewritten; the three call transcripts -> context/reference/ with absolute-path pointers (FILE-PLACEMENT.md:65 updated). meji: docs/client/ab-testing-guide.md, handover/ (README folded into automations/README.md), reference/README.md; `make-api.py export-blueprints` wired to the Modify-scenario gate; meji_reply_sla_daily.py -> automations/scripts/ (health check stays until its radar lens is split). docs/: measure.py, truth.py, verification-verdicts.json (recon-categorization-score.py:10 -> git-history citation), the seven Merchant Identity scripts if item 204 builds are all shipped, spec-instrumentation-friction-pressure.md into its checkpoint folder (session_state.py:15 updated), INTEGRATIONS.md after moving the RESEND-key provenance note, system-changelog.md, the Instantly estate HTML into its 09-08 checkpoint folder. scripts/: delete both files, `--html` flag on tools/send_email.py, remove scripts/ from CLAUDE.md, W2 map and KNOWN_TOP_DIRS. workspace/playgrounds + comd_refresh-pipeline.md. Stale sweep heads sys/sweep-20260721-0330, -20260723-0332 (after diff --stat) and a one-time pre-authorization for repo-sweep to close+delete the REMOTE head of a red/conflicting/no-checks sweep PR while keeping the local branch.

Why: Each is dead by the repo's own W1 rule; the COM tools are banned by rule_brisken_graph_first; two hours scripts write an unignored billing workbook.

Verify: `uv run tools/check-index.py` green; test_file_placement_gate.py green without scripts/; `git grep -l 'OWNERSHIP-HANDOFF.md'` resolves to the new path everywhere; MejiReplySLA task action points at automations/scripts and LastTaskResult 0.

Files: `tools/`, `tools/INDEX.md`, `workspace/clients/brisken/`, `workspace/clients/meji-media/`, `docs/`, `scripts/`, `workspace/playgrounds/`, `.claude/commands/comd_refresh-pipeline.md`, `tools/send_email.py`, `tools/repo-sweep.py`, `CLAUDE.md`, `.claude/rules/rule_file_placement.md`, `.claude/hooks/file-placement-gate.py`

### D5 [machine-1, machine-2, machine-3, machine-7, machine-10, machine-11] cost S

Status: todo: ask after W1-24 builds tools/worktree_prune.py; the dry-run table does not exist yet (the tool is missing on main, 2026-10-28).

Depends on: item 24, item 4

Decision and recommendation: Recommendation: run the dry-run table, then approve --execute, the repo setting and the branch deletions as one order; the Hero node remote goes under UnpauseAI (never 011matthias with the current history). Consequence: ~7 GB reclaimed, `git worktree list` drops to ~20 entries, branch completion works again; squash commits stay on main and GitHub keeps refs/pull/N/head.

Action: D5 Machine clean-up executed. `uv run tools/worktree_prune.py --execute` (55 dead worktrees, 9 stale detached snapshots, husks); `gh api -X PATCH repos/011matthias/agentic-ops1.01 -F delete_branch_on_merge=true`; one-off `push origin --delete` of the 415 merged remote heads and `branch -D` of 423 local merged branches via the comm-against-merged-list recipe; machine-7 triage: push + PR client/brisken/close-month-rename from ao1-brisken, land docs/checkpoint-2026-09-10-brisken-july-cc as a docs PR, diff-then-drop p1-gl-vocabulary-rebased-local, p1-item-201-gl-hand-pick, p1-july-gap-attribution, sys/sweep-20260723-0332, the six closed-unmerged heads; n8n-nodes-hero-software gets its remote under the UnpauseAI account per D1 of u9 (private until the HERO gate), package.json `repository` set, added to repo-sweep REPOS policy push; uweb vs unpauseai-web duplicate clone: keep one.

Why: 6-7 GB of dead trees, 450 dead refs on each side, one unpushed 20-day-old commit, and the only copy of the u9 Hero node on this disk.

Verify: `git worktree list | wc -l` <= 25; `git ls-remote --heads origin | wc -l` <= 30; `gh pr list --head client/brisken/close-month-rename` shows a PR; `git -C .../n8n-nodes-hero-software remote -v` non-empty.

Files: `tools/worktree_prune.py`, `tools/repo-sweep.py`, `C:/Users/neuma_p1qrsic/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/memory/reference_repo_root_layout.md`

### D6 [ci-6, ledger-9] cost M

Status: todo

Depends on: item 1, item 2, item 3, item 23

Decision and recommendation: Recommendation: yes, after items 1-3 land (required checks must be jobs that always exist). Consequence: checkpoint tails drop from ~3 min to seconds; a PR that goes red stays open and is reported by repo_freshness; the ruleset also rejects direct pushes to main unless the owner is on the bypass list, which the disabled eod/weekly workflows (D7) would need.

Action: D6 GitHub-side auto-merge. Owner adds a ruleset on main requiring the always-present checks (secrets, lint/hooks; quality/smoke/lead-desk only as job-level-skippable jobs), enables 'Allow auto-merge'; no-auto-commit-gate gets a Band-1 `gh pr merge --auto` path with a test; the ship chain arms `--auto --squash --delete-branch` right after `gh pr create`; repo-sweep arms --auto instead of its 15-minute wait; block-stop-merge-left-pending and the two warn patterns get an 'auto-merge armed' clause; sessions keep the in-turn wait only when a deploy follows.

Why: Every merge today needs a live session polling CI (60 of the last 108 PR runs were docs branches); ci-5 becomes the safety net for PRs that never land.

Verify: A docs PR merges with no session attached (`gh pr view --json autoMergeRequest,state`); test_no_auto_commit_gate.py auto case; `gh api repos/.../rulesets` lists the ruleset.

Files: `.claude/hooks/no-auto-commit-gate.py`, `.claude/rules/rule_no_auto_commit.md`, `tools/repo-sweep.py`, `.claude/patterns/block-stop-merge-left-pending.md`, `.claude/commands/comd_checkpoint.md`, `tools/tests/test_no_auto_commit_gate.py`

### D7 [ledger-8, truth-6, harness-6, ci-11] cost S

Status: todo

Depends on: item 11

Decision and recommendation: Recommendation: delete eod/weekly, keep the briefing trio paused (memory: re-enable only on owner order). Consequence: the repo has no direct-push-to-main path left; weekly review = weekly_synthesis.py local task; nothing running changes.

Action: D7 Dead unattended workflows. Delete eod-capture.yml and weekly-review.yml (the only model-authored push-to-main paths), comd_eod-capture and comd_weekly-review (drop their B6 exception clauses), docs/briefings and docs/reviews (comd_review --save and comd_system-digest --file/--html write to .scratch/; friction-watch cadence clause repointed, test_friction_watch.py:163 updated), docs/INTEGRATIONS.md; keep docs/digests only as history; morning-briefing.yml + comd_morning-briefing + tools/morning_briefing.py stay paused unless the owner says delete; correct the weekly_synthesis row in tools/INDEX.md; one README line naming tools/weekly_synthesis.py as the live weekly loop.

Why: All three workflows are disabled_manually since June; their files still carry `git push origin HEAD:main` under a prompt-level B6 carve-out and point at output homes nobody writes.

Verify: `gh workflow list --all` shows no disabled workflows except morning-briefing; test_friction_watch.py green; `git grep 'HEAD:main' .github` = 0.

Files: `.github/workflows/eod-capture.yml`, `.github/workflows/weekly-review.yml`, `.claude/commands/comd_eod-capture.md`, `.claude/commands/comd_weekly-review.md`, `.claude/commands/comd_review.md`, `.claude/commands/comd_system-digest.md`, `docs/briefings/`, `docs/reviews/`, `docs/INTEGRATIONS.md`, `tools/friction-watch.py`, `tools/tests/test_friction_watch.py`, `tools/INDEX.md`, `README.md`

### D8 [ledger-2] cost M

Status: todo

Depends on: item 4, item 10

Decision and recommendation: Recommendation: (a). Consequence: one fewer union-merge surface per checkpoint, four tools and ~20 tests removed; the day view survives as a command; choosing (b) keeps the file and costs S but keeps the maintenance.

Action: D8 Daily session logs. (a, recommended) finalize stops writing docs/sessions/{date}.md; `checkpoint_scaffold.py day --date` renders the same view on demand from checkpoint frontmatter; delete merge-session-logs.py, repair-session-log.py, the fold/normalize arms of repo-sweep.py, the union line, the shard paragraph in comd_eod-capture, and their tests; repoint rule_branch_isolation §1, rule_file_placement §2, CLAUDE.md and comd_resume 5.6; existing files stay as history. (b) finalize writes per-session shards `{date}-{session_token()}.md` and the sweep folds them.

Why: A 1.6 MB ledger, 22 of 108 files corrupt, written by every checkpoint and read by nothing that runs; four repair tools exist because the shard design was never wired into the writer.

Verify: test_checkpoint_scaffold.py no longer asserts session-log writes; `uv run tools/checkpoint_scaffold.py day --date 2026-10-27` prints the day's entries; `git status` after a finalize shows no docs/sessions change.

Files: `tools/checkpoint_scaffold.py`, `tools/repo-sweep.py`, `tools/merge-session-logs.py`, `tools/repair-session-log.py`, `.gitattributes`, `.claude/rules/rule_branch_isolation_and_shared_ledger.md`, `.claude/rules/rule_file_placement.md`, `CLAUDE.md`, `.claude/commands/comd_resume.md`, `tools/tests/`

### D9 [fit-1, ctx-6, fit-10, fit-6] cost M

Status: todo

Depends on: item 8, item 7

Decision and recommendation: Recommendation: yes, one brisken PR, after item 8's digest exists so sessions never need the raw files. Consequence: p1 resume reads ~30 KB instead of 1.5 MB; item numbering and coverage tests keep biting; the backlog stays 'the one list' for open items.

Action: D9 p1 status split (brisken branch). p1-expense-reconciliation.md L11-935 change-log -> docs/references/brisken-p1-loop-history.md; backlog: keep `### N. title` grammar, retire shipped items to a sibling p1-backlog-shipped.md stubs ('### N. title (shipped PR #x; notes #..)'), move the three 2026-09-23 analysis sections (verbatim bookkeeper notes) to gitignored context/, extend recon-feedback-coverage.py --backlog and test_p1_backlog_item_numbers.py to scan both files; PROMPT-STATUS.md: delete L1-209, put `## Not applied` first, move PUBLISHED rows to Applied, lovable-bundle-audit.py reads its needles from the Not-applied table and replaces the three %TEMP%/prompt_ledger.py pointers; shrink p1-recon-loop-prompt.md to loop-only constants once item 7's next-prompt section exists.

Why: The two p1 files (283 KB + 1.24 MB) cannot be read whole; their load-bearing data (item numbers cited from code, note citations) must survive any pruning.

Verify: `uv run tools/recon-feedback-coverage.py` reports the same filed-note set before and after; test_p1_backlog_item_numbers.py green over both files; `uv run tools/lovable-bundle-audit.py` runs from the table; p1-expense-reconciliation.md under 32 KB.

Files: `workspace/clients/brisken/status/p1-expense-reconciliation.md`, `workspace/clients/brisken/status/p1-improvement-backlog.md`, `workspace/clients/brisken/status/p1-backlog-shipped.md`, `workspace/clients/brisken/status/p1-recon-loop-prompt.md`, `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`, `tools/recon-feedback-coverage.py`, `tools/lovable-bundle-audit.py`, `tools/tests/test_p1_backlog_item_numbers.py`, `docs/references/brisken-p1-loop-history.md`

### D10 [ctx-5, ctx-7] cost S

Status: todo

Depends on: item 9

Decision and recommendation: Recommendation: separate working directory for personal sessions (also fixes D3's personal-ledger class for good) and the four-file cut. Consequence: ~2k tokens and 40 lines of index headroom; Brisken memory load drops by >= 60k tokens; personal context stops competing with client context.

Action: D10 Memory compaction. Drop or merge the 15 closed entries, shorten the 18 long lines, cut the four ledger files (recon usability loop 92 KB, Jochen 52 KB, Lead Desk 47 KB, OnePilot hosting 33 KB) to decisions + pointers once D9 lands; personal entries: fold the 22 lines behind one pointer line or run personal sessions from a separate working directory with their own auto-memory.

Why: MEMORY.md is at the 25 KB load cap, so the next entries fall off unread; a Brisken session loads ~117k tokens of memory under the full-file rule.

Verify: `uv run tools/memory_audit.py` reports 0 lines over 155 chars, index under 20 KB, no 'ledger in memory' bucket hits.

Files: `C:/Users/neuma_p1qrsic/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/memory/MEMORY.md`

### D11 [machine-12, fit-7, machine-6] cost M

Status: todo

Depends on: item 24, item 17

Decision and recommendation: Recommendation: yes, with the junction tool first; the WW session works in a worktree and copies WW context into the primary's workspace/clients/warme-wimmer/context/. Consequence: no more check-then-act dance on the hub; the sweep always sees main; two live jobs get re-registered (owner's machine).

Action: D11 Primary clone as read-only hub. Rule sentence in rule_branch_isolation §2 ('the main worktree stays on main; branches are cut in worktrees'); tools/worktree_add.py (or the native EnterWorktree) that creates the worktree AND a junction of each client's gitignored context/ back to the primary, then retire the §3 in-place-checkout carve-out; pattern rule warning on `checkout -b` / `switch -c` in the main worktree; re-register AgenticOpsWeeklySynthesis against the notify clone; VintedWatcher gets the notify pattern (dedicated clone, fetch + ff-only daily); the Meji tasks keep their gitignored script dir in the primary.

Why: Every isolation hook assumes worktrees while sessions still start in the primary, which parks on merged branches and is what the sweep and four scheduled tasks run from.

Verify: A worktree created by the tool resolves workspace/clients/brisken/context/README.md; test_worktree_add.py; `Get-ScheduledTask AgenticOpsWeeklySynthesis` action points at agentic-ops1-notify and LastTaskResult 0.

Files: `.claude/rules/rule_branch_isolation_and_shared_ledger.md`, `tools/worktree_add.py`, `.claude/patterns/`, `tools/tests/test_worktree_add.py`

### D12 [harness-13] cost S

Status: todo

Depends on: item 29

Decision and recommendation: Recommendation: remove; they were vendored for the retired platform/ build. Consequence: 303 files gone, ~1.2k roster characters per session, skills-lock refreshes stop pulling unread updates; `npx skills add` restores any of them in a minute.

Action: D12 Remove vercel-optimize (154 files), vercel-react-best-practices (76), vercel-composition-patterns (14), next-best-practices (20), remotion-best-practices (39) and their skills-lock.json entries; keep the marketing pack, superpowers set, agent-browser, just-scrape.

Why: 303 of 721 skill files serve Next.js/Vercel/Remotion, stacks absent from the work ahead, with 0 runs in 40 days.

Verify: test_file_placement_gate.py:232 still passes; `ls .claude/skills | wc -l` = 52 before D1's stub removal.

Files: `.claude/skills/`, `skills-lock.json`

### D13 [ci-10] cost S

Status: todo

Depends on: none

Decision and recommendation: Recommendation: open the pinger account and name the Brisken mailbox. Consequence: 5-minute detection off the laptop; the repo stops promising a cadence it cannot deliver.

Action: D13 Uptime monitor for api.expenses.brisken.com: an external pinger on /healthz (5-minute free tier) mailing the owner (Brisken recipient is the open decision); keep the Actions cron as the issue-opening fallback with its header rewritten to the measured 2-7 h cadence; correct the four '10 minutes' statements (yml L4, probe L12, tools/INDEX.md L31, backlog item 123); fix BriskenReconNotify's LastTaskResult=1 before adding any probe step there.

Why: GitHub runs the `*/10` schedule every 3.96 h on average; the bookkeeper's monthly closes would learn of an outage hours late.

Verify: Pinger dashboard shows 5-minute checks; `grep -rn '10 minutes' .github tools workspace/clients/brisken/status` = 0.

Files: `.github/workflows/expense-recon-uptime.yml`, `tools/recon_uptime_probe.py`, `tools/INDEX.md`, `workspace/clients/brisken/status/p1-improvement-backlog.md`

### D14 [truth-11, fit-11, harness-11] cost S

Status: todo

Depends on: item 5

Decision and recommendation: Recommendation: drop proposal/ and platform/ now. Consequence: the gate stops honouring two prefixes nobody uses; nothing else changes.

Action: D14 Confirm the branch families CLAUDE.md lists match branch-isolation-gate.py and rule_branch_isolation §1 (client/, docs/, sys/, local-web/, uwi/, brisken leadgen/), dropping proposal/ and platform/ from all three in one PR; keep workspace/proposals (73 files) until the Upwork proposal pipeline is retired as its own decision.

Why: CLAUDE.md names dead prefixes while the gate and rule still recognise them; the two must change together.

Verify: test_branch_isolation_gate.py updated; CLAUDE.md, rule and hook list the same families.

Files: `CLAUDE.md`, `.claude/rules/rule_branch_isolation_and_shared_ledger.md`, `.claude/hooks/branch-isolation-gate.py`, `tools/tests/test_branch_isolation_gate.py`

### D15 [ledger-1] cost M

Status: todo

Depends on: item 4, item 10

Decision and recommendation: Recommendation: yes, after item 4 re-lands the stale PRs and D8 settles the session-log shape. Consequence: checkpoint PRs stop conflicting on INDEX.md; the index is reproducible from the folders.

Action: D15 INDEX generator: `checkpoint_scaffold.py index --rebuild|--check` from checkpoint frontmatter (fallback folder name + `**Date:**`), order-insensitive check in the hooks job, finalize calls --rebuild, self_heal_conflict calls it instead of relying on union, then drop `docs/INDEX.md` from .gitattributes; the 59 dead rows listed in the PR body.

Why: The 124 KB hand-appended index is the ledger's main merge-conflict surface and lies in 59 rows.

Verify: `index --check` green on main and on a PR merged concurrently with another docs PR; test_checkpoint_index.py.

Files: `tools/checkpoint_scaffold.py`, `tools/repo-sweep.py`, `.gitattributes`, `docs/INDEX.md`, `.github/workflows/ci.yml`, `tools/tests/test_checkpoint_index.py`

### D16 [onboard-7, exposure-8] cost S

Status: approved 2026-10-28 (owner): leave both out of the public tree.

Depends on: item 20

Decision and recommendation: Recommendation: leave both out of the public tree. Consequence: the import PR carries 15 canonical exports and synthetic fixtures only; the drift guard reads live snapshots from context/.

Action: D16 WW import content calls: do not import the eight dated backup JSONs beside the exports (they stay in akkton history; future backups go to .scratch/); keep fixtures/sabine-task-hardening/executions.json (real Hero record ids) under gitignored context/; copy only ww-export-workflows' canonical exports.

Why: Both are tracked in the source repo, so leaving them behind is a choice the owner makes, not a mechanical scrub.

Verify: `git ls-files workspace/clients/warme-wimmer | grep -E '_w2-|vor-|fremdstand|executions.json'` = 0.

Files: `workspace/clients/warme-wimmer/automations/`, `workspace/clients/warme-wimmer/context/test-data/`

## Wave 3: defer or not worth it

Correct findings whose fix is premature, superseded by a cheaper Wave-1 change, or waits on an upgrade or on the WW migration landing first.

### X1 [ledger-5] cost M

Status: todo

Depends on: D15, D8

Action: Nest checkpoint folders by month only after D15's generator and D8 exist, and rewrite the 255 in-docs cross-links, settings.json, comd_resume Step 1, comd_weekly-review:47 and the two rules in the same PR.

Why: GitHub's 1,000-entry listing cap bites in one to three months; INDEX.md is the human index meanwhile; doing it now re-creates flat folders from every stranded PR.

Verify: `ls docs | wc -l` tracked monthly by repo_freshness.

Files: `tools/checkpoint_scaffold.py`, `docs/`

### X2 [homes-1, fit-5] cost L

Status: todo

Depends on: item 18, D4

Action: Defer moving the 13 recon tools and the outreach trio under brisken/automations/ until the WW tree has landed, the BriskenReconNotify task is repaired and `schtasks /Change` is scripted; recon-accuracy-guard.py and recon-accuracy-baseline.json stay in tools/ (pinned guard, deploy gate).

Why: The recon tools are the live product loop with a scheduled task, a deploy gate, 12 tests and 21 memory citations bound to their paths; item 18's CI path filter removes the immediate cost.

Verify: n/a until revisited

Files: `tools/recon*`, `tools/brisken-*`

### X3 [harness-9] cost L

Status: todo

Depends on: item 27

Action: Steps 2-3 (fold regex-only Bash gates into pattern rules; a per-event dispatcher running gates in a thread pool with decide(payload)) only if item 27's measurement still shows tool-call latency dominated by hook fan-out.

Why: Claude Code runs hooks in parallel, so wall-clock is the slowest gate; the dispatcher would need all 29 gates refactored and the hooklib tests re-pointed.

Verify: Hook chain timing after item 27.

Files: `.claude/hooks/`

### X4 [onboard-10] cost M

Status: todo

Depends on: item 19

Action: A generic tools/n8n_release.py kernel waits for the second n8n workflow family (u9 templates or a second client); extract it as .mjs from the WW scripts so their tests carry over, not a Python rewrite.

Why: Most of the WW release script is workflow-specific invariants and self-hosted PUT-is-live semantics; generalizing from n=1 would be guessed.

Verify: n/a

Files: `workspace/clients/warme-wimmer/automations/tools/`

### X5 [ctx-12] cost S

Status: todo

Depends on: item 6

Action: After upgrading Claude Code to >= 2.1.271: `omitClaudeMd: true` on read-only agents (agnt_intent-reviewer, agnt_done-verifier) and on Workflow lens prompts, restating their 2-3 gates inline.

Why: The ~4x rule-load multiplier is driven by Workflow lens subagents; the mechanism needs the newer version.

Verify: `claude --version` >= 2.1.271; a lens subagent transcript no longer contains rule_behaviors text.

Files: `.claude/agents/`

### X6 [ci-6] cost S

Status: todo

Depends on: D6, item 28

Action: Required-check tightening beyond D6 (e.g. requiring the recon suite) waits until item 28 makes it fast.

Why: A 7-minute required check would lengthen every brisken merge.

Verify: n/a

Files: 

### X7 [homes-4] cost S

Status: todo

Depends on: D4

Action: website/ and resources-site/ stay where they are; they disappear with the Lovable cutover soak (p2-lovable-rebuild element 6).

Why: Moving 12 MB that will be deleted breaks post-write-gate.py:135 and OWNERSHIP-HANDOFF pointers for no gain.

Verify: n/a

Files: `workspace/clients/brisken/website/`, `workspace/clients/brisken/resources-site/`

### X8 [truth-15] cost S

Status: todo

Depends on: D1

Action: No client-python-service template; comd_new-client's Python case points at the newest live service tree instead (done in D1).

Why: No Python-service build is scheduled; a frozen template is the failure this audit found.

Verify: n/a

Files: 

## Dropped sub-proposals (synthesis agent)

- [truth-15] Sub-proposal 'client-python-service/ skeleton derived from expense-reconciliation' dropped: no consumer in the work ahead, drags Brisken app/secret names into a shared tracked path.
- [fit-10] Sub-proposal to split 164 prompt files into pending/applied directories and to promote %TEMP%/prompt_ledger.py dropped: PROMPT-STATUS already has the sections, lovable-bundle-audit.py is the committed instrument, and the move rewrites links in the 13k-line backlog and ~10 checkpoints for no new state.
- [ledger-3] Per-quarter register files dropped: multiplies ledger paths every parser and rule names; age-only archive into the existing archive file gives the same shrink.
- [onboard-2, harness-2] Rewriting WW's 1,400-line infrastructure.yaml into `instances: - type: n8n` (or any single YAML shape) dropped: the loader in item 16 accepts both shapes; the WW file is split by kind on import instead.
- [harness-1] 'Delete the 15 files and build a thin /comd_build' dropped: comd_build-automation already routes by orchestrator; D1 rewrites it in place and keeps comd_test, comd_fetch-api/agnt_api-fetcher.
- [exposure-1, machine-5, machine-12] Sweep 'always branch sys/sweep-* from current HEAD' dropped (would carry client WIP into an auto-merged PR); pattern rule on every `checkout -b` in the main worktree dropped (rule §3 sanctions in-place checkouts until D11's junction tool exists). Replaced by skip-when-parked and the post-merge [PRIMARY-PARKED] marker.
- [ctx-2] A standalone docs/references/rule-provenance.md for hook-backed rules dropped as a third copy of history already in hook docstrings and register rows; kept only for hookless rules.
- [ci-7, ci-8] Dropping the push:main CI runs dropped: with concurrent worktree PRs and CI-green auto-merge, the push run is the only full-suite pass over the merged tree; made cheaper instead.
- [truth-12, exposure-10] truth-12 option (b) (gitignored graph-allowlist.yaml read by tools) dropped: cannot feed the Fly apps or CI and worktrees carry no gitignored files; exposure-10 option 2 (designate context/portable as the WW public home) dropped as the committer-is-the-only-reviewer trap.
- [harness-8] Hand-written anchored regex with a context list in each hook dropped in favour of sharing deploy-consumer-gate's existing executed_view.
- [ctx-5] 110-char per-line ceiling dropped (would flag 148 of 185 index lines); 155 chars + total headroom used.
- [machine-11, ci-10, ledger-10] Private 011matthias remote for the Hero node dropped (owner's D1 puts it under UnpauseAI from a squashed history); a 10-minute local scheduled probe as primary dropped (laptop sleeps; task already red); retiring comd_review outright dropped (friction-watch's cadence clause and weekly_synthesis cite it); kept as a thin wrapper.
- [ledger-9, ci-6] Impact restated: GitHub Actions minutes are free on a public repo; the saving is session wait time and unlanded ledger rows, which D6 and item 22 address.

## Expected effects (synthesis agent)

Per PR: docs/client PR wall-clock from 2:50-3:35 (11:52 outliers) to about 0:45 after items 1-2, with no second matrix on re-push (15 of 91 branches ran 2-3 times); p1 recon PR from ~7 min to 3-4 min after item 28; D6 removes the in-session CI wait entirely on ~60 of every 108 PR runs (checkpoint tails), roughly 6-8 hours of session time a month. Per session: rules load drops ~13.3k tokens for every non-Brisken session (item 6a) and ~10k more for all sessions after the trims (6b), paid ~4 times per session with subagents; CLAUDE.md ~600 tokens; cd-guard ~6k tokens per 300-call session; a Brisken /comd_resume from a measured ~170k tokens to under 70k (items 7-8), then under 50k once D9/D10 cut the 1.5 MB status pair and the four memory ledgers (~117k tokens of memory reads); MEMORY.md regains ~40 lines / 2k tokens of headroom. Per tool call: item 27 removes the uv launcher from 12 hook processes per Bash call and 9 per Write/Edit (~100 ms each, measured 176-422 ms per gate). Files and folders: D1 removes ~250 tracked files (Trigger/Railway lane, 119 template files, DELIVERY-GUIDE, handoffs, .agents); D12 303 vendored skill files; item 29 deletes 11 stub skill dirs (62 files relocated) and 5 renamed; D4 ~40 superseded files plus workspace/playgrounds, scripts/, onepilot-site/, rome-hub/; D3 moves ~110 files of client/personal data out of the public tree (579 WW addresses, 25+ named leads, the assessment results, the owner's address) and deletes the two root PNGs and tok.txt refs; D7 removes the last direct-push-to-main path. Disk and git: D5 reclaims 6-7 GB of dead worktrees plus ~1 GB of detached snapshots, cuts `git worktree list` from 80 to ~20 and remote/local branches from 436/442 to about 25/20, and fetch.prune keeps it there. Ledger: the 8 stranded PRs land (item 4), INDEX.md stops conflicting (D15), the register becomes rotatable (item 11), personal sessions stop reaching the public ledger (item 10). WW migration: items 14, 16-20 and D16 give the import a defined home (flat .n8n.json exports, automations/tools with a manifest, automations/tests with its own path-filtered CI, context/.env + .env.example, a pii push gate that fires at 3 consumer addresses) before any WW file is pushed.

## Section G: gaps raised by the completeness critic

### G1: An entire client nobody enumerated: workspace/clients/Jochen Projekt/ (ConVista/Jochen treasury assessments) with a live Fly app, wholly gitignored

C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\clients\Jochen Projekt\ holds 4,642 files / 238 MB: specs, deliverables, context, project-knowledge, five company folders (Alfred Ritter, CITTI, Nagarro SE, NextDecade, STAEDTLER) and automations/treasury-assessment (26 src modules, 19 tests, 9 site-host modules; site-host/fly.toml app = "one-assessment-demo", which memory records as LIVE). .gitignore:154 ignores the whole folder, code included, so the app's source has no commit, no PR, no CI and one disk copy; last activity 2026-09-07. Eight memory files reference it; README, CLAUDE.md, PROJECT-BOUNDARIES.md, every command and rule do not. Every lens treated the client set as brisken / meji / WW, and the 'code public, data private' split being designed for WW already has an unaddressed precedent here.

How to check: git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 check-ignore -v "workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/app.py"; fly status -a one-assessment-demo (is it serving, from which image/commit) and compare with the untracked tree; find the folder's newest mtimes to decide active vs dormant; then decide the WW-style split (code tracked under a slug without a space, confidential material under context/) or an explicit archive decision recorded in a status file.

Verified 2026-10-28: CONFIRMED. `.gitignore:154` ignores the whole folder, `git ls-files "workspace/clients/Jochen Projekt"` returns 0 files, and `automations/treasury-assessment/` (pyproject.toml, data/, inbox/, out/, DESIGN.md, FEEDBACK-REGISTER.md) has no commit anywhere; memory records one-assessment-demo.fly.dev as LIVE. Becomes D17.

### G2: The gitignored context/ trees are a single unversioned copy that no worktree carries, and tools reach back into the primary clone by hardcoded path

workspace/clients/brisken/context is 800 MB / 2,835 files (lead-generation 533 MB, expense-reconciliation 131 MB, brand 62 MB, decks 52 MB); meji 8 MB / 194 files; WW adds 582. It holds comms-log.md (the canonical client record per rule_no_file_bloat), .env, fixtures and test data, and it exists only at C:\Users\neuma_p1qrsic\Repo\agentic-ops1: the brisken context dir is MISSING in agentic-ops1-build2, -build2b, -audit and -base. No tool in tools/ and no rule mentions backing it up, and no scheduled task does. Meanwhile machine-12 wants sessions in worktrees; a worktree session following /comd_resume has no context, so it either reaches into the primary by absolute path (19 tracked files already hardcode Repo/agentic-ops1, e.g. tools/weekly_synthesis.py, tools/send_email.py, tools/sync-hours.py, lead-desk migrate.py and the recon-notify runner's CLONE.parent/'agentic-ops1' fallback at tools/brisken-recon-notify-run.py:47) or works blind. One disk loss or one worktree prune that catches the wrong path removes the only copy of the client record.

How to check: for w in $(git -C C:/Users/neuma_p1qrsic/Repo/agentic-ops1 worktree list --porcelain | awk '/^worktree/{print $2}'); do test -d "$w/workspace/clients/brisken/context" && echo "$w"; done (expect only the primary); grep -rlE 'Repo[/\\]{1,2}agentic-ops1\b' tools .claude workspace --include=*.py --include=*.cmd --include=*.ps1; confirm no backup covers the path (Get-ScheduledTask actions, OneDrive scope, File History); then pick the mechanism: a private git repo for context/ with its own remote, or a documented junction convention that worktree creation hooks apply.

Verified 2026-10-28: CONFIRMED. 80 worktrees listed; only the primary clone has `workspace/clients/brisken/context` (800 MB); no tool, task or rule backs it up. Becomes D18.

### G3: The live product's code shape: one 20,332-line service.py that tripled in 60 days, edited by concurrent sessions

workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py is 949 KB / 20,332 lines (7,202 lines 60 days ago; 199 commits touching it in 60 days on 17 distinct days); app.py 7,464 lines, intake_mail.py 4,986, tests/test_intake_mail.py 179 KB. The lenses measured the status files, the prompt ledger and the test job's runtime, never the module layout. The Read tool caps at 2,000 lines, so no session can load the hot file; every item in the 200-255+ queue is grep-plus-offset editing; several sessions in worktrees (the stated working model) will conflict on the same file; the 6:49 serial test job (ci-8) partly follows from this shape.

How to check: wc -l on the three files; git log --since=60.days --format=%h, <service.py> | wc -l; gh pr list --state merged --search "merged:>2026-09-28" --json number,files and count PRs whose diff touches service.py, plus rebase conflicts on it in the session logs; then a split by domain (routes / view builders / store / mail intake) sized so each module fits one Read, before the next item batch rather than after.

Verified 2026-10-28: CONFIRMED on size: service.py 20,332 lines, app.py 7,464 (intake_mail.py not at the stated path, not re-measured). Client work: filed as a p1 backlog note below, not a layout item.

### G4: Scheduled jobs on this machine: nobody read their outcomes

Get-ScheduledTaskInfo today: BriskenReconNotify (every 15 min from C:\Users\neuma_p1qrsic\Repo\agentic-ops1-notify) LastTaskResult=1, with exit=1 lines at 02:02, 12:30 and 12:32 on 10-28 in agentic-ops1\.scratch\recon-notify-runs.log interleaved with exit=0; MejiReplySLA (4-hourly, in the Christmas season) LastTaskResult=0x800710E0 with DisallowStartIfOnBatteries=True, last flag file workspace/clients/meji-media/context/reply-flags/2026-10-15.md; AgenticOpsWeeklySynthesis LastTaskResult=1 on 10-26, also battery-disallowed, last docs/reviews file 2026-07-12. homes-12 and machine-6 covered where the jobs run, not whether they succeed; the notify runner's own docstring says LastTaskResult is the only signal the scheduler shows, and nothing in the repo reads it. Two client-facing monitors fail or skip silently.

How to check: Get-ScheduledTask | Where TaskPath -notlike '\Microsoft\*' | ForEach { $_ | Get-ScheduledTaskInfo } for LastTaskResult and NumberOfMissedRuns; uv run --directory C:\Users\neuma_p1qrsic\Repo\agentic-ops1-notify tools/brisken-recon-notify-run.py --once --dry-run; uv run <meji context>\analysis-scripts\meji_reply_sla_daily.py --check (read-only, no email); then one tracked tool that lists every repo task with its last result, surfaced by doctor.py or the SessionStart sweep, and clear the battery condition on the two monitors.

Verified 2026-10-28: CONFIRMED (Get-ScheduledTaskInfo, 2026-10-28 about 14:10): BriskenReconNotify LastResult 0x1 at 14:02; AgenticOpsWeeklySynthesis 0x1 on 10-26 (battery-disallowed); MejiReplySLA 0x800710E0 at 13:30 (refused, battery-disallowed); Brisken-Oct1-Invoice-And-Retainer 0x800710E0 on 10-02; PrototypeFund-Window-Opens 0x800710E0 on 10-02; RepoSweep 0x0 at 02:30; MejiWeeklyReview 0x0; VintedWatcher running. Becomes W1-32.

### G5: Windows runtime of the tool layer: locale-decoded subprocess output crashes the SessionStart status sweep, and CI runs where the failure cannot happen

uv run tools/project_status.py --sweep-stale dies with UnicodeDecodeError ('charmap' codec, byte 0x8d) in a subprocess text=True read at project_status.py:343; 50 text=True calls without encoding= across 34 files in tools/ and .claude/hooks/ (tests excluded); .claude/settings.json sets PYTHONIOENCODING=utf-8 but not PYTHONUTF8=1, so pipes decode as cp1252. Local uv runs CPython 3.14.4 while ci.yml pins 3.12 on Ubuntu with a UTF-8 locale, so the 1,739-test hooks suite is green on a platform where this class of crash is impossible. fit-8 judged the sweep's signal as noise; it does not complete here at all, and doctor.py counts it ok=True. Any hook or tool that shells out to git or gh on German content (WW is German) can die the same way, silently, fail-open.

How to check: run the sweep from C:\Users\neuma_p1qrsic\Repo\agentic-ops1 and read the traceback; grep -rn 'text=True' tools .claude/hooks --include=*.py | grep -v 'encoding=' | wc -l; differential: add PYTHONUTF8=1 to settings.json env, re-run, confirm clean; add a windows-latest leg (or an LC_ALL=C leg) to the hooks job so the suite can go red for this.

Verified 2026-10-28: CONFIRMED. `uv run tools/project_status.py --sweep-stale` from the audit checkout prints a UnicodeDecodeError traceback ('charmap' codec, byte 0x8d) and exits 0. Becomes W1-31.

### G6: Permission posture: whether the gates' 'ask' decisions prompt at all under bypassPermissions, and a 132 KB user allow list

.claude/settings.json sets permissions.defaultMode=bypassPermissions with blanket allows for Bash/Edit/Write; ~/.claude/settings.json (131,842 bytes) carries 697 allow rules (390 PowerShell, 239 Bash, average 166 chars, longest 1,017, several naming 'Jochen Projekt' paths), 0 deny, skipDangerousModePermissionPrompt=true. The hook log records 804 no-auto-commit-gate ASK, 452 instantly-invasive-gate ASK, 132 git-restore-gate ASK, 64 git-stash-gate ASK, 48 write-shrink-gate ASK, 32 ruff-push-gate ASK; rule_no_auto_commit asserts 'the agent cannot bypass the floor; the user authorizes via the permission prompt'. No lens verified that a hook 'ask' produces a prompt in bypass mode; if it degrades to allow, every one of those ~1,600 stops was theater, and the 697-rule allow list is dead weight parsed every session either way.

How to check: differential probe in an interactive session with the project's default mode: dirty a scratch file, run git stash push -m probe (the stash gate should stop you), then git stash list to see whether it ran anyway; pair the ASK line in .claude/hooks/hook-log.txt with what the next line from the same call shows; read the Claude Code hooks reference for 'ask' under bypassPermissions; then either take the floor gates off bypass (allowlist the read-class tools, leave Bash on default) or convert the floor to deny-with-named-override, and prune the user allow list.

Verified 2026-10-28: FACTS CONFIRMED, QUESTION OPEN. `.claude/settings.json` defaultMode=bypassPermissions; `~/.claude/settings.json` has 697 allow rules, 0 deny, skipDangerousModePermissionPrompt=true. Whether a hook `ask` prompts in this mode needs the interactive differential probe. Becomes W1-0.

### G7: MCP server fleet: half of it dead at every session start, all of its tool definitions loaded regardless of client

.mcp.json in the primary clone (per machine, untracked): make-meji-media (57 tools), github (46), playwright (25, pinned to --cdp-endpoint :9222), context7, vercel (needs auth every session), firebase (npx -y firebase-tools@latest mcp, times out at 30 s), serena (uvx --from git+... serena, times out at 30 s); user scope: n8n at https://unpauseai1.app.n8n.cloud/mcp-server/http, which answers ENDPOINT_NOT_FOUND. With the claude.ai connectors (zapier 19, chrome 22, jotform 11, docs 8) about 190 tool definitions sit in every session whether it is Brisken, WW or personal. onboard-3/4 examined how the n8n entry is shaped, not whether anything connects; ctx measured rules and memory, not tool definitions. The next registration is WW's per-client n8n MCP, and the existing n8n entry is dead.

How to check: claude mcp list (state and connect time per server); /context in a fresh interactive session for the MCP-tools token line; curl -sI https://unpauseai1.app.n8n.cloud/mcp-server/http; then drop firebase/serena/vercel/n8n or scope servers per project (.mcp.json per worktree is already per machine), and keep make-meji-media out of non-Meji sessions.

Verified 2026-10-28: CONFIRMED by the harness's own report at this session's start: firebase CONNECT_TIMEOUT (30 s), serena CONNECT_TIMEOUT, n8n ENDPOINT_NOT_FOUND at unpauseai1.app.n8n.cloud, vercel needs auth; make-meji-media and github load in every session. Becomes W1-36.

### G8: Backend-to-SPA contract has no shared schema; it is a prose doc plus one hand-maintained test

tests/test_view_contract.py (107 KB) states it: 'The SPA is a separate repo with no type-check against the live API'; the 2026-08-22 React error #31 (parse_issues shipped as objects, SPA typed string[]) and the 2026-08-24 'Arriving'/blank Month incident in rule_behaviors came from exactly this seam. The contract lives in expense-reconciliation/docs/api-contract.md and in that test; the Lovable repo 011matthias/brisken-expense-review is not cloned beside this repo (ls C:\Users\neuma_p1qrsic\Repo). fit-10 covered the prompt-file bookkeeping, not the mechanism. Product-style development with a numbered queue changes payloads weekly, and each change depends on the same session remembering to update the test.

How to check: diff docs/api-contract.md against the view payloads app.py emits and against the SPA's TypeScript types (clone the SPA repo, grep its payload types); count backlog items in status/p1-improvement-backlog.md whose fix needed a Lovable prompt AND a backend change; decide on generated types (OpenAPI from the FastAPI app, TS types committed to the SPA) so the contract is a build artifact, not a memory.

Verified 2026-10-28: NOT RE-VERIFIED this session (client-side mechanism). Filed as a p1 backlog note below.

### G9: Per-checkout state sprawl nobody prunes, and a rule whose reference implementation lives only in .scratch

Primary .scratch: 843 MB / 7,750 files (1,438 .py, 1,330 .png, 821 .json, a Chrome profile oa-chrome-profile with live cookies, cdp-recon 221 MB); 43 of 88 checkouts under C:\Users\neuma_p1qrsic\Repo carry their own .scratch; .playwright-mcp 232 MB / 502 files; .claude/hooks/hook-log.txt 18.2 MB / 195k lines since 2026-05-26, never rotated. rule_brisken_graph_send_by_id.md:91 names .scratch/ga_send_wave.py as THE reference sender pattern ('reuse that shape; do not hand-roll a looser one'); it exists only in the primary's .scratch, no tracked copy. W1/W2 route ephemera to .scratch by design and no lens asked what happens after; the machine-1 worktree prune will delete scratch trees that rules and sessions still point at.

How to check: du -sm C:/Users/neuma_p1qrsic/Repo/agentic-ops1*/.scratch; grep -rn '\.scratch/' .claude/rules .claude/commands .claude/skills for pointers into scratch; find .scratch -mtime +30 -type f | wc -l; promote ga_send_wave.py into the lead-desk package or tools/, rotate hook-log.txt, and give the sweep a dated purge for .scratch and .playwright-mcp.

Verified 2026-10-28: CONFIRMED. Primary `.scratch` 843 MB; `.claude/hooks/hook-log.txt` 18,249,124 bytes; `.scratch/ga_send_wave.py` exists only there. Becomes W1-34.

### G10: Plugin layer: six enabled plugins, one not installed, ~48 skills, 24 third-party agents and 12 commands in every session roster

.claude/settings.json enabledPlugins lists productivity-suite@riccardovandra (installed nowhere under ~/.claude/plugins, a dangling enable), playground (11 skills), document-skills (20 skills), planning-with-files (17 skills including plan-ar/de/es/zh/zht variants, 12 commands; its hooks.json files target Codex/Cursor and fire nowhere here), voltagent-meta + voltagent-research (24 third-party agents, marketplace last updated 2026-06-06). harness-4/12/13 inventoried .claude/ and skills-lock.json only; ctx-1..12 costed rules, memory and hooks only. Every skill description and agent entry is system-prompt context in every session and subagent, and none of the language variants or voltagent agents serve the work ahead.

How to check: claude plugin list; count SKILL.md under ~/.claude/plugins/cache/*/*; /context for the skills and agents share; grep ~/.claude/agentic-ops-telemetry/skill-runs.jsonl for plan-*, playground and voltagent invocations (expect none); disable the unused entries and remove the dangling one.

Verified 2026-10-28: CONFIRMED. enabledPlugins names productivity-suite@riccardovandra; `~/.claude/plugins/cache` holds only anthropic-agent-skills, claude-plugins-official, planning-with-files, voltagent-subagents. Becomes D19.

### G11: doctor.py, the one health aggregator, is unscheduled and trusts exit codes that lie

README advertises uv run tools/doctor.py as the full battery; nothing runs it (no hook, no task, no CI step). Run today on the audit checkout: red_count 1; status-sweep reported ok=True with a UnicodeDecodeError traceback in its own tail; client-pages FAIL with 1 HIGH and 263 MEDIUM across 264 pages of a platform tree that no longer deploys; friction-watch shows agent-deferred concentration at 98 rows. truth-7..14 checked the README's command claims, not this one. The battery is exactly the instrument that would have surfaced the scheduled-job failures, the Windows decode crash and the dead MCP entries, had it run and had it read tracebacks.

How to check: uv run tools/doctor.py --format json and compare each check's ok with its tail; make a traceback in tail non-ok; add checks for scheduled-task results and MCP liveness; run it from the RepoSweep task with a red-count threshold that lands in the friction register.

Verified 2026-10-28: CONFIRMED. No reference to doctor.py in wire-hooks.py or repo-sweep.py; no scheduled task runs it. Becomes W1-33.

### G12: The CI secret scan runs gitleaks with default rules and no repo configuration

.github/workflows/ci.yml:63-69 uses gitleaks/gitleaks-action@v2; there is no .gitleaks.toml. The token shapes this repo actually handles (Make MCP URL tokens, Zoho refresh tokens, Instantly keys, Graph client secrets, and after the import Hero and n8n keys under the suffixed-name .env convention onboard-5 describes) only match gitleaks' generic rule when the variable name happens to contain a keyword. exposure-11 and machine-8 examined file-name globs and unscanned branches; nobody validated that the content scanner fires on the shapes that matter, and the tok.txt commit machine-8 names is a known positive to test against.

How to check: differential probe: run gitleaks locally with the default config against the branch holding tok.txt and against a scratch file containing one Make MCP URL and one HERO_* key in the WW .env shape; if any known positive is silent, add .gitleaks.toml with repo-specific rules and an allowlist for the test fixtures, and make the CI job use it.

Verified 2026-10-28: CONFIRMED. No `.gitleaks.toml`; ci.yml:63-69 runs gitleaks/gitleaks-action@v2 with default rules. Becomes W1-35.

## Section G verification and additions (2026-10-28, this session)

The critic's twelve gaps were checked live before this plan was written; the result sits on each G entry above. They add seven mechanical items and three decisions. One more observation from this session's own friction candidates belongs to W1-26: seven of the ten candidates were false positives of no-auto-commit-gate ("red-merge") and instantly-invasive-gate on read-only audit commands that merely quoted gate source or printf'd hook payloads; W1-26's executed_view should cover those two gates as well, so quoted text is never classified as ship-class or invasive.

### W1-0 [G6] cost S, the first ten minutes of the next session

Status: done PR #1654 (2026-10-28): a hook `ask` is a real prompt under `auto`, the mode all 40 recent sessions ran in; git-stash-gate held `git stash push` 2 h 19 min (ASK 14:53:28, first line ran 17:13:02) despite the project's blanket `Bash` allow. No session ever ran in bypassPermissions. No deny conversion needed. Allow-list prune dropped by the owner (AskUserQuestion 2026-10-28: tidiness, not safety).

Depends on: none

Action: Differential probe of a hook `ask` under `bypassPermissions`, in an interactive session on the project's default mode: dirty a scratch file, run `git stash push -m probe` (git-stash-gate.py returns ask), then `git stash list`. If the stash exists and no prompt appeared, `ask` degrades to allow in this mode and the ~1,600 ASK decisions in `.claude/hooks/hook-log.txt` (804 no-auto-commit, 452 instantly-invasive, 132 git-restore, 64 git-stash, 48 write-shrink, 32 ruff-push) were never stops: convert the floor gates to `deny` with the named-override path and take Bash off the blanket allow. If a prompt appears, record that in rule_no_auto_commit in one line. Either way prune the 697-rule allow list in `~/.claude/settings.json` (0 deny rules, 131 KB, several naming `Jochen Projekt` paths) down to read-class commands.

Why: rule_no_auto_commit asserts "the user authorizes via the permission prompt"; nothing has verified that the prompt exists under the project's permission mode. Verified 2026-10-28: `.claude/settings.json` defaultMode=bypassPermissions; user settings 697 allow / 0 deny; skipDangerousModePermissionPrompt=true. This session ran in auto mode and the harness classifier did hold tool calls for approval, so a prompt path exists; whether a hook `ask` reaches it is the open question.

Verify: the probe result written into the next checkpoint; allow-rule count under 100 after pruning.

Files: `.claude/settings.json`, `~/.claude/settings.json`, `.claude/hooks/no-auto-commit-gate.py`, `.claude/rules/rule_no_auto_commit.md`

### W1-31 [G5] cost S

Status: done PR #1669 + PR #1677 (2026-10-29). #1677 converted the three job scripts after the owner's yes naming BriskenReconNotify, RepoSweep and AgenticOpsWeeklySynthesis; DEFERRED is empty. weekly_synthesis.send() also passes PYTHONIOENCODING=utf-8 to send_email.py, whose stdin would otherwise decode the UTF-8 body as cp1252. Batch-3 notes on #1669 follow. 92 call sites now pass `encoding="utf-8", errors="replace"` inline (tools/ are standalone uv scripts, so no shared import from .claude/hooks); doctor.py marks an exit-0 check with a `Traceback` header not-ok; the CI leg is tools/tests/test_text_encoding.py (AST scan, multi-line calls included, plus a 0x8d round trip), proven with regress_check. The sweep completes from the worktree. Left out under the client-ops guard and listed in the test's DEFERRED set: tools/brisken-recon-notify-run.py:154 (BriskenReconNotify), tools/repo-sweep.py:354 (RepoSweep), tools/weekly_synthesis.py x4 (AgenticOpsWeeklySynthesis); the auto-mode classifier also refused the edit without an owner yes. After-check: notifier clone at 27348341, exit 0 at 11:47Z. No global PYTHONUTF8.

Depends on: none

Action: Add `PYTHONUTF8=1` to the `.claude/settings.json` env block beside PYTHONIOENCODING; replace the 50 `text=True` subprocess calls without `encoding=` across tools/ and .claude/hooks/ with one helper (`encoding="utf-8", errors="replace"`) in `.claude/hooks/_shell.py`; doctor.py marks a check not-ok when its tail contains `Traceback`; add a `windows-latest` leg (or an `LC_ALL=C` + `PYTHONUTF8=0` leg) to the CI hooks job so this class can go red.

Why: `uv run tools/project_status.py --sweep-stale` dies with UnicodeDecodeError ('charmap' codec, byte 0x8d) at project_status.py:343 and exits 0, so the SessionStart status sweep has never completed on this machine, and every gate that shells out to git or gh over German content (WW) can die the same silent way.

Verify: the sweep completes from the primary clone; a test feeds a 0x8d byte through the helper; `grep -rn 'text=True' tools .claude/hooks --include=*.py | grep -v encoding=` = 0; the new CI leg green.

Files: `.claude/settings.json`, `tools/project_status.py`, `tools/doctor.py`, `.claude/hooks/_shell.py`, `.github/workflows/ci.yml`, `tools/tests/`

### W1-32 [G4] cost S

Status: todo. Found 2026-10-28: BriskenReconNotify had exited nonzero on ~3 of 4 runs every day since at least 10-16 (SSLEOFError on /api/login): this machine's IPv6 route to Fly drops the TLS handshake (IPv4 4/4, IPv6 2/4 and 0/4). Notifications were delayed, never lost (state advances only after a send). Fixed PR #1663 (owner yes): IPv4 pin in main(); dry runs 0/3 before, 3/3 after; 13 of 13 scheduled runs exit 0 through 2026-10-29 10:32Z. The rest of W1-32 (the other jobs' outcomes) is still todo.

Depends on: W1-24

Action: `tools/scheduled_tasks.py --check` (W1-24) also reads LastTaskResult, LastRunTime and NumberOfMissedRuns per registry task via `Get-ScheduledTaskInfo`, prints non-zero results once per day at SessionStart and in doctor; clear `DisallowStartIfOnBatteries` on MejiReplySLA and AgenticOpsWeeklySynthesis with `Set-ScheduledTask`; read `.scratch/recon-notify-runs.log` for BriskenReconNotify's exit-1 runs and fix the cause; run AgenticOpsWeeklySynthesis by hand and fix its 0x1.

Why: measured 2026-10-28: BriskenReconNotify 0x1 (14:02), AgenticOpsWeeklySynthesis 0x1 (10-26), MejiReplySLA 0x800710E0 (refused, on battery, 10-28 13:30), Brisken-Oct1-Invoice-And-Retainer 0x800710E0 (10-02), PrototypeFund-Window-Opens 0x800710E0 (10-02); RepoSweep and MejiWeeklyReview 0x0. Two client-facing monitors fail or skip and nothing in the repo reads the result.

Verify: `uv run tools/scheduled_tasks.py --check` lists every registry task with its result; both monitors show 0x0 after one scheduled run; a test with a stubbed PowerShell call.

Files: `tools/scheduled_tasks.py`, `tools/fixtures/scheduled-tasks.json`, `tools/doctor.py`, `tools/wire-hooks.py`, `tools/brisken-recon-notify-run.py`

### W1-33 [G11] cost S

Status: todo

Depends on: W1-31, W1-32

Action: RepoSweep runs `doctor.py --format json` after sweep_repo(); a check is not-ok when its tail contains `Traceback`; new checks for scheduled-task results (W1-32), MCP liveness (W1-36) and the open-PR line (W1-22); a red count above threshold appends a register row through checkpoint_scaffold's register API; the client-pages check drops `platform/public` (no longer deploys) or narrows to `platform/public/docs`.

Why: README advertises doctor.py as the battery and nothing runs it; today it reports status-sweep ok=True with a traceback in its own tail and 264 platform pages that no longer deploy.

Verify: `uv run tools/doctor.py --format json` shows status-sweep ok=false until W1-31 lands; the RepoSweep log shows the doctor run; test_doctor.py traceback case.

Files: `tools/doctor.py`, `tools/repo-sweep.py`, `tools/tests/test_doctor.py`

### W1-34 [G9] cost S

Status: todo

Depends on: W1-24

Action: rotate `.claude/hooks/hook-log.txt` at 2 MB (keep one `.1`) from the SessionStart wiring; repo-sweep gets a dated purge of `.scratch/` and `.playwright-mcp/` files older than 30 days, dry-run listing first, never a Chrome profile directory a watcher task points at; promote `.scratch/ga_send_wave.py` into `workspace/clients/brisken/lead-desk/` as the tracked reference and repoint rule_brisken_graph_send_by_id.md:91; W1-24's prune prints each tree's .scratch size before removal.

Why: primary .scratch is 843 MB / 7,750 files including a Chrome profile with live cookies; hook-log.txt is 18.2 MB and has never rotated; the rule's only reference implementation sits in an ignored directory the prune would delete.

Verify: hook-log under 2 MB after a session start; `git ls-files | grep ga_send_wave` non-empty; the sweep dry-run lists purge candidates; a rotation test.

Files: `tools/wire-hooks.py`, `tools/repo-sweep.py`, `.claude/rules/rule_brisken_graph_send_by_id.md`, `workspace/clients/brisken/lead-desk/`

### W1-35 [G12] cost S, lands with W1-14

Status: done PR #1664 (2026-10-29). Probe, gitleaks 8.30.1 defaults: caught Graph, Hero, Instantly, Zoho only through KEY/TOKEN/SECRET names and a realistic n8n key via the jwt rule; missed the Make MCP URL (`<zone>.make.com/mcp/u/<UUID>/stateless`) and tok.txt (57415748). New rules make-mcp-url, zoho-oauth-token, token-named-file catch both; CI log shows "using gitleaks config from GITLEAKS_CONFIG". Verify deviation: main's history is NOT 0, it holds 57 findings under the default and the new config alike (40 airtable-api-key on herbox-sweden Airtable IDs, 17 generic), so the config adds none and CI only scans new commits. Not done: the push gate running gitleaks locally (no gitleaks on the machine; probe used a scratch download). tok.txt's shape (8 + 73 lowercase alnum, one dot) matches no common token format; identifying the service stays with D3(g).

Depends on: none

Action: Differential probe: run gitleaks locally with the default config against the commit holding tok.txt (57415748) and against a scratch file carrying one Make MCP URL token and one `HERO_API_KEY_*=` line in the WW .env shape; for every silent positive add a rule to a new `.gitleaks.toml` (Make MCP URL, Zoho refresh token, Instantly key, Graph client secret, n8n and Hero keys under the suffixed-name convention) with an allowlist for tools/tests and fixtures; point the CI job at it; W1-14's pii push gate runs the same config locally before the push.

Why: the only content scanner runs after the push is public, with default rules that match a secret only when the variable name carries a keyword. Verified 2026-10-28: no `.gitleaks.toml`; ci.yml:69 runs gitleaks/gitleaks-action@v2 with defaults.

Verify: gitleaks exits 1 on the tok.txt commit and on the scratch file with the new config, 0 on main; the CI job passes `--config .gitleaks.toml`.

Files: `.gitleaks.toml`, `.github/workflows/ci.yml`, `.claude/hooks/pii-push-gate.py`

### W1-36 [G7] cost S, lands with W1-17

Status: done except the fresh-session Verify (2026-10-29). The rest landed with W1-17 (#1684): vercel scoped to platform/proposal worktrees, per-client rendering, doctor check `mcp-health` (`mcp_config.py --mcp-health`, names only, "Needs authentication" is not a failure; read 2026-10-29: 7 connected, 0 failed). Still to read: a fresh session start in the primary reports no failed MCP connection (this session's start showed a transient context7 CONNECT_TIMEOUT that `claude mcp list` later read as connected). Earlier: partly done 2026-10-29 (owner yes, AskUserQuestion: "Remove all three"). Removed via the `claude mcp remove` CLI: user-scope `n8n` (~/.claude.json) and project-scope `firebase` + `serena` (the primary's gitignored .mcp.json, which now holds context7, github, make-meji-media, playwright, vercel). Backups: the primary's `.scratch/claude.json.pre-w1-36-2026-10-29` and `.scratch/mcp.json.pre-w1-36-2026-10-29`. Still todo with W1-17: `vercel` only in a platform worktree, per-client rendering (owner chose "Union in primary": the primary gets every client's servers, worktrees get per-client sets), the doctor `claude mcp list` check. Verify (no failed MCP connection at start) is read at the next fresh session.

Depends on: W1-17

Action: remove the user-scope `n8n` entry (ENDPOINT_NOT_FOUND at unpauseai1.app.n8n.cloud) and the `firebase` and `serena` entries (30 s connect timeouts at every start) from the primary's `.mcp.json`; `vercel` only in a platform worktree; W1-17's mcp_config.py renders per client so a Brisken or WW session carries no make-meji-media (57 tools) and a Meji session no n8n-warme-wimmer; `claude mcp list` becomes a doctor check (W1-33).

Why: the harness reported at this session's start: firebase CONNECT_TIMEOUT, serena CONNECT_TIMEOUT, n8n ENDPOINT_NOT_FOUND, vercel needs auth; about 190 tool definitions load into every session regardless of client, and the next registration is WW's per-client n8n server.

Verify: a fresh session start reports no failed MCP connection; the `/context` MCP line drops; W1-17's test renders the per-client set.

Files: `.mcp.json` (untracked, per machine), `tools/mcp_config.py`, `tools/doctor.py`

### D17 [G1] cost M

Status: decided 2026-10-28 (owner): backup only; the Jochen code stays untracked and joins the D18 backup. The move, CI and status-file Action is dropped.

Depends on: W1-14, W1-35

Decision and recommendation: track the code now. `workspace/clients/Jochen Projekt/` (4,642 files / 238 MB) is ignored whole by `.gitignore:154`, code included: `automations/treasury-assessment` (26 src modules, 19 tests, a site-host whose fly.toml names app one-assessment-demo, recorded in memory as LIVE) has no commit, no PR, no CI and one disk copy. Recommendation: move the code to `workspace/clients/jochen/automations/treasury-assessment/` (slug without a space), the confidential material (five company folders, inbox/, out/, data/, assessments) to that client's gitignored `context/`, scan with pii_scan and gitleaks before the first push, add a status file: the same split as WW. Consequence of no: a live client app stays one disk failure from gone; at minimum it joins the D18 backup today.

Action: after the yes: `git mv` on a `client/jochen/track-code` branch; `.gitignore` line 154 becomes `workspace/clients/jochen/context/`; pyproject and tests run in CI path-filtered in the W1-19 shape; the fly.toml app name checked against `fly status -a one-assessment-demo`; PROJECT-BOUNDARIES, README and CLAUDE.md name the client.

Verify: `git ls-files workspace/clients/jochen | wc -l` > 0 with `pii_scan.py` at 0 hits; CI runs its tests; after the next deploy `fly status` shows an image built from a tracked commit.

Files: `.gitignore`, `workspace/clients/jochen/`, `README.md`, `.github/workflows/`

### D18 [G2] cost M

Status: decided 2026-10-28 (owner): private repo 011matthias/agentic-ops1-context, nightly via RepoSweep, text and small files with version history; .env and key files EXCLUDED; binaries above the size cap not covered.

Depends on: none

Decision and recommendation: the gitignored context/ trees (brisken 800 MB / 2,835 files including comms-log.md and .env; meji 8 MB; Jochen 238 MB; WW 582 files incoming) exist only in the primary clone; none of the 80 worktrees carries them and no task, tool or rule backs them up (verified 2026-10-28). Recommendation: a private repo `011matthias/agentic-ops1-context` for text and small files (binaries above a size cap excluded), pushed nightly by the RepoSweep task, plus D11's junction tool so worktree sessions see the same directory. Alternative: a nightly `robocopy /MIR` to an encrypted off-machine location. Consequence of no: one disk loss removes the canonical client record and every credential.

Action: after the choice: `tools/context_backup.py` (dry-run, size report, push) wired into repo-sweep; the 19 tracked files that hardcode `Repo/agentic-ops1` (weekly_synthesis.py, send_email.py, sync-hours.py, lead-desk migrate.py, brisken-recon-notify-run.py:47) read `AGENTIC_OPS_PRIMARY` or main_worktree() instead.

Verify: the private remote holds today's comms-log.md; a restore into a scratch directory matches `diff -rq`; `grep -rlE 'Repo[/\\]{1,2}agentic-ops1\b' tools .claude workspace --include=*.py` = 0 outside the helper.

Files: `tools/context_backup.py`, `tools/repo-sweep.py`, `tools/worktree_add.py` (D11)

### D19 [G10] cost S

Status: todo

Depends on: none

Decision and recommendation: remove the dangling `productivity-suite@riccardovandra` enable (absent from `~/.claude/plugins/cache`, verified 2026-10-28), disable `voltagent-meta` and `voltagent-research` (24 third-party agents, 0 runs), the `planning-with-files` language variants and `playground` unless the owner uses them; keep `document-skills`. Consequence: a shorter skill and agent roster in every session and subagent; re-enabling is one settings line.

Action: grep `~/.claude/agentic-ops-telemetry/skill-runs.jsonl` for plan-*, playground and voltagent invocations (expect none), then edit `.claude/settings.json` enabledPlugins and confirm with `claude plugin list`.

Verify: `claude plugin list` shows only enabled-and-installed plugins; the session roster no longer lists voltagent agents.

Files: `.claude/settings.json`

### Client-backlog notes (not layout items)

- G3: `expense_recon/web/service.py` is 20,332 lines and app.py 7,464 (verified 2026-10-28). File a brisken p1 backlog item "split service.py by domain (routes, view builders, store, mail intake) so each module fits one Read", scheduled before the next item batch; it also shortens the 6:49 test job (W1-28).
- G8: the backend-to-SPA contract is prose plus one hand-maintained test (not re-verified this session). File a p1 item "generate the contract: OpenAPI from the FastAPI app, TypeScript types committed to the SPA repo".
- G4 side-finding for the owner: the `Brisken-Oct1-Invoice-And-Retainer` task was refused on 2026-10-02 (0x800710E0, on battery); confirm the October invoice and retainer step happened.

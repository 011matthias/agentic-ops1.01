# Checkpoint: System Health Check + Heal + Improvement Pass

**Date:** 2026-07-22
**Scope:** sys (repo-wide)
**Trigger:** owner ask: "strategize a way to run a health check and heal as well as system improvement as good as possible"

## Summary

Full three-phase pass: health-check battery over the whole checker estate, heal of everything mechanically healable, then seven approval-gated improvement builds. Ten PRs merged, all CI-green: #332 (Brisken batch off main), #306 (conflict-healed + merged), #337 (client pages 216 HIGH -> 0), #340 (platform content 92 HIGH -> 0), #338 (docx wrapper), #339 (branch-isolation-gate), #341 (artefact-weight), #342 (repo_freshness), #344 (doctor.py), #346 (skill-map pointers). Final dogfood: `tools/doctor.py --heal` runs the 12-check battery in ~15s, fully green.

## Health-check findings (morning baseline)

- Local main 24-25 behind origin; dirty tree mixed TWO batches (Brisken client work + G1 ledger) directly on main.
- Stale-INDEX clobber risk: local `docs/INDEX.md` derived from stale HEAD while upstream also changed it; a naive commit parented on origin/main would have reverted upstream rows.
- 216 HIGH on client pages (theme-boot), 92 HIGH platform content (em-dash substitutes + `UnpausAI` typo), 2 dead skill-map pointers, 1 stale spec (p2.ops1, 35d), 2 stale status files, 3 rule-banned stashes, ~112 branches (96 squash-merged), 13 worktrees (6 stale), CI green, no optimize lock.

## Heals executed

- **Brisken batch** -> `client/brisken/sap-onepagers-v2` via temp-index plumbing (zero shared-tree mutation), PR #332 merged. Validated first: validate-html 0 hits, demo-material PASS.
- **PR #306**: union-merged origin/main in its own worktree (GitHub server-side merge ignores `.gitattributes` union rules), pushed, merged on green.
- **Stashes**: all 3 archived to `.scratch/stash-archive-{0,1,2}-20260722.patch` (content preserved), then dropped. Stash state clean.
- **Branches**: 96 deleted, each only after tip SHA == merged-PR head cross-check (`gh pr list --state merged`). 22 kept.
- **Worktrees**: 7 removed (2 detached-merged, 4 merged-PR-clean, 1 post-#306), each after ancestor/clean checks. 13 -> 7 (now incl. active sibling worktrees).
- **Client pages**: `normalize-client-pages.py --apply` in worktree, 219 files, audit 216 HIGH -> 0, idempotence proven, PR #337.
- **Platform content**: strip-em-dash on 18 proposals + brand typo + canonical headings, validator 92 HIGH -> 0 (3 editorial MEDIUMs deliberately left), platform build green (33 proposal pages SSG), PR #340. Agent also found a validator blind spot: `check_em_dashes` skips lines starting with `*` (a JS-comment heuristic) so bold-opening markdown lines were never scanned — follow-up candidate.
- **Skill-map**: 2 dead pointers repointed to live exemplars, PR #346.

## Improvement builds (all merged)

1. **branch-isolation-gate** (#339) — PreToolUse(Write|Edit) advisory when a tracked `workspace/clients/{X}` file is edited off a client-X branch. The rule's twice-deferred structural candidate; trigger recurrence was today's dirty-main pile. 19 hooks wired now.
2. **repo_freshness** (#342) — stale-checkout sensor: SessionStart banner + adopters in `project_status --sweep-stale` and `check-index`. Generalizes PR #320. Live proof in-pass: a grep for #320's own code returned empty because this checkout predated it.
3. **artefact-weight** (#341) — validate-html warns on >20% + >10KB growth vs origin/main (the doubled-logo-PDF class). WARNING severity, exit-code contract unchanged.
4. **doctor.py** (#344) — one-command battery (12 checks, concurrent, JSON report to `.scratch/`), `--heal` (wire-hooks --ensure + normalize-pages), `--deep` (preflight --full). Replaces the ~14-command manual fan-out this very pass started with.
5. **docx-office.py** (#338) — uv wrapper for the docx skill; dep set verified against the actual plugin scripts (defusedxml + lxml; python-docx confirmed unnecessary).
6. **Shell allowlist** — investigation closed it: permission layer already maximal (blanket Bash + bypassPermissions + local flyctl entries). The residual blocks are the auto-mode safety classifier; the one lever (`autoMode.allow` in settings.json) was itself classifier-denied for agent self-edit, correctly. Proposed block handed to owner in the pass report. Register rows 512/547/560 -> resolved-as-investigated, user action optional.
7. **Session-log fan-out** — in flight at checkpoint time (background build agent; per-session shard files + merge tool + repo-sweep integration). If its PR is open when you read this, check `gh pr list`.

## Self-annealing notes (Layer 2)

- **Stale-checkout bite, in-session:** I grepped the stale working tree for PR #320's STALE-CHECKOUT code and concluded absence; the code existed on origin/main. Caught immediately because the exploration reports had flagged the blind spot. The recurrence-kill (build 2) shipped the same hour.
- **Doctor test failure (1 iteration):** Python 3.13+ dataclass creation resolves `cls.__module__` via `sys.modules`; spec-loaded test modules must register there before exec. Transferable: any spec-load test helper for a module using dataclasses needs `sys.modules[name] = mod`.
- **Coordination reality:** sibling sessions landed #330 (ledger backlog) and #333 (S3) mid-pass; exploration snapshots went stale within minutes. Every commit in this pass used temp-index plumbing or isolated worktrees; the shared tree's HEAD/index were never switched.

## Decision menu (open items for the owner)

1. **PR #300** (07-21 sweep, no CI checks, largely superseded by #330 + later PRs): recommend close (Band-3, needs your order).
2. **Stash archives** in `.scratch/stash-archive-*.patch`: review-or-delete at leisure; stash@{2} held a 292-line wire-hooks diff from 06-06 (long superseded) + praxis-uslu.astro changes.
3. **Unmerged-tip branches kept** (report-only): `client/brisken/lead-gen-onepilot` [ahead 14/behind 92], `system/no-auto-commit-prototype-carveout` [ahead 2], `system/exec-assistant-integrations` [gone upstream, no merged PR], `recon-ui-verify`, `sys/cadence-pin`, leadgen/task-2..7, deck-foundation-v2, lead-desk-ground-outreach / outreach-phases, recon-combined-verify, meji checkpoint-0610, insurance proposal branch.
4. **Stale spec** `p2.ops1` (2-build, 35d): close out / archive / work it.
5. **2 stale status files** (p2-outreach.md, p2-lead-gen-general.md, 2026-06-21): need content-accurate refresh, not mechanical.
6. **autoMode.allow block**: paste into `.claude/settings.json` if you want classifier guidance for flyctl/scratchpad-python (exact JSON in the pass report).
7. **Platform prod deploy**: #337/#340 touched `platform/` — NOT live until `tools/vercel-force-deploy.sh` runs (Band-3, your order). Also still open from backlog: revoke the chat-exposed Vercel token.
8. **Validator blind spot** (platform-content `*`-prefix skip): small follow-up build candidate.

## Next steps

- Land the fan-out PR (if still open), then residual ledger sync PR (this checkpoint rides in it).
- At sibling quiesce: `git pull --ff-only` in the shared tree; if refused, the refusal list is ledger-PR-2 (same temp-index recipe).
- `uv run tools/doctor.py` is now the standing health-check entry; `--deep` before big sessions.

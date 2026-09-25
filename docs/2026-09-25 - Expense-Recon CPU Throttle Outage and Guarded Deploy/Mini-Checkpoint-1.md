# Mini-Checkpoint: Expense-Recon CPU Throttle Outage and Guarded Deploy

**Date:** 2026-09-25
**Status:** Outage fixed and live; stale-tree deploy risk closed (#1395, #1414 merged)
**Type:** mini

---

## Summary
The recon SPA looked dead because the Fly machine's single shared vCPU was throttled to its 6.25% baseline, not because of a code fault. Resized to shared-cpu-4x on owner order, then made a stale worktree unable to shrink it again: recon deploys now go only through the module's `deploy.py`, and a direct `flyctl deploy` of the app is denied.

## What Was Done
- Diagnosed in-VM (python over `flyctl ssh console`; the image has no `ps`/`top`): `/proc/stat` steal 92.7%, idle 0, `/proc/pressure/cpu` some avg10 78, load 6-7. `/healthz` took 2-27 s against the 5 s check, and the proxy logged `PR01 no known healthy instances` on every route. Cause: burst balance (~500 s) spent by 11 deploys in under 2 h plus jobs and sibling SPA drives.
- `flyctl scale vm shared-cpu-4x --vm-memory 1024` (owner: "thats fine do it") took `/healthz` to 0.06-0.09 s. The SPA was driven cold in Chrome: months list plus the September workbench rendered in ~1 s.
- #1395: `fly.toml` `[[vm]] cpus = 4` (merge `d9fc2572`).
- #1414 (merge `08d2cc20`): module `deploy.py` (fetch; refuse a dirty module, a module that differs from origin/main, or a fly.toml smaller than the live machine; stamp GIT_COMMIT; verify `/healthz` commit and machine size; `--dry-run`, `--image`). `recon-accuracy-deploy-gate.py` now denies direct deploys, and its accuracy check runs on `deploy.py` runs. Docs switched (operating.md, if-it-is-down.md, PARALLEL-ROUND-PROTOCOL.md, Dockerfile). `block-flyctl-deploy-git-commit` pattern removed (superseded).
- Delivery to running sessions: staged only `.claude/hooks/recon-accuracy-deploy-gate.py` into the primary checkout's index from origin/main. Proven live: `flyctl deploy --help -a brisken-expense-recon` was denied in this already-running session.
- Verified: `deploy.py --dry-run` from a fresh origin/main tree passes; two surviving pre-#1395 worktrees (`cpus = 1`) cannot run it. regress_check bites on all three wiring points. `preflight-hooks --full` 2037 pass; CI 8/8 on both PRs.

## What Did NOT Work (and why)
- **First `flyctl scale vm` call:** denied by the auto-mode classifier ("Modify Shared Resources") until the owner ordered it in the turn.
- **`flyctl scale vm ... --yes`:** no such flag on `scale vm` (`unknown flag: --yes`); the working form is `--vm-memory 1024` with no confirm flag.
- **Fly Prometheus API for `fly_instance_cpu_balance`:** 401 "something went wrong resolving organization" with the `~/.fly/config.yml` token under Bearer, bare and FlyV1 prefixes; the in-VM `/proc` read was the instrument instead.
- **Playwright MCP:** it binds to Edge CDP :9222, which was not running (ECONNREFUSED); `agent-browser --session <name> --executable-path chrome.exe` worked.
- **A pattern rule as the block:** the `command` field is raw text, so a regex fires on greps and PR bodies (the stale `warn-flyctl-deploy-git-commit` fired on every grep this session); the block went into the hook, which strips prose.
- **Dropping an untracked copy of a new file into the primary checkout:** a later `git merge --ff-only` aborts on an identical untracked file (tested). Staging from origin/main (`git checkout origin/main -- <file>`) keeps the ff working (tested).

## Current Status
Live: machine 7843d54b579598 shared/4/1024, `/healthz` ~0.07 s, commit `c5a426aa` (a sibling's v240). Both PRs merged; main has the guard. The primary checkout (fa8104aa, 100+ behind) carries one staged file, the new gate. That is intended and resolves on its next fast-forward. Ops status: unknown plan (no `platform` section in infrastructure.yaml).

## Next Steps
1. The next recon deploy (any session) runs `deploy.py` from a fresh origin/main tree; confirm its output ends `VERIFIED` and the machine stays 4/1024.
2. If throttling recurs at 4x (slow `/healthz`, check flapping, steal high in `/proc/stat`), move to `performance-1x` (~$32/mo, no quota) and sync `fly.toml` in the same PR.
3. When the primary checkout is next fast-forwarded, confirm the staged hook file merges away cleanly (`git status` empty for it).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/deploy.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/operating.md` ("Deploy")
- `.claude/hooks/recon-accuracy-deploy-gate.py`
- memory `project_brisken_expense_recon_fly_hosting.md` (outage signature and diagnosis recipe)

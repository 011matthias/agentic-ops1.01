# No Auto-Commit Gate (B6)

**Hard constraint.** The git/GitHub ship chain runs automatically.
Autonomy is keyed on **deterministic scope** and an **objective
external signal**, never on the agent's judgment that a change is
"good enough." Three bands:

- **Autonomous** — feature-branch `git commit`, feature-branch
  `git push`, and `gh pr create` run with no human order, once real
  verification has passed.
- **Auto-merge (CI-gated)** — `gh pr merge` runs automatically the
  moment the target PR's CI is green. The gate decides on the
  objective signal (`gh pr checks`), not on the agent asserting the
  code is fine.
- **Gated floor** — irreversible or outward-facing actions (direct
  push-to-main, force push, commit-on-main, deploy commands,
  tag / release, subtree push to client handoff repos, prod MCP
  writes) need an explicit user order or a named session
  pre-authorization. These never fire on their own.

The model is automatic for the normal inner loop (commit → push →
PR → merge) and stops only at the irreversible floor. The
2026-05-26 incident was unverified work landing on main on the
agent's say-so; keying the merge on the user's own CI closes that
path while removing the per-step "ship it" tax.

**Prototype carve-out.** Ship-class commands whose scope is 100%
within `workspace/projects/local-web/**` bypass the gate entirely,
including direct-to-main. Preemptive local-business demo sites:
low blast radius, no production client data. Bypass is structural:
the hook inspects `git diff --cached --name-only` (commit), the
upstream diff (push), or the base-branch diff (PR) and allows when
every touched file is under the prototype path. A mixed commit (one
local-web file + one client file + a system rule edit) does NOT
bypass. This carve-out is the source of truth;
`no-auto-commit-gate.py` is the structural backstop.

## Band 1 — autonomous lane (no order needed)

Runs without asking, PROVIDED the verification precondition below
is met:

- `git commit` / `git commit --amend` on a non-main feature branch
- `git push` of a feature branch to its own remote (no `main` /
  `master` refspec, no `--force` / `--force-with-lease`)
- `gh pr create`

**Verification precondition (agent-enforced, not hook-enforced).**
Before using Band 1, the agent must have run real verification of
the behavior it is shipping, not just a passing build: a named test
(`uv run pytest ...`), a runtime check (triggered the webhook,
fetched the URL for 200 + content), or a lint/validate pass
appropriate to the artifact. "The build compiled" or "the file
wrote" is NOT verification. The hook enforces the scope split; it
cannot see whether you verified. Using the autonomous lane on
unverified work is a friction event (`verification-theater`).

For changes under `tools/`, `.claude/hooks/`, or `tools/tests/`,
run `uv run tools/preflight-hooks.py` (`--full` before a
`tools/tests` change) so "passes locally" means "passes the CI
`Enforcement hook tests` job". One structural backstop closes the
lint half automatically: `.claude/hooks/ruff-push-gate.py`
(PreToolUse:Bash|PowerShell, wired in `wire-hooks.py`) runs the
exact CI ruff command at `git push` time when the push touches a
Python file in that scope, and returns permissionDecision="ask"
with the ruff output inline if it would fail; the slower pytest
half stays in CI plus the `--full` runner. Built 2026-07-17 after
five PRs went red on the `hooks` job in one day for ruff F401/F841
in newly-added files that passed locally but not in the clean CI
env.

## Band 2 — auto-merge, CI-gated

`gh pr merge` runs automatically when the target PR's CI is green.
The hook calls `gh pr checks` for the PR and:

- **green** (all checks pass) → merge fires, no human order
- **red / pending / undeterminable** → needs an order that NAMES the
  override ("merge anyway", "force merge", "override CI"), otherwise
  ASK. A generic ship word ("push", "deploy", "ship it") from an
  earlier turn does NOT clear a non-green merge, because merging red
  lands code the user never saw pass. Enforced separately from the
  generic authorization scan since 2026-07-22, after a stale "deploy"
  order (meant for a Vercel deploy) auto-merged a PR whose hooks job
  had just failed and turned `main` red. The narrowing is
  merge-specific: every other gated-floor action still clears on a
  generic order.

CI is the objective signal that makes an autonomous merge-to-main
safe: the repo's CI (`.github/workflows/ci.yml`) runs the platform
type-check / lint / build, the spell check, the Playwright smoke
suite, and the enforcement-hook pytest suite (`tools/tests`). A
green PR has passed all of these. This is the realization of "a gate
that decides autonomously whether something should be merged": it
decides on the checks, not on the agent's opinion.

The agent's role in Band 2 is to let CI run and merge on green
(poll with `gh pr checks --watch` or re-check), not to ask the user
to merge. Asking "want me to merge?" on a green PR is a deferral.

## Band 3 — gated floor (explicit order required)

These NEVER run autonomously, regardless of CI or verification
state. They need an explicit order or a named session
pre-authorization:

- `git push` to `main` / `master`, or any `git push` while the
  current branch IS main / master (bypasses the PR + CI gate; the
  repo prohibits direct-to-main anyway)
- `git push --force` / `--force-with-lease` (irreversible on the
  remote)
- `git commit` while on main / master
- Any deploy command (`flyctl deploy`, `vercel deploy`,
  `vercel-force-deploy.sh`, Railway deploy). Note: the normal
  production deploy happens automatically when Vercel builds `main`
  after an auto-merge; these explicit deploy commands are manual
  overrides and stay gated.
- `git tag`, `gh release create`
- Subtree push to client handoff repos
- `gh pr close`, `gh issue close`, `gh issue comment` on shared
  issues
- `git revert` on commits already on a shared branch
- MCP write calls that mutate shared resources (e.g.
  `scenarios_run` against production instances) — see also
  `rule_instantly_invasive.md` for the Instantly-specific equivalent

Acceptable orders: "push", "force push", "deploy", "merge anyway",
"land it", "ship it", or a named session-scoped pre-authorization
("deploy to prod today, I'll watch it"). A session
pre-authorization stands for that session's named scope ONLY; a new
session resets to explicit-order-required.

## What is NOT ship-class (auto-runs)

These need no order under this rule:

- Local file edits (`Edit`, `Write`, `NotebookEdit`)
- Reads, greps, globs
- Local test runs, build commands without deploy (`npm run build`, `uv run pytest`)
- WebFetch, MCP read operations
- `git status`, `git diff`, `git log`, `git branch -v`, `git show`
- `git checkout <branch>` (navigation, not state change)
- `git stash`, `git stash pop` (local-only)
- Local file moves and renames (when not part of a ship)
- Memory file writes
- TodoWrite / planning operations

## Required response protocol

When the user gives an editing task:

1. Plan the work and write the code/edits.
2. Run real verification of the behavior changed (Band 1
   precondition). Name the test performed.
3. If verification passed: run the chain autonomously — commit and
   push the feature branch, open the PR (Band 1), then let CI run
   and merge on green (Band 2). No "ship it" needed.
4. STOP at the gated floor (Band 3): a deploy command, a force
   push, a push-to-main, a tag/release, a client subtree push.
   Surface the pending floor action and wait for the explicit order.
5. If verification did NOT run, do not use Band 1 / Band 2; stop at
   the staging boundary.
6. If CI goes red, do not merge-anyway autonomously: surface the
   failing checks and fix, or wait for an explicit "merge anyway".

## Overrides rule_behaviors ship-gate

`rule_behaviors.md` says: *"Build passes → commit + push + PR +
merge as ONE action. Never pause mid-chain."* This rule sharpens
that: the chain runs as one autonomous action, but "build passes"
is not the merge trigger; **CI green** is. The chain auto-runs
commit → push → PR-open → (CI) → merge, and stops only at the
gated floor (deploy / force / push-to-main / tag / client push).

The *"ANTI-PATTERN: 'Should I merge?', 'Want me to push?'"* warning
applies in full to Bands 1–2: asking to commit, push, open a PR, or
merge a green PR is a deferral. Surfacing a pending Band-3 floor
action once is correct, not a deferral.

## Why

User correction 2026-05-26 after PRs #57 and #58 auto-shipped to
main without runtime verification (skil_web-build §3a integration +
3 BRIEF back-fills). The skill changes passed `git commit` but the
runtime behavior on next invocation was unverified; build success
was treated as proof of correctness (verification theater per
`rule_behaviors.md` Layer 2). The first fix was a flat gate: every
ship-class action needed an explicit human order.

Revised 2026-06-06, in two steps, on user direction ("I'd rather
have an automated control gate that decides autonomously whether
something should be committed / pushed / merged ... I want it to be
automatic"):

1. Tiered the gate so reversible feature-branch work (commit / push
   / PR-open) runs autonomously and only main-landing / irreversible
   work is gated.
2. Made the merge automatic too, keyed on the objective CI signal
   (`gh pr checks` green) rather than a human order. The flat gate
   caught the 2026-05-26 incident at the wrong place (every commit)
   and never required the verification that was the actual missing
   piece. CI-gated auto-merge requires it structurally: a green PR
   has passed the enforcement-hook pytest suite, the platform build,
   and the smoke tests. The incident is still prevented — a red or
   pending PR does NOT auto-merge, and direct push-to-main / force
   push stay on the gated floor.

This rule operationalizes [[feedback_no_auto_commit]] as a Layer 1
structural gate (rule = fires at decision time) instead of a Layer 3
memory (depends on agent recall).

## Enforcement

Honored at decision time as a B-gate (B6). The structural backstop
is `.claude/hooks/no-auto-commit-gate.py` (PreToolUse:Bash|PowerShell,
wired in `tools/wire-hooks.py` as one of the canonical hooks). It:

1. Detects ship-class commands on a normalized view of the command
   (`.claude/hooks/_shell.py`: PowerShell call operator stripped,
   `.cmd`/`.exe` program paths reduced to their stem, backslashes
   normalized) so Windows spellings like
   `& "$dir\vercel.cmd" deploy --prod` cannot evade the patterns.
2. Allows the prototype carve-out (100% local-web) silently.
3. Classifies the band from the command + live current branch
   (`git rev-parse --abbrev-ref HEAD`). Band 1 (feature-branch
   commit / non-main non-force push / `gh pr create`) → allow.
4. For `gh pr merge`, calls `ci_is_green()` (`gh pr checks`): green
   → allow (Band 2); otherwise fall through.
5. Gated floor + non-green merge → scan recent user turns for an
   explicit order; allow if found, else `permissionDecision: "ask"`.

The hook decides SCOPE deterministically and reads the CI signal; it
does NOT and cannot verify behavior beyond what CI covers. The Band-1
verification precondition is agent discipline plus the CI gate at
merge. The agent cannot bypass the floor; the user authorizes via the
permission prompt OR cancels. Mirrors the `instantly-invasive-gate.py`
always-ask pattern. Built 2026-05-26 (Phase 6, Agent Teams series);
tiered + auto-merge 2026-06-06.

Edge cases: `git log`, `git status`, `git diff`, `git tag -l|--list`
and other read-class git commands are NOT ship-class and pass through
silently. Two env-var test seams force the branch and CI verdict for
deterministic smoke tests, never set in production:
`NO_AUTO_COMMIT_GATE_BRANCH` and `NO_AUTO_COMMIT_GATE_CI`. The pytest
regression suite is `tools/tests/test_no_auto_commit_gate.py` (run by
the CI `hooks` job); a human-readable matrix lives in
`tools/fixtures/no-auto-commit-gate/README.md`.

This rule + this hook together replace the memory-only fix
([[feedback_no_auto_commit]]) that demonstrably failed within
hours of being written (PR #57/#58/#60 regressions on 2026-05-26).

# No Auto-Commit Gate (B6)

**Hard constraint.** Never run a ship-class git or GitHub action
without explicit user authorization in the current conversation.
General autonomy grants, "ship-gate" reflexes from
`rule_behaviors.md`, and post-edit momentum do NOT authorize commits,
pushes, PRs, or merges. The user must explicitly order the action
("commit this", "push", "open the PR", "merge", "ship it") OR
pre-authorize a named scope for the session ("ship everything to PR
today, I'll review at the end").

## What counts as ship-class (gated)

These require an explicit order or session pre-authorization:

- `git commit`, `git commit --amend`
- `git push`, `git push --force`
- `gh pr create`, `gh pr merge`, `gh pr close`
- `gh issue close`, `gh issue comment` on shared issues
- `git revert` on commits already on a shared branch
- `git tag`, `gh release create`
- Subtree push to client handoff repos
- Any deploy command (`flyctl deploy`, `vercel deploy`, `vercel-force-deploy.sh`, Railway deploy, etc.)
- Hook / cron / routine creation that affects production state
- MCP write calls that mutate shared resources (e.g. `scenarios_run` against production instances) — see also `rule_instantly_invasive.md` for the Instantly-specific equivalent

## What is NOT ship-class (auto-runs)

These need no explicit order under this rule:

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

When the user gives an editing task that does NOT include an explicit
ship order:

1. Plan the work and write the code/edits.
2. Make the local edits via `Edit` / `Write`.
3. STOP at the staging boundary. Surface a one-line summary of what
   changed (files touched, line counts).
4. Wait for the user's explicit ship order. Acceptable orders:
   "commit", "ship it", "push", "PR it", "merge", "land it", or a
   named session-scoped pre-authorization.
5. Only after explicit order: execute the ship chain (branch +
   commit + push + PR + merge) as directed. If the user orders only
   one step ("commit" but not "merge"), execute that step and stop
   at the next ship boundary.

If the user pre-authorizes a chain ("ship everything to PR today"),
the authorization stands for that session's named scope ONLY. A new
session resets to default (explicit order required per action).

## Overrides rule_behaviors ship-gate

`rule_behaviors.md` says: *"Build passes → commit + push + PR +
merge as ONE action. Never pause mid-chain."* That gate is overridden
by THIS rule for ship-class actions. The auto-chain behavior remains
valid ONLY when the user has explicitly ordered a chain ship in the
current conversation.

The *"ANTI-PATTERN: 'Should I merge?', 'Want me to push?'"* warning
in `rule_behaviors.md` is NOT activated by an honest ship-gate check
under this rule. Asking "ready to ship?" once after edits is the
correct behavior, not a deferral, because the agent is required by
this rule to surface the ship decision rather than assume it.

## Why

User correction 2026-05-26 after PRs #57 and #58 auto-shipped to
main without runtime verification (skil_web-build §3a integration +
3 BRIEF back-fills). The skill changes passed `git commit` but the
runtime behavior of the integrated skill on next invocation was
unverified — build success was treated as proof of correctness, which
is the verification-theater pattern called out in
`rule_behaviors.md` Layer 2. The structural fix: make the commit
boundary explicit at decision time rather than rely on per-session
memory of a feedback rule.

This rule operationalizes [[feedback_no_auto_commit]] as a Layer 1
structural gate (rule = fires at decision time) instead of a Layer 3
memory (depends on agent recall).

## Enforcement

Honored at decision time as a B-gate (B6). A `PreToolUse:Bash` hook
matching `git commit|git push|gh pr (create|merge)|flyctl deploy|
vercel deploy` that requires explicit prior user authorization in
the current turn is the natural Layer 1 evolution of this gate
(operationalizes the rule so it cannot be forgotten by a future
session). Not yet built; logging as `infrastructure-deferred` for
the next hook pass.

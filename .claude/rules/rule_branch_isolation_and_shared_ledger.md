# Branch Isolation + Shared-Ledger-on-Trunk (G1)

**Hard constraint.** Two git-hygiene rules that keep `main` and the
feature branches functional with GitHub, and that kill the recurring
cross-project stash/recovery mess (2026-06-12 Brisken p1-finance vs
p2-lead-gen, recovered via `fsck`; see
[[feedback_worktree_for_concurrent_sessions]]).

This rule is the source of truth for WHERE a change is committed
across branches. It sits beside [[rule_no_auto_commit]] (which governs
WHEN the ship chain fires) and the CLAUDE.md git workflow (feature
branches, PR-to-main, no direct push).

## 1. The shared system ledger lives on the trunk, reached only by PR

These paths are **system-wide ledger** content. Every session edits
them regardless of which client or project it is scoped to:

- `docs/INDEX.md` (the checkpoint index)
- `docs/friction-register.md` (the single system-wide friction ledger)
- `docs/sessions/*.md` (daily session logs)
- `docs/*/Checkpoint.md` (checkpoint folders an INDEX row links to)

Rules:

- Ledger edits reach `main` **only through a `docs/...` PR** (Band 1
  feature-branch commit + push + `gh pr create`, auto-merge on CI
  green per [[rule_no_auto_commit]]). Never a direct commit/push to
  `main`.
- **Never commit a ledger file on a `client/...`, `proposal/...`, or
  `platform/...` feature branch.** Fragmenting the friction register
  or session log across feature branches guarantees a merge conflict
  on the next PR and splits the ledger so neither branch is the
  authority. If a feature branch's tree has dirty ledger files (a
  checkpoint ran mid-feature), move them onto a `docs/...` branch and
  PR them; do not fold them into the feature commit.
- When an `INDEX.md` row is added, the `Checkpoint.md` it links to
  goes in the **same** docs PR, or the link is dead on `main`.

`PROJECT-BOUNDARIES.md` and other per-client shared files (one file
both projects in a client folder edit) are a softer case: edit on
whichever branch is live, accept the occasional small conflict, and
prefer landing structural boundary changes via the trunk when the
edit is not coupled to feature code.

## 2. One project per branch; branch BEFORE the first edit

When a client folder holds more than one project (Brisken: `p1`
expense-reconciliation on `main`/finance branches, `p2` lead-gen on
`client/brisken/lead-gen-*`), each project commits only to its own
branch:

- Create the `client/{client}/{project-desc}` branch **before the
  first edit**, not at recovery time. The 2026-06-12 tangle was
  caused entirely by editing p2 files on a p1 finance branch and only
  branching once it had to be untangled.
- Never edit project-X files while the current branch is named for
  project-Y. A feature branch's TREE legitimately contains the whole
  trunk (baseline finance code sitting on a lead-gen branch is fine);
  the constraint is on new EDITS and COMMITS, not tree contents.
- A feature branch that only ever touches its own project's files
  (`workspace/clients/{c}/specs/{proj}-*`, its `deliverables/`,
  `automations/{proj}/`) PRs cleanly even when behind `main`, because
  nothing it changed overlaps what moved on `main`. A stale-but-
  isolated feature branch does **not** need a `merge main` before
  continuing; sync only if a real file overlap exists.

## 3. Never `git stash` to isolate cross-project or cross-session WIP

`git stash` is shared state across every checkout of one clone; a
stash pushed by one project's session can be popped onto another
project's branch (the 2026-06-12 mess: a finance session stashed p2
WIP, it landed on the lead-gen branch, recovered via `fsck`). Stash
is not isolation.

- To park WIP that belongs elsewhere: **commit it on a dedicated
  branch** (a `docs/...` branch for ledger WIP, the project's own
  branch for project WIP). A committed branch cannot be popped onto
  the wrong place.
- For **genuinely concurrent** sessions (two agents on one clone at
  once), use a `git worktree`, per
  [[feedback_worktree_for_concurrent_sessions]].
- For a **sequential single-session** switch, prefer an in-place
  `git checkout` over a worktree when the project depends on
  **gitignored on-disk context** (Brisken's `context/lead-generation/`
  catalog + evidence pack). Worktrees do not carry gitignored or
  untracked files into the new directory, so a worktree would orphan
  that context; an in-place checkout keeps it in the one working
  directory where it lives.

## Why

One root cause produced three friction events on 2026-06-12: p2
lead-gen edits made on a p1 finance branch, the parallel finance
session stashing the cross-project WIP to clean its tree, and the
recovery session restoring it via `fsck` onto a fresh branch. The fix
the prior session reached for (a memory: "use a worktree") is Layer 3
and depends on recall. This rule operationalizes the wider standard at
Layer 1: the ledger has a fixed home (trunk via PR), projects have
fixed homes (their own branch, cut before the first edit), and stash
is banned for isolation outright.

## Enforcement

- **Agent discipline at decision time (G1).** Before the first edit
  of a cross-project session, confirm the current branch matches the
  project being edited; if not, switch/cut the project branch first.
  Before committing, if the staged set includes a §1 ledger path on a
  non-`docs/` branch, unstage it and route it to a docs PR.
- **Backstop (existing).** [[rule_no_auto_commit]]'s
  `no-auto-commit-gate.py` already blocks direct commit/push to
  `main`, forcing ledger updates through a PR.
- **Structural guard (built 2026-07-22).**
  `.claude/hooks/branch-isolation-gate.py` (PreToolUse Write|Edit,
  wired in `wire-hooks.py`) advises when the target path is a TRACKED
  `workspace/clients/{X}/...` file and the current branch is not a
  client-X branch (`client/{X}/...`, legacy `{X}/...`, or a sanctioned
  per-client family like brisken's `leadgen/`). Gitignored targets
  (the `context/` home) are exempt — they never commit. Advisory, not
  deny: cross-cutting system changes stay possible, but the wrong-branch
  edit is loud in the same turn. Suggested twice in 2026-06-12
  checkpoints; the trigger recurrence was the 2026-07-22 dirty-main
  pile. Tests: `tools/tests/test_branch_isolation_gate.py`.

**Self-detection.** A cross-project edit on the wrong branch, a ledger
file committed on a feature branch, or a stash used for isolation is a
`boundary-violation` / `branch-hygiene` friction event; log at
`/comd_checkpoint`. The recurrence-kill is the structural guard above,
not memorizing harder.

Related: [[rule_no_auto_commit]],
[[feedback_worktree_for_concurrent_sessions]], PROJECT-BOUNDARIES.md
(per-client session scope), CLAUDE.md (git workflow).

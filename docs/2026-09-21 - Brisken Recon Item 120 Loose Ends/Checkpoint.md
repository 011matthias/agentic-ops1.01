# Checkpoint: Brisken Recon Item 120 Loose Ends

**Date:** 2026-09-21
**Status:** All three loose ends closed; backup live; item 120 down to two owner decisions

---

## Summary

The three ends item 120 left open on 09-20 are closed: a client-failure row
now names the build that served it, the notifier runs from a checkout that
updates itself, and the SharePoint backup is ON, so Brisken holds a copy of
its own reconciliation data for the first time. Item 120 is now two owner
decisions wide (personal Fly account, unrehearsed restore) rather than five.

---

## What Was Done This Session

### Build identity on stored failures (PR #1170, deployed `b34ace5b`)

1. `client_errors` gains `server_commit` + `server_image`, stamped from
   `machine.snapshot()` when the report ARRIVES, so a row keeps the build
   that served the failure however many deploys later it is read.
2. Migration through the existing mechanism (`PRAGMA table_info` +
   `ALTER TABLE` in `_migrate`), beside the eleven columns already added to
   the live volume that way. Pre-existing rows read `""`.
3. `machine.py`'s docstring and the probe test both stated the gap as open;
   both now describe the code. `docs/api-contract.md` gained the
   `server.commit` / `server.image` rows PR #1156 shipped undocumented.

### The notifier off the shared tree (PR #1173, live)

1. `tools/brisken-recon-notify-run.py` runs the notifier from a dedicated
   clone (`Repo/agentic-ops1-notify`) that fast-forwards itself first.
2. Windows task `BriskenReconNotify` repointed at it.
3. `docs/operating.md` + `tools/INDEX.md` updated; the 2026-07-22 status row
   saying "the task runs from the PRIMARY clone" corrected.

### SharePoint backup switched on (owner directive, live)

1. Four settings in one command, one restart: `_SITE`, `_FOLDER=ExpenseTool`,
   `_MAX_BYTES=400 MB`, `_BACKUP=1`. Set as secrets, not `fly.toml` env, so
   the running image was unchanged by the config change.
2. First copy `expense-recon-data-20260921T181135Z.zip`, 127.2 MB, 42 s after
   the restart.

### Records (PR #1175)

Item 120, item 121, `docs/backup-and-restore.md`, `docs/operating.md`,
`rule_brisken_graph_first`, `status/p1-expense-reconciliation.md`.

---

## Key Decisions Made

### Column names are `server_commit` / `server_image`, not `commit` / `image`

- **Choice:** prefix both.
- **Rationale:** `commit` is a SQLite keyword; `CREATE TABLE t (commit TEXT)`
  is a syntax error. Verified before writing the migration, not after.

### Old client-error rows read `""` rather than a back-filled commit

- **Choice:** no back-fill.
- **Rationale:** the build that served them is unrecoverable, so a back-fill
  could only write the build doing the back-filling. Wrong identity sends the
  next investigation to the wrong release; absent identity costs it nothing.

### A separate clone for the notifier, not a worktree

- **Choice:** `git clone --no-hardlinks` from the shared tree, origin
  repointed to GitHub.
- **Rationale:** a worktree shares `.git` — refs, objects, locks. A separate
  clone makes "cannot disturb the shared tree" a property rather than a
  claim. Confirmed after: shared HEAD `a7a5a4b1` before and after, clean,
  zero stashes.

### The notifier reads the EXISTING state file, it does not get a fresh one

- **Choice:** resolve state by finding an existing file; only fall back to a
  new path when none exists anywhere.
- **Rationale:** a fresh state is not a clean slate, it is an instruction to
  announce the whole history at once. Measured: a dry run against an empty
  state planned 8+ mails (7 month runs, 37 re-matches) where the real state
  planned none.

### Backup ceiling raised to 400 MB in the same command as the enable flag

- **Choice:** four settings, one restart.
- **Rationale:** `run_backup` refuses on `_MAX_BYTES` before it reaches
  SharePoint. At 144-146 MB against a 100 MB default, `_BACKUP=1` alone
  starts a scheduler that refuses every round while reading as enabled,
  which is worse than one visibly off. 400 MB is 2.7x today, so ordinary
  growth does not silently re-break it.

---

## What Did NOT Work (and why)

- **`flyctl deploy` with a POSIX path under `MSYS_NO_PATHCONV=1`:** failed
  with `chdir C:\c\Users\...: The system cannot find the path specified`.
  `flyctl` is a native Windows binary, so it resolves `/c/Users/...` against
  the current drive; suppressing MSYS translation is what causes this, not
  what fixes it. `cygpath -w` first.
- **`flyctl ssh console`:** refused by the Claude Code auto-mode classifier,
  so `expense-recon backup --dry-run` could not be run on the machine at
  all. The `/healthz` `disk` block substituted for most of it.
- **Nested `uv run --no-project --with pytest` around `regress_check`:** sets
  `VIRTUAL_ENV`, which makes the inner `uv run --extra web` ignore the
  project env; the module's web tests then `importorskip` and the run reports
  `1 skipped` as success. Ran `regress_check` under plain `python` instead.
- **First probe of the SharePoint drive:** used the path form
  `/sites/{path}/drive` where the code uses the RESOLVED site id
  (`/sites/{id}/drive`). The 404 was mine and nearly became a filed finding
  that `backup --check` is a blind instrument. Re-probed the way the code
  does: drive resolves, 18 folders, ~50 GB.
- **Playwright MCP:** bound to the user's Edge on :9222, which is busy;
  `initializeServer` timed out at 30 s. Used `agent-browser` with its own
  Chrome and a named session.
- **First consumer re-drive:** the snapshot returned empty because the login
  had silently not registered, yet the deploy-consumer gate printed
  `[CONSUMER DRIVEN] ... closed`. Caught and re-driven properly.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/store.py` | edit | `client_errors` DDL + `_migrate` ALTER for the two columns |
| `src/expense_recon/web/app.py` | edit | stamp `server_commit` / `server_image` on the incoming report |
| `src/expense_recon/web/machine.py` | edit | docstring: the gap it named is closed |
| `tests/test_client_error_probe.py` | edit | 4 tests; corrected the docstring stating the gap |
| `docs/api-contract.md` | edit | `server.commit` / `server.image`; the two new row fields |
| `tools/brisken-recon-notify-run.py` | new | self-updating runner for the notifier |
| `tools/tests/test_brisken_recon_notify_run.py` | new | 11 tests |
| `tools/INDEX.md` | edit | runner row |
| `docs/operating.md` | edit | notifier section rewritten; backup limit retired |
| `docs/backup-and-restore.md` | edit | backup is on; the ceiling trap; the 404-reads-as-empty trap |
| `.claude/rules/rule_brisken_graph_first.md` | edit | app-only SharePoint works, incl. writes |
| `status/p1-improvement-backlog.md` | edit | item 120 three ends; item 121 note |
| `status/p1-expense-reconciliation.md` | edit | item-120 row tail; stale notifier NOTE |
| `memory/reference_repo_tooling_gotchas.md` | edit | flyctl needs Windows paths; ssh console blocked |

---

## Current Status

Three PRs merged (#1170, #1173, #1175). Live app on `b34ace5b`, verified by
`/healthz` returning the stamped commit. Backup running daily. Notifier
running every 15 minutes from its own clone, proven unattended: the 18:32:12Z
scheduled run fast-forwarded `8be609b6..9c8a1fee` and ran from it with nobody
watching.

`platform: unknown plan, ~?/? ops/mo. Last assessed: ?.` — brisken has no
`platform` section in `infrastructure.yaml` while running on Fly; a
feasibility assessment is still unfiled.

Item 120 is now two owner decisions: the personal Fly account, and a restore
nobody has rehearsed.

---

## Next Steps

1. **Rehearse the restore.** The copy is verified to exist and not verified
   to work. Needs a throwaway app + volume; the runbook step 4 is written and
   untested. This is the highest-value remaining item on 120.
2. **Decide backup retention.** Nothing prunes; 127 MB/day is ~3.8 GB/month
   in Brisken's tenant, forever. A retention rule or a longer
   `EXPENSE_RECON_BACKUP_INTERVAL_HOURS`. Not urgent, does not self-resolve.
3. **Decide whether the copies belong on MARKETING** or a finance-owned site.
   One variable either way.
4. Two stale p2 status files untouched by this session:
   `p2-product-decks.md` (60d), `p2-targeting.md` (61d). Not mine to update
   blind; a p2 session should resolve or delete them.
5. Brisken comms-log is 13 days stale.
6. File a brisken `platform` feasibility assessment in `infrastructure.yaml`.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 120)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/backup-and-restore.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/operating.md`

### Open Questions
- Retention/cadence for the SharePoint copies (owner).
- MARKETING vs a finance-owned site for financial records (owner).
- When to spend the throwaway app + volume on a restore rehearsal (owner).

### Working Notes

The live data folder is 144.0 MB over 586 files (`/data/runs` 87 MB,
`/data/inbound` 60 MB); `/healthz` `used_bytes` reads 146 MB for the whole
volume; the first archive compressed to 127.2 MB. Ceiling now 400 MB.

`backup --check` cannot distinguish an unreachable target from an empty
folder: `list_folder` folds any Graph 404 into `[]`, including one raised
while resolving the drive. Prove the instrument by listing the drive root
first.

The notifier's freshness is readable at
`agentic-ops1/.scratch/recon-notify-runs.log` (`update=STALE (...)` means the
fast-forward failed and the run went ahead on the commit named).

Deploy stamp path that works on this box:
`MW=$(cygpath -w "$M"); flyctl deploy "$MW" --config "$MW\fly.toml" ...`.

### Reference Materials
- https://brisken-expense-recon.fly.dev/healthz
- https://expenses.brisken.com (Cloudflare; needs a browser UA)
- SharePoint `brisken.sharepoint.com:/sites/MARKETING` → `ExpenseTool`

---

## How to Continue

`/resume brisken`. The three ends are done and deployed; nothing here is
mid-flight. The next real work on item 120 is the restore rehearsal, which
needs an owner yes before it costs a second machine and volume.

---

## Strategic Feedback

### What Worked Well This Session

- **Proving the instrument before believing a negative** paid twice. "0 files
  in the backup folder" and "nothing new" from the notifier were both
  confident negatives; both were validated against a state known to be
  positive (list the drive root; run the diff against an empty state), and
  the second of those directly measured the mail storm a naive migration
  would have caused.
- **`regress_check` worked cleanly on four wiring points**, contradicting the
  2026-09-18 register row that called its verdict unusable. Given plain
  `python` rather than a nested `uv run`, it reported real pass/fail counts
  both times.

### Suggestions

- `deploy-consumer-gate.py` closes on a foreground snapshot even when that
  snapshot returns NOTHING. A drive that reads back empty proves as little as
  a navigation, and the gate's own advisory then reads back as evidence.
  Requiring non-empty output would close the last version of the hole the
  2026-09-15 tightening was aimed at.

### System Health

- The gate that blocked this session's first Stop fired on the literal string
  `flyctl deploy` inside memory text being appended, not on a deploy. A
  substring match over response text will keep producing these; it cost one
  redundant re-drive here, which is cheap, but it trains the reflex of
  treating the gate as noise.
- Autonomy: 1 human intervention (the `ExpenseTool` directive, which was an
  answer to a question this session raised).

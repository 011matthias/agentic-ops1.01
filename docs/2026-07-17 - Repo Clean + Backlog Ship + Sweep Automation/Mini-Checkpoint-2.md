# Mini-Checkpoint: Git-Automation Hardening (PRs #252/#253)

**Date:** 2026-07-17
**Status:** SHIPPED — one dangling user step (Resend key)
**Type:** mini

---

## Summary
Second pass on the commit/push automation, planned and approved via plan
mode: the nightly sweep is now self-healing, secret-scanned, and monitored.

## What Was Done
- `.gitattributes` (new): merge=union for friction-register, anneal-ledger,
  docs/INDEX, session logs. Rehearsed: both-sides-appended edits
  auto-resolve; non-union files still conflict (control).
- `repo-sweep.py` v2: structured CI decision table (`gh pr view --json`),
  CONFLICTING self-heal via local merge (one attempt), adopt+close older
  sweep PRs, unique branch names, `--normalize-sessions` frontmatter
  repairer, deletion-aware quiesce, try/finally branch restore.
- CI: gitleaks secret-content scan on every PR (proved green on #252, 10s).
- `weekly_synthesis.py`: ops_health (sweep heartbeat >48h alert, lingering
  sweep PRs, close-candidate worktrees, stale branches) + OPS email section.
  First live run surfaced 46 unmerged branches idle >14d and flagged
  agentic-ops1-recon as a close candidate; #253 fixed its main-checkout
  false positive.
- Cadence worktree recreated (branch sys/cadence-pin);
  AgenticOpsWeeklySynthesis task registered by user (Monday 07:10, Ready).

## Current Status
main at `acdbfac`, both PRs merged, 151+ tests green. Weekly email BLOCKED
on a fresh Resend key: no RESEND_API_KEY/BRIEFING_TO env vars exist, vault
has no Resend entry, old key is rotate-never-reuse. Until set, Monday runs
exit 1 (NO_SEND) with a red LastTaskResult.

## Next Steps
1. User: create a fresh key at resend.com, then
   `[Environment]::SetEnvironmentVariable('RESEND_API_KEY','<key>','User')`
   + `[Environment]::SetEnvironmentVariable('BRIEFING_TO','<email>','User')`,
   then re-run `uv run tools/weekly_synthesis.py --preflight` from the
   cadence worktree.
2. Triage the 46 stale branches + agentic-ops1-recon close candidate in a
   `/comd_system-dev` pass (nothing auto-deleted by design).
3. This checkpoint itself is left uncommitted deliberately: tonight's sweep
   should PR it — the first live proof of the full unattended chain.

## Files to Read First
- tools/repo-sweep.py, .gitattributes
- memory: project_repo_sweep_automation.md

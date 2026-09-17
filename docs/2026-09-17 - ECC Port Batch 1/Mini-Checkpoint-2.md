# Mini-Checkpoint: ECC Port Batch 1

**Date:** 2026-09-17
**Status:** Batch 1 merged and verified live; next build named, not started
**Type:** mini

---

## Summary

Wrap-up after the batch-1 checkpoint: verified the merged hooks are wired and firing in the primary checkout, corrected two claims the full checkpoint got wrong, and established that the per-session state-file build is safe to run alongside the live Brisken expense-recon sessions.

## What Was Done

- `wire-hooks.py --check` in the primary checkout: **27/27 wired**, including `tool-failure-gate.py` and `config-protection-gate.py`. A sibling's SessionStart had already run `--ensure` after the merges.
- Live fire test in the primary checkout: a failing Bash command with lock-shaped output returned `[TRANSIENT] file-lock: retry with backoff in this turn`. The merged gate works outside the proof harness.
- Safety analysis for the per-session state-file follow-up against the live recon sessions (see What Did NOT Work for the corrections that came out of it).

## What Did NOT Work (and why)

- **Claiming the two new hooks were inert until the next SessionStart:** wrong, they were already wired; the read-only check corrected it before any action was taken. Check wiring before recommending a rewire.
- **Claiming the primary checkout sits on main at 430fe76d:** it had since been switched to `client/brisken/recon-untrusted-inbound` with 9 dirty expense-recon files. A `git log -1` reading goes stale in a shared tree within minutes.

## Current Status

Items 2, 3, 7, 6-rule and 10 are on main (#957-#960) and the checkpoint ledger merged (#962). My four worktrees are pruned. The primary checkout is on a Brisken client branch with uncommitted recon WIP; every session's hooks execute from that checkout, so a merge to main reaches them only when it next switches or pulls.

## Next Steps

1. Per-session session-state file. Safe to build alongside the live recon work: separate worktree, no file overlap (their branch touches only `workspace/clients/brisken/automations/expense-reconciliation/**`), and `session_state` is fail-open so a mid-session code swap degrades to restarted counters. Keep the legacy shared-file path working when no `session_id` is available.
2. ECC batch 2 (item 1) and item 5 already have sibling worktrees `sys/ecc-port-batch-2` and `sys/ecc-port-item5-memory-audit`; both touch `wire-hooks.py`, so coordinate before starting either.
3. The recon mail-intake code half of `rule_untrusted_inbound` appears to be in flight on `client/brisken/recon-untrusted-inbound`; check with that session before starting it.

## Files to Read First

- `docs/2026-09-17 - ECC Port Batch 1/Checkpoint.md` (the full batch-1 record)
- `tools/session_state.py` (the shared-state defect the next build fixes)

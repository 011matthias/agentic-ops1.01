# Mini-Checkpoint 1 — Worktree and branch consolidation

**Date:** 2026-08-25 · **Type:** system-infra
**Shipped:** #638, #639, #640, #403 merged; #430 and #537 closed with reasons.

## Before and after

| | Before | After |
|---|---|---|
| Directories under `~/Repo` | 7 `agentic-ops1*` | 2 |
| Worktrees | 7 | 2 (primary on `main`, plus `-deploy` detached) |
| Local branches | 218 | 2 (`main`, one parking branch) |
| Remote branches | 190 | 16 (archive) |
| Open PRs | 2, both stale | 0 |
| Primary clone | 216 behind, dirty, 18 untracked | clean on `main` |

## Rescue came before anything destructive

Two bodies of work existed only on disk and would have gone with the reset:

- **13 orphaned ledger files** — ten checkpoint folders (2026-07-28 to
  08-18), the W31 digest, two session logs. Shipped in #638, with their
  INDEX rows re-derived on top of CURRENT main rather than taken from the
  clone's stale index, which was 216 commits behind and would have
  reverted every row landed since July.
- **The Brisken hours-evidence deliverable** (2026-08-21), committed but
  never PR'd. Shipped in #639. It is billing evidence.

The clone's dirty ledger files were **parked, not discarded**:
`parking/primary-clone-wip-2026-08-25`, pushed, marked never-merge. So even
the content deliberately not merged is recoverable.

## Reading the branches changed the outcome three times

This is the part worth keeping.

**1. Sixteen "unmerged" files were deliberate deletions.** They looked like
work stranded on old branches. They were the Jinja review UI (superseded by
the Lovable SPA at v31), `zoho/client.py` (the 2026-08-22 cut-every-tie-to-
Zoho directive), the meji corporate-sample page (removed in PR #192), and
the smart-trading deck (retired by the TC story alignment). Each was checked
against its own deletion commit before deciding, and re-verified after
staging that none had reappeared. Restoring any would have silently undone a
live decision.

**2. A name match against 608 merged PRs is not sufficient.** A branch
reused after its PR merged matches by name while still carrying unmerged
commits. Seven would have been deleted on that basis, including
`lead-gen-onepilot` (120 commits) and five `leadgen/task-*` (93-95 each),
between them holding 57 files present nowhere on main. An ahead-count guard
(keep anything more than 5 commits ahead, regardless of name) caught all
seven. That content then shipped properly in #640.

**3. The salvage upgraded main rather than restoring it.** `leadgen-task-6`
existed on main at its 2026-07-11 version (PR #207); the branch carried the
2026-07-14 "Calvin clip v3" built to Dirk's direction that day, and 13 of 14
files differed. Checking which side was newer, instead of assuming main was,
is what turned a merge conflict into an improvement.

## The self-inflicted one

A bulk delete reported 197 consecutive failures and my first reading was
"git is refusing." It was mine: the delete list came from Python's
`write_text`, whose default newline translation on Windows appended CR to
every branch name, so git was handed names that do not exist. Diagnosed by
running one delete with stderr visible (it succeeded) and `od -c` on the
list. B3 exactly: my own recent action is the likeliest cause of a failure
that appears right after it. Two habits fall out — pass `newline=""` when
writing a machine-consumed list on Windows, and do not suppress stderr on a
bulk loop whose failure mode you have not seen yet.

## What the 16 remaining remote branches are

Archive, kept on the owner's instruction to keep them and merge anything
that needed it. Everything that needed it was merged: the lead-gen output
(#640) and the B6 red-merge hardening (#403, whose July CI was re-run
against current main first, green including the enforcement-hook suite that
guards the file it changes). `deckgen-native` is explicitly protected so its
27 commits stay revivable after #430 was closed.

## Recovery

Every deleted branch is recorded with its SHA at
`%TEMP%/claude/branch-recovery-manifest.tsv`. Four branches that had no
remote counterpart were pushed before anything was deleted. Gitignored
client context survived the reset intact (2,689 Brisken files, the `.env`).

## Two things the next session should know

`p1-recon-loop-prompt.md` is brought current in this same change: Fly v97,
suite 1352, next round is PR 3 (the coverage surface). It now also says the
worktrees were consolidated, because it used to name
`agentic-ops1-recon`, which no longer exists.

Seven sibling `claude` sessions from 2026-08-24 are still running. None was
active in anything pruned (every worktree had been idle 20 hours to 12
days), but one resuming will find `main` where its branch used to be.

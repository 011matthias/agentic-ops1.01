# Checkpoint: Expense-Recon Statement Append + Repo Consolidation

**Date:** 2026-08-25
**Status:** Both halves shipped, merged, deployed and verified. 0 open PRs. Enforcement layer repaired at close.

---

## Summary

Shipped backlog item 29's last build round (PR 2b-2b-2, the `statements[]`
surface), then consolidated the repo from 7 worktrees and 218 local branches
to 2 and 2 with nothing lost. Closing the checkpoint surfaced that the
enforcement layer had been inert for the entire session; it is now repaired.

---

## What Was Done This Session

### Expense-recon: PR 2b-2b-2, the statements[] surface (#636, Fly v97)

1. Lifted the second-statement refusal from **both** layers it sat in, the
   route gate and `prepare_statement_attach` beneath it. Two tests pinned the
   closed door and now pin the open one; the second was found by the full
   suite, not by reading.
2. Made the 2b-2b-1 fold load-bearing. `statements[]` records every upload as
   a parallel field on both payloads, written by `rematch_month` inside the
   commit lock so the month has one writer.
3. Anchored the sheet writeback **per upload** (`statement_anchors`).
4. Answered both hazards by surfacing, never deduping: an `advisory` fires
   when one card is typed against two account ids, or when an upload lands
   100% new over a period the same account already covers.
5. Closed a race the round opened: `rematch_month` refuses any commit that
   would drop a charge the month gained meanwhile.

### Repo consolidation (#638, #639, #640, #403)

1. Rescued 13 orphaned checkpoint/session files and the hours-evidence
   deliverable **before** anything destructive; both existed nowhere else.
2. Parked the primary clone's stale ledger edits on a never-merge branch,
   then reset it to `main`.
3. Salvaged 72 Rome lead-gen files into `deliverables/rome-2026-leadgen/`
   and removed the stray root `output/`.
4. Deleted 197 local and 181 remote merged branches; merged the B6
   red-merge hardening after re-running its July CI against current main.
5. Brought `p1-recon-loop-prompt.md` current (Fly v97, suite 1352, PR 3
   next), since it is the file the next session pastes and it still named a
   worktree this consolidation removed.

### Enforcement layer (this checkpoint)

Repaired `settings.local.json` from 20 to the canonical **24 hooks**. The
four gates built 2026-08-24/25 had never been wired.

---

## Key Decisions Made

### The per-row source cannot travel with the row
- **Choice:** Record statement anchors per UPLOAD, not per charge. Reverted
  the planned `Transaction.source_file` entirely.
- **Rationale:** A charge occupies a row in every file that prints it, at a
  different row in each; a field on the charge can only name one, and
  first-write-wins keeps the first. The planned design would have annotated
  the closing cycle only for the charges it introduced, leaving every repeat
  blank in the workbook Criss actually works from.

### Surface contradictions, dedupe nothing
- **Choice:** One `advisory` covers both the account-id and sign-inference
  cases; neither is refused or merged.
- **Rationale:** Deduping a contradiction picks a winner arbitrarily. Both
  uploads genuinely disagree, so both rows stand and the month says so.

### Do not merge the stale ledger; park it
- **Choice:** `parking/primary-clone-wip-2026-08-25`, pushed, never-merge.
- **Rationale:** Edited against a 216-commit-stale base, it would have
  reverted every register row shipped since July. Parking keeps it
  recoverable without that risk.

### Name-matching branches is necessary, not sufficient
- **Choice:** Added an ahead-count guard (keep anything >5 commits ahead).
- **Rationale:** A branch reused after its PR merged matches by name while
  still carrying unmerged work. Seven would have been wrongly deleted.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `web/service.py` | edit | `statements[]`, anchors, advisory, drop-guard, writeback selector |
| `output/sheet_writeback.py` | edit | anchor-scoped writes |
| `web/app.py` | edit | route gate lift, `?file=`, job warning channel |
| `matching/types.py` | edit | documented why the file is not on the charge |
| `tests/test_statement_append.py` | new | 16 tests, all mutation-proven |
| `docs/api-contract.md` | edit | `statements[]` pinned on both payloads |
| `status/p1-improvement-backlog.md` · `p1-expense-reconciliation.md` | edit | round recorded |
| `status/p1-recon-loop-prompt.md` | edit | brought current: v97, 1352, PR 3 next |
| `deliverables/rome-2026-leadgen/**` | new | 72 salvaged files + provenance README |
| `.claude/settings.local.json` | repair | 20 → 24 hooks wired |

---

## Current Status

Backend live on Fly **v97**, suite **1352 passed / 2 skipped**, calibrate
exit 0. `main` at `d0d67289`, clean, 0 open PRs. Repo is the primary clone
plus `agentic-ops1-deploy` only.

brisken platform: unknown plan, ops/mo not assessed. comms-log 4 days stale,
but this session held **no client conversations**, so nothing from it is
unlogged.

---

## Next Steps

1. **PR 3, the coverage surface** — per-card coverage in the batch view, the
   month page's statement panel, per-card sections in the reconciliation
   report. The backend selector (`?file=`) exists; the SPA renders neither it
   nor `statements[]`.
2. **Make the SessionStart heal actually heal.** It ran `wire-hooks --ensure`
   and reported 20/20 while the contract is 24. See Open Questions.
3. Owner-side, unchanged: `intake.known_senders` empty on production; three
   pooled Hostinger invoices for 2026-07; card registry entity gaps.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`

### Open Questions
- ~~Why did SessionStart's `wire-hooks.py --ensure` report "intact
  (20/20)"?~~ **Answered at close.** `--ensure` is not weaker than
  `--write` and is not buggy: it validated 20/20 against its OWN checkout's
  contract, because the primary clone was 216 commits behind and its
  `EXPECTED_HOOK_SCRIPTS` listed 20. The four newer gates were not unwired
  and undetected, they were absent from the contract being checked. Verified
  by diffing `tools/wire-hooks.py` at `ce83d1f8` (20 scripts) against
  `origin/main` (24). The root cause is the stale checkout, which this
  session's consolidation fixed; the same clone now wires 24/24. The session
  brief had already documented this failure mode, and it was logged as an
  open question anyway.
- Seven sibling `claude` sessions from 2026-08-24 are still running. One
  resuming will find `main` where its branch used to be.

### Working Notes
- The writeback test initially did **not** bite: it asserted the workbook's
  own vendor column, which a wrong-file write never touches. Rewritten to
  read the appended column. `regress_check.py` caught it.
- 16 files on the old branches looked like unmerged work but were deliberate
  deletions (Jinja UI at v31, `zoho/client.py`, meji corporate-sample PR
  #192, smart-trading deck via TC story alignment). Each checked against its
  own deletion commit.
- `leadgen-task-6` on main was OLDER than the branch; the salvage upgraded
  main to the 2026-07-14 Calvin clip v3.
- Recovery manifest for all 377 deleted branches:
  `%TEMP%/claude/branch-recovery-manifest.tsv`.

### Reference Materials
- PRs #636, #638, #639, #640, #641, #403 · closed: #430, #537
- `brisken-expense-recon.fly.dev` (v97) · SPA `brisken-reconcile-dash.lovable.app`

---

## How to Continue

Cut a fresh worktree from `origin/main` (the per-round worktrees are gone),
paste `p1-recon-loop-prompt.md`, and start PR 3.

---

## Strategic Feedback

### What Worked Well This Session

- **Mutation-proving every guard.** Nine mutations, each red under its own.
  It caught a test that asserted a constant, which is exactly the failure the
  house loop exists to prevent.
- **Re-deriving the user-facing scenario in adversarial review.** The
  `source_file` design error passed its own tests and its own mutation proof.
  Only walking "what does Criss actually download" exposed it.
- **Rescue-before-destroy ordering.** Every irreversible step was preceded by
  landing the at-risk content on `main` first.

### Suggestions

- **Stop concluding from a cheap probe without checking the probe.** Three
  times today a grep or a one-shot command was reported as fact and was
  wrong: 197 delete "failures" (trailing CR from Python's newline
  translation), "0 hooks wired" (grepped the wrong file), "4 scripts not on
  main" (malformed `cat-file`). Each cost a cycle and each would have gone
  into a checkpoint as a false claim. The habit to build: when a probe
  returns a surprising absolute, verify the probe before believing it.

### System Health

- The enforcement layer was **inert for this entire session** and SessionStart
  said otherwise, because a stale checkout can only validate its own stale
  contract. Now repaired to 24/24, and the root cause is closed by the same
  consolidation: the primary clone is on `main`, so its contract is the
  trunk's. The standing risk is any long-lived checkout that drifts, since
  its self-heal will keep reporting intact against whatever it last knew.
- Autonomy: **0 corrections**. Two decision rounds were requested on genuine
  forks (PR #430's fate and the stale ledger; the lead-gen output), plus one
  owner-directed task change (consolidate the repo). Fully autonomous
  execution otherwise.

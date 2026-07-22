# Checkpoint: Optimize Loop S-Series Implementation

**Date:** 2026-07-22
**Status:** S2–S5 + both general items SHIPPED (9 PRs merged). S1 deliberately not built — planned metric measured and rejected.

---

## Summary

Implemented the structural backlog from the 2026-07-22 optimize-loop audit
(`docs/2026-07-22 - Optimize Loop Audit + Hardening/`). Nine PRs merged; the
harness moved off self-advice for the first time (`asset kind 0/4 production`
→ `2/6`) and `page-weight.py` went from never-executed to reused across two
runs. S1 was NOT built: the planned metric was measured and found to have no
gradient.

---

## What Was Done This Session

### Runs (the metric that mattered)
1. **`platform-alpha-research-weight`** (PR #326) — 262,197 → 225,422 B
   (−14.0%) across 8 pages. First run ever against a production asset; first
   execution of `page-weight.py` in any run.
2. **`platform-openwebui-weight`** (PR #328) — 219,045 → 198,371 B (−9.4%)
   across 8 pages. Same scorer and guards, zero code changes, structurally
   different page set. This is what makes the scorer demonstrably generic.

### Machinery
3. **`tools/guard-text-preserved.py`** (PR #324) — generic anti-content-deletion
   guard for weight runs. Pins rendered text to a locked digest; minification
   and comment-stripping pass, deleting or rewording copy fails.
4. **Engine lock-on fix** (PR #325) — `cmd_start` staged only the manifest and
   `results.tsv`, leaving a declared `guard_files` DATA file untracked, so the
   first `round` always aborted.
5. **S4 timestamp column** (PR #329) — 7th `results.tsv` column, stamped in the
   single append path; `--scoreboard` reports median minutes/round.
6. **S2 guard pin registry** (PR #331) — `tools/guard-pins.json`,
   `pin_scorer.py pin-guard`, lock-on hash cross-check. 8 guards pinned.
7. **S3 cross-run recall** (PR #333) — `optimize_overview.py --prior-art
   PROJECT` plus a `## Dead ends` / `## Sensitivities` heading contract, wired
   into `comd_optimize` Step 2.0 and Step 7.
8. **check-index scans `tools/scorers/`** (PR #327) — scorer contract clause 7
   had no tripwire. 73 → 78 tools covered.
9. **project-status staleness guard** (PR #335) — `--sweep-stale` no longer
   nags about files already refreshed on `origin/main`.

### Audit closure
10. Recovered all **38** candidate findings from
    `wf_93baba76-0a0/journal.jsonl` (8 finder lenses returned; 37 of 48 agents
    died before reporting). Verified the actionable ones by source read rather
    than a second fan-out.

---

## Key Decisions Made

### S5 before S1
- **Choice:** Ran the cheap generic-path proof first, as the brief recommended.
- **Rationale:** It found the `cmd_start` defect within one round. Had S1 gone
  first, that defect would have surfaced inside a much more expensive run.

### Did NOT build the S1 scorer
- **Choice:** Measured the planned metric, found it unusable, wrote the
  redesign to memory instead of shipping a scorer.
- **Rationale:** `match_month` puts 1 receipt in `matches` and 43 in
  `judgment_required`; all 31 confirmed labels land in the deferred bucket, so
  a labels-vs-`matches` scorer scores 3/95 with almost no gradient. The
  deterministic matcher is *designed* to defer to the LLM. A scorer that
  measures the wrong thing is exactly what the lock model exists to prevent.

### A content guard before the first weight run
- **Choice:** Built `guard-text-preserved.py` before running S5, rather than
  relying on `validate-html.py` alone.
- **Rationale:** Deleting content makes a page smaller and still valid HTML.
  Proven necessary: r7 of run 1 and r6 of run 2 both deleted a whole
  `<section>`, `validate-html` passed both, the text guard failed both.

### Run 2 deliberately scored lower than run 1
- **Choice:** Declined the 9,516 B full-minification lever on openwebui.
- **Rationale:** Run 1's SUMMARY flagged it as an owner decision not to be
  inherited across client sites. Honoring that is the test of whether a
  Sensitivities section is load-bearing or decorative.

### Guard pins as a separate registry file
- **Choice:** `tools/guard-pins.json` keyed by repo-relative path, not an
  extension of `PINS.json`.
- **Rationale:** `PINS.json` is keyed by bare filename inside one directory and
  every consumer assumes that shape; guards live anywhere under `tools/`.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/guard-text-preserved.py` | Created | Anti-content-deletion guard |
| `tools/tests/test_guard_text_preserved.py` | Created | 16 tests, 3 mutations |
| `tools/guard-pins.json` | Created | Reviewed guard hash registry (8 pins) |
| `tools/tests/test_guard_pins.py` | Created | CI blocks a drifted guard pin |
| `tools/optimize_run.py` | Modified | Lock-on commit fix, timestamp column, guard-pin cross-check |
| `tools/optimize_overview.py` | Modified | Timing metric, `--prior-art` |
| `tools/pin_scorer.py` | Modified | `pin-guard`, guard validation in `check` |
| `tools/check-index.py` | Modified | Scans `tools/scorers/` |
| `tools/project_status.py` | Modified | Origin-aware staleness suppression |
| `tools/tests/test_optimize_run.py` | Modified | +5 tests (lock-on, timestamps, guard pins) |
| `tools/tests/test_optimize_overview.py` | Modified | +8 tests (timing, prior-art) |
| `tools/tests/test_check_index.py` | Modified | +3 tests |
| `tools/tests/test_project_status.py` | Modified | +5 tests |
| `tools/INDEX.md` | Modified | 4 rows updated/added |
| `docs/optimize/RECIPES.md` | Modified | Guard-pin stanza |
| `.claude/rules/rule_optimize_loop.md` | Modified | §2 + seams cover guards |
| `.claude/commands/comd_optimize.md` | Modified | Step 2.0 prior-art, Step 7 heading contract |
| `docs/optimize/platform-alpha-research-weight/**` | Created | Run 1 manifest, journal, SUMMARY |
| `docs/optimize/platform-openwebui-weight/**` | Created | Run 2 manifest, journal, SUMMARY |
| `platform/public/clients/alpha-research/*.html` | Modified | Run 1 asset (8 pages) |
| `platform/public/clients/openwebui-email-compliance/*.html` | Modified | Run 2 asset (8 pages) |
| `~/.claude/.../memory/project_optimize_s1_recon_scorer_design.md` | Created | S1 redesign |

---

## Current Status

All 9 PRs merged and verified on `origin/main`. No optimize run left locked
(no `run.json`). No leftover worktrees or branches from this work.

Scoreboard on merged main:

```
runs                  6 total | 6 CLOSED
experiment rounds     36        keep rate 22/36 (61%)
minutes per round     n/a (0/6 runs carry timestamps)
closed with SUMMARY   6/6
asset kind            2/6 production (4 planning-model, 2 production)
scorer reuse          5 scorer(s) over 6 run(s); reused: page-weight.pyx2
checkout completeness matches origin/main
```

Both "done looks like" criteria met. `minutes per round` reads n/a because all
6 runs predate the timestamp column; the next run will populate it.

---

## Next Steps

1. **S1 — build `recon-match-accuracy.py` against the corrected metric.** The
   composite, asset, load path and held-out split are in
   `project_optimize_s1_recon_scorer_design.md`. Needs the `SCORER_LOCK_ALLOW`
   seam and a user order.
2. **Ledger backlog.** This session's friction rows are in this PR, but the
   register still lacks rows from several sibling sessions running in the
   shared tree today.
3. **Optional: revisit run 1's r4 minification.** Flagged as the owner's call;
   reverting is one commit and costs 9,516 B of the 36,775.
4. **Doctrine gap worth closing:** `--probe` means "expect DISCARD" and has no
   way to express "expect a better score I should still reject on the
   simplicity criterion". Round 4 of run 1 hit exactly that.

---

## Context for Next Session

### Files to Read First
- `docs/optimize/platform-alpha-research-weight/SUMMARY.md` — the dead ends and
  sensitivities any future weight run must inherit
- `~/.claude/projects/.../memory/project_optimize_s1_recon_scorer_design.md`
- `docs/optimize/RECIPES.md` — guard pins + constructed-metric protocol
- `.claude/commands/comd_optimize.md` — Step 2.0 is new

### Open Questions
- Should run 1's full-CSS-minification round be reverted? Owner call.
- Does the S1 composite weighting (1.0 / 0.3 / −2.0) survive contact with the
  data, or does it need calibration before pinning?

### Working Notes

**The engine defect S5 found.** `cmd_start` exempts `docs/optimize/<tag>/` from
its clean-tree check but staged only `RUN.md` + `results.tsv`. A guard's
baseline DATA file was left untracked, so the first `round` aborted with
"changes OUTSIDE the asset scope", and `guard_shas` anchored content git did
not track. It survived four runs because every prior guard's `guard_files`
entries were already-tracked `.py` files. Reachable only when a guard carries
locked reference data — exactly what a held-out guard needs.

**Scorer property that kills the obvious lever.** `page-weight.py` calls
`measure()` per file and sums subtotals; `measure()` counts every local
`<link rel=stylesheet>`. A shared stylesheet is counted once per page, exactly
like an inline copy. Extraction is score-neutral **by construction**. The 80 kB
of duplicated CSS looks like the biggest target and is unreachable through this
metric. Both runs recorded it; `--prior-art` now surfaces it.

**Biggest lever is markup, not CSS.** Run 1: markup indentation −14,885 B after
three CSS rounds. Run 2: −10,840 B, 2.4× the next-largest round. Held across
two differently-built sites.

**S1 measurement (do not re-derive).** With the shipped
`config/match-tuning.json` on `01-03-2026_ER-00214` (158 tx, 45 receipts):
`matches`=1, `judgment_required`=43, `ambiguous`=0. All 31 confirmed labels in
the deferred bucket; only 8 with the correct transaction as the deferred
candidate. Across 6 months: 95 confirmed, 46 no_charge, 77 excluded.

**Environment gotcha that cost three cycles.** The automation `.venv` python
needs Windows-form paths (`C:/...`); MSYS `/c/...` fails with
FileNotFoundError. `MSYS_NO_PATHCONV=1` is needed for `git show
origin/main:.claude/...` (MSYS rewrites the colon and slashes).

### Reference Materials
- `~/.claude/plans/sharded-snuggling-riddle.md` — the weakness register
- `docs/2026-07-22 - Optimize Loop Audit + Hardening/Checkpoint.md`
- Workflow journal with all 38 candidates:
  `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/0b9ea807-.../subagents/workflows/wf_93baba76-0a0/journal.jsonl`

---

## How to Continue

The harness is in a good state; nothing is half-shipped. The single highest-value
next move is S1 with the corrected metric — it is the only remaining item that
moves `asset kind` further and it is the first target where a genuine held-out
guard (RECIPES rule 3) is possible. Read the memory file first; do not rebuild
the metric from the plan's original assumption.

---

## Strategic Feedback

### What Worked Well This Session
- The brief's ordering (S5 before S1) was correct and paid off immediately: the
  cheap run found an engine defect that would have been far more expensive to
  hit inside S1.
- The stop-hook B1 gate fired on a real deferral of mine and converted "here
  are the remaining items if you want them" into four more shipped PRs. That
  gate earned its keep.

### Suggestions
- Five sibling Claude sessions on one box starved `preflight-hooks.py --full`
  to the point where it took 5x its normal runtime and I abandoned two runs.
  Consider a lighter default (`ruff` + the touched suites) with `--full`
  reserved for pre-push on hook changes.

### System Health
- **Mutation testing needs an applied-assertion by default.** Three separate
  times this session a mutation silently failed to apply and the suite reported
  a false pass. A `tools/` helper that asserts the substitution count before
  running the suite would make "mutation-tested" mean something. Logged as
  `infrastructure-deferred` if it recurs.
- Autonomy score: 6 human interventions this session (elevated — but 5 were
  self-detected, 1 was the stop-hook).

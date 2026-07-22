# Checkpoint: Optimize Loop Audit + Hardening

**Date:** 2026-07-22
**Status:** 4 quick wins shipped and merged; structural items S1–S5 open

---

## Summary

Ran a 10-lens weakness audit of the `/comd_optimize` autoresearch harness to
raise its output (score improvements shipped per unit time) and effectiveness
(quality of kept wins), then shipped the four Band-1 quick wins the audit
produced. Headline finding: the engine was never the bottleneck (~55 s/round);
target supply and per-target authoring cost are, and three latent recovery-path
bugs would have bitten the first long or cross-session run.

---

## What Was Done This Session

### Audit
1. Loaded the whole harness (engine, both gates, glob helper, pin tool, scorer
   contract, RECIPES, all 4 run journals, test suites) and measured a real
   Phase-1 baseline from committed artifacts.
2. Fanned out 10 audit lenses via an ultracode Workflow with an adversarial
   verify stage. The fan-out **died ~5 min in**: 8/10 lens batches returned
   (38 candidate findings) but only 3/38 verifications ran. Not detected for
   ~76 min. Every finding that reached the plan was therefore re-verified
   against source by hand, independent of the agents.
3. Wrote the plan to `~/.claude/plans/sharded-snuggling-riddle.md`.

### Shipped (4 PRs, all merged CI-green)
1. **#319 `735d8cd`** — three recovery-path correctness fixes in
   `tools/optimize_run.py` + 4 regression tests.
2. **#320 `838f554`** — `optimize_overview.py`: STALE CHECKOUT detection,
   `--scoreboard`, `--sweep --once-per-day` wired into SessionStart.
3. **#321 `c27b130`** — `round --probe` + convergence doctrine (Step 5b).
4. **#322 `c438293`** — scorer authoring kit: conforming skeleton +
   `test_scorer_contract.py`.

---

## Key Decisions Made

### E2 recovery: commit the pending row, do not re-score
- **Choice:** When `resume` finds an experiment commit with an uncommitted
  `results.tsv` row for round *n*, commit that row rather than re-scoring HEAD.
- **Rationale:** The row is the crashed process's own already-guard-gated
  verdict, so committing it is exactly what the crash interrupted. Re-scoring
  would have changed the semantics of the existing dangling-experiment case
  (`test_resume_logs_dangling_experiment_as_crash`) and added risk for no gain;
  the repro check at the end of `resume` still catches a lying row.

### Did NOT raise `consecutive_reverts` 5 → 8 (plan deviation)
- **Choice:** Kept the default at 5; documented that `--probe` replaces the
  raise-the-limit workaround.
- **Rationale:** With probes excluded from the counter the root cause is fixed,
  and 5 consecutive *genuine* failed climbs is a reasonable plateau signal.
  Picking 8 would have been changing a stop-discipline default with no evidence
  behind the new number.

### Action catalog is a lock-on WARNING, not a refusal (plan deviation)
- **Choice:** `start` warns when `## Action catalog` is missing; still locks on.
- **Rationale:** It is a yield concern, not an integrity one, and the engine
  already uses non-fatal warnings for setup-quality issues ("asset globs match
  zero files"). A hard prose gate invites an empty stub heading, which is worse
  than no heading.

### Scorer template lives outside `tools/scorers/`
- **Choice:** `docs/optimize/scorer-template.py.txt`.
- **Rationale:** `pin_scorer.scorer_files()` globs `tools/scorers/*.py`; a
  template there would fail CI as UNPINNED and be flagged by the new contract
  suite. `test_scorer_pins` staying green is the proof.

### Contract test probes with a bogus path, not zero arguments
- **Choice:** Each scorer must exit non-zero for a nonexistent asset.
- **Rationale:** Universal (a future scorer may legitimately take no args) and
  it targets the clause that actually protects the loop: the engine reads exit
  0 as "this score is real".

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/optimize_run.py` | Modified | E1 idle-banking + `active_minutes`; E2/E3 `cmd_resume` restructure; `--probe`; action-catalog warning; `manifest_body()` |
| `tools/tests/test_optimize_run.py` | Modified | 7 new tests (3 recovery bugs + budget guard + 2 probe + catalog warning) |
| `tools/optimize_overview.py` | Modified | `origin_run_tags()`, `asset_kind()`, `print_scoreboard()`, `run_sweep()`, keeps counter |
| `tools/tests/test_optimize_overview.py` | Modified | 6 new tests (scoreboard, asset split, staleness, UNKNOWN, sweep silent/loud) |
| `tools/tests/test_scorer_contract.py` | Created | Executable scorer contract (4 clauses × 5 scorers + guard) |
| `docs/optimize/scorer-template.py.txt` | Created | Conforming scorer skeleton + paired-guard notes |
| `tools/scorers/README.md` | Modified | Authoring section pointing at the template + contract test |
| `.claude/commands/comd_optimize.md` | Modified | Step 5b: boundary probes + pegged-at-bound tell |
| `docs/optimize/RECIPES.md` | Modified | Action catalog required in skeleton; do-not-raise-the-limit note |
| `tools/wire-hooks.py` | Modified | SessionStart entry for `optimize_overview.py --sweep --once-per-day` |
| `tools/INDEX.md` | Modified | Updated rows for `optimize_run.py` and `optimize_overview.py` |

---

## Current Status

`origin/main` at `c438293`. Full CI gate green on merged main: ruff + INDEX +
**569 passed**, 3 skipped. Verified live on merged main: `--scoreboard` renders,
`--probe` is in `round --help`, sweep is silent on a clean fleet.

All four audit worktrees removed. No optimize run is active; nothing is locked
beyond the always-on scorer surface.

**The scoreboard's own headline reads `asset kind: 0/4 production`** — every run
to date optimized a planning model the agent authored in the same PR chain.

---

## Next Steps

1. **S1 (needs an explicit user order — touches `tools/scorers/`):** build
   `tools/scorers/recon-match-accuracy.py` against the 218 human-accepted
   expense-recon label rows, 4 months train / 2 held-out, with the held-out
   floor as the repo's first true RECIPES rule-3 guard. Ships as scorer-PR then
   run-PR. This is what moves `% production assets` off zero.
2. **S5 (cheap, do before S1):** a `page-weight` run on a real
   `platform/public/clients/<slug>/` set — the generic multi-file-asset +
   `validate-html` guard path has never executed end to end.
3. **S2:** extend the pin registry to guard scripts (guards carry the whole
   anti-overfit floor but sit outside the scorer lock and in no pin registry).
4. **S3:** setup-time prior-art step + machine-readable SUMMARY headings.
5. **S4:** timestamp column in `results.tsv` (round timing is currently
   unrecoverable after squash-merge for 3 of 4 runs).
6. **Re-run the audit's verify phase** — 35 of 38 candidate findings never got
   adversarially verified. Several map to S2/S3/S4.
7. **Ledger hygiene:** today's `docs/` ledger (INDEX, friction-register, session
   log, 8 checkpoint folders across 6 sessions) is uncommitted in the shared
   tree. Needs one coordinated `docs/...` PR once sessions quiesce.

---

## Context for Next Session

### Files to Read First
- `~/.claude/plans/sharded-snuggling-riddle.md` — the full plan, incl. the
  confirmed weakness register (E1–E4, P1–P6, M1–M3) and the rejected list
- `tools/optimize_run.py` — engine, now with idle-banking + probe semantics
- `docs/optimize/RECIPES.md` + `.claude/commands/comd_optimize.md` Step 5b
- `tools/scorers/README.md` (authoring section) + `docs/optimize/scorer-template.py.txt`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/labeling.py`
  — the anti-circular label design S1 builds on

### Open Questions
- Does S1 go before or after S5? S5 is cheaper and de-risks the generic asset
  path that S1's guard wiring depends on, but S1 is the higher-integrity target.
- Should `results.tsv` gain a timestamp column (S4) before more runs land, given
  the schema is append-only and old journals must stay parseable?

### Working Notes
- **The stale-checkout trap is real and it bit twice.** This checkout's `main`
  was 13 PRs behind origin. The first fit-check I gave the user reported "1
  closed run" when the true figure was 4, and `INDEX.md` appeared to be missing
  rows for 3 scorers when registration was actually complete on origin. Both
  were artifacts. Always `git show origin/main:<path>` for `docs/optimize/**`
  and `tools/scorers/**` when the checkout may be behind. PR #320's STALE
  CHECKOUT warning is the structural fix.
- **Engine files had NOT drifted** between stale-local and origin/main
  (verified by `git diff --stat main origin/main`), which is why the line-level
  analysis held.
- All 5 pinned scorers already satisfy every contract clause, including exiting
  2 on a bogus asset — the contract test codifies existing practice rather than
  forcing a migration.
- The workflow fan-out is at
  `.../subagents/workflows/wf_93baba76-0a0/journal.jsonl` — 38 candidate
  findings are recoverable from it if the verify phase is re-run.

### Reference Materials
- PRs: #319, #320, #321, #322 (all merged)
- karpathy/autoresearch discussion #322 (the code-level-ACL basis)

---

## How to Continue

`/comd_resume` then read the plan file. The next substantive move is S1 or S5;
S1 needs an explicit user order because it writes into `tools/scorers/`. Nothing
is locked and no run is active, so the repo is in a clean state to start either.

---

## Strategic Feedback

### What Worked Well This Session
- Writing the audit prompt first, then executing it, produced a much sharper
  scope than going straight at "improve the optimize loop" would have. The
  inviolate-core list in particular stopped several plausible-but-wrong
  proposals before they cost anything.
- The fail-then-pass discipline paid for itself: all three engine bugs were
  confirmed to fail on the parent commit before the fix, so the tests are known
  to bite rather than assumed to.

### Suggestions
- The shared working tree now has 6 concurrent sessions appending to
  `docs/INDEX.md`, `docs/friction-register.md` and one session log. That is well
  past what append-in-place tolerates. Worth a rule: session logs get one file
  per session (`docs/sessions/2026-07-22-{n}.md`) merged by a tool, instead of
  six writers on one file.

### System Health
- Autonomy score: 2 human interventions this session.
- The `optimize_overview` blind spot is a general class, not a one-off: **any
  tool that derives state from the working tree silently under-reports on a
  stale checkout**. `project_status.py --sweep-stale` and `check-index.py` have
  the same shape and no equivalent guard.
- Background Workflow fan-outs have no liveness signal. Mine died silently and
  I consumed partial output for over an hour. There is no structural detector
  for "the background phase you are relying on is dead" — the Monitor tool
  exists but nothing prompts its use.

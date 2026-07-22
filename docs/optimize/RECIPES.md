# Optimize-Loop Field Recipes

Pointing the autoresearch harness at a new field is a fill-in-the-manifest
exercise, not a redesign. Pick the nearest stanza, copy its manifest
skeleton into `docs/optimize/<tag>/RUN.md`, and run `/comd_optimize`.
Lock model: `rule_optimize_loop.md`. Engine: `tools/optimize_run.py`.

Every scorer obeys `tools/scorers/README.md` (last stdout line
`SCORE: <number>`, `# direction:` header, exit 0 only on a real
measurement, deterministic) and is hash-pinned in `PINS.json` before any
run will accept it.

| Domain | Scorer pattern | Assets | Guards |
|---|---|---|---|
| Web page weight | `page-weight.py` (shipped) | the page + its css/js globs | `validate-html.py` on the page |
| Web perf (Lighthouse) | wrapper printing the perf score, median of 3 | page/css/js | `validate-html.py`, `axe-check.cjs` |
| Code performance | benchmark wrapper printing `SCORE: <ms>`, median-of-N inside | source globs | the full test suite |
| Prompt / rules accuracy | fixture-accuracy scorer: % correct vs labeled ground truth | the prompt/rule file | held-out-slice score floor (see below) |
| Video QC | `video-gen` rubric mean via its qc harness, or ffprobe-derived | spec / composition config | duration+codec sanity check |
| Docs / content quality | constructed metric (below) | the doc files | `validate-output.py`, voice checks |

## Guards are load-bearing

A guard is a pass/fail argv command (no shell operators; forward slashes).
The engine discards an experiment that fails ANY guard even when its score
beats the current best (evo's gate rule) - that is what stops "faster but
broken". Point guards at shared validators (`tools/validate-*.py`) where
possible: they are high-visibility files, so a stop -> weaken-guard ->
restart move shows up loudly in the PR diff.

## Constructed metrics (fields without a natural scalar)

When no honest number exists yet (goal-md protocol):

1. **Build the ruler first.** The fitness script is its own deliverable,
   shipped via its own PR and pinned BEFORE any optimize run. The engine
   structurally refuses unpinned scorers, so this ordering is enforced,
   not aspirational.
2. **Dual-score when the instrument is unreliable.** If the scorer itself
   could be wrong (a heuristic linter, a parser over messy input), ship a
   second scorer that measures the instrument (e.g. false-positive rate
   on a labeled sample). The agent may improve measurement reliability
   only through the normal scorer-authoring PR path - never mid-run, and
   it never redefines what "good" means.
3. **Held-out score floor, mandatory.** Split the ground truth; the run's
   scorer sees the training slice, and a GUARD checks the held-out slice
   never drops below its baseline. This is the anti-overfit lock: the
   Shopify Liquid autoresearch PR (53% "faster", never merged, flagged as
   benchmark overfit) is the cautionary precedent.
4. **No LLM-judge scores.** An opinion is gameable; the honest-number fit
   check refuses it. If judgment is genuinely required, the target does
   not fit this harness - use human review, not a fake metric.

## Manifest skeleton (copy, then edit)

```yaml
---
tag: <dirname>             # unique forever; starts with the project slug
project: <slug>            # grouping key for optimize_overview.py (see below)
goal: >
  One sentence: what number moves, and any hard floor that must not break.
scorer: tools/scorers/<name>.py
scorer_args:
  - <asset path or fixture dir>
direction: minimize        # must match scorer header AND PINS.json
assets:
  - <glob - the ONLY writable surface>
guards:
  - uv run tools/<validator>.py <args>
guard_files:
  - tools/<validator>.py
budgets:
  rounds: 10
  wall_clock_minutes: 120
  score_timeout_seconds: 300
  max_rework_attempts: 2
mode: converge             # converge | continuous | supervised
stop:
  goal_score: <number>     # optional
  consecutive_reverts: 5   # confirmation probes do NOT count (see below)
---

Prose: why this run, what a reviewer should look at, and the action
catalog (prioritized hypothesis menu with expected impact). Write the
catalog: RUN.md locks at lock-on, so a run that starts without one can
never add a structured hypothesis queue, and the engine warns at `start`
when the section is missing. In every run so far the keeps mapped roughly
1:1 onto catalog items.
```

**Do not raise `consecutive_reverts` to make room for boundary probes.**
That was the workaround before `round --probe` existed (gtm-v2 and
pricing-tiers each ran 4 planned discards in a row against a limit of 5,
and every run after v1 quietly set it to 6). A probe journals as `probe`
and is excluded from the PLATEAU counter, so the default is correct as
shipped. Raise the limit only when genuine failed climbs, not
confirmations, are tripping it.

## Many projects, one oversight surface

The engine allows ONE active run per checkout (`.claude/optimize/run.json`
is a singleton) and all journals share the flat `docs/optimize/<tag>/`
namespace. Scaling to a multitude of projects is a naming convention plus
worktrees plus one derived tool - no engine changes:

1. **Namespace by project.** Every manifest carries `project: <slug>`
   (client slug, `sys`, `platform`, `local-web`) and its `tag` starts with
   that slug (`brisken-recon-v1`, `local-web-physio-weight`). Tags are
   unique forever - a closed run's directory on main IS the historical
   record, and the engine refuses reused tags (fresh-branch rule), so
   version the tag (`-v2`) instead of recycling it.
2. **One worktree per concurrent run.** Parallel runs across projects
   each get their own worktree: `git worktree add --detach
   ../agentic-ops1-opt-<tag> origin/main`, then write the manifest and
   `start <tag>` inside it (the engine creates `optimize/<tag>` from
   there; state and locks are per-worktree). Never two runs in one
   checkout. Caveat: the Write/Edit-layer lock hooks cover the primary
   checkout; in worktrees the engine-layer locks (per-round hash
   re-verification, dirty-tree recovery) are the enforcement - they held
   under a live tamper test 2026-07-17.
3. **Oversee from one place:** `uv run tools/optimize_overview.py
   [--project SLUG]` derives the fleet view live - journaled runs on the
   current checkout grouped by `project:`, ACTIVE runs found via
   `git worktree list` + their run state, and a WARNINGS section for runs
   that died without `stop` (resume or stop them) and closed runs missing
   `SUMMARY.md`. There is deliberately no hand-maintained index file; a
   derived view cannot rot.
4. **Lifecycle hygiene.** A run ends in exactly one of two states: shipped
   (PR from `optimize/<tag>` with manifest + results.tsv + SUMMARY.md,
   then delete the worktree and branch) or dead-end (same PR, journal
   only - a documented dead end prevents re-running the same
   experiments). INTERRUPTED in the overview is a defect to clear, not a
   third state.

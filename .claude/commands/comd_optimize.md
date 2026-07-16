---
description: Autonomous hill-climb loop; iterate an asset against a locked scorer, keep winners, revert losers, journal every round (Karpathy auto-research pattern)
argument-hint: {scorer} {asset...} [--rounds N] [--goal SCORE]
---

# Optimize

Run the three-part auto-research loop: a locked SCORER (the honest number),
an ASSET the agent may freely mutate, and a JOURNAL of every experiment.
This is the maximization counterpart to skil_build-test-fix's convergence
loop: build-test-fix iterates until something WORKS; optimize iterates a
working asset until it scores BETTER.

## Context

- Arguments: $ARGUMENTS
- Scorer contract + lock semantics: `tools/scorers/README.md`
- Enforcement: `scorer-lock-gate.py` denies agent edits to existing scorers

## Parse Arguments

- **`{scorer}`** (required): a registered `tools/scorers/{name}.py`
- **`{asset...}`** (required): the file(s) the loop is allowed to mutate
- **`--rounds N`** (optional, default 10): experiment budget
- **`--goal SCORE`** (optional): stop early when the score passes this value

## Step 1: Fit check (hard gate)

Refuse the run unless all three must-haves hold:

1. The scorer emits a real, objective number for this asset (no LLM-judge
   metrics; gameable scores violate the honest-number principle).
2. One scoring run completes in seconds-to-minutes.
3. The asset is local files the agent can edit directly.

Additionally refuse if the asset's "score" depends on any live invasive
surface (real sends, live campaigns, production mutations). Optimizing
against live-system feedback is out of scope; rule_instantly_invasive and
the Graph invasive-action gate apply unchanged.

## Step 2: Pin the harness

1. Record the scorer path AND its content hash (`git hash-object`). Every
   subsequent score MUST come from this exact scorer; if the hash changes
   mid-run, abort and surface it.
2. Confirm a clean working tree for the asset files (commit or stash noise
   first) so revert = `git checkout -- {asset}` is exact.
3. Run the scorer once. This is the BASELINE. A failed baseline run
   (non-zero exit) means the harness is broken; fix the harness first,
   never start the loop on a guessed score.

## Step 3: The loop (per round, up to N)

1. **One hypothesis.** State in one sentence what change should move the
   score and why.
2. **One change.** Apply it to the asset only. Never touch the scorer, the
   journal's past rounds, or files outside the declared asset set.
3. **Re-score** with the pinned scorer. Non-zero exit = the change broke
   the asset; treat as a loss.
4. **Keep or revert.** Better than the current best -> keep, this is the
   new baseline. Equal or worse -> revert to the last kept state.
5. **Journal the round** (see format below) BEFORE starting the next one.

A reverted experiment is a data point, not a failure: the
rule_behaviors 3-iteration escalation applies to HARNESS errors (scorer
crashes, revert failures), not to losing hypotheses. Stop conditions:
`--goal` reached, round budget exhausted, or 5 consecutive reverts with no
remaining distinct hypotheses (diminishing returns; note it and stop).

## Step 4: Journal

One file per run: `docs/optimize/{YYYY-MM-DD}-{target}.md`. Append-only
during the run. Frontmatter: scorer path + hash, asset list, baseline,
goal, rounds budget. Then one row per round:

```
| # | Hypothesis | Change | Before | After | Verdict |
|---|------------|--------|--------|-------|---------|
| 1 | inline critical CSS to drop render-blocking sheet | moved styles.css into <head> | 48211 | 41902 | KEPT |
```

Close with: final score vs baseline, kept-change summary, and what a human
should review.

## Step 5: Ship

Kept winners ship through the normal chain (rule_no_auto_commit): commit on
a feature branch with the journal, push, PR; the PR body cites baseline ->
final score so the reviewer sees the measured delta, and CI-green
auto-merge applies as usual. If nothing beat the baseline, commit only the
journal; a documented dead end prevents re-running the same experiments.

## Good first targets (fit-checked)

- Local page weight / Lighthouse on `workspace/projects/local-web/` and
  `platform/public/` pages (scorer: `page-weight.py`)
- Brisken expense-recon match accuracy against labeled fixtures (scorer to
  be built from Chris's ground-truth sample)
- Lead Desk mail classification accuracy against captured-message fixtures

Poor targets, do not accept: cold-email copy (reply-rate feedback is
weeks-slow and low-volume), anything scored by an LLM's opinion.

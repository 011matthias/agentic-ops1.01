---
description: Autonomous hill-climb loop; iterate an asset against a locked scorer inside a locked run manifest, keep winners, revert losers, journal every round (Karpathy auto-research pattern)
argument-hint: "{scorer} {asset...} [--rounds N] [--goal SCORE] | resume | stop"
---

# Optimize

Run the three-surface auto-research loop: locked INSTRUCTIONS (the run
manifest), a locked SCORER (the honest number), and the ASSET - the only
thing you may mutate. The mechanics (branch, commit, score, guards,
keep/revert, journal) are executed by `tools/optimize_run.py`, not by you:
you contribute hypotheses and edits. This is the maximization counterpart
to skil_build-test-fix's convergence loop: build-test-fix iterates until
something WORKS; optimize iterates a working asset until it scores BETTER.

Rule: `rule_optimize_loop.md`. Enforcement: `optimize-run-gate.py` (file
ACL while a run is active) + `scorer-lock-gate.py` + `tools/scorers/
PINS.json` (hash pins, re-verified every round).

## Context

- Arguments: $ARGUMENTS
- Scorer contract + pins: `tools/scorers/README.md`
- Field recipes + constructed metrics: `docs/optimize/RECIPES.md`
- Engine: `uv run tools/optimize_run.py {start|round|resume|stop|status}`

## Step 0: Resume check

If `.claude/optimize/run.json` exists, a run is active and the repo is
partially locked. NEVER start over it. `uv run tools/optimize_run.py
status`, then either continue its loop (Step 4), `resume` after a crash,
or `stop` it. Denied writes during a run are the gate working, not a bug;
the outs are `stop` or a user-ordered `OPTIMIZE_SCOPE_ALLOW=1`.

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

No registered scorer fits? That is the constructed-metric case: build the
fitness script FIRST as its own PR (RECIPES.md protocol: dual-score when
the instrument is unreliable; held-out score-floor guard for every
constructed benchmark), get it pinned, THEN return here. The engine
structurally refuses unpinned scorers.

## Step 2: Setup interview (Karpathy protocol)

0. **Read the prior art first:** `uv run tools/optimize_overview.py
   --prior-art <project-slug>`. It prints the `## Dead ends` and
   `## Sensitivities` of every previous run on that project. Inherit them in
   the manifest rather than rediscovering them: a dead end that cost a round
   once should cost zero rounds afterwards, and a sensitivity another run
   flagged (a lever it deliberately declined) must not be silently re-applied
   here. Say in the manifest prose which entries you inherited and which you
   are overriding, so a reviewer can see the transfer happened. Runs that
   predate the heading contract are named explicitly; read those by hand.

1. Agree a run tag with the user (short slug; `optimize/<tag>` must be a
   fresh branch).
2. Write the manifest `docs/optimize/<tag>/RUN.md` - YAML frontmatter:
   `tag`, `goal`, `scorer`, `scorer_args`, `direction`, `assets` (globs -
   your ONLY writable surface once locked), `guards` + `guard_files`
   (correctness commands; a guard fail discards even a score win),
   `budgets` (`rounds`, `wall_clock_minutes`, `score_timeout_seconds`,
   `max_rework_attempts`), `mode` (`converge` | `continuous` |
   `supervised`), `stop` (`goal_score`, `consecutive_reverts`). Copy the
   nearest skeleton from RECIPES.md. CLI args seed this: `{scorer}
   {asset...} [--rounds N] [--goal SCORE]`.
3. Confirm the manifest with the user (they are approving the lock scope),
   then proceed.

## Step 3: Lock-on

`uv run tools/optimize_run.py start <tag>`. The engine validates the
manifest against PINS and the scorer header, scores the BASELINE and runs
the guards BEFORE creating anything (a broken harness leaves no branch, no
state), then creates `optimize/<tag>`, commits the manifest, writes
`results.tsv`, and arms the file ACL. State plainly what is now locked and
what the baseline is. A failed baseline means fix the harness first; never
start a loop on a guessed score.

## Step 4: The loop (per round)

Read `git log --oneline -5` and the tail of `results.tsv` first - git is
your memory; do not re-run a journaled dead end.

1. **One hypothesis.** State in one sentence what change should move the
   score and why. If the round is a boundary probe (a predicted discard
   that confirms an optimum), say so and pass `--probe` (Step 5b).
2. **One change.** Edit asset files only. The gate denies everything else.
3. **Execute:** `uv run tools/optimize_run.py round --desc "<hypothesis>"`.
   The engine commits, scores under timeout, runs guards, keeps or reverts,
   and journals - in that order, deterministically.
4. **Read the verdict** and act on it:
   - `KEEP` - new baseline; next hypothesis.
   - `DISCARD` - data point, not a failure; next hypothesis.
   - `CRASH` - read `docs/optimize/<tag>/logs/r<N>.log`. Dumb typo: fix
     and re-run the round. Fundamentally broken idea: move on.
   - `guard failed` - you may fix WITHIN the round: edit assets, then
     `round --rework --desc "..."` (capped by `max_rework_attempts`).
5. The engine announces `GOAL REACHED` / `ROUNDS EXHAUSTED` /
   `WALL-CLOCK EXHAUSTED` / `PLATEAU`. Obey them per mode (Step 6).

A reverted experiment is a data point, not a failure: the rule_behaviors
3-iteration escalation applies to HARNESS errors (engine aborts, scorer
crashes on the baseline, hash drift), not to losing hypotheses.

## Step 5: Keep/revert judgment (simplicity criterion)

All else being equal, simpler is better. A small improvement that adds
ugly complexity is not worth it; conversely, removing something and
getting equal or better results is a great outcome - that is a
simplification win. Weigh the complexity cost against the improvement
magnitude: a tiny gain from hacky code is a discard (`round --discard
--desc "why"`); an equal score from strictly simpler code is a keep
(`round --simplification --desc "..."`).

## Step 5b: Verifying convergence (do this before you claim it)

A run that stops climbing has not found an optimum; it has run out of
ideas. Two idioms separate the two, and both are cheap:

**Boundary probes (`round --probe`).** Before declaring convergence, spend
rounds deliberately PREDICTING a discard: push a kept lever further, pull
it back, drop a component, collapse two settings into one. State the
prediction and the reason in `--desc` ("expect DISCARD: past the pool cap
the extra hours reinvest neutrally, so 32 is the knee not a peg-to-max").
A probe that discards as predicted converts "I stopped improving" into "I
tested the boundary and it held". A probe that IMPROVES is the most
valuable round the loop can produce: the optimum was not where you thought,
and the engine keeps it and says so loudly. Probes journal as `probe` and
do NOT count toward PLATEAU, so run them freely; that is what the flag is
for. Do not raise `consecutive_reverts` to make room for probes, which is
what runs did before the flag existed.

**The pegged-at-bound tell.** When a winning lever sits exactly on its
declared min or max, the model has no resistance there and the number is
an artifact of where you set the bound, not a discovered optimum. Name
every pegged lever in SUMMARY.md as a sensitivity to validate before
anyone acts on it. This is not theoretical: gtm-v1 converged with care
price at its ceiling and build price at its floor, and gtm-v2 (which added
the missing elasticity) moved both off their bounds and overturned the
specific numbers while confirming the strategic direction. A pegged
winner is a prompt to fix the model, usually in a `-v2` run.

## Step 6: Modes and stopping

- **converge** (default): stop at goal, any budget, or plateau -
  `uv run tools/optimize_run.py stop --reason "<which>"`.
- **continuous**: NEVER-STOP semantics within budget. Once looping, do not
  pause to ask "should I keep going?" - the user may be asleep and expects
  you to continue until stopped. PLATEAU is a journal event, not a stop:
  think harder, re-read the asset for new angles, combine previous
  near-misses. Across sessions, drive with `/loop` + `resume`; the run
  state and locks persist. The session-pressure rule WINS over NEVER-STOP:
  at Critical pressure, checkpoint and end the SESSION - the RUN persists
  and resumes.
- **supervised**: present each hypothesis and wait for the user's ack
  before `round` (for sensitive assets that pass the fit check but warrant
  a human per experiment).

## Step 7: Close

`stop` writes the final journal row and unlocks. Then write
`docs/optimize/<tag>/SUMMARY.md` FROM the TSV: final vs baseline score,
kept changes with their deltas, dead ends worth remembering, and what a
human should review. (SUMMARY.md is written after unlock; during the run
it would be a locked-path write.)

**Two headings are a contract, not a style preference.** `## Dead ends` and
`## Sensitivities` are what `--prior-art` parses, so anything you record
outside them is invisible to the next run and survives only if a human
remembers it. Put in `## Dead ends` what a later run must not spend a round
rediscovering (a lever that is score-neutral by construction, a probe that
confirmed a bound). Put in `## Sensitivities` what a later run must not
blindly inherit: a lever you took that is really the owner's judgment call,
and the blind spots your guards do not cover.

## Step 8: Ship

The run branch already exists - ship through the normal chain
(rule_no_auto_commit): push, PR; the body cites baseline -> final so the
reviewer sees the measured delta; CI-green auto-merge applies as usual.
The manifest + results.tsv + SUMMARY.md ship in the same PR. If nothing
beat the baseline, ship the journal anyway - a documented dead end
prevents re-running the same experiments.

## Good first targets (fit-checked)

- Local page weight / Lighthouse on `workspace/projects/local-web/` and
  `platform/public/` pages (scorer: `page-weight.py`)
- Brisken expense-recon match accuracy against labeled fixtures (scorer to
  be built from Chris's ground-truth sample)
- Lead Desk mail classification accuracy against captured-message fixtures

Poor targets, do not accept: cold-email copy (reply-rate feedback is
weeks-slow and low-volume), anything scored by an LLM's opinion.

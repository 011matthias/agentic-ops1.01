# Optimize-Loop Lock Model (autoresearch harness)

**Hard constraint.** The `/comd_optimize` loop is trustworthy only because
the agent that mutates the asset can touch NOTHING else that defines the
experiment. Three surfaces, per the Karpathy autoresearch architecture and
the owner's 2026-07-17 directive ("no mistakes can be made"):

1. **Instructions** - the run manifest `docs/optimize/<tag>/RUN.md` -
   human-approved at setup, LOCKED for the run's duration.
2. **Scoring** - `tools/scorers/**` + `tools/scorers/PINS.json`, and the
   GUARDS that carry the anti-overfit floor (`tools/guard-pins.json`) - locked
   ALWAYS (in and out of runs), hash-pinned, re-verified every round.
3. **Asset** - the manifest's `assets` globs - the ONLY agent-writable
   repo surface while a run is active.

Reference basis: karpathy/autoresearch discussion #322 - in every ported
domain, prompt-level bans failed and only code-level enforcement held. So
the locks here are code, not prose.

## Enforcement (three layers)

- **`optimize-run-gate.py`** (PreToolUse `Write|Edit` + `Bash|PowerShell`,
  wired via `wire-hooks.py`): while `.claude/optimize/run.json` exists,
  DENY edits to the manifest, `results.tsv`, `guard_files`, scorers,
  PINS.json, and the enforcement machinery itself (`.claude/hooks/**`,
  `wire-hooks.py`, `optimize_run.py`, `pin_scorer.py`, this rule, the
  command file - hardcoded in-hook so a tampered state file cannot unlock
  them); DENY edits outside the asset globs; shell arm denies write-shaped
  commands on locked paths and `git checkout/restore/apply` on locked
  pathspecs. Scorer/PINS shell writes are denied even with NO active run.
  Corrupt run state -> ask (never fail-open, never brick).
- **`tools/optimize_run.py`** (the engine) executes branch/commit/score/
  guard/keep-revert/journal deterministically and re-verifies the scorer,
  manifest, and journal hashes EVERY round - a tampered harness can never
  yield an accepted round. Guards fail => discard even on a score win.
- **CI** - `test_scorer_pins.py` refuses to merge a scorer whose content
  drifted from its pin; the hook suites pin the gate's decision matrix.

Residual (documented): interpreter escapes (`python -c "open(...)"`) can
still write files - they cannot produce an accepted round (hash checks) or
merge (CI), and remain a `scorer-lock-bypass`-class friction event.

## The two seams (user-order-only, always surfaced)

- `SCORER_LOCK_ALLOW=1` - scorer authoring/maintenance + `pin_scorer.py
  pin`, and guard re-pinning via `pin_scorer.py pin-guard`. The PINS.json /
  guard-pins.json diff ships in the PR; reviewer sign-off is the honesty
  gate. A guard defines the FLOOR an experiment must clear, so moving one is
  the same class of act as moving the metric and goes through the same seam;
  `start` refuses a declared guard whose hash diverges from its reviewed pin.
- `OPTIMIZE_SCOPE_ALLOW=1` - mid-run out-of-scope edit (e.g. urgent
  hotfix). Downgrades deny to a loud advisory. Alternative: `stop`, fix,
  re-run.

Setting either WITHOUT an explicit user order is a `skipped-gate` friction
event (B-gate class).

## Non-negotiables

- One run at a time; runs are fresh (`optimize/<tag>` must not pre-exist).
- Baseline before anything: a failed baseline score or baseline guard
  aborts lock-on with nothing created. Never start on a guessed score.
- `results.tsv` is append-only and engine-written; its integrity anchors
  (line count + sha256) are verified before every append.
- Kept winners ship via the normal B6 bands (the engine never pushes or
  merges); dead-end journals ship too - a documented dead end prevents
  re-running the same experiments.
- Live invasive surfaces (real sends, campaigns, prod mutations) are never
  optimize targets; rule_instantly_invasive applies unchanged.
- Constructed metrics (no natural scalar) follow `docs/optimize/RECIPES.md`:
  fitness script first as its own PR, dual-score when the instrument is
  unreliable, held-out score-floor guard mandatory.

## Why

Shipped 2026-07-17 (owner directive: field-agnostic optimize infrastructure,
maximal correctness bar) on top of PR #247's v1. The v1 locked only the
scorer at the Write/Edit layer and acknowledged its own shell-redirect
bypass; the #322 evidence (agents gaming evaluators through every
prompt-level defense) made the full three-surface, code-level lock the
design floor. Tests: `test_optimize_run_gate.py`, `test_optimize_run.py`,
`test_scorer_pins.py`, `test_scorer_lock_gate.py`.

Related: [[rule_no_auto_commit]] (B6 ship bands),
[[rule_behaviors]] (escalation carve-out: engine/harness errors escalate,
losing hypotheses do not), [[rule_instantly_invasive]] (B5),
[[rule_session-pressure]] (pressure beats NEVER-STOP: the session
checkpoints, the run persists).

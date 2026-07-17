# Scorers (the locked half of the optimize loop)

A scorer turns "is this asset good?" into ONE objective number. It is the
fitness function for `/comd_optimize` hill-climb runs (the Karpathy
auto-research pattern: baseline -> one change -> re-score -> keep or revert).
The loop only works if the metric cannot be gamed, so scorers are locked
against agent edits: `scorer-lock-gate.py` (PreToolUse Write|Edit) denies any
agent modification of an existing `tools/scorers/*.py`. Goalpost-moving is a
structural impossibility, not a discipline hope.

## Contract

1. One scorer = one file, `tools/scorers/{target}.py`, PEP 723 inline deps,
   stdlib preferred.
2. Invocation: `uv run tools/scorers/{target}.py <asset...>`.
3. Output: the LAST stdout line is exactly `SCORE: <number>`. Anything before
   it is free-form detail for the journal.
4. Exit 0 only on a successful measurement. A crashed or partial measurement
   exits non-zero and is NEVER treated as a score by the loop.
5. A header comment `# direction: minimize` or `# direction: maximize`
   declares which way is better. The loop reads it; a scorer without it is
   invalid.
6. Deterministic: the same asset yields the same score. If the metric is
   noisy (network timing, LLM calls), the scorer itself must take the median
   of N runs internally and say so in its docstring.
7. Register every scorer in `tools/INDEX.md` in the same change.

## Lock semantics

- Agent Edit/Write on an existing `tools/scorers/*.py` -> denied by the hook.
- Creating a NEW scorer file is allowed (that is how scorers get authored);
  it ships through the normal PR chain, and the human review of that PR is
  the sign-off that the metric is honest.
- `SCORER_LOCK_ALLOW=1` is the maintenance escape hatch for a session where
  the user has explicitly approved editing a scorer. Never set it on your own
  initiative; the ask must come from the user.
- This README stays editable (documentation, not a metric).
- The hook only sees Write/Edit tool calls. Rewriting a scorer via shell
  redirection would bypass it; doing so is a friction event
  (`scorer-lock-bypass`) of the same class as a skipped B-gate.

## Fit check before adding a scorer

All three must hold for the target asset (else the optimize loop is the
wrong tool):

- Objectively scorable with a real number (no "LLM judge" scores; those are
  gameable and violate the honest-number principle).
- Fast feedback: a scoring run completes in seconds to minutes, not weeks.
- The agent has direct write access to the asset being scored.

## Registered scorers

| Scorer | Metric | Direction |
|---|---|---|
| `page-weight.py FILE.html [...]` | Total local page weight in bytes (HTML + referenced local assets) | minimize |

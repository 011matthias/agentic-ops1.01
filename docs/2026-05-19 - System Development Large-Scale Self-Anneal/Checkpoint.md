# Checkpoint: System Development Large-Scale Self-Anneal

**Date:** 2026-05-19
**Status:** COMPLETE — F1 + STEP 1 + F2 + F3 all shipped to main. The 2026-05-19 root cause and all three deferred follow-ups are structurally resolved.

> This is the consolidated final checkpoint for the whole self-anneal arc.
> F1 was the prior session (PRs #29/#30); its per-session detail lives in
> git history + the 2026-05-19 friction-register root-cause row. This doc
> reflects the completed end-state for next-session continuity.

---

## Summary
The entire `.claude/hooks` enforcement layer had been silently dead on this machine since 2026-05-18 15:41 (device-sync stripped machine-specific hook wiring from tracked `settings.json`; the gitignored `settings.local.json` never carried a hooks block). F1 restored it on this machine and rewrote `stop-b1-gate.py` into a precise classifier. This continuation closed the three deferred items: a tracked cross-device bootstrap (STEP 1), enforcement-classifier precision (F2), and the structural pre-client-message data-verification gate that memory failed to hold twice (F3).

---

## What Was Done This Session (continuation)

### STEP 1 — cross-device recurrence kill (PR #31, `0ffa0f2`)
1. `tools/wire-hooks.py` (TRACKED): single source of truth for the canonical 9-hook block. Modes `--check` (assert + loud warn + exit 1), `--ensure` (auto-heal, exit 0), `--write` (idempotent repair). Replaces only the `hooks` key — `permissions`/`enabledPlugins` preserved. Portable `uv run python .claude/hooks/X.py` relative paths only.
2. `.claude/settings.json`: machine-agnostic SessionStart hook runs `wire-hooks.py --ensure` every session on every device. Silent enforcement death can no longer survive past one session start anywhere.
3. `tools/INDEX.md` manifest entry.
4. Verified behaviorally 5/5 in an isolated sandbox.

### F2 — enforcement-classifier precision (PR #33, `a671813`)
Killed 4 false-positives, 3 observed **live this session** while shipping STEP 1:
1. **F2a pre-publish FP:** `VALIDATE_PATTERNS` only knew npm/pytest/tsc/validate-*; added `py_compile`, `--check`, `--dry-run`, `.claude/hooks/*.py`, `json.load`/`json.tool`, `smoke`/`sandbox`, `tests/`.
2. **F2b publish-in-payload FP:** `publish_residue()` strips quoted spans + heredoc bodies; any `.claude/hooks/` invocation = hook test, not a publish.
3. **F2c iteration-3x misfire:** `is_readonly()` excludes read-only/idempotent repeats from the stuck-loop count.
4. **F2d stop-b1 meta-text:** `strip_code()` now blanks short double-quoted + curly-double-quoted example spans; single quotes deliberately not stripped (contraction-safe). Resolves the F2-deferred blind spot row.
5. Verified behaviorally 10/10 (isolated buffers, native Windows transcript paths), including 4 "still-fires" cases proving no neutering.

### F3 — structural pre-client-message data-verification gate (PR #34, `24bfb96`)
1. `validate-output.py` new `unsourced-claim` (HIGH): flags a present-tense factual client-facing problem/impact assertion when no source-attribution cue appears within ±2 lines. Hedged hypotheses excluded. Suppressible via existing `output-allow`. Already wired through `post-write-gate → in_output_scope` (comms/deliverables) — no duplicate gate.
2. **Incidental, disclosed:** fixed a pre-existing latent bug — a leading `\b` before the `<`/`>` literal in two `unverified-claim` stat rules made them silently never match when the symbol followed whitespace (`< 30s response time`, the exact 2026-03-23 #15 shape). Surfaced by F3's own test harness (T7).
3. `rule_behaviors.md` B4 extended to problem-claims, now citing the real enforcement.
4. Friction-register resolution row; resolves #7 + 2026-03-23 #14/#15.
5. Verified behaviorally 9/9 — T1 = the exact register #7 message text flagged HIGH; T7 confirms existing rules un-neutered.

---

## Key Decisions Made

### Bootstrap auto-heals (`--ensure` at SessionStart), not warn-only
- **Choice:** SessionStart runs `wire-hooks.py --ensure` (idempotent write if drifted), not just a warning.
- **Rationale:** A warn-only assertion still needs a human to act — that's the exact failure mode that ran ~1 day undetected. Auto-heal makes silent enforcement death structurally impossible to sustain past one session start, on any device. The tracked tool is machine-agnostic so a future "sync before switching devices" cleanup has no path-portability reason to strip it.

### F3 extends `validate-output.py`, not a new gate
- **Choice:** Add `unsourced-claim` to the existing validator rather than a new hook/tool.
- **Rationale:** `post-write-gate → in_output_scope` already routes comms drafts + deliverables to `validate-output.py`. A second gate would duplicate scope and create the ordering risk the dispatcher was built to remove. Single source of truth.

### F3 incidental regex fix shipped with disclosure
- **Choice:** Fixed the pre-existing `\b`-anchor bug in two sibling `unverified-claim` rules within the F3 PR, disclosed explicitly in the commit + PR body.
- **Rationale:** Shipping F3 while leaving a *discovered-broken* sibling rule in the same verification-theater category would itself be a B2 "done with known gap". The bug was surfaced by F3's own test and is correctness restoration of the exact subsystem the brief targets. Logged transparently as a self-detected scope judgment (see Friction).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `tools/wire-hooks.py` | Created (tracked, PR #31) | Cross-device 9-hook bootstrap; SSOT for the hooks block |
| `.claude/settings.json` | Modified (PR #31) | Machine-agnostic SessionStart `--ensure` self-heal |
| `tools/INDEX.md` | Modified (PR #31, #34) | Manifest entries (wire-hooks, validate-output unsourced-claim) |
| `.claude/hooks/gate-skip-detector.py` | Modified (PR #33) | F2a/b/c precision: validation recognition, publish-residue, read-only guard |
| `.claude/hooks/stop-b1-gate.py` | Modified (PR #33) | F2d: strip double-quoted example spans |
| `tools/validate-output.py` | Modified (PR #34) | F3: `unsourced-claim` HIGH + `<`/`>` anchor bug fix |
| `.claude/rules/rule_behaviors.md` | Modified (PR #34) | B4 extended to problem-claims, cites real enforcement |
| `docs/friction-register.md` | Modified (PR #34) | Resolution row; resolves #7 + 2026-03-23 #14/#15 |

---

## Current Status
All work shipped to `main` (HEAD `24bfb96`). No stray branches, no working-tree drift on any of the 8 tracked files. Enforcement layer live and verified: 9/9 hooks intact (`wire-hooks.py --check` → OK); F2/F3 code runs from the working tree and was observably firing correctly while shipping. No client touched (system-infra) — no ops/comms/infra-reconciliation applicable.

---

## Next Steps
1. None blocking — the self-anneal arc is closed. The next routine session can proceed normally; SessionStart `--ensure` will report `OK: enforcement layer intact` (or auto-repair + loud-warn if a device sync recurs).
2. **Optional hardening (not deferred work, an idea):** a hook-liveness heartbeat (a periodic "hooks fired N times in the last session" line) so a future *partial* failure (one hook silently erroring vs the whole block missing) is also visible. STEP 1 covers the block-missing case fully; per-hook silent error is a smaller residual surface.
3. **Other-device first run:** on the other developer's machine / a fresh device, the first session will loud-warn + auto-repair (expected, by design). No action needed; just don't be alarmed by the one-time `ENFORCEMENT LAYER WAS DOWN -- AUTO-REPAIRED` banner.

---

## Context for Next Session

### Files to Read First
- This checkpoint (final end-state of the arc)
- `tools/wire-hooks.py` — the bootstrap; `CANONICAL_HOOKS` is the contract (update it in the same change if a hook is ever added/removed)
- `docs/friction-register.md` — last two 2026-05-19 system rows (F2-deferred blind spot now resolved by F2d; the consolidated RESOLUTION row)

### Open Questions
- None. The arc's open questions (cross-device gap, meta-text FP) are both resolved (STEP 1, F2d).

### Working Notes
- `git reset --hard origin/main` was used to sync local main after each `gh pr merge` (gh merges remotely; local main lagged). Safe here: local main carried no unique commits; untracked parallel-session dirs are not touched by reset; the only discarded tracked change was auto-generated `hook-log.txt` append noise.
- The F3 incidental regex bug: leading `\b` before a non-word literal (`<`/`>`) never matches when the literal follows whitespace. Fix pattern: anchor the *word* alternatives only — `(?:\b(?:less than|under)\s+|<\s*)` — let the symbol branch float. Transferable: any `\b(?:words|<symbol>)` regex has this latent hole for the symbol branch.
- **Context YAML deliberately NOT written** (`docs/sessions/2026-05-19-context.yaml`): hard constraint from the task brief — it carries the parallel Meji session's 2026-05-20 hard-clock `resume_point`. Same approach Sessions 2 & 3 took this day. Session log `.md` + friction register were appended (additive, safe).

### Reference Materials
- PR #31 (STEP 1): https://github.com/011matthias/agentic-ops1.01/pull/31 (MERGED `0ffa0f2`)
- PR #33 (F2): https://github.com/011matthias/agentic-ops1.01/pull/33 (MERGED `a671813`)
- PR #34 (F3): https://github.com/011matthias/agentic-ops1.01/pull/34 (MERGED `24bfb96`)
- F1 prior-session: PRs #29/#30 (MERGED)

---

## How to Continue
Nothing to pick up — the arc is complete and verified. Start the next session normally; the SessionStart `--ensure` self-heal is now the standing guard. If a checkpoint or `/resume` ever shows the enforcement layer warning, that is STEP 1 working as designed (it will have already auto-repaired).

---

## Strategic Feedback

### What Worked Well This Session
- The "ship each fix as its own branch→PR→merge without pausing" instruction kept three independent fixes cleanly separated and individually revertable, while the ship-gate stopped any mid-chain hesitation. Three PRs in one session with zero "should I merge?" stalls.
- Testing the validator's *behavior* via subprocess (not reading its RULES) is what surfaced the pre-existing `<`/`>` anchor bug. Behavioral verification found a latent defect that config-reading would have missed entirely — a concrete payoff of the B2 discipline.

### Suggestions
- The gate-skip-detector + B2-streak hooks fired ~6 advisory false-positives on this very session's all-green verification runs *before* F2 landed. That noise is now fixed, but it is worth a periodic `friction-watch`-style scan of `hook-log.txt` for `ALLOW:`/`BLOCK`/advisory ratios so classifier drift is measured, not noticed anecdotally.

### System Health
- Autonomy score: 0 human interventions — fully autonomous (1 self-detected, PR-disclosed scope judgment: the F3 incidental regex fix). Gates: B1 held throughout (state verified before declaring "locked in", nothing findable asked of the user); B2 fired strongly (5/5 + 10/10 + 9/9 behavioral, plus final-state verification — behavior tested, not config declared); B3 fired decisively once (T7 failure → probed the regex directly instead of theorizing root cause); skipped: 0.
- The enforcement layer now has a real cross-device liveness guarantee (STEP 1) and two precision-tightened classifiers (F2). The remaining architectural gap is per-hook silent-error visibility (vs whole-block-missing, now covered) — small surface, noted as optional hardening, not deferred.

# Mini-Checkpoint: Agent Teams Phase 6

**Date:** 2026-05-26
**Status:** Phase 6 closed — `no-auto-commit-gate.py` shipped as the structural backstop for B6 / `rule_no_auto_commit.md`. The infrastructure-deferred hook flagged in the rule itself is now built.
**Type:** mini
**Prior:** [Phase 1](../2026-05-26%20-%20Agent%20Teams%20Phase%201/Mini-Checkpoint-1.md) · [Phase 2](../2026-05-26%20-%20Agent%20Teams%20Phase%202/Mini-Checkpoint-1.md) · [Phase 3](../2026-05-26%20-%20Agent%20Teams%20Phase%203/Mini-Checkpoint-1.md) · [Phase 4](../2026-05-26%20-%20Agent%20Teams%20Phase%204/Mini-Checkpoint-1.md) · [Phase 5](../2026-05-26%20-%20Agent%20Teams%20Phase%205/Mini-Checkpoint-1.md)

---

## Summary

Built [.claude/hooks/no-auto-commit-gate.py](../../.claude/hooks/no-auto-commit-gate.py) — the structural enforcement of B6 (`rule_no_auto_commit.md`). Different shape from Phases 1-5: not an agent, a `PreToolUse:Bash` hook. Intercepts ship-class commands (git commit / push / tag / subtree-push, gh pr create / merge / close, gh release, flyctl / vercel / railway / vercel-force-deploy), scans recent user turns for explicit ship authorization, and returns `permissionDecision: "ask"` when no order is found. Mirrors the proven `instantly-invasive-gate.py` always-ask pattern. Operationalizes the rule from a Layer-3 memory-recall fix (which demonstrably failed within hours of being written on 2026-05-26) into a Layer-1 structural gate that fires at decision time. Smoke-tested across 5 cases: non-ship pass-through, ship-class+no-auth ASK, ship-class+auth allow, ship-class+no-transcript ASK, read-class git no-false-fire.

## What Was Done

- Read the existing hook architecture: [.claude/hooks/instantly-invasive-gate.py](../../.claude/hooks/instantly-invasive-gate.py) (closest structural sibling — same ASK-pattern, same B5-style scope-of-effects reason), [.claude/hooks/stop-b1-gate.py](../../.claude/hooks/stop-b1-gate.py) (transcript-reader helper pattern), [tools/wire-hooks.py](../../tools/wire-hooks.py) (the canonical hooks registry + EXPECTED_HOOK_SCRIPTS contract).
- Built [.claude/hooks/no-auto-commit-gate.py](../../.claude/hooks/no-auto-commit-gate.py):
  - **Ship-class detection** — 12-pattern regex covering all the rule's enumerated ship-class commands (`git commit|push|tag|subtree push`, `gh pr create|merge|close`, `gh release create`, `flyctl deploy`, `vercel deploy`, `vercel-force-deploy.sh`, `railway up`). Read-class git commands (`git log`, `git status`, `git diff`, `git tag -l`, `git tag --list`) deliberately do NOT match.
  - **Authorization scan** — `recent_user_messages(transcript_path, lookback=3)` reads the last 3 user turns from the JSONL transcript; `has_authorization(msgs)` regex-matches against 22 canonical authorization phrasings drawn from the rule's "Acceptable orders" list ("commit", "push", "ship it", "PR it", "merge", "land it", "deploy", "ship everything", "you can commit", "go ahead and merge", etc.). Strips system-reminder content + Stop-hook-feedback content from the scan (those are harness text, not user authorization).
  - **Decision** — ship-class detected + no authorization → `permissionDecision: "ask"` with full B6 reason text. Ship-class detected + authorization found → log `allow:{tag} auth={snippet}` and exit 0. Non-ship-class → exit 0 silently.
  - **Defensive contract** — any error, missing transcript, or unparseable payload → exit 0 (fail-open). A broken classifier must never block legitimate work; a missed ship-class command is cheaper than a fully blocked git workflow.
  - **Why ASK not DENY** — same as `instantly-invasive-gate.py`: the user can authorize via the prompt; the agent cannot bypass. "Deny" would block the user too, requiring hook disable to ship anything. "Ask" is the right primitive for "human must consent to this specific instance."
- Wired into [tools/wire-hooks.py](../../tools/wire-hooks.py):
  - Added the hook to `CANONICAL_HOOKS["PreToolUse"]` `Bash` matcher, alongside `instantly-invasive-gate.py` and `cd-guard.py`
  - Added `no-auto-commit-gate.py` to `EXPECTED_HOOK_SCRIPTS`
  - Updated docstring and all 3 print messages from "10 hooks" / "9 hooks" → "11 hooks"
  - Ran `uv run python tools/wire-hooks.py --ensure` — confirmed `(was missing: ['no-auto-commit-gate.py'])` repair message, then re-running shows `(11/11 hooks)` intact
- Created persistent fixtures at [tools/fixtures/no-auto-commit-gate/](../../tools/fixtures/no-auto-commit-gate/):
  - `no-auth.jsonl` — synthetic single-turn transcript without any ship-class authorization keyword (just "please scan the repo for TODOs")
  - `auth.jsonl` — synthetic single-turn transcript with "ship it" + "merge"
  - `README.md` — 5-test matrix + how to re-run + Windows/path note documenting the `/tmp/` Git-Bash-vs-Python-native pitfall discovered during smoke-test
- Updated [.claude/rules/rule_no_auto_commit.md](../../.claude/rules/rule_no_auto_commit.md) §Enforcement section: replaced the "Not yet built; logging as infrastructure-deferred for the next hook pass" line with the canonical reference to the hook + fixture locations + the always-ask design rationale. Removed the `infrastructure-deferred` flag.
- Smoke-tested the hook directly (`PreToolUse` payload piped via stdin) across 5 cases:

  | Test | Command | Transcript | Result | Status |
  |------|---------|-----------|--------|--------|
  | A | `ls -la` | empty | no output, exit 0 | PASS — non-ship-class passes through |
  | B | `git commit -m test` | no-auth.jsonl | `permissionDecision: ask` JSON with `git-commit` tag | PASS — ASK path correct |
  | C | `git push origin main` | auth.jsonl | no output, exit 0 | PASS — auth scan correctly matched "ship it" / "merge" |
  | D | `gh pr merge 99 --squash` | empty | `permissionDecision: ask` JSON with `gh-pr-merge` tag | PASS — no-transcript correctly defaults to ASK |
  | E | `git log --oneline -5` | any | no output, exit 0 | PASS — read-class git does NOT false-fire |

  Hook-log entries from smoke-test sequence: `ASK:git-commit ...`, `ASK:git-push ...` (initial Test C run before path fix), `ASK:gh-pr-merge ...`, then after the path fix: `allow:git-push auth=...` (Test C re-run with correct Windows-resolvable path).

## Friction events this session

- **`slow-path`** — Initial Test C run failed because the smoke-test wrote fixture files to `/tmp/nacg-test/auth-transcript.jsonl` (Git Bash path). Python sees `/tmp/` as `C:\tmp\` on Windows-native, which doesn't exist, so the hook's `os.path.isfile(transcript_path)` returned False and `recent_user_messages` silently returned `[]` — making the auth scan miss every authorization in the fixture. Diagnosed by printing `os.path.isfile()` from Python directly. Fix: moved fixtures to `tools/fixtures/no-auto-commit-gate/` (relative path under the repo root, which both Git Bash and Windows-native Python resolve identically). The fix-cost was 2 extra Bash calls — slow-path but bounded. Documented in fixture README's "Windows / path note" section so the pitfall doesn't recur. Self-detected.

- **B1 deferral re-fire** — the final response of Phase 5 leaked a deferral pattern ("If you want a further phase tonight, the non-agent candidate ... is genuinely ungated"). The Stop hook (stop-b1-gate.py) caught it and forced this turn. This is exactly the friction pattern Phase 5's checkpoint flagged the morning of, and the hook caught it within minutes of the checkpoint mentioning it. Operationalization vs memory: the structural Stop hook fired faster than the just-written memory-class observation. Validates the B6 hook's design choice (structural > memory for ship-class decisions).

## Current Status

- 11 enforcement hooks now wired (was 10). All run automatically via `tools/wire-hooks.py --ensure` at session start.
- Phase 6 closes the `infrastructure-deferred` flag that was logged in `rule_no_auto_commit.md` itself — the rule no longer has open structural debt.
- Three pieces of work pending review across Phases 1-6:
  - Five agent files + five wire-edits + five fixture sets + five mini-checkpoints (Phases 1-5)
  - One hook file + wire-hooks.py edits + fixture set + rule update + this mini-checkpoint (Phase 6)
  
  Total: ~25 uncommitted files across Phases 1-6, awaiting explicit ship order per `feedback_no_auto_commit` AND now per `rule_no_auto_commit.md` AND now per the live hook.

## Self-test of the new hook

The B6 hook now applies to EVERY future ship-class command this session — including any commit / push / PR / merge of the Phase 1-6 work itself. The first real test will be the next genuine ship attempt:
- If the user types "commit" / "push" / "ship it" → the hook's auth-scan should match → command runs.
- If the agent attempts a ship-class command without the user having typed an order → the hook should fire `ask` and the user gets a prompt.

That's the dogfooding moment. The next time work is shipped, the hook is the proof.

## Gaps remaining (from original Phase-1 diagnostic + spillover)

- **#3b per-orchestrator testers** — STILL deferred, same "wait for 2-3 real builds" gate.
- **#6 memory-recall enforcer** — STILL deferred, same "wait for 3-5 real /draft runs" gate.

Both remaining gaps have explicit data-trigger gates. Building either of them tonight would re-violate the "earn it" principle in a way Phase 5 and 6 had defensible overrides for (Phase 5: only ungated agent; Phase 6: rule itself flagged the work as needed). Tonight the answer for any further phase is: wait for real-use data.

## Next Steps

1. **Review.** All 6 phases now pending. The Phase 6 hook is materially different from the Phase 1-5 agents — it's an enforcement primitive, not an audit/build/produce primitive. May be worth its own commit separate from the agent series.
2. **Dogfood the hook.** Next ship attempt this session OR next session will exercise the hook against the real ship-class commands of THIS work. Watch the hook-log.txt for accuracy: are the auth-scan matches firing correctly? Are read-class commands (`git diff`, `git status`) staying silent?
3. **Don't build #3b testers or #6 memory-recall enforcer yet.** Both gated.
4. **Consider stopping here for the day.** Six phases shipped (5 agents + 1 hook), all uncommitted. The next high-leverage move is the harvest step (commit + review) — which requires the user's explicit ship order, which is exactly what the new B6 hook now enforces structurally. Natural pause point.

## Files to Read First

- [.claude/hooks/no-auto-commit-gate.py](../../.claude/hooks/no-auto-commit-gate.py) — the new hook
- [.claude/rules/rule_no_auto_commit.md](../../.claude/rules/rule_no_auto_commit.md) §Enforcement — updated to reference the hook as the canonical backstop
- [tools/wire-hooks.py](../../tools/wire-hooks.py) — see CANONICAL_HOOKS PreToolUse Bash block + EXPECTED_HOOK_SCRIPTS (now 11 scripts)
- [tools/fixtures/no-auto-commit-gate/README.md](../../tools/fixtures/no-auto-commit-gate/README.md) — 5-test matrix + re-run commands + Windows/path note
- [docs/2026-05-26 - Agent Teams Phase 5/Mini-Checkpoint-1.md](../2026-05-26%20-%20Agent%20Teams%20Phase%205/Mini-Checkpoint-1.md) — Phase 5 closing, which suggested this hook as the next non-agent candidate

## What worked well

- **Mirroring the `instantly-invasive-gate.py` pattern.** Same shape (PreToolUse:Bash, ASK decision, plain-language reason citing the rule), so the contract is consistent across both invasive-action backstops. The user already knows what an "ASK" prompt looks like and what to do with it.
- **Transcript-reader from stop-b1-gate.py.** Adapted the existing JSONL-parsing helper rather than inventing one. Same defensive contract (any failure → fail-open → exit 0).
- **Hook intercepts the agent's OWN session.** Once the next real ship-class command runs, the hook will gate the very Phase 1-6 commits that ship this work — the structural fix immediately applies to its own creation chain.
- **5-test matrix caught a real bug.** The /tmp Git-Bash vs Python-native path issue was a genuine bug surfaced only because Test C compared expected vs actual. Without the matrix, the hook would have shipped with a silently broken auth-scan.

## Session pressure

Very high. Six phases in one session (5 agents + 1 hook + 6 checkpoints + 6 INDEX entries + many fixtures), heavy reads + heavy writes. The B1 deferral re-fire at the Phase-5→Phase-6 boundary is a pressure symptom (the previous session would have suggested commit-review-rest as a third option; the response leaked it as a deferral). The dogfooding moment for the hook is the natural pause: any further work tonight should be commit-review-rest (which requires the user's explicit ship order and exercises the new hook), or stop.

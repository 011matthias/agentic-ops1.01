# Checkpoint: Friction Fix Program Close-Out

**Date:** 2026-09-17
**Status:** Items 1 (#3) and 3 (small follow-ups) shipped. Item 2 (#5 shell-trap rewrite) stopped on its own stop condition; awaiting an owner call.

---

## Summary

Shipped the per-session state file (PR #1006) and the consumer-gate / cdp-rule precision fixes (PR #1012). The live experiment for the cd-guard rewrite showed that a PreToolUse `permissionDecision: "allow"` skips the approval a command would otherwise need, so the rewrite was not built.

---

## What Was Done This Session

### #3 per-session state (PR #1006, merged 0f8d2d2b)
1. `session_state.py`: path `agentic-ops-session-state-{sid}.json`; resolution order env override, `bind_session()` id, `CLAUDE_CODE_SESSION_ID`, legacy shared file. Legacy is read only when it records this session's id and the session has no file yet, so the first write carries it over. Stale per-session files (7 days) are swept when a session creates its file.
2. `bind_session(payload)` right after stdin parsing in all 13 writer hooks. A structural test fails if a hook imports `session_state` without binding.
3. CLI: `--session-id`, resolves `CLAUDE_CODE_SESSION_ID`, `--status` reads context from this session's transcript first (`context_source`, `state_file` in JSON).
4. `session_registry.py` read the nonexistent `CLAUDE_SESSION_ID`, now `CLAUDE_CODE_SESSION_ID`.
5. `hooklib.run_hook` isolates state by default (drops the inherited session id, points an empty override at a throwaway file). Before this, tests passing `AGENTIC_OPS_SESSION_STATE: ""` wrote candidates into the live shared file.
6. Tests: `test_session_state_per_session.py`, 11 cases through real hook and CLI subprocesses with TEMP redirected. `regress_check` bites in git-stash-gate, the pressure meter, input-classifier and `session_state.py`. `preflight --full` 1779 passed.

### #5 live experiment (not built)
Headless `claude -p` (CC 2.1.212, haiku, default mode) in a throwaway dir; the hook rewrote `python mark.py orig` to `... rewritten`; `m.txt` showed what ran.

| Case | Result |
|---|---|
| no hook, no rule | denied |
| `allow` + `updatedInput`, no rule | rewritten ran, no approval |
| `updatedInput` only | rewrite applied, still denied |
| `updatedInput` only, allow rule for original | denied (rules match the rewrite) |
| `updatedInput` only, allow rule for rewrite | rewritten ran |
| `allow` hook vs deny rule / ask rule | denied both |
| rewrite hook + sibling `ask` hook, allow rule | denied (ask survives) |

### Small follow-ups (PR #1012)
1. (a) `deploy-consumer-gate`: deploy patterns match `executed_view()`; label strips quotes. Probed 17 shapes first: every real deploy still opens, every search/echo mention stays silent. 9 new parametrized cases.
2. (b) `warn-attach-busy-cdp-9222`: `event: file` to `event: bash`. Lint clean; `test --text` matches the three incident shapes on bash, none on file. 2 seed cases plus a file-text negative.
3. `regress_check` bites on both; `preflight --full` clean.

---

## Key Decisions Made

### Stop item 5 instead of building
- **Choice:** no cd-guard rewrite shipped.
- **Rationale:** the directive's stop condition fired (hook `allow` bypassed the approval in C1 vs C0). A rewrite-only variant keeps the permission flow in every tested case, but it was not the approved design and the auto-mode classifier's view of a rewrite is untested.

### `--status` reads the transcript, not only the state file
- **Choice:** CLI prefers a live transcript read for the resolved session.
- **Rationale:** live hooks run from the primary clone, which is behind main and owned by siblings; until it pulls, no per-session file exists and the reading would stay wrong.

### Item 3's two fixes in one PR
- **Choice:** one `sys/gate-precision-followups` branch.
- **Rationale:** the handoff grouped them as one item; both are one-line gate retunes with separate tests and separate regress checks.

---

## What Did NOT Work (and why)
- **`--status` at session start:** named sibling session 4310562e at 460k, because the single state file held that sibling's reading; this session had just started. Fixed by #1006.
- **`cd $W && ...` in Bash (x2):** cd-guard refused, including `cd X 2>/dev/null;` at the head of a background CI loop. `git -C` / `--repo` / subshell work.
- **Heredoc writing the Python experiment harness:** heredoc gate refused a double backslash in the payload; the Write tool worked.
- **`MSYS_NO_PATHCONV=1 git -C /c/Users/...`:** git got the literal `/c/...` path ("not a git repository"); with the env var set, use `C:/...` paths.
- **Project `.claude/settings.json` for `claude -p` in an untrusted temp dir:** not loaded (an exact allow rule was ignored); passing `--settings <file>` loaded rules and hooks.
- **grep patterns containing the deploy verb (x3):** the live, pre-#1012 consumer gate opened a false marker each time; cleared by deleting this session's marker file.
- **`awk -F' \\| '` over register rows:** awk read `|` as regex alternation; a Python cell splitter worked.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `tools/session_state.py` | edit (#1006) | per-session path, `bind_session`, legacy fallback, sweep, transcript `--status` |
| `.claude/hooks/{13 writer hooks}.py` | edit (#1006) | bind from payload session_id |
| `tools/session_registry.py` | edit (#1006) | `CLAUDE_CODE_SESSION_ID` |
| `tools/tests/hooklib.py` | edit (#1006) | default state isolation |
| `tools/tests/test_session_state_per_session.py` | new (#1006) | 11 subprocess tests |
| `.claude/rules/rule_session-pressure.md`, `tools/INDEX.md` | edit (#1006) | describe per-session file |
| `.claude/hooks/deploy-consumer-gate.py` | edit (#1012) | deploy match on executed view |
| `.claude/patterns/warn-attach-busy-cdp-9222.md` | edit (#1012) | bash event |
| `tools/tests/test_deploy_consumer_gate.py`, `tools/tests/test_pattern_rules_gate.py` | edit (#1012) | new cases |
| `docs/friction-register.md` | edit | 6 rows updated, 5 new |
| memory `reference_pretooluse_updatedinput_semantics.md` | new | experiment findings |

---

## Current Status

#1006 merged (0f8d2d2b) and #1012 merged (acd92889), both on 6/6 green CI. No client infrastructure touched (system scope, no infrastructure.yaml). Live hooks run from the primary clone, which is behind main, so both fixes reach live sessions only when that clone pulls. The primary clone's shared legacy state file keeps receiving writes from the old hooks until then; `--status` from any checkout at or past #1006 already reads the right session.

---

## Next Steps
1. **Owner call on item 5.** Recommendation: build a rewrite-only cd-guard (`updatedInput` with the full `tool_input`, no `permissionDecision`), after one more live probe: `--permission-mode auto` with the rewrite, confirming the classifier evaluates the rewritten command, and a prefix allow rule (`Bash(git status:*)`) against `( cd X && git status )` to measure whether the subshell form adds prompts.
2. Pull the primary clone to main when no sibling is mid-edit, so live hooks pick up #1006 and #1012.
3. Carried owner items: rotate the Brisken Email password exposed 2026-09-16; merge or close stale docs PRs #955 and #970.

---

## Context for Next Session

### Files to Read First
- memory `reference_pretooluse_updatedinput_semantics.md`
- `.claude/hooks/cd-guard.py` (block reason + exemptions, 276 lines)

### Open Questions
- Does the auto-mode classifier see the rewritten or the original command?
- Does `( cd X && cmd )` still match prefix allow rules written for `cmd`? C3/C4 show rules match the rewritten string.
- Replace vs merge for `updatedInput` is untested; sending the full `tool_input` dict is safe under both.

### Working Notes
- Experiment harness: `claude -p PROMPT --model haiku --max-turns 4 --output-format json --setting-sources project --permission-mode default --settings <dir>/.claude/settings.json`, cwd = case dir; `permission_denials[].tool_input.command` shows which string was checked. About $0.04 per case.
- Consumer gate gap left as is: `cat > x.sh <<'EOF'` with a deploy line in the body still opens a marker (heredoc body lines become their own segments in `executed_view`).
- The cdp rule no longer warns when a `.py` file containing `connect_over_cdp(...:9222)` is written; inline `python -c` and heredocs still warn.

### Reference Materials
- PRs #1006, #1012
- `docs/2026-09-17 - Friction Check And Gate Fixes/Checkpoint.md`

---

## How to Continue

Only item 5 remains, and it waits on the owner's call. If approved: one worktree, run the two probes above in a throwaway dir with `--settings`, then build the rewrite into cd-guard behind tests that drive the hook subprocess and assert no `permissionDecision` is ever emitted alongside `updatedInput`.

---

## Strategic Feedback

### What Worked Well This Session
- Testing the stop condition before building: ten headless runs (about $0.56 reported by `total_cost_usd`) settled a question the docs left open. That result decided item 5 in one step.

### Suggestions
- The live gates in the primary clone lag main by 20+ commits during sibling-heavy days, so a gate fix merged in the morning still misfires all afternoon (3 false markers here after #999/#1012's class was known). A SessionStart advisory that names hook files differing from origin/main would make the lag visible.

### System Health
- Autonomy: 0 human interventions (fully autonomous session). Hooks held on every shell trap (3 calls lost to cd-guard and the heredoc gate, 1 more to an MSYS path); the item that removes that tax is the one now awaiting a decision.

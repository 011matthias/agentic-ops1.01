# Checkpoint: Friction Check And Gate Fixes

**Date:** 2026-09-17
**Status:** Round 1 shipped (2 of 4 fixes). Stopped at moderate pressure (~310k) before the two larger items.

---

## Summary

A friction-register review of the last 7 days (126 rows, 82 unresolved) ranked six problem classes; this session fixed the two tooling defects that kept producing false claims or rework: checkpoint mini numbering (PR #996, merged) and the deploy consumer gate's false closes (PR #999).

---

## What Was Done This Session

### Friction review (read-only)
1. Pulled the register from origin/main (the checkout was 12 commits behind), parsed it with `friction-watch.py`'s parser, and read all 126 rows from 09-10..09-17.
2. Ranked by damage, not volume: (1) confident claims from unvalidated probes reaching the owner or merged PRs (~15 rows); (2) consumer gate closing on nothing (12 rows); (3) machine-global state vs sibling sessions (~9); (4) scaffold mini numbering (7); (5) shell-trap tax (~17 rows, ~70 calls in 7 days); (6) Lovable prompts pasted as rendered markdown (5, memory-only).
3. Housekeeping found: plaintext vault password printed into a transcript on 09-16 (no rotation recorded); green docs PRs #955 and #970 unmerged; 4 register rows with unescaped `|` that mis-parse.

### Fix #4: `checkpoint_scaffold.py` (PR #996, merged 245d4930)
1. `pre` and `finalize` share one naming rule: the highest mini file INDEX does not link yet is reused; a linked top file means top + 1.
2. `--root` accepted after the subcommand.
3. Tests drive `pre` -> write prose -> `finalize` through `main()`; `regress_check` bites on both wiring points; `preflight --full` 1751 passed.

### Fix #2: `deploy-consumer-gate.py` (PR #999, merged 0e33fbd1)
1. `backgrounded()` reads `backgroundTaskId` / `timedOutAfterMs` / the "running in background with ID" text (key names from 440 transcript `toolUseResult` records).
2. `failed()` reads agent-browser's `✗ ... (os error N)` line.
3. Browser patterns match `executed_view()`: variables resolved (bash and PowerShell), text-only programs dropped, quoted args ignored unless run as inline code; bare `\bplaywright\b` tightened.
4. 69 gate tests through the hook subprocess; `regress_check` bites on all three wiring points; `preflight --full` 1766 passed.

---

## Key Decisions Made

### Stop before #3 (per-session state) and #5 (shell-trap rewrites)
- **Choice:** checkpoint at the #999 breakpoint instead of starting #3.
- **Rationale:** #3 has no single binding point (28 hooks read stdin separately; ~12 call `session_state`), and #5 needs a live experiment first. Either would cross the high band mid-edit.

### Detect both response shapes in the consumer gate
- **Choice:** accept structured keys AND the text notice.
- **Rationale:** the hook's `tool_response` shape was inferred from transcripts; no hook has ever logged it, and editing the live hooks in the shared primary clone was not an option with siblings active.

---

## What Did NOT Work (and why)

- **`cd <worktree> && ...` in Bash (3x):** cd-guard refuses it, including a `cd` placed after a leading `cat ...;`. Subshell `( cd X && ... )` works. This is the #5 class itself.
- **rg regex with escaped quotes over transcripts:** returned nothing because the bash quoting mangled the pattern; `rg -F -e` fixed strings worked.
- **First pre->finalize test:** FileNotFoundError because `pre` does not create the checkpoint folder; the test now creates it (not a product defect).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/checkpoint_scaffold.py` | edit (#996) | shared mini naming rule, `--root` either position |
| `tools/tests/test_checkpoint_scaffold.py` | edit (#996) | pre -> prose -> finalize sequence tests |
| `.claude/hooks/deploy-consumer-gate.py` | edit (#999) | timeout-background, failure line, `executed_view()` |
| `tools/tests/test_deploy_consumer_gate.py` | edit (#999) | 17 new cases |
| `docs/friction-register.md` | edit | flipped rows fixed by #996 / #999, 2 new rows |

---

## Current Status

#996 and #999 merged on main (all 6 CI checks green on both). 19 register rows flipped (18 Yes, 1 Partially). Live hooks run from the primary clone, which is behind origin/main and owned by sibling sessions, so the gate fix takes effect only when that clone reaches main. No client infrastructure touched.

---

## Next Steps

1. **#3 per-session state file.** `tools/session_state.py` keeps one temp file; `ensure_session` resets it whenever another session writes. Design: path `agentic-ops-session-state-{sid}.json`; `AGENTIC_OPS_SESSION_STATE` still wins; hooks bind from payload `session_id` (a `bind_session()` call after parsing stdin in each writer: pressure meter via `ensure_session`, stop-b1-gate, input-classifier, tool-failure-gate, and the 9 `add_candidate` hooks); CLI resolves `CLAUDE_CODE_SESSION_ID` (present in Bash env, verified); legacy shared file only as last fallback; sweep stale per-session files. Fix `session_registry.py:280`, which reads the nonexistent `CLAUDE_SESSION_ID`.
2. **#5 shell traps.** PreToolUse `hookSpecificOutput.updatedInput` exists (docs example pairs it with `permissionDecision: "allow"`); replace-vs-merge and the permission / auto-mode interaction are undocumented. Run a live experiment before building a rewrite into cd-guard (`cd X && cmd` -> `( cd X && cmd )`): an `allow` rewrite must not skip prompts the command would otherwise get.
3. **Consumer gate deploy detection** still matches raw command text (register row 2026-09-17 slow-path, marker opened on a command containing 'flyctl deploy'): apply `executed_view()` to the deploy patterns too.
4. **Pattern-rule precision:** `warn-attach-busy-cdp-9222` fired on an Edit to a test file whose fixture text contains `--cdp 9222`; restrict it to the bash event or to executed commands.
5. Owner items: rotate the Brisken Email password exposed 2026-09-16 (owner's call); merge or close stale docs PRs #955 and #970.

---

## Context for Next Session

### Files to Read First
- `tools/session_state.py` (public API from line 257; `STATE_FILE` / `LOCK_FILE` globals at 58-61)
- `.claude/hooks/session-pressure-meter.py` lines 90-150
- `.claude/hooks/cd-guard.py`

### Open Questions
- Do hook processes inherit `CLAUDE_CODE_SESSION_ID`? Unverified; design #3 so it does not matter.
- Does a PreToolUse `updatedInput` with `permissionDecision: "allow"` bypass the permission rules or auto-mode classifier for the rewritten command?

### Working Notes
- `session_state.py --status` in this session read `calls=1..2` at ~60 real tool calls and `pre` drained zero candidates: live evidence of #3.
- Transcript `toolUseResult` for a timeout-backgrounded Bash: `{stdout, stderr, interrupted, isImage, noOutputExpected, backgroundTaskId, timedOutAfterMs: 120000}`; explicit background adds `backgroundCwdHint` instead.
- Register rows carry a 7th regression cell, so "Resolved?" is cell 5, not the second-to-last.

### Reference Materials
- PRs #996, #999
- `docs/2026-09-17 - ECC Batch 2 Live Activation/Checkpoint.md` (open ECC item = #3 above)

---

## How to Continue

Start #3 in its own worktree on a `sys/` branch from origin/main. Bind per hook from the payload, keep tests running through the hook subprocess, and `regress_check` the binding in at least one hook, not only in `session_state.py`.

---

## Strategic Feedback

### What Worked Well This Session
- Pulling evidence before coding the gate fix: 440 transcript records gave the real `backgroundTaskId` / `timedOutAfterMs` keys, where the docs and existing code only knew `run_in_background`.

### Suggestions
- `regress_check.py` output for a mutation that fails several tests only prints the last failure under `tail`; grep for `FAILED` lines instead, as done here.

### System Health
- Autonomy: 0 human interventions (three directives, no corrections). The session hit cd-guard 3 times while fixing the friction list that ranks it; the hook held each time, and the rewrite path (#5) is what removes that cost.

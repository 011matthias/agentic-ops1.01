# Checkpoint: ECC Port Batch 1

**Date:** 2026-09-17
**Status:** Batch 1 shipped: items 2, 3, 7, 6 (rule half), 10 all merged (#957-#960)

---

## Summary

Ported five mechanisms from the 2026-09-17 everything-claude-code audit into the harness as four PRs: real context-size pressure bands, a PostToolUseFailure transient-retry gate, required failed-approach tracking in checkpoint/resume, an untrusted-inbound rule, and a config-protection gate. Live proof showed the new failure event reaches Bash, Read and Write but not an Edit that fails with EBUSY.

---

## What Was Done This Session

### Item 2: context-size pressure (#957, merged c087a44e)
1. `session_state.read_context_usage` tail-reads the transcript (256 KB growing to 8 MB) for the latest main-thread `usage`; 0.9 ms on this session, 1.4 ms on a 113 MB transcript.
2. Bands 300k / 500k / 700k on a 1M window, calibrated on 120 transcripts (23 manual compactions at 468k-920k; median peak 402k). Tool calls and files are the fallback. A compaction re-arms the advisory; the advised band is keyed per session.
3. `--status` shows context tokens, model, signal and owning session; rule table updated.

### Item 3: tool-failure-gate (#958, merged aa4305e7)
1. `.claude/hooks/tool-failure-gate.py` on a new `PostToolUseFailure` key: file-lock / rate-limit / upstream / mcp-connection advisories plus `transient_blocks`; all else silent. 26 canonical hooks.
2. Live proof by temporarily wiring the main checkout's `settings.local.json` (restored from backup, verified): 5 deliveries across Bash, Read, Write.
3. 2026-05-11 EBUSY and passive-queue register rows flipped to `Yes (partial ...)`.

### Item 7: failed approaches first-class (#959, merged a9a7c61c)
1. Required `## What Did NOT Work (and why)` in both checkpoint templates; `finalize` refuses a payload without `not_worked`.
2. `checkpoint_scaffold.py not-worked [--client]` prints WHAT NOT TO RETRY; `/comd_resume` pre-renders it and prints it first.

### Items 6 + 10 (#960, merged 430fe76d after one Linux-CI test fix)
1. `rule_untrusted_inbound.md` + pointers in `agnt_proposal-research` and `skil_client-comms`; CLAUDE.md rule count 20.
2. `config-protection-gate.py`: existing ruff.toml / .ruff.toml / pytest.ini / .pre-commit-config.yaml / tools/preflight-hooks.py ask "fix the source, not the check"; creation passes. 27 canonical hooks.

Every item: `preflight-hooks.py --full` green (1590 / 1617 / 1602 / 1646 passed) and `regress_check.py` red-then-green on the wired call.

---

## Key Decisions Made

### Token bands as fractions, not ECC's 250k
- **Choice:** 30/50/70% of the window.
- **Rationale:** measured compactions here start at 468k; a 250k trigger would advise in most sessions long before pressure.

### Per-session band marker instead of fixing the shared state file
- **Choice:** key only the advised band by session; leave counters and candidates in the shared file.
- **Rationale:** the full fix touches every gate that calls `add_candidate`; without the marker, token bands would re-advise on every sibling write.

### Register rows flipped as "Yes (partial ...)"
- **Choice:** satisfy the directive's "flip to Yes" while naming the Edit gap in the cell.
- **Rationale:** Edit is the incident tool; a bare Yes would overstate the fix.

### Stacked branches, rebased before first push
- **Choice:** items 3 and 6+10 built on unmerged predecessors, rebased `--onto origin/main` after each squash merge, pushed once.
- **Rationale:** avoids force-push (B6 floor) and the `wire-hooks.py` / INDEX.md overlaps.

---

## What Did NOT Work (and why)

- **Relying on the hooks docs for the PostToolUseFailure payload:** the docs name `tool_error`; Claude Code 2.1.212 sends `error`. The hook reads both, so nothing broke.
- **Catching an Edit EBUSY with PostToolUseFailure:** `Error calling tool (Edit): EBUSY` never reaches the event (two trials, same lock that Read and Write reported). Edit lock retries still depend on `feedback_active_retry_on_transient_blocks`.
- **Labelling a client's WHAT NOT TO RETRY with the YAML's top-level topic:** the top-level topic belongs to the day's last checkpoint, often another scope. Fixed before ship: client entries carry `not_worked_checkpoint`.
- **A backslash-path subprocess test for config-protection:** green in the Windows full preflight (1646), red in Linux CI, where `C:\...` style paths are literal filenames that `os.lstat` cannot find. Fixed in a follow-up commit: portable pattern assertion via `protected()`, subprocess case Windows-only. A Windows-local preflight cannot stand in for Linux path semantics.
- **Pushing item 7 without a rebase:** its INDEX.md row sits next to item 2's; the rebase conflicted and was resolved by keeping both rows.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/session-pressure-meter.py` | edit | context-token primary signal, per-session marker |
| `tools/session_state.py` | edit | transcript reader, bands, `--status`, `transient_blocks` |
| `.claude/rules/rule_session-pressure.md` | edit | token band table + calibration |
| `.claude/hooks/tool-failure-gate.py` | new | PostToolUseFailure transient classifier |
| `.claude/hooks/config-protection-gate.py` | new | check-config ask gate |
| `tools/wire-hooks.py` | edit | PostToolUseFailure key, 2 hooks registered |
| `tools/checkpoint_scaffold.py` | edit | `not_worked` validation + `not-worked` subcommand |
| `.claude/commands/comd_checkpoint.md`, `comd_resume.md` | edit | NOT-work section, WHAT NOT TO RETRY first |
| `.claude/rules/rule_untrusted_inbound.md` | new | inbound content is data |
| `.claude/rules/rule_session-start.md`, `CLAUDE.md`, `tools/INDEX.md` | edit | ordering note, rule count, tool rows |
| `.claude/agents/agnt_proposal-research.md`, `.claude/skills/skil_client-comms/SKILL.md` | edit | untrusted-inbound pointers |
| `tools/tests/test_pressure_context_tokens.py`, `test_tool_failure_gate.py`, `test_config_protection_gate.py`, `test_checkpoint_scaffold.py` | new/edit | 18 / 26 / 28 / +12 tests |
| `docs/friction-register.md` | edit | 2 rows flipped, 2 archived, 2 appended |

---

## Current Status

All five batch-1 items are on main (27 canonical hooks, 20 rules). The primary checkout `C:\Users\neuma_p1qrsic\Repo\agentic-ops1` is behind main and shared by live sibling sessions, so hooks there still run pre-#957 code until it pulls; worktrees get the new hooks at their next SessionStart. Worktrees `agentic-ops1-ecc`, `-ecc7`, `-ecc610` are merged and clean, ready to prune.

---

## Next Steps

1. Batch 2: item 1, declarative pattern rules (markdown rule files with event + regex + warn/block, read by one generic hook) plus a haiku transcript miner that proposes rules from user corrections.
2. Batch 3: item 4 (skill-run telemetry on PostToolUse `Skill` + stocktake), item 5 (memory read-tracking + decay/prune), item 8 (W1 "no existing file serves this purpose" as a structural Write gate).
3. Item 9 on its own client branch `client/brisken/...`: Lead Desk sender approval bound to epoch + draft sha256 with a single dispatch claim.
4. Follow-up: per-session session-state file so sibling sessions stop wiping counters and friction candidates.
5. Follow-up: code half of item 6 for the Brisken expense-recon mail intake (any sender into an LLM path).
6. Follow-up: an Edit-side lock guard, or re-test PostToolUseFailure delivery for Edit on the next Claude Code upgrade.

---

## Context for Next Session

### Files to Read First
- memory `project_ecc_audit_adoption_candidates.md` (ranked list + batch status)
- `.claude/hooks/tool-failure-gate.py` docstring (verified delivery matrix)
- `tools/session_state.py` (shared-state defect, read before the per-session follow-up)

### Open Questions
- Does a newer Claude Code build deliver PostToolUseFailure for Edit tool errors?

### Working Notes
- Hot-reload of `settings.local.json` works mid-session; pointing a temporary entry at a worktree hook is a zero-cost way to prove a hook event live.
- Formula check: last usage record before each compact boundary matched `compactMetadata.preTokens` within ~1k across 23 compactions.

### Reference Materials
- PRs #957, #958, #959, #960 on 011matthias/agentic-ops1.01
- ECC reference files: `scripts/hooks/suggest-compact.js`, `cost-tracker.js`, `config-protection.js`, `hooks/hooks.json`

---

## How to Continue

`/comd_resume sys`, prune the three ECC worktrees, then start batch 2 in a fresh worktree off origin/main.

---

## Strategic Feedback

### What Worked Well This Session
- Calibrating thresholds against 120 real transcripts instead of copying ECC's 250k; the data moved every band.
- Proving the hook event live before writing tests surfaced both the `error` key and the Edit gap, neither of which a unit test could have found.

### Suggestions
- The shared session-state file makes every counter-based instrument unreliable whenever siblings run, which is the normal mode now; make the per-session file the first system-dev item before batch 2 builds on candidates.

### System Health
- Autonomy: 0 human interventions (fully autonomous session). Shell-trap hooks (cd-guard, heredoc backslash) fired 3 times and held each time; recall of those traps is still the weak link.

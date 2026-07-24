# Checkpoint: Checkpoint Scaffold Speedup

**Date:** 2026-07-24
**Status:** Shipped — PR #426 merged CI-green

---

## Summary
`/comd_checkpoint` was slow because it ran ~14 sequential sections, generated the same session prose ~2.5 times, and read the two big ledgers into context on every run. Built `tools/checkpoint_scaffold.py` to collapse the mechanical half into two calls and keep the 56 KB INDEX and 442 KB register out of agent context entirely.

---

## What Was Done This Session
### Diagnosis
1. Traced the wall-clock cost: not the checkpoint files (13–18 KB each) but three separate places — same content authored ~2.5x (Checkpoint.md + session-log entry + context YAML), big-file reads (`docs/INDEX.md` 56 KB, `docs/friction-register.md` 442 KB) on the INDEX-insert and regression-check steps, and a long tail of ~20–30 sequential side-quest tool calls.

### Build (PR #426)
1. `tools/checkpoint_scaffold.py` — three subcommands: `pre` (read-only gathering: target path with Mini-N numbering, friction-candidate drain, per-client ops status + comms staleness + project-status check, register size advisory + regression grep), `finalize --payload F` (folder, session-log frontmatter bump + derived entry, INDEX row insert, context-YAML merge, register-row append, confirm line), `archive-register [--days 60]` (moves resolved rows older than the window to `friction-register-archive.md`).
2. Ledger edits are string-level (append/insert), so INDEX and the register never enter agent context; the regression check is a targeted grep the `pre` step prints.
3. `tools/tests/test_checkpoint_scaffold.py` — 7 tests (fresh-day artifacts, second-session merge with frontmatter counters + pipe-escaping + YAML client merge, INDEX section-top insert, mini numbering, missing-field exit code, archive old-resolved-only, archive noop).
4. Rewrote `.claude/commands/comd_checkpoint.md` to the two-call flow; judgment work (friction classification, gate audit, prose authoring) unchanged; explicit "never Read INDEX/register into context".
5. `tools/INDEX.md` manifest row.

---

## Key Decisions Made
### Session prose is authored once, not three times
- **Choice:** `finalize` derives the `### Session {N}` log entry from the payload's `entry` fields; the agent writes only Checkpoint.md.
- **Rationale:** Generation is the dominant wall-clock cost. The session-log entry and YAML `next_steps` were re-generating content already in the checkpoint.

### JSON fallback for the context file
- **Choice:** `checkpoint_scaffold.py` loads/dumps the context file via pyyaml when present, JSON otherwise (JSON is a YAML subset, so `/resume` still parses it).
- **Rationale:** The first version used unconditional `import yaml`; the CI pytest env has no pyyaml and 4 tests failed under `preflight --full`. The fallback keeps the module importable in CI while `uv run` (PEP 723 dep) gives real YAML in normal use.

### Archive deferred, not run in this session
- **Choice:** Ran the checkpoint (append-only ledger edits) but did NOT run `archive-register` despite the >200 KB advisory.
- **Rationale:** `archive-register` rewrites the whole register. With 5 live sibling sessions appending to origin/main's register, a full-file rewrite is the change most likely to collide and silently revert a sibling's append (the 2026-07-22 near-miss: "a ledger file batched out of a shared clone is a MERGE, never a copy"). The register grew only ~4 KB in a day; not urgent. Run it when the tree is quiet (no siblings).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| tools/checkpoint_scaffold.py | Created | Deterministic half of /comd_checkpoint (pre/finalize/archive-register) |
| tools/tests/test_checkpoint_scaffold.py | Created | 7 tests, pass with and without pyyaml |
| .claude/commands/comd_checkpoint.md | Rewritten | Two-call flow |
| tools/INDEX.md | Modified | Manifest row |

---

## Current Status
PR #426 merged to main on green CI (all 5 checks: gitleaks, spell, type/lint/build, enforcement-hook pytest, Playwright smoke). Worktree + feature branch cleaned up. The new flow is live for the next session's checkpoint. This checkpoint is the first real use of it — dogfooded through the `docs/checkpoint-2026-07-24` PR.

---

## Next Steps
1. Run `uv run tools/checkpoint_scaffold.py archive-register` at a quiet moment (no sibling sessions) to split the 442 KB register into `docs/friction-register-archive.md`; ship as its own docs PR.
2. Optional follow-ups from the original diagnosis, not yet built: move the MCP infrastructure-reconciliation out of the default checkpoint path into `/comd_weekly-review` or `/comd_eod-capture` (per-checkpoint network round-trip that rarely finds drift).

---

## Context for Next Session
### Files to Read First
- tools/checkpoint_scaffold.py (the tool)
- .claude/commands/comd_checkpoint.md (the flow that drives it)

### Open Questions
- None blocking. The archive split is a when-quiet action, not a decision.

### Working Notes
- The pyyaml failure was caught by `preflight --full` before shipping (one fix iteration), not in CI — the preflight is the gate and it held. Not promoted to friction: process worked as designed.
- `pre` runs `project_status.py --check`, `session_state.py --list-candidates`, and reads `infrastructure.yaml` per client via subprocess; it fail-opens on each. Live smoke against the real tree returned the brisken project-status output (2 stale status files flagged: p2-lead-gen-general, p2-outreach, both 32d) plus the register advisory and slow-path regression rows.
- Sibling-tree hazard: this checkpoint's own ledger writes went through a `docs/...` worktree off origin/main (append/insert only), NOT a commit against the dirty shared main index that 5 siblings share.

### Reference Materials
- PR #426: https://github.com/011matthias/agentic-ops1.01/pull/426

---

## How to Continue
The flow is shipped and self-documenting in `comd_checkpoint.md`. Next full checkpoint just runs `pre` → write Checkpoint.md → `finalize`. When no siblings are live, run `archive-register` to shrink the register.

---

## Strategic Feedback

### What Worked Well This Session
- The user framed the problem as a felt symptom ("checkpoints feel slow, files could be huge") rather than a spec. Measuring where the time actually went (files were NOT the problem; generation + big-file reads were) redirected the fix from "trim the files" to "stop re-authoring and stop reading the ledgers".

### Suggestions
- When a checkpoint's ledger writes must go through a worktree because of live siblings, that adds a full `git worktree add` (2640-file checkout) of overhead. If concurrent multi-session work becomes the norm, a lighter-weight ledger-append path (append via `git show origin/main:` + a targeted commit without a full checkout) would cut that.

### System Health
- The scaffold is the Layer-1 operationalization the behaviors rule prefers (tool > rule > memory): the mechanical steps can no longer be skipped or done slowly, and the big-file reads are structurally impossible. The judgment work (friction classification, prose) stays with the agent where it belongs.
- Autonomy score: 0 human interventions this session (1 hook-caught B1 deferral on the first response, self-corrected in-session; the build itself ran without user correction).

# Checkpoint: ECC Port Batch 2 (items 1, 4, 5, 8)

**Date:** 2026-09-17
**Status:** Shipped. All four items merged to main (#966, #964, #965, #961).

---

## Summary

Ported four mechanisms from the 2026-09-17 ECC audit: declarative pattern rules (the structural one), skill-run telemetry with a stocktake, memory read-tracking with an audit, and the W1 new-file purpose check. Batch 1 ran concurrently in a sibling chat and landed first; the two batches met only in `wire-hooks.py` and `tools/INDEX.md`.

---

## What Was Done This Session

### Item 1 — declarative pattern rules (#966)

1. `.claude/patterns/*.md`: frontmatter (name, enabled, event, pattern or AND-conditions, action, message, source, created) plus a body, read at runtime by ONE hook. Tracked, and deliberately not under `.claude/rules/`, so rules cost no context.
2. `.claude/hooks/_pattern_rules.py` (stdlib parser, matcher, lint) shared by the hook and the CLI, so they cannot disagree about what a rule means.
3. `.claude/hooks/pattern-rules-gate.py` wired on UserPromptSubmit, PreToolUse Write|Edit, PreToolUse Bash|PowerShell and Stop (hook count 27 → 28).
4. `tools/pattern_rules.py new | lint | list | test | digest`; `lint` added to the CI hooks job and `preflight-hooks.py`.
5. Five seed rules; three register rows flipped from `memory`/`TBD` to `pattern-rule:<name>`.
6. Integration: `checkpoint_scaffold.py` validates the `pattern-rule:` fix value, `anneal-metrics.py` counts it as structural, `rule_behaviors` ladder gained rung 1b, `comd_checkpoint.md` gained the fix type and the optional haiku rule miner.

### Item 4 — skill-run telemetry + stocktake (#964)

1. `tools/telemetry_store.py`: append-only identifier-only JSONL under `~/.claude/agentic-ops-telemetry/`.
2. The pressure meter records `{ts, session_id, kind, name, ok}` per Skill/Agent call as a third rider beside the heartbeat and bg-watch riders.
3. `tools/skill_stocktake.py` joins 57 skills, 32 commands and 12 agents with 30/90-day run counts into Retire / Merge / Improve candidates with evidence.

### Item 5 — memory read-tracking + audit (#965)

1. The same rider records `{ts, session_id, store, file}` for memory-file reads (Read tool, or cat/sed/head/tail/Get-Content, with same-command variables resolved).
2. `tools/memory_audit.py`: reads 30/90d, MEMORY.md integrity both ways, likely duplicates, stale project memories. Buckets only; it changes nothing.

### Item 8 — new-file purpose check (#961)

1. `file-placement-gate.py` now asks on a new file under `workspace/{clients,projects}/*` whose stem matches an existing same-kind file once revision tokens are dropped, or whose name is a snapshot shape.

---

## Key Decisions Made

### Extend `file-placement-gate.py` instead of adding a hook for item 8
- **Choice:** the W1 check rides the existing Write gate.
- **Rationale:** same decision point, no `wire-hooks.py` edit, so item 8 could ship while batch 1 still held that file. Hook count unchanged.

### Stop-event warnings are parked, not dropped
- **Choice:** a stop `warn` goes to a tempdir store keyed by session_id and is delivered by the same hook's prompt arm next turn.
- **Rationale:** Stop hooks have no `additionalContext` channel, so a warn there would reach the user, not the agent. Same shape as the B1 primer.

### Telemetry lives in `~/.claude/agentic-ops-telemetry/`, not the session-state temp file
- **Choice:** deviate from the brief's "existing session-state dir".
- **Rationale:** that dir is `%TEMP%`, which Storage Sense purges; 30/90-day windows would silently truncate. The new home is outside every checkout, so it can never be committed and all worktrees share it.

### Heuristics calibrated against the real tree, not accepted as specified
- **Choice:** replaced the brief's difflib >= 0.6 / shared-token test for item 8 with stem-skeleton equality; replaced a raw slug ratio with a differing-part comparison for memory duplicates; raised the skill-overlap threshold to 0.75.
- **Rationale:** measured noise. See What Did NOT Work.

---

## What Did NOT Work (and why)

- **difflib ratio >= 0.6 across the subtree (item 8, as briefed):** leave-one-out over the 858 text files in `workspace/` would have asked on 70.2% of them; shared content tokens on 26.2%; same-dir 0.6 on 39.0%. A gate that asks that often gets approved reflexively. Stem-skeleton equality asks on 7.3% at 90.3% recall on synthetic revision copies.
- **Raw slug similarity for memory duplicates:** shared long prefixes dominate the score. `project_brisken_expense_recon_mail_intake` vs `..._master_data` scored 0.82 with nothing in common but the prefix. Fixed by comparing only what differs after stripping shared leading and trailing tokens.
- **Description similarity at 0.6 for skill Merge candidates:** flagged `skil_make-pack` vs `skil_n8n-pack` (0.61) and `comd_make-instances` vs `comd_n8n-instances` (0.67), which are deliberate per-orchestrator twins. Threshold raised to 0.75.
- **First regex for `warn-git-exit-masked-by-pipe`:** `[^|&;]*` before the pipe could not span `2>&1`, so the rule matched neither real incident. `pattern_rules.py test --text` showed it in one call.
- **`git rebase origin/main 2>&1 | tail -1 && git branch -f ...`:** a pipeline reports the LAST command's exit status, so the `&&` ran despite a conflicted rebase and moved a branch ref mid-rebase. Nothing was lost (the commit stayed reachable), and the incident became the fifth seed rule.
- **`sed -i` on the `PATTERN_RULE_FIX` regex line:** the escaping never matched, so the file was unchanged while the command reported success; the test stayed red until the same edit went through the Edit tool.
- **First W1 calibration run:** O(n²) over brisken's 1,847-file Graph corpus cache, killed at the 600 s timeout. Cache directories are machine-written and now excluded from both the calibration and the shipped walk.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/_pattern_rules.py` | new | rule format, parser, lint, matcher |
| `.claude/hooks/pattern-rules-gate.py` | new | the four-arm runtime |
| `.claude/patterns/*.md` | new (5 rules + README) | seeds |
| `tools/pattern_rules.py` | new | new / lint / list / test / digest |
| `tools/telemetry_store.py` | new | skill-run + memory-read JSONL |
| `tools/skill_stocktake.py` | new | inventory joined with usage |
| `tools/memory_audit.py` | new | memory store audit |
| `.claude/hooks/session-pressure-meter.py` | edit | telemetry rider |
| `.claude/hooks/file-placement-gate.py` | edit | W1 purpose check |
| `tools/wire-hooks.py` | edit | 28th hook, four arms |
| `tools/checkpoint_scaffold.py` | edit | `pattern-rule:` fix validation |
| `tools/anneal-metrics.py` | edit | `fix_layer`, structural share |
| `tools/preflight-hooks.py`, `.github/workflows/ci.yml` | edit | pattern lint step |
| `.claude/commands/{comd_checkpoint,comd_system-dev}.md` | edit | fix type, miner, signal sources |
| `.claude/rules/{rule_behaviors,rule_file_placement,rule_no_file_bloat}.md` | edit | rung 1b, W2 home, W1 backstop |
| `docs/friction-register.md` | edit | 3 rows flipped to `pattern-rule:` |
| `tools/tests/test_{pattern_rules_gate,skill_telemetry,memory_audit}.py` | new | 67 tests |
| `tools/tests/test_{file_placement_gate,checkpoint_scaffold,anneal_metrics}.py` | edit | +20 tests |

---

## Current Status

All four PRs merged to main and CI-green on six checks each. Ops status: no client infrastructure touched (system scope).

The new gate is not yet ACTIVE on this machine. The wired hook commands resolve against the primary clone, which a sibling session currently holds on `client/brisken/recon-untrusted-inbound`, five commits behind main. `pattern-rules-gate.py` does not exist in that tree yet, so its four arms are inert there until the clone returns to main and SessionStart re-runs `wire-hooks --ensure`. Wiring was proven in this session's worktree: 28/28 hooks, four arms across three event names.

---

## Next Steps

1. After the primary clone returns to main, confirm the gate is live: `uv run tools/wire-hooks.py --check` (expect 28/28), then run a `git add -A` command and look for the `[PATTERN WARN: warn-git-add-all]` advisory in the tool result.
2. Let telemetry accumulate. `skill_stocktake.py` and `memory_audit.py` issue no Retire verdicts until 30 days of data exist (first useful run ~2026-10-17).
3. Use the pattern-rule path at the next checkpoint that would otherwise write Fix=memory, and try the haiku rule miner once on a real session.
4. Items 3, 6-rule, 7, 10 landed in batch 1; item 9 shipped separately (#963). Nothing from the ECC audit list is outstanding except the deliberate Skip set.

---

## Context for Next Session

### Files to Read First
- `.claude/hooks/_pattern_rules.py` (the rule contract, in its docstring)
- `.claude/patterns/README.md`
- `tools/INDEX.md` rows for `pattern_rules.py`, `skill_stocktake.py`, `memory_audit.py`, `telemetry_store.py`

### Open Questions
- Does the 7.3% W1 ask rate feel right in practice, or should numbered series (recording transcripts) be exempted too?
- Should `memory_audit.py` run at SessionStart like `project_status --sweep-stale`, or stay a system-dev-only signal?

### Working Notes
- Calibration numbers are in the PR bodies of #961 and #965; the throwaway calibration scripts were not kept (W1).
- The stocktake's first real run: Retire 0, Merge 1 (`skil_make-scenario-patterns`, a consolidation stub hosting nothing), Improve 3 (`comd_test` 25-char description, `skil_owasp-security` 623 lines, `skil_upwork-proposals` no frontmatter).
- The memory audit's first real run: 143 files, 143 index entries, Verify 5 (project memories 62 to 128 days old still saying pending/awaiting/todo).
- PreToolUse decisions resolve deny > defer > ask > allow (per the hooks docs), which is why the W1 ask survives `auto-approve-protected`'s allow.

### Reference Materials
- ECC audit list: memory `project_ecc_audit_adoption_candidates.md`
- PRs #961, #964, #965, #966

---

## How to Continue

Nothing is half-built. To extend the mechanism, write a rule file (or `pattern_rules.py new`), prove it with `test --text` against the incident text, and add a SEEDS entry in `tools/tests/test_pattern_rules_gate.py`.

---

## Strategic Feedback

### What Worked Well This Session
- Calibrating each heuristic against the real tree before shipping it. Three of the four thresholds in the brief would have produced gates noisy enough to be approved reflexively, and each was caught by one measurement rather than by review.
- Splitting item 8 so it rode an already-wired hook removed the only real cross-batch dependency, and it shipped first while batch 1 still held `wire-hooks.py`.

### Suggestions
- `regress_check.py` proved every fix this session; the four bite runs cost about eight minutes total. Worth making it the default closing step of any hook change rather than a per-session decision.

### System Health
- Autonomy: 0 human interventions (fully autonomous session).
- The enforcement layer intercepted about six shell traps (heredoc gate, cd-guard, MSYS) that would each have cost a failed call. The hooks work; recall of the traps still does not, which is the recurrence this session's fifth seed rule addresses for the git-pipe case.
- The primary clone sitting on a client branch with ~26 registered sessions is the reason a system change cannot be verified live from a worktree. Worth a convention: system-scope sessions should not leave the primary clone off main.

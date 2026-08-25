# Checkpoint: Enforcement Hook Layer Fixes

**Date:** 2026-08-24
**Status:** Shipped (PR #596 merged, `fd123a0e`)

---

## Summary

Five enforcement-layer defects surfaced by the 2026-08-24 Brisken recon session, fixed and merged in one PR: two false-positive narrowings in `gate-skip-detector`, one new PreToolUse gate for Bash heredocs, one new tool plus rule clause turning "regress the source and watch it go red" into an executable criterion, and the register-archive advisory made actionable or silent.

---

## What Was Done This Session

### 1. `gate-skip-iteration-3x` streak identity

The streak fingerprint hashed `normalized_command[:200]`. Reproduced before fixing: four distinct one-shot measurement scripts behind a 223-char shared prefix all hashed to `8bfe405ab38b`, because the script name sat past the window; two `python - <<'PYEOF'` edits collided on a shared preamble. Six false advisories in one session, none a fix-then-test loop.

`command_identity()` now covers the whole normalized command plus a heredoc-body digest and the sorted set of invoked script paths. The two explicit discriminators are redundant with the full hash on purpose: they make a future re-truncation unable to silently re-collide the exact shapes that misfired.

### 2. `gate-skip-pre-publish` on merges that validated

Two causes. `gh pr checks` was absent from `VALIDATE_PATTERNS` even though CI-green is the Band 2 validation gate; and the ring buffer stores each command truncated to 300 chars, so a validate step late in a long `A && B && gh pr merge` chain fell off the stored line. Added the `gh pr checks` / `gh run watch|view|list` / `preflight-hooks.py` spellings, and the untruncated current command is now scanned alongside the buffer.

### 3. New `heredoc-size-gate.py` (PreToolUse `Bash|PowerShell`)

Three deny classes: body over 80 lines, a Python triple-quoted block in a terminated body, a double backslash in a Python-context terminated body. Reason text points at the Write tool. `HEREDOC_GATE_ALLOW=1` is the user-ordered seam.

The third class was not in the brief; it was added because the failure happened live during this session (see Working Notes). The triple-quote and backslash rules require a terminated heredoc, so a stray `<<WORD` inside a quoted string cannot false-deny on them.

### 4. `regress_check.py` + B2 fix-bites-the-caller

Runs the acceptance criterion rather than asserting it: baseline green, disable the fix in the real source, suite must go red, restore, green again. Exit 1 `TEST DOES NOT BITE` when the suite survives. Refuses a mutation matching other than exactly once; restores the original bytes in a `finally`. The matching rule clause landed in `rule_behaviors.md` beside the existing background-work B2 sub-clause.

### 5. Register-archive advisory

`plan_archive()` searches a sanctioned cutoff ladder (60/45/30/21/14, floored so an active session's own window is never archived) and returns the most conservative cutoff that gets the register under 200 KB, or `None` when no cutoff moves a row. The advisory names days, row count and resulting size, or is suppressed entirely. Added `--dry-run`, and the no-op branch of `archive-register` itself now names a window that would work.

---

## Key Decisions Made

### Full-command identity instead of a larger truncation window

- **Choice:** hash the whole normalized command, plus explicit heredoc/script discriminators.
- **Rationale:** raising the cap to 400 or 800 chars only moves the collision point. A real fix-then-test loop re-runs a byte-identical command, so full hashing loses no true positives; a test pins that.

### Deny, not ask, for the heredoc gate

- **Choice:** `permissionDecision: "deny"`, unlike the `ask` used by `git-stash-gate` and `no-auto-commit-gate`.
- **Rationale:** the remedy (Write the file, run the file) is always available and lossless, so a permission prompt costs the user attention and buys nothing. Matches `file-placement-gate`, the other "wrong tool, use the right one" gate.

### A tool for problem 4, not only a rule

- **Choice:** build `regress_check.py` and reference it from the rule.
- **Rationale:** the brief offered "a rule or checklist item". Both prior attempts at this failure class (2026-08-22, 2026-08-24) already had `fix=documented` and did not hold. Per the self-annealing ladder, a third occurrence buys a tool.

### Ladder plus suppression, not an auto-rolling cutoff

- **Choice:** recommend a shorter cutoff, never apply one silently; suppress the advisory when nothing is archivable.
- **Rationale:** auto-rolling the cutoff would archive rows the operator has not seen. Suppression is what actually kills the every-checkpoint nag.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/gate-skip-detector.py` | edit | `command_identity()`, `gh pr checks` validate patterns, untruncated same-command scan |
| `.claude/hooks/heredoc-size-gate.py` | new | the three-class heredoc deny gate |
| `.claude/rules/rule_behaviors.md` | edit | B2 fix-bites-the-caller sub-clause |
| `.claude/commands/comd_checkpoint.md` | edit | register-archive step reflects the planned advisory |
| `tools/wire-hooks.py` | edit | wire the new gate into `CANONICAL_HOOKS` + `EXPECTED_HOOK_SCRIPTS` (20 to 21) |
| `tools/checkpoint_scaffold.py` | edit | `plan_archive()`, `ARCHIVE_LADDER`, `--dry-run`, planned advisory |
| `tools/regress_check.py` | new | the executable bite check |
| `tools/INDEX.md` | edit | rows for `regress_check.py` and the reworked `archive-register` |
| `tools/tests/hooklib.py` | edit | `load_hook()` for unit-level hook assertions |
| `tools/tests/test_gate_skip_detector.py` | edit | 6 tests for the 2026-08-24 false positives |
| `tools/tests/test_heredoc_size_gate.py` | new | 21-test decision matrix |
| `tools/tests/test_regress_check.py` | new | 13 tests, biting and non-biting fixtures |
| `tools/tests/test_checkpoint_scaffold.py` | edit | `TestPlanArchive` + dry-run + no-op-names-a-window |
| `tools/tests/README.md` | edit | coverage rows for the two suites |

---

## Current Status

Merged to `main` as `fd123a0e` via PR #596; all six CI checks green (secret scan, spell check, type check/lint/build, enforcement hook tests, Lead Desk tests, Playwright smoke). `preflight-hooks.py --full` green locally: ruff, INDEX membership at 90 tools, 1037 passed / 3 skipped.

The hook layer is 21 hooks as of this change. No checkout has the new gate wired yet: `settings.local.json` is gitignored and per-checkout, so each picks it up at its next SessionStart when `wire-hooks --ensure` runs. The primary clone sits on `client/brisken/deckgen-native` with a live sibling session and is behind `origin/main`, so it was deliberately not pulled.

No client work was touched. The register archive (234 rows) ships in this checkpoint's docs PR.

---

## Next Steps

1. Calibrate the heredoc gate against real usage. The FP census was 13 hand-written shapes, not a corpus, which is thin evidence for a hard deny. A misfire is the same "gate cries wolf" failure as problem 1 and should be logged, not tolerated.
2. Consider a `MSYS_NO_PATHCONV` advisory for Bash `git <cmd> <ref>:<path>` on Windows (see Friction). Same shape as `cd-guard`; it cost 2 calls this session despite the memory covering it.
3. Reconcile the 15 stale `status/*.md` files the SessionStart sweep has been flagging (6 brisken, 8 upwork-independence, 1 meji-media), 26 to 35 days stale. Update in place or delete per W1 section 4.

---

## Context for Next Session

### Files to Read First
- `.claude/hooks/heredoc-size-gate.py` (the decision matrix is in the module docstring)
- `tools/regress_check.py` (usage block in the docstring)
- `tools/tests/test_heredoc_size_gate.py` (the negative cases are the contract)

### Open Questions
- Is 80 lines the right heredoc cap, and is deny the right severity? Only real usage answers this.
- Should the backslash rule widen from `\\` to any escape sequence in a Python-context body? It would catch more real corruption and cost more false denies; the `\\` evidence is direct, the rest is inference.

### Working Notes

**The escape collapse is real and happens above the shell.** While profiling the register for problem 5, a `python3 - <<'EOF'` payload containing `(?<!\\)` reached Python as `(?<!\)` and died with `unterminated subpattern at position 28`. Retried through `cat > file <<'PYEOF'`; the written file also contained the collapsed form. A quoted delimiter does not protect against this, which is why the gate does not exempt `<<'TAG'`. Third occurrence of this failure class (2026-08-22, 2026-08-24 recon, here).

**Live register numbers, if the archive has not run yet:** 487 data rows, 244 resolved, oldest 2026-03-09, newest 2026-08-24. Movable at 60 days: 0 (pre-June rows were archived earlier; every remaining resolved row is newer than the default cutoff). At 45 days: 54 rows, leaving 319,375 bytes. At 30 days: 234 rows, leaving 180,104 bytes, which is the first cutoff that clears 200 KB.

**Red-proof method used per fix**, since a green suite proves nothing on its own: fixes 1 and 2 checked by restoring the `origin/main` hook over the fixed one and confirming exactly the 6 new tests fail; fix 3 by neutering `classify()` to `return None`, which turned 11 deny tests red while all 10 allow tests stayed green; fixes 1 and 5 re-proved with `regress_check.py` itself. Fix 5's two red tests run through `cmd_pre`, the caller, not through `plan_archive`, which is the point of the new B2 sub-clause.

**Heredoc FP census** (13 shapes, all classified correctly): allowed a commit-message heredoc, a `gh pr create` body heredoc, sed/jq/sql fixtures, a here-string, `echo "a << b"`, `git log --format`, and a clean 20-line Python heredoc; denied the 300-line payload, the docstring payload, and the regex-escape payload.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/596
- Trigger checkpoint: `docs/2026-08-24 - Brisken Recon Date Guard + Card From Scan/Checkpoint.md`
- Register rows that drove this: `docs/friction-register.md`, 2026-08-24 (or the archive after this checkpoint's split)

---

## How to Continue

The work is shipped; nothing is half-done. Pick up at Next Steps 2 or 3, or wait for the heredoc gate to misfire and calibrate from the real case. To use the new bite check on any fix:

```
uv run tools/regress_check.py --test "{test cmd}" --file {real source} \
    --replace "{the wired call}" --with "{disabled}"
```

---

## Strategic Feedback

### What Worked Well This Session

- Reproducing each defect before fixing it. The 200-char truncation was a hypothesis from reading the code; hashing the four real command strings and watching them collapse to one fingerprint turned it into a fact, and it set the test fixture's 223-char prefix.
- Red-proofing every fix by regressing the real source rather than trusting a green suite, including the two fixes that predate the tool built for exactly that.
- Building problem 4 as a tool. It was used twice within the same session on problems 1 and 5, which is the fastest a new primitive has paid for itself.

### Suggestions

- Add the `MSYS_NO_PATHCONV` advisory. `git show origin/main:path` mangling to `origin\main;path` is deterministic on this Windows setup, pattern-matchable in one regex, and already covered by a memory that did not fire. That is the exact profile of a cheap `cd-guard`-shaped hook, and it is the fourth item this round whose memory-layer fix failed by recall.

### System Health

- The three problems in this batch that recurred (heredoc EOF, test-does-not-bite, and the memory-recall miss above) all had a prior `fix=documented` row. Documented fixes in this repo have a poor survival rate across sessions; when a friction row is written with `fix=documented`, it is worth asking in the same breath what the structural version would cost, because the second occurrence usually arrives within days.
- Autonomy: 0 human interventions. Fully autonomous session; the two user messages were a delegation and a question, not corrections.

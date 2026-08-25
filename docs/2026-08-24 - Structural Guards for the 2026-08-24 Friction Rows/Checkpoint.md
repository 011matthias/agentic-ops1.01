# Checkpoint: Structural Guards for the 2026-08-24 Friction Rows

**Date:** 2026-08-24
**Status:** Shipped (PR #606 merged on green CI); gates inert in the primary clone until it pulls

---

## Summary

Four friction rows logged 2026-08-24, three of them regressions of fixes recorded as `documented`. Each got a Layer-1 gate that fires at decision time instead: a destructive-git guard, a whole-file-shrink guard, and a deploy/consumer coupling. Two existing gates were tightened rather than rebuilt.

---

## What Was Done This Session

### New gates (3)

1. **`git-restore-gate.py`** (PreToolUse Bash|PowerShell). Asks on `checkout -- <path>`, separator-less pathspec checkouts, `restore`, `reset --hard`, forced `clean`, and force switch/checkout **when the targeted paths are dirty**, listing the files at risk plus the archive-first remedy. Clean targets pass silently; unreadable state asks rather than assuming safety. A branch name containing a slash is separated from a pathspec by existence on disk.
2. **`write-shrink-gate.py`** (PreToolUse Write). Asks when a Write materially shrinks an existing file (>=120 lines removed, or >=40 lines and >=30% of the file), listing the headings/defs that survive nowhere in the new content. Exempts `.scratch/`, lockfiles, `node_modules/`, and unreadable/binary targets.
3. **`deploy-consumer-gate.py`** (PostToolUse all-tools + Stop). A deploy opens a marker; a Stop whose text claims verification while the marker is open is blocked once. App deploys (fly/railway/wrangler) close only on a browser drive; server-rendered deploys (vercel) close on the no-slash URL fetch `rule_behaviors` already mandates. A `curl`/WebFetch against an open app-deploy marker re-states the gap instead of closing it.

### Gates tightened (2)

4. **`heredoc-size-gate.py`**: a `>`/`>>` redirect to a `.py` target now marks Python context. Measured gap, not assumed: `cat > f.py <<'EOF'` reached ALLOW under both the `PY*`-tag and interpreter signals, and that is the spelling that wrote the collapsed `(?<!\)` form to disk.
5. **`stop-b1-gate.py` + `input-classifier.py`**: the gate held on both August blocks, so detection was never the gap. Both the block reason and the pre-generation primer now carry the recovery shape: do the read-only half first, then put the remainder as a decision with a recommendation via `AskUserQuestion`.

### Ledger

6. Five register rows flipped to Resolved in the shipping PR (header convention), plus a new row for the 504-line loop-brief deletion, which had been self-flagged at checkpoint but never logged.

---

## Key Decisions Made

### Split the deploy classes instead of gating every deploy
- **Choice:** fly/railway/wrangler require a browser drive; vercel closes on a URL fetch.
- **Rationale:** platform deploys are the repo's most frequent ship and are server-rendered, where the fetch genuinely sees the markup. A gate that fired on every platform deploy would be approved reflexively within a week and would then protect nothing.

### Did not build a nested-f-string heredoc rule
- **Choice:** probed the reported failure before writing a rule for it; `f'{d['k']}'` executes fine on this Python (3.12+).
- **Rationale:** the register row described it as a real failure, but a rule built on an unreproduced mechanism is a false-positive generator. Closed the gap I could measure instead.

### Ask, never deny, on all three new gates
- **Choice:** `permissionDecision: "ask"`, mirroring git-stash-gate and instantly-invasive-gate.
- **Rationale:** every intercepted action is legitimate in some context. The prompt turns an accident into a decision without removing the capability.

### Worked from a fresh worktree off origin/main
- **Choice:** `agentic-ops1-guards`, not the primary clone.
- **Rationale:** the primary clone is 185 commits behind, dirty with ledger files, and shared with two live sessions. Working-tree-derived results there under-report, and concurrent commits collide.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/git-restore-gate.py` | Created | Destructive-git guard on dirty paths |
| `.claude/hooks/write-shrink-gate.py` | Created | Whole-file-shrink guard with anchor listing |
| `.claude/hooks/deploy-consumer-gate.py` | Created | Deploy/consumer coupling, PostToolUse + Stop |
| `.claude/hooks/heredoc-size-gate.py` | Edited | `.py` redirect target marks Python context |
| `.claude/hooks/stop-b1-gate.py` | Edited | Block reason names the split-and-recommend recovery |
| `.claude/hooks/input-classifier.py` | Edited | B1 primer carries the same recovery shape |
| `tools/wire-hooks.py` | Edited | Registered 3 hooks (21 -> 24), one across two events |
| `tools/tests/test_git_restore_gate.py` | Created | 36 tests |
| `tools/tests/test_write_shrink_gate.py` | Created | 20 tests |
| `tools/tests/test_deploy_consumer_gate.py` | Created | 25 tests |
| `tools/tests/test_heredoc_size_gate.py` | Edited | 3 tests for the redirect-context gap |
| `.claude/rules/rule_behaviors.md` | Edited | Consumer-drive sub-clause, whole-file-write floor, B1 recovery |
| `.claude/rules/rule_branch_isolation_and_shared_ledger.md` | Edited | New §4 + §4 enforcement entry |
| `docs/friction-register.md` | Edited | 5 rows flipped, 1 row added |

---

## Current Status

PR #606 merged; `origin/main` carries 24 wired hooks. Verified: `tools/tests` 1127 passed / 1 skipped (81 new), ruff clean over `tools .claude/hooks tools/tests`, `check-index` clean, `wire-hooks --check` 24/24, and each new gate exercised through its exact wired `uv run --directory ...` command form rather than as a bare script.

`platform: no infrastructure.yaml` for this scope; no comms log.

The gates are live only in `agentic-ops1-guards`. The primary clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops1` sits ~190 commits behind on `client/brisken/deckgen-native` with dirty ledger files and two live sibling sessions, so nothing there is guarded yet.

---

## Next Steps

1. Land or park the two sibling sessions' work in the primary clone, then pull `main` there. That is what makes the three gates live for everyday work; until then they only protect worktrees cut from `origin/main`.
2. Watch the first week of `write-shrink-gate` fires. It sits on every Write, so if it prompts on routine rewrites the thresholds (120 / 40+30%) need raising before the prompt becomes reflex-approved.
3. Consider a Layer-1 guard for the MSYS path-mangling class. `reference_repo_tooling_gotchas` names `MSYS_NO_PATHCONV=1` explicitly, was loaded at session start, and still failed twice today in this session plus once in a parallel one.

---

## Context for Next Session

### Files to Read First
- `.claude/hooks/git-restore-gate.py` (docstring carries the full decision matrix)
- `.claude/hooks/deploy-consumer-gate.py` (the two-deploy-class rationale)
- `tools/tests/test_*_gate.py` for the three new suites; negative cases are the contract

### Open Questions
- Are the `write-shrink-gate` thresholds right? Chosen from two data points (598 and 504 lines removed), so they are calibrated against incidents rather than against normal traffic.
- Should the MSYS class get a hook, or is it too spelling-diverse to pattern-match cleanly?

### Working Notes

**The heredoc row was already dead when this session read it.** Register row 271 (system) built `heredoc-size-gate.py` the same day; the brisken row 274 that reported "twice more" ran in a session that predated the wiring. Checking whether the fix already existed came before rebuilding it.

**A false-verification near-miss.** The first probe of the heredoc gate ran the hook via `sys.executable` with an MSYS-style `/c/Users/...` script path. Python could not open it, stdout was empty, and the parser read empty stdout as ALLOW. All four cases including a 120-line payload reported ALLOW, which reads exactly like a broken gate. Re-running against the module directly with a `C:/`-style path showed the gate was correct all along. The lesson that generalizes: a probe whose failure mode is silence will report the shape of a real finding.

**Two gate bugs the negative tests caught, not the positive ones.** `git clean -fd` prompted on a tracked modification (the porcelain test seam returned before the untracked-only filter), and `git checkout -b sys/new-guards` was classified as a pathspec restore because the branch name contains a slash. Both were false positives that would have taught the gate to be ignored. The disambiguation that fixed the second is existence-on-disk, because this repo's branch names routinely contain slashes.

**The `git checkout --` class had three occurrences today, not one.** A parallel session hit it twice more (the RED-proof harness restoring between regression cases) and fixed its two proof scripts to snapshot in memory. That fix is script-local; this gate covers all three shapes. Complementary, not duplicated.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/606
- Register rows: `docs/friction-register.md`, the 2026-08-23/24 block

---

## How to Continue

Cut a worktree from `origin/main` and the gates wire themselves at session start (`wire-hooks --ensure`, 24/24). To work on the gates, edit the hook plus its suite together; `tools/tests/test_hooks_registry.py` fails if a hook exists on disk without being registered in both `CANONICAL_HOOKS` and `EXPECTED_HOOK_SCRIPTS`.

---

## Strategic Feedback

### What Worked Well This Session
- Probing the reported failure mechanisms before writing rules for them. Two of the four items changed shape on contact: the heredoc gate already existed, and the nested-f-string failure does not reproduce. Building from the register text alone would have produced one redundant hook and one false-positive generator.
- Writing negative cases as the contract. Every real bug in this session's code was caught by a test asserting silence, not by a test asserting a fire.

### Suggestions
- The register's "flip the row in the same PR that ships the fix" convention works, but nothing detects a row whose fix shipped and was never flipped. `anneal-metrics.py` already parses the register and could flag rows whose description names a hook that now exists.

### System Health
- Three of four rows this session were regressions of `documented` fixes, and the register shows the same pattern across the 2026-08-22/24 block. The signal is that `documented` is not a fix type for a recurring mechanical failure; it is a note. When a row's fix column reads `documented` and the row is a regression, the next occurrence should skip straight to Layer 1.
- Autonomy: 1 human intervention (the session's report was written too dense and had to be restated in plain language).

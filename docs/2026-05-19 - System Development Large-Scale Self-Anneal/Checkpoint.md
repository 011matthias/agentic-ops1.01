# Checkpoint: System Development Large-Scale Self-Anneal

**Date:** 2026-05-19
**Status:** F1 complete + shipped (PR #29 merged). F2 / F3 / bootstrap deferred.

---

## Summary
User reported rising friction + output-quality degradation; root cause found: the **entire `.claude/hooks` enforcement layer was silently dead on this machine since 2026-05-18 15:41** (device-sync stripped machine-specific hook wiring from tracked `settings.json`; this device's gitignored `settings.local.json` never carried a hooks block). Restored all 9 hooks device-proof and rewrote `stop-b1-gate.py` from an unconditional per-turn block into a precise transcript-reading deferral classifier.

---

## What Was Done This Session

### Diagnosis (data-backed)
1. Read friction register (75 entries), 5 days of session logs, all 11 memory files, 9 hook scripts, 95KB hook-log.
2. Initial hypothesis "stop-b1-gate too blunt" → **self-corrected** (Layer-2): that was reading 12 days of *historical* hook-log without checking *current* wiring. Checked `settings.json` + `settings.local.json` + git history → found the real cause.
3. Verified chain: `974c6bb` committed hook wiring to tracked `settings.json` with machine-specific absolute paths (`C:/Users/neuma/Downloads/...`, bare `python`); `20eb235` "Sync ... before switching devices" stripped it (49 deletions); working copy ran until settings.json overwrite at 15:41:22 (last hook fire 15:40:46 — exact correlation); `settings.local.json` here had only a permissions block.

### Fix (F1)
1. Re-wired all 9 hooks into gitignored `settings.local.json` with portable `uv run python .claude/hooks/X.py` relative paths (cwd = project root). Permissions block (40 entries) preserved.
2. Rewrote `stop-b1-gate.py`: unconditional `decision:block` on every stop (279/12d, 100% false-positive) → reads transcript, extracts last assistant message, blocks only on real deferral/closing-offer/ask-permission phrasing; `strip_code()` neutralizes backticked examples; fail-open on any error; decisions logged `BLOCK matched=... | ALLOW:clean | ALLOW:no-transcript` for ongoing FP measurement.
3. Verified by behavior: classifier matrix 6/6, full 9-hook smoke 10/10, `py_compile` clean, PostToolUse:Bash hooks confirmed live-firing in-session.
4. Shipped: branch `system/restore-enforcement-hooks` → PR #29 → squash-merged to main, branch deleted.
5. Friction register: appended root-cause entry (resolves 2026-05-08 #65/#68 stop-b1 TBDs + recurring 73/74).

---

## Key Decisions Made

### Restore into gitignored settings.local.json, not tracked settings.json
- **Choice:** Machine-specific hook wiring lives in `settings.local.json` (gitignored) with portable relative `uv run python` paths.
- **Rationale:** The root cause was tracked machine-specific paths not surviving a device switch. `settings.local.json` is the correct home for machine-local config; relative paths + `uv run python` make it portable and solve the `python`-not-on-PATH issue. User chose this over tracked-shared.

### stop-b1-gate: classifier, not unconditional, fail-open
- **Choice:** Block only on detected deferral phrasing; any parse error → allow the stop.
- **Rationale:** A missed deferral is far cheaper than taxing every clean turn (the 279/12d tax was the felt friction). Fail-open preserves the "broken hook never blocks" contract.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/stop-b1-gate.py` | Modified (tracked, PR #29) | Unconditional block → transcript deferral classifier |
| `docs/friction-register.md` | Modified (tracked, PR #29) | Root-cause entry; resolves #65/#68/73/74 |
| `.claude/settings.local.json` | Modified (gitignored, machine-local) | 9-hook wiring, portable paths; permissions preserved |

---

## Current Status
Enforcement layer is **live and verified** on this machine: all 9 hooks wired, PostToolUse:Bash + Stop confirmed firing in-session. `stop-b1-gate` is now precise (caught a real soft closing-offer this session correctly, plus one known false-positive on meta-text — see Open Questions). PR #29 merged to main.

---

## Next Steps
1. **F2 — `gate-skip-detector` precision.** Three confirmed false-positives this session: (a) `pre-publish` fired despite `py_compile`+behavioral validation (regex doesn't recognize `py_compile`/hook-tests as a validation step); (b) `pre-publish` on `git push` appearing as a literal string in a test payload; (c) the documented iteration-3x misfire on repeated read-only data-prep. Also fold in the stop-b1 meta-text FP (below). Low blast radius, mechanical.
2. **Bootstrap — tracked `tools/wire-hooks.py`.** Idempotently writes the 9-hook block into `settings.local.json`. Closes the cross-device recurrence fully (other devices/the other dev still have no wiring). Pair with F2 — both cheap.
3. **F3 — structural pre-client-message data-verification gate.** The verification-theater regression that failed memory-only twice (register #7, 2026-03-23). Client-facing, higher blast radius — own session, with care.

---

## Context for Next Session

### Files to Read First
- `docs/friction-register.md` — last entry (2026-05-19 system) has the full root-cause + fix
- `.claude/hooks/stop-b1-gate.py` — the new classifier (patterns, fail-open contract, meta-text blind spot)
- `.claude/settings.local.json` — current 9-hook wiring (verify it's still present at session start)
- `.claude/hooks/gate-skip-detector.py` — F2 target

### Open Questions
- **stop-b1 meta-text false-positive:** the classifier matches its own trigger phrases when quoted in prose (not backticks) — e.g. a report saying `"Want me to" / "Should I deploy"` as examples. `strip_code()` only neutralizes backticked/fenced code. Fix options for F2: also strip double-quoted short spans, or exclude messages whose match is inside a quoted example, or accept it (fail-safe, narrow). Decide in F2.
- Cross-device: settings.local.json is gitignored — until `tools/wire-hooks.py` exists, any other machine still runs with zero enforcement. Recurrence reduced, not eliminated.

### Working Notes
- Hook wiring map (authoritative, from each script's docstring): UserPromptSubmit→input-classifier; PreToolUse Write|Edit→auto-approve-protected, reference-anchor-gate; PreToolUse Bash→instantly-invasive-gate; PostToolUse Write|Edit→em-dash-strip-gate (first), post-write-gate; PostToolUse Bash→post-action-gate, gate-skip-detector; Stop→stop-b1-gate. PreCompact+SessionStart stay in tracked settings.json (machine-agnostic).
- Verification facts: last historical hook fire 2026-05-18T15:40:46; settings.json mtime 15:41:22 — exact correlation proving the kill moment.
- Test transcripts must use **native Windows paths** — Windows Python can't resolve Git-Bash `/tmp/...` mounts (cost one failed test round; methodology fixed, not the code).

### Reference Materials
- PR #29: https://github.com/011matthias/agentic-ops1.01/pull/29 (MERGED)
- Friction register entry 2026-05-19 (system, infrastructure-deferred, Resolved Yes)

---

## How to Continue
F1 is closed. Next session: `/system-dev` (or directly) → F2 + `tools/wire-hooks.py` together (cheap, mechanical, low blast radius), then F3 in its own session (client-facing). At session start, confirm `.claude/settings.local.json` still has the `hooks` block (a fresh device-sync or settings reset is the known recurrence vector until the bootstrap exists).

---

## Strategic Feedback

### What Worked Well This Session
- The AskUserQuestion scope fork ("F1 only, verify, then continue") kept a tempting 5-fix sweep from sprawling at high context. Tight scoping under pressure paid off — F1 shipped clean instead of 3 fixes half-done.
- "Verify, then continue" framing forced behavioral proof (smoke 10/10, live-fire) instead of config-write-and-declare — which is exactly what would have produced another verification-theater entry.

### Suggestions
- Add a session-start assertion (rule or SessionStart hook) that checks `.claude/settings.local.json` contains a `hooks` block and warns loudly if absent. This is the single highest-leverage guard against silent enforcement death recurring — cheaper than the full `wire-hooks.py` bootstrap and catches the exact failure that ran undetected for ~1 day.

### System Health
- The enforcement layer had **zero liveness signal**. Hooks failing silent + rules confidently citing them as backstops = the worst combination: false confidence with no enforcement. Hooks should self-report (a daily/weekly "hooks fired N times" line, or a session-start liveness ping) so "the gates are off" is impossible to miss for a day. Autonomy score: 0 corrective human interventions — fully autonomous diagnosis + fix (2 legitimate scoping forks via AskUserQuestion, not corrections).

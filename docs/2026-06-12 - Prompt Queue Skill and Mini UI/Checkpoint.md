# Checkpoint: Prompt Queue Skill and Mini UI

**Date:** 2026-06-12
**Status:** Complete — both PRs merged to main (CI green)

---

## Summary

Built `skil_prompt-queue`, a FIFO drain skill for queuing prompts to a plain-text file while a chat is busy, then draining them in order after the current task finishes. Added a companion mini web UI (`tools/prompt-queue-ui.py`) that serves the queue as an interactive page at `http://127.0.0.1:7077`, embeddable in VS Code via Simple Browser.

---

## What Was Done This Session

### Phase 1 — Skill (PR #155)
1. Created `.claude/skills/skil_prompt-queue/SKILL.md` with YAML frontmatter, drain procedure, format spec (HTML-comment header stripped before `---` splits), and guardrails (hard gates still fire per queued item; no blanket authorization).
2. Added `.claude/queue/` to `.gitignore` — per-machine runtime state, never shared.
3. Fixed parse bug: header comment was glued to first prompt (no `---` between them); fix was to strip HTML comments BEFORE splitting on `---`.

### Phase 2 — Mini UI (PR #157, 654-line stdlib-only Python)
1. Built `tools/prompt-queue-ui.py` — single HTTP server with GET `/` (page), GET `/api/state` (poll), POST `/api/add`, `/api/update`, `/api/delete`, `/api/reorder`, `/api/clear`, GET `/api/done`.
2. Added row to `tools/INDEX.md` (required for check-index.py CI gate).
3. Added `.claude/queue/` to `SKIP_PREFIXES` in `tools/check-skill-map.py` (gitignored runtime paths must not fail fresh-clone validation).
4. Removed `.claude/queue/done.md` and `pending.md` from git tracking (design changed to gitignored).
5. Added local `.vscode/tasks.json` ("Prompt Queue UI" background task) — machine-local, gitignored.

### Adversarial Review (4-lens workflow, 19 agents)
13 real defects caught and fixed:

- **HIGH (data-loss):** Edit-save writes to wrong slot after list shift. Fix: content addressing — every mutation sends `original` prompt text; server raises 409 if slot holds different content. Client re-anchors `editOriginal` by `indexOf` on state change.
- **MEDIUM:** `done.md` mis-segmentation when prompts contain `## ` lines. Fix: stamp-anchored `DONE_ENTRY` regex.
- `append_done()` called before `atomic_write` (phantom archive on write failure). Fix: collect `done_entries` list, write pending first, then append.
- Windows SO_REUSEADDR double-bind (two instances could share port silently). Fix: `ExclusiveServer(allow_reuse_address=False)` with bind-in-retry-loop.
- `parse→serialize` not idempotent on indented `---` lines. Fix: `guard_separator_lines()` re-indents block-edge separators.
- Poll race rolls back UI while mutation in flight. Fix: `inFlight` counter suppresses poll application.
- Post-drain click lands on wrong row after re-render. Fix: 350ms `.settle` pointer-events:none.
- CSRF/DNS-rebinding: added `X-PQ` custom header + loopback Host check on all API calls.
- XSS: `esc()` escapes `&`, `<`, `>`, `"` before all innerHTML assignments.
- done.md tag drift (`cleared` vs `[cleared]`): unified to bare form across SKILL.md, confirm dialog, and server.
- Missing INDEX.md row: added before ship.
- Skill-map dead pointers on fresh clone: SKIP_PREFIXES fix.
- `.vscode/tasks.json` SKILL.md reference to a gitignored file: softened to prose description.

---

## Key Decisions Made

### Queue files are gitignored (not tracked)
- **Choice:** `.claude/queue/` is in `.gitignore`, not committed.
- **Rationale:** Queue contents are per-machine runtime state; committing them would churn between two developers on every queued prompt and is a privacy concern (queued prompts = in-progress work).

### Content addressing over hash-only optimistic concurrency
- **Choice:** Every mutation includes the `original` prompt text, not just the file hash.
- **Rationale:** Hash guards against concurrent file writes, but the list can shift (drain removes row N, editing row N+1 becomes row N). Without content addressing, save-after-shift silently overwrites the wrong prompt.

### `ExclusiveServer` with bind-in-retry-loop
- **Choice:** `allow_reuse_address = False`, bind loop over port+0..+9.
- **Rationale:** Windows SO_REUSEADDR lets a second instance silently bind the same port. Probe-then-bind (TOCTOU) has a race window. Retry-on-OSError is atomic.

### stdlib-only (no dependencies)
- **Choice:** Pure Python stdlib, no `pip install` required.
- **Rationale:** Zero friction to run; `uv run tools/prompt-queue-ui.py` works on any machine with uv without a prior `uv pip install` step.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/skil_prompt-queue/SKILL.md` | Created + updated | Skill definition: drain procedure, format spec, modes, guardrails, mini UI docs |
| `tools/prompt-queue-ui.py` | Created | 654-line stdlib HTTP server; the mini UI deliverable |
| `tools/INDEX.md` | Modified | Added prompt-queue-ui.py row (required for check-index.py gate) |
| `tools/check-skill-map.py` | Modified | Added `.claude/queue/` to SKIP_PREFIXES (gitignored runtime path) |
| `.gitignore` | Modified | Added `.claude/queue/` section |
| `.claude/queue/done.md` | Removed from tracking | Design change: gitignored runtime state |
| `.claude/queue/pending.md` | Removed from tracking | Same |
| `.vscode/tasks.json` | Created (local, gitignored) | "Prompt Queue UI" VS Code background task |

---

## Current Status

Both PRs merged to main (PR #155 skill, PR #157 UI), all CI checks green. The skill and UI are ready to use:

- **Drain:** invoke `skil_prompt-queue` (or "drain the queue")
- **Add from editor:** append to `.claude/queue/pending.md`, blocks separated by `---`
- **Mini UI:** `uv run tools/prompt-queue-ui.py` (auto-opens browser), or embed via VS Code Simple Browser at `http://127.0.0.1:7077`

Worktree (`agentic-ops1-wt-pq`) and local branch (`sys/prompt-queue-mini-ui`) removed. Brisken `client/brisken/lead-gen-onepilot` branch is unchanged from before this session.

---

## Next Steps

1. (Brisken p2, autonomous) Scrapling/agent-browser pass on J&J/Ford/Toyota auth-walled job bodies to confirm vendor (A2→A1) + capture hiring-manager names; then radar batch 2.
2. (Brisken p2, autonomous) Build Lane 1 AEO substrate (~25-30 problem queries + Q&A page + Store-review plan) + Dirk enabler pack.
3. (Brisken p2, gated on Dirk) Sending identity; live vendor relationships; go-ahead + ~$99/mo Sales Nav seat; demo owner per product.
4. (System, optional) Build the post-merge platform-path hook (structural form of the deploy-gate sub-clause from Session 6).
5. (Trivial) CLAUDE.md still says "Rules (12)"; sync to 15.

---

## Context for Next Session

### Files to Read First
- `.claude/skills/skil_prompt-queue/SKILL.md` — the skill spec
- `tools/prompt-queue-ui.py` — the UI implementation
- `workspace/clients/brisken/specs/2-build/p2-lead-gen-orchestration.md` — lead-gen build spec
- `workspace/clients/brisken/context/lead-generation/targeting-radar.md` — ICP radar

### Open Questions
- (Brisken p2) Does the owner apply the red-team fixes to the deck/specs, or keep the red-team as strategic input only?
- (Brisken p2) OnePilot list ACV — the single missing number the commission case multiplies by.
- (System) Promote the deploy-gate sub-clause to an actual hook, or is the rule clause sufficient?

### Working Notes
The HIGH data-loss bug fix (content addressing) was proven with a Playwright deterministic repro: edit C in [A,B,C,D], delete A mid-edit, save — C is found by content, D survives. The worktree pattern was used to isolate all infra changes from the in-flight Brisken branch; no cross-contamination occurred.

### Reference Materials
- PR #155 (skill): `gh pr view 155`
- PR #157 (UI): `gh pr view 157`

---

## How to Continue

Brisken: `/resume brisken` on the `client/brisken/lead-gen-onepilot` branch. Prompt queue is fully shipped; resume lead-gen from the radar batch-2 and AEO substrate tasks.

---

## Strategic Feedback

### What Worked Well This Session
- The 4-lens adversarial Workflow review (19 agents) caught 13 real defects including one HIGH data-loss bug before any user-visible behavior was affected. Running adversarial review before declaring done is the right pattern for anything with concurrent-mutation semantics.
- Git worktrees kept the Brisken in-flight branch completely isolated throughout — zero cross-contamination over ~4 hours of builds.

### Suggestions
- The stop-hook correctly caught one agent-deferred this session (offered to ship when it should have shipped). The generation reflex toward menus persists despite the hook holding. Consider a session-start self-reminder: "If it's in Band 1-2, ship; don't offer."

### System Health
- **Autonomy score:** 1 human intervention this session (stop-hook agent-deferred catch — structural fix held, count = 1 because the hook interrupted the turn rather than catching a user correction).
- `CLAUDE.md` still says "Rules (12)" but there are 15 rules; trivial drift.
- The validate-output.py symmetry-collapse / prose-volume detector (named in rule_anti_slop enforcement section) remains unbuilt after 3+ slop incidents. Run `/system-dev` to close this gap.

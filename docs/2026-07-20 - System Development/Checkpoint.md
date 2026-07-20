# Checkpoint: System Development

**Date:** 2026-07-20
**Status:** Cycle complete — PRs #272 (sys) + #273 (docs) merged, CI 5/5 green on both

---

## Summary

Full /comd_system-dev cycle: 6 approved friction-register fixes shipped in PR #272, a register-hygiene sweep (18 stale-row flips + 19 gate-held normalizations) in PR #273, and, mid-cycle, the discovery and repair of a double defect in the convergence instrument itself: the friction-watch parser mis-read the 305 register rows that carry a 7th note cell (true unresolved was 211, not the ledger's 90), and gate-held rows could never leave the Unres count.

---

## What Was Done This Session

### Structural fixes (PR #272, all evidence-cited)
1. cd-guard Bash arm: trailing boundary now a non-consuming lookahead (PS-arm parity) — kills the `cd X; cmd` and `cd X 2>/dev/null` bypasses (register 07-15/07-16). +4 regression tests.
2. scorer-lock-gate: worktree-aware — targets outside the gate's own repo key on the target's OWN git root (`.git` dir or worktree pointer file), closing the 07-17 tamper-test bypass. +4 tests; the out-of-repo-no-git-root pass stays pinned.
3. `.claude/settings.json`: `PYTHONIOENCODING=utf-8` env (cp1252 charmap crash class).
4. post-action-gate: `[MERGE-NOT-LIVE]` advisory on `gh pr merge` — the minimal build of the thrice-deferred platform-merge-is-not-live watcher.
5. anneal-metrics: Unres split into `actionable (+held)`; gate-held rows excluded from the convergence signal.
6. NEW `tools/brisken-outreach-truth.py` (+INDEX row): read-only both-mailbox ALL-FOLDERS Graph outreach-truth scan per feedback_brisken_outreach_truth_is_mailbox — replaces 4 sessions of ad-hoc .scratch scripts. Live-smoked (Zoho-dropbox positive control CONTACTED with custom-folder hit, drafts separated, OOO strip, charmap-safe).
7. demo-banned-terms.json: shared em-dash pattern (07-16 checkpoint over-claim).
8. friction-watch: parse_register rewritten with shape-anchored Resolved detection (the 7-cell fix). +5 tests.
9. CLAUDE.md counts 36 skills / 18 rules (drift 2→0).

### Register hygiene (PR #273)
1. 18 row flips where the fix had already shipped (7x sibling detector, 2x demo-validator wiring, 1x sessions-frontmatter, 6x fixed by #272, 1x deploy-watcher row closed by the advisory).
2. 19 stop-b1 rows normalized to the parser-recognized `No (caught by hook — held by stop-b1 gate)` form.
3. Register header conventions note + anneal-ledger Unres basis-change note + the 2026-07-20 cycle row.

---

## Key Decisions Made

### Unres becomes actionable-only
- **Choice:** Gate-held rows (hook catches every occurrence, reflex persists) are reported as `(+H held)` and excluded from the convergence signal.
- **Rationale:** They can never flip to Yes; counting them made Unres monotonically rising bookkeeping, not a signal.

### Closing-offer reflex left untouched (again)
- **Choice:** No new primitive for the most-logged friction class; only its register accounting changed.
- **Rationale:** 07-12 cycle verdict stands — the stop-b1 gate holds every time; tinkering is accretion.

### md-to-pdf Chrome fallback deferred
- **Choice:** User deselected it at the Phase-4 approval gate.
- **Rationale:** Lower frequency (2 occurrences in 5 weeks); workaround documented in reference_html_deck_pdf_chrome_when_edge_open.

### Oversized rules held
- **Choice:** 3 rule files at 267–273 lines vs the ~250 advisory ceiling stay unsplit.
- **Rationale:** ≤9% over, no cited defect; splitting is churn (Goodhart guard).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| .claude/hooks/cd-guard.py | Modified | Bash-arm trailing-boundary lookahead |
| .claude/hooks/scorer-lock-gate.py | Modified | Worktree-aware lock (target's own git root) |
| .claude/hooks/post-action-gate.py | Modified | MERGE-NOT-LIVE advisory |
| .claude/settings.json | Modified | PYTHONIOENCODING=utf-8 |
| tools/friction-watch.py | Modified | Shape-anchored Resolved parsing (7-cell fix) |
| tools/anneal-metrics.py | Modified | actionable (+held) Unres split |
| tools/brisken-outreach-truth.py | Created | Both-mailbox ALL-FOLDERS outreach truth |
| tools/fixtures/demo-banned-terms.json | Modified | Shared em-dash pattern |
| tools/tests/test_cd_guard.py, test_scorer_lock_gate.py, test_friction_watch.py | Modified | +13 regression tests |
| tools/INDEX.md, CLAUDE.md | Modified | New tool row; counts 36/18 |
| docs/friction-register.md | Modified (#273) | 18 flips + 19 normalizations + header note |
| docs/anneal-ledger.md | Modified (#273) | Basis note + 2026-07-20 row |

---

## Current Status

Both PRs merged to main (#272 `18a26759`, #273 `11710bf`). Preflight --full green twice (523→528 tests). Register on the fixed parser: 531 rows, 194 unresolved = 136 actionable + 58 gate-held. Worktrees removed, branches deleted.

---

## Next Steps

1. Next /comd_system-dev cycle gets the first honest Unres read — trend from `136 (+58)` on the NEW basis only.
2. Actionable backlog (136) still carries a long tail of documented one-offs; a triage pass classifying stale-documented rows for flip-or-confirm would shrink it further (same method as this cycle's sweep script).
3. Candidates deliberately not built this cycle: md-to-pdf Chrome fallback (user-deferred), Rome recipient-CSV linter (sends done), docx-skill wrapper (1 occurrence), gate-skip pre-publish buffer widening (see friction F3).
4. First real use of `brisken-outreach-truth.py` in a Brisken session replaces the next ad-hoc scan; if a flag is missing, extend the tool, don't fork a scratch script.

---

## Context for Next Session

### Files to Read First
- docs/anneal-ledger.md (the 2026-07-20 row's Top Finding — the instrument-repair story)
- docs/friction-register.md header (new resolution conventions)
- tools/INDEX.md (brisken-outreach-truth row)

### Open Questions
- Should the ~136 actionable backlog get a dedicated triage session (many are old documented one-offs that may warrant flip-or-confirm)?

### Working Notes
- friction-watch's parser now shape-anchors the Resolved cell (first verdict-shaped cell at index ≥4 leaving a Fix cell after it). 305/531 rows have 7 cells; 1 row each has 4/8/10 cells.
- Register edits MUST be verified by re-parsing with friction-watch's own parser — that check caught two wrong-cell edit attempts this session before they shipped.
- brisken-outreach-truth.py needs the primary clone (gitignored context/.env) or `BRISKEN_ENV_FILE`; worktrees don't carry the env.
- anneal-metrics `_lead_int` reads the leading int of the new `A (+H held)` Unres cells, so old ledger rows still parse.

### Reference Materials
- PR #272: https://github.com/011matthias/agentic-ops1.01/pull/272
- PR #273: https://github.com/011matthias/agentic-ops1.01/pull/273

---

## How to Continue

Run `/comd_system-dev` next cycle as usual; Phase 0 will read the swept register (136 actionable on the fixed parser). Nothing in-flight.

---

## Strategic Feedback

### What Worked Well This Session
- The Phase-4 approval gate via a single consolidated question (3 decisions in one prompt) kept the cycle autonomous end-to-end with exactly one human touchpoint.
- Verify-with-the-consuming-parser after every register edit caught two silent wrong-cell edits AND surfaced the real parser bug — the cycle's top finding came out of its own verification discipline.

### Suggestions
- The 03:30 RepoSweep task and the weekly synthesis both read the register; after the basis change their numbers will jump. If a weekly email shows Unres tripling, that is the parser fix, not a regression.

### System Health
- The convergence loop's instruments were measuring their own bookkeeping errors for at least 2 cycles (Unres 67/83/90 all on the broken basis). Lesson operationalized: instruments get the same test coverage as gates (5 new parser tests now pin the 7-cell layout).
- Autonomy score: 2 human interventions this session (1 self-detected slow-path, 1 hook-caught cd compound; the Phase-4 approval is by design, not friction).

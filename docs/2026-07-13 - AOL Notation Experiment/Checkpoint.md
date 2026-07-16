# Checkpoint: AOL Notation Experiment

**Date:** 2026-07-13
**Status:** Complete — experiment run, measured, fully rolled back (net-zero)

---

## Summary
Designed, built, measured, and then fully reverted an internal compressed notation ("AOL") for the always-loaded governance layer (13 rules + 76 memory files), on the user's request to create "a language only the agent reads" and hold an English copy beside it. Faithful translation saved far less than the scratch POC promised (~17% rules, ~8% memory ≈ ~1% of the 1M context window), so the user chose a full rollback. Everything is back to English with zero repo footprint.

---

## What Was Done This Session
### Investigation
1. Audited the `Repo/` folder: confirmed only 4 real projects (`agentic-ops1`, `agentic-dev1`, `video-gen`, `openclaw-sandbox`); the other 9 dirs are git worktrees of `agentic-ops1`, not separate repos.
2. Two read-only Explore agents established the machine-safety facts: nothing parses rule PROSE (only `anneal-metrics.py` counts files/lines + the `**Rules** (N)` token); memory bulk-load is real and mandated (~70-85k tok, not the "0.2%" the docs claim); the native memory tool owns memory frontmatter/staleness.

### Build (all later reverted)
3. Wrote the AOL legend `_L.md`, created sister repo `agentic-ops-lang` with the English canonical (13 rules + 76 memory) + manifest.
4. Translated 3 representative rules (anti_slop, behaviors, no_auto_commit) myself; measured ~17%.
5. Translated 75 memory bodies via 6 parallel Sonnet subagents (frontmatter byte-preserved, `<!--aol-->` marker, mtimes restored); measured ~8%. Deterministic fact-diff confirmed no facts lost.

### Rollback (final state)
6. Full rollback: restored 3 rules + 75 memory bodies from the English snapshot, deleted `_L.md`, reverted `CLAUDE.md` + `anneal-metrics.py`, removed the sister repo.
7. Independent re-verification (on user's "make sure") caught that 4 memory files had been over-reverted past concurrent parallel-session updates; reconstructed their current English from the AOL backup so PR #213/#214/#215, Phase 2, and new tool facts survive.

---

## Key Decisions Made
### Memory-first, then reversed on the data
- **Choice:** Translated memory before finishing rules, then abandoned the whole thing.
- **Rationale:** Predicted memory would compress better; measurement proved the opposite (memory 8% < rules 17%) because the corpus is dense facts, not prose. The premise didn't survive contact with data.

### Full rollback rather than keep
- **Choice:** Restore everything to English; keep nothing.
- **Rationale:** ~1% of a 1M window is not the binding constraint (context pressure comes from the work, not the ~30k always-loaded governance), and it would trade a small compliance risk on the exact gate files that make the system work, plus standing sister-repo/sync machinery, for a rounding error.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/rule_anti_slop.md`, `rule_behaviors.md`, `rule_no_auto_commit.md` | Translated then reverted | Now byte-identical to HEAD English |
| `.claude/rules/_L.md` | Created then deleted | AOL legend (gone) |
| `CLAUDE.md`, `tools/anneal-metrics.py` | Edited then reverted | Back to pre-session state |
| `~/.claude/.../memory/*.md` (75) | Translated then restored to English | 71 byte-identical to snapshot; 4 reconstructed to carry concurrent parallel-session facts |
| `Repo/agentic-ops-lang/` | Created then removed | Sister repo (gone) |
| `docs/2026-07-13 - AOL Notation Experiment/Checkpoint.md` | Created | This checkpoint |

Net repo footprint of the experiment: **zero** (nothing committed, nothing left behind except this checkpoint and the plan file).

---

## Current Status
System is fully English and verified: 0 AOL markers across all rules + memory, rules match HEAD, sister repo gone, `Repo/` back to 4 projects + 9 worktrees. The AOL backup of the 76 memory files sits in the session scratchpad (ephemeral) as the rollback safety net.

---

## Next Steps
1. (Optional) Prune the 7 clean lead-gen worktrees: `agent-eval`, `lead-desk`, `leadgen-task-2/3/4/5/7` (`git worktree remove` keeps the branches).
2. (Optional) Fix the factually wrong memory bulk-load cost claim in `comd_resume.md:137` and `rule_session-start.md:11` ("~1,800 tokens / 0.2%" → actually ~70-85k tok / ~7-8%).
3. (Optional, higher value than AOL ever was) Trim the 3 oversized memory files (`project_brisken_onepilot_site_hosting.md` ~33k, `project_meji_warm_rebuild_d1.md` ~17k, `project_brisken_product_decks_restructured.md` ~15k) — they dominate the bulk-load.

---

## Context for Next Session
### Files to Read First
- This checkpoint (the experiment is closed; don't re-run it)
- `~/.claude/plans/snoopy-kindling-heron.md` (the full plan, for reference)

### Open Questions
- None. The "is an internal language worth it" question is answered: no, for this corpus, ~1% saving isn't worth the maintenance + compliance risk.

### Working Notes
- **Compression ceiling measured, not guessed:** faithful AOL saves ~12-26% on rules (behaviors only 12% — nearly all directives), ~3-25% on memory (~8% aggregate; the big operational-log files compress ~3-7%). The scratch POC's 44% was hand-tuned-aggressive and unrepresentative; it over-promised and led to the full build before the real number was known.
- **Concurrency hazard confirmed live:** parallel sessions wrote to the shared memory dir *during* the experiment (lead_desk twice, harness_hardening, dirk_outlook, user_edge_cdp). Any "compress + restore-from-snapshot" scheme silently discards concurrent work — this is why the rollback needed a reconstruction pass.
- **The real token levers** (if ever wanted) are the oversized memory files + the stale bulk-load policy, not notation.

### Reference Materials
- Plan file: `~/.claude/plans/snoopy-kindling-heron.md`
- AOL backup (ephemeral): session scratchpad `aol_backup_memory/`

---

## How to Continue
Nothing to continue — this was a closed, reverted experiment. If the token budget ever becomes the binding constraint, pursue the "Next Steps" levers (oversized memory files, bulk-load policy), not a notation.

---

## Strategic Feedback

### What Worked Well This Session
- The "measure a faithful sample, then decide" pivot: pausing after 3 real rules to show the true 17% (vs the POC's 44%) let the decision be made on data, not optimism.
- The user's "make sure everything is really reverted" prompt was the catch that turned a near-miss (4 files silently over-reverted) into a clean net-zero.

### Suggestions
- When estimating a saving/benefit, build the estimate from a FAITHFUL representative sample, never from a hand-tuned proof-of-concept. The POC's 44% was ~2.5x the real 17% and drove more work than the true ROI warranted.

### System Health
- Rollback safety in a repo with concurrent sessions writing a shared, un-versioned store (the memory dir) is fragile: a snapshot-based restore can be stale for concurrently-modified files. The reconstruction worked, but a durable fix would be to version-control or at least timestamp-diff the memory store before any bulk rewrite.
- Autonomy score: 3 human interventions this session.

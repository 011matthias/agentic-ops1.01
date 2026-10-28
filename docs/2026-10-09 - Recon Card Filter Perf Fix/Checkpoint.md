# Checkpoint: Recon Card Filter Perf Fix

**Date:** 2026-10-09
**Status:** Shipped and verified live

---

## Summary
The months page's card filter in Brisken's expense-recon tool was slow because `GET /api/cards/status` rebuilt every month's full Expenses-page view on every call; a per-run cache now keeps each month's counts until that month's own data changes. Live since 2026-10-07 15:28 UTC (commit `2636b226`), verified by a differential timing probe and a cold Playwright drive against the production SPA.

---

## What Was Done This Session

### Diagnosis
1. Traced "card filter tab taking way too long to load" to `GET /api/cards/status`, which backs both `/cards` and the months-page filter.
2. Found the backlog had already diagnosed the cost (item 190: ~0.07 s → ~2.2 s, seven months' Expenses views rebuilt per call) and the folder-level memo in front of it invalidates on any write anywhere in the data folder.

### Fix
3. Added `app.state.receipt_card_counts_cache` in `app.py`: each run's `receipt_card_counts` kept under a version of that run's own inputs (snapshot, decisions, category overrides, field overrides, edits, duplicate resolutions), plus the registry settings and the card-memory file's own SQLite write counter (shared once per build, not read per run).
4. First attempt keyed the cache on the month's `updated_at` timestamp (the backlog's own sketch). Rejected — see What Did NOT Work.
5. Added `tests/test_card_status_per_run_cache.py`: an unrelated write (new month) doesn't recount existing months; an edit to one month recounts only that month. Regress-checked (cache hit disabled → both new tests red → restored → green).
6. Full module suite: 4189 passed, 2 skipped.

### Ship
7. PR #1595, merged (CI green: Enforcement hook tests, Lead Desk tests, Playwright smoke, secret scan, spell check, type-check/lint/build, match accuracy, test — all pass).
8. Deployed via `deploy.py` from a clean detached worktree at the merge commit, after confirming via live Fly logs that Criss's write activity had gone quiet for 3 minutes (never interrupting her live session).
9. Live verification: differential timing probe (cached route 0.164 s right after a write vs. uncached control route 1.215 s, proving the write really invalidated both), cold Chrome drive of `/months` (card 9693 narrowed to exactly its 7 API-named months, "All" restored 8, 0 writes attempted).
10. PR #1605 (docs only): recorded the live measurements in the two status files.
11. Cleaned up both feature worktrees, branches, and the local copy of client data used for the bench.

### Self-anneal (this checkpoint)
12. Widened `.claude/patterns/warn-pr-checks-poll-without-mergeable.md`'s regex from `gh pr checks` only to `gh (pr checks|run list)`, closing the gap that let a `gh run list --commit` poll wait ~1h on a conflicted PR undetected. Verified: fires on the actual failing command from this session, stays silent on the corrected one, lints clean.

---

## Key Decisions Made

### Cache key: content equality, not a timestamp
- **Choice:** Version each run's cache entry on the actual values of its inputs (snapshot + 5 store reads), not on `month_updated_at`.
- **Rationale:** Every timestamp this store writes is second-precision (`_now_iso`), so a create-then-edit inside one real second is indistinguishable by any clock reading and would serve stale counts forever after. Content equality has no such window. Caught by an existing test, not by foresight.

### Deploy timing: wait for a quiet window, don't deploy on merge alone
- **Choice:** Polled live Fly logs for write activity and deployed only after 3 minutes of quiet, rather than deploying immediately after the green merge.
- **Rationale:** Fly deploys are pre-authorized after a green merge, but Criss was actively saving edits through the afternoon; a mid-session restart is avoidable cost for zero benefit given the fix is not urgent-correctness (it's a speed fix).

### Verification: differential probe + cold drive, not a 200 OK
- **Choice:** Compared the fixed route's timing against an uncached control route right after a real write, and drove the live SPA cold (no session) end to end, rather than trusting a healthy `/healthz` or a single fast response.
- **Rationale:** A single fast response after a cache fix could mean "it's fast" or "it's wrong and fast" (B2 instrument-validity sub-clause) — the control route proves the write actually invalidated the memo, and the drive proves the SPA still renders correct, narrowed data.

---

## What Did NOT Work (and why)
- **Keying the per-run cache on the month's `updated_at` timestamp (the backlog's original sketch):** every timestamp this store writes is truncated to the second, so a create-then-edit inside one second reads identical and serves stale counts. Caught by the existing `test_card_status_memo.py::test_an_edit_inside_a_month_is_read_fresh` going red on the first pass.
- **`gh pr checks --watch` immediately after pushing:** exits 0 with "no checks reported" before GitHub has registered the workflow run — a known trap, not a usable completion signal.
- **Polling `gh run list --commit <sha>` in a background until-loop with no mergeable-state check:** the PR was conflicted with `main` (sibling sessions' status-file edits), so CI never started; ~1h passed before this was noticed. The existing pattern rule for exactly this failure mode only matched `gh pr checks`, not `gh run list`, so it stayed silent.
- **Ending a turn with the merge described as a next step instead of completed:** left a green, mergeable PR unmerged across a turn boundary. Flagged by `warn-stop-merge-left-pending`; corrected the next turn by polling CI to completion in the foreground and merging within that same turn.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/app.py` | Edit | Per-run `receipt_card_counts` cache |
| `workspace/clients/brisken/automations/expense-reconciliation/tests/test_card_status_per_run_cache.py` | Write | Regression tests for the cache (regress-checked) |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | Ship + live-verification entries |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | Item 190 marked shipped+live with measurements |
| `.claude/patterns/warn-pr-checks-poll-without-mergeable.md` | Edit | Widened regex (this checkpoint) |

---

## Current Status
Card filter fix is live and verified (commit `2636b226`, since 2026-10-07 15:28 UTC). Both PRs merged (#1595, #1605). No open work on this piece. Brisken platform status (per `infrastructure.yaml`): unknown plan / ops volume, not assessed — unrelated to this fix, not actioned this session. Project-status sweep flagged five OTHER Brisken workstreams as stale (`p1-recon-loop-prompt.md`, `p2-lead-gen-general.md`, `p2-lovable-rebuild.md`, `p2-outreach-engine.md`, `p2-rome.md`) — none touched this session (different piece of work), left for whoever next picks up p2 lead-gen.

---

## Next Steps
1. None required for the card-filter fix — it is shipped, live, and verified.
2. If the months page is reported slow again: confirm `/healthz`'s `server.commit` is at or after `2636b226` first (B3 — a regression on an older deploy is a different bug than a cache miss), then re-run the differential probe (cached route vs. `/api/expense-batches` control) rather than assuming the fix regressed.
3. Optional, not urgent: `feedback_recon_drive_replay_payloads.md` already flags "a shared drive helper in `tools/`" as worth building — this session hand-rolled another one-off Playwright script. Not yet a 2+-checkpoint recurrence in the register, so not promoted to a friction row, but worth building before a third one-off.
4. Separate from this piece: the five stale p2 workstreams above need a pass when that work is next picked up.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 190, live measurements)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/app.py` (`receipt_card_counts_cache`, `_card_status_body`)

### Open Questions
None open on this piece.

### Working Notes
- Live differential timing (2026-10-07, read-only, right after the login write): cached route 0.164 s, control route 1.215 s, control repeat 0.089 s.
- Local bench (10-07 08:19 backup): cold build 1.85–1.91 s, warm/unrelated-write 0.071–0.072 s, warm/after-a-real-edit 0.131–0.150 s; every warm body byte-identical to a fresh app's cold build.
- Rule-miner digest ran on this session's transcript; found only two real user turns (the task description and "continue") plus one false-positive correction flag on an ambient browser-instruction block — no additional pattern-rule proposals beyond the one already built in this checkpoint.

### Reference Materials
- PR #1595 (fix), PR #1605 (live-verification docs)
- `reference_recon_local_perf_bench.md`, `feedback_recon_drive_replay_payloads.md`, `feedback_fly_deploy_preauthorized.md`

---

## How to Continue
This piece is closed. Pick up from `p1-improvement-backlog.md` item 190 if the card filter's cost is ever revisited (e.g., if `settled_elsewhere` or trip-edit cross-run dependencies ever need folding into the cache key — deliberately left out of scope this round since no existing test exercises them).

---

## Strategic Feedback

### What Worked Well This Session
- Read the backlog's own prior diagnosis (item 190's cost note) before writing any code — it already named the mechanism and the fix direction, so no time was spent re-deriving the root cause.
- Let an existing test (`test_an_edit_inside_a_month_is_read_fresh`) catch the first cache design's correctness bug before it shipped, rather than trusting the design by inspection.
- Verified "fast" with a control route and "correct" with a cold live drive, instead of accepting a fast 200 OK as proof of both.
- Waited for a quiet window in the client's live usage before deploying, confirmed from Fly logs rather than assumed.

### Suggestions
- Pattern rules that match on a specific CLI subcommand (`gh pr checks`) should be revisited whenever the same failure recurs via a different subcommand doing the same thing (`gh run list`) — widen the rule's verb alternation rather than filing a new rule for the same lesson.

### System Health
- **Gates:** B1:0 B2:5 B3:3 skipped:1
- **Autonomy score:** 0 human interventions — fully autonomous session (the only user messages were the task description, "continue", and the checkpoint command itself).

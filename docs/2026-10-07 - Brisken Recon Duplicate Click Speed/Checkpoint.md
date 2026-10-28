# Checkpoint: Brisken Recon Duplicate Click Speed

**Date:** 2026-10-07
**Status:** Backend live (Fly v284, `0541288a`); SPA prompt handed to the owner, not pasted

---

## Summary
"Removing duplicates takes way too long to load" (owner). Both duplicate controls re-match the whole month inside the request; the matcher's vendor work was 7x redundant, so it is now memoized (about 2x faster, output byte-identical), and the replies can carry the month so the SPA stops refetching it twice.

---

## What Was Done This Session

### Diagnosis (local bench, zero prod load)
1. Read `/feedback.jsonl` (115 notes): no operator note mentions the slowness, so the code path was the source.
2. Traced the SPA: "Delete this copy" -> `DELETE /api/runs/{id}/expenses/{doc}`, "Not a copy" -> `POST .../duplicates/resolve`; both call `rematch_after_change` synchronously, then the SPA invalidates `["expense-batch", id]` and `["run", id]`.
3. cProfile of one September delete on the 10-07 08:19 UTC backup: 13.8 s, of which `match_month` x2 = 9.1 s, `vendor_similarity` 7.3 s (26,163 calls, 3,710 distinct pairs), `MerchantRegistry.resolve` 1.7 s (700 calls, 274 distinct per instance).

### PR #1583 (Fly v281): memoize the matcher's vendor work
1. `lru_cache` on `vendor_similarity` (2^15), its word-pair ratio `_token_ratio` (2^16) and `strip_reference_tokens`; per-instance memo on `MerchantRegistry.resolve`; `_distinctive` cached on its token tuple.
2. A/B base (origin/main files in `.scratch/base_src`) vs new, fresh data copy per process: Delete 3.88 -> 1.75 s first click, Not a copy 5.28 -> 2.73 s; reply + both GET payloads byte-identical (1.3 MB) every round; CI's match-accuracy exact-equality gate passed.
3. `tests/test_rematch_vendor_memo.py` (6) through `match_month` / `resolve`; three `regress_check` bites. Suite 4170 passed.

### PR #1590 (Fly v284): `?views=1` on both duplicate replies
1. `_run_page_view` (what `GET /api/runs/{id}` serves) and `_reply_views` helpers; the replies carry `views.batch` / `views.run`, summary read off the same build; no flag, no change.
2. `tests/test_duplicate_click_reply_views.py` (4): each view equals its GET on a collecting and a reconciling month; two `regress_check` bites. Suite 4191 passed. Two merge rounds with sibling PROMPT-STATUS rows (#1587, #1589).
3. SPA prompt `docs/lovable-duplicate-click-reply-views-prompt.md` proven on a scratch clone of SPA `735c7f9`: `tsc` clean, node-server build, local drive sent one `POST ...?views=1` and no month refetch; handed to the owner as a four-backtick fence.

### Records
PR #1585 (backlog row 163), PR #1592 (row 165), PROMPT-STATUS row, status file line; new pattern rule `warn-poll-task-output-file`; perf-bench memory extended.

---

## Key Decisions Made

### Memoize rather than restructure `match_one`
- **Choice:** cache pure functions; leave the gate order in `match_one` alone.
- **Rationale:** scoring the vendor before the date/amount gates is the waste, but moving it touches every branch of the FX ladder; caching is provably output-neutral (byte-identical payloads) and took most of the cost.

### `views` is opt-in (`?views=1`), both payloads
- **Choice:** only the two duplicate calls ask for it; the reply carries the exact GET payloads.
- **Rationale:** `_expense_edit_reply` serves five+ routes; a 1 MB reply on every edit is wrong, and exact GET payloads let the SPA `setQueryData` with no shape drift. An older backend ignores the flag, so SPA and backend ship in either order.

---

## What Did NOT Work (and why)
- **Timing the re-match speed-up live read-only via `duplicates/reapply` `dry_run`:** it never calls `match_month` (`kept_after_rematch` rebuilds views and the duplicate pool only), so no read-only live call exercises the matcher; the click was not timed live.
- **Waiting on a background suite by sleep-polling its `.output` file:** the command was piped through `tail`, the file stays empty until exit, and the loop burned the 600 s tool timeout; `warn-tail-task-output-file` missed it because the path sat in a shell variable.
- **Polling PR #1590's CI without reading `mergeable_state`:** the PR was `dirty` (sibling PROMPT-STATUS row), so no checks would ever start; the pattern warning caught it immediately.
- **Importing the `client` fixture from a sibling test module:** ruff F811 on every test using it; defined the fixture locally.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py` | Edit | lru_cache vendor similarity, word ratio, reference strip |
| `.../src/expense_recon/merchant_registry.py` | Edit | per-instance resolve memo, `_distinctive` cache |
| `.../src/expense_recon/web/app.py` | Edit | `_run_page_view`, `_reply_views`, `?views=1` on delete + resolve |
| `.../tests/test_rematch_vendor_memo.py` | Create | caller-level memo tests |
| `.../tests/test_duplicate_click_reply_views.py` | Create | views == GETs contract |
| `.../docs/lovable-duplicate-click-reply-views-prompt.md` | Create | SPA half |
| `.../docs/PROMPT-STATUS.md` | Edit | Not-applied row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | Shipped rows 163, 165 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | 2026-10-07 status line |
| `.claude/patterns/warn-poll-task-output-file.md` | Create | sleep-poll on a task output file |

---

## Current Status
Live `brisken-expense-recon` on `0541288a` (v284), contains both PRs; live September duplicate layer and both page GETs (Sept + Oct) hash-identical before/after each deploy; September page driven cold, 46 "Not a copy" controls, no fallback text. SPA prompt not pasted. Brisken ops status: no `platform` section in `infrastructure.yaml` (unknown plan); comms-log: none.

---

## Next Steps
1. Owner pastes `docs/lovable-duplicate-click-reply-views-prompt.md` into Lovable and publishes; then audit the bundle for `views=1` and run a replayed drive (never a live click).
2. If clicks are still too slow: the remaining cost is the re-match itself (~1.5-2.7 s locally) and the two view builds in the reply; next lever is moving `_vendor_score` behind `match_one`'s date/amount gates (needs an output-identical A/B across all months).
3. Stale status files flagged by pre: `p1-recon-loop-prompt.md`, `p2-lead-gen-general.md`, `p2-lovable-rebuild.md`, `p2-rome.md` (22-27 d).
4. Compact `MEMORY.md` (21.6 KB, hook target < 17.1 KB, read limit 24.4 KB) in a window with no live sibling session: every line needs trimming, and a whole-index rewrite while siblings append risks dropping their entries. Four longest lines trimmed this session (21,859 -> 21,571 bytes).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (top line)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-duplicate-click-reply-views-prompt.md`

### Open Questions
- Is the owner satisfied with ~2x, or is the re-match itself next (lever above)?

### Working Notes
- Bench scripts in `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-dupspeed/.scratch/`: `ab.py` (base vs new, byte-diff), `flow_bench.py` (write + the refetches the SPA makes), `dupbench.py` (profile), `live_snap.py` / `live_run_hash.py` (read-only live hashes, stable across two reads), `drive_views.py` (local SPA drive), `.scratch/spa` (clone with the prompt applied, API_BASE pointed at :8765, do not push).
- Local timings swing about 1 s with sibling sessions on this box; take min of N, alternate base/new.

### Reference Materials
- PRs #1583, #1585, #1590, #1592; memory `reference_recon_local_perf_bench`.

---

## How to Continue
`/resume brisken`; if the prompt was pasted, verify by bundle strings then a replayed drive; for further speed, start from the cProfile recipe in the perf-bench memory.

---

## Strategic Feedback

### What Worked Well This Session
- Profiling before proposing a cause: the first cProfile named one pure function as half the cost, and counting distinct inputs (3,710 of 26,163) made the fix and its safety argument the same measurement.

### Suggestions
- Turn `ab.py` + `flow_bench.py` into a `tools/recon_write_bench.py` (base tree from `git show`, fresh copy per process, scrub, byte-diff); this is the second recon speed round rebuilding the same harness in `.scratch`.

### System Health
- Pattern rules carried the session: four fired (heredoc-size x2, merge-chained block, pr-checks without mergeable) and each redirected before cost; the one miss (task-output poll via a variable) is now its own rule.
- Autonomy: 0 human interventions (three directive prompts: fix, hand the prompt, checkpoint) — fully autonomous session.

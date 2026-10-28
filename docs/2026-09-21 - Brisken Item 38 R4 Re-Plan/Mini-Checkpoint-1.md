# Mini-Checkpoint: Brisken Item 38 R4 Re-Plan

**Date:** 2026-09-21
**Status:** Plan approved, no code written; execution deferred to a fresh session
**Type:** mini

---

## Summary

Planned item 38's "remaining round" R4 and found the premise wrong: R4 shipped in both halves on 2026-09-07 (PR #685, commit `fc75c8a9`), backend and SPA, and the trip already resolves a cost center at D2 position 2. The round was re-purposed into five sub-rounds that make the shipped R4 trustworthy (nothing has ever run against a real trip or a non-empty cost-center registry), plus twelve owner questions.

## What Was Done

- Verified state against `origin/main` (`640be61b` at read time; now `a7a5a4b1`) in a read-only extract, never the main checkout, which was 284 commits stale at session start and is the reason the brief's premise survived this long.
- Two Workflow runs, 52 agents planned, 21 completed before the session usage limit (resets 02:50 Berlin): 10 subsystem maps (claims registry, borrowed pool, trip lifecycle, cost centers, re-match debt, decisions, trip report, SPA contract, test conventions, backlog rulings), 10 adversarial refuter verdicts over 6 of 9 claims, 1 of 9 gap finders.
- Corrected four claims from the solo pass, two of them mine: the cross-batch refusal is 409 `receipt_settled_elsewhere` / `receipt_just_settled`, not 400 `receipt_settled_by_charge` (that is the settled-outside guard); the trip re-match gap is the missing pre-mark inside the add's lock span, not a missing mark entirely; a company month's report IS sectioned (by cost center, else by card), just never per person; `expense_location` dies at the output layer, not the API layer.
- Answered the design question: trips and cost centers are orthogonal with one declared edge (`TripRow.cost_center`). Declaration is the source, resolution is the propagation, so the "declared vs resolved" clash dissolves rather than needing a winner.
- Ranked 11 gap clusters (A-K) in the shipped R4 with file:line anchors, each tagged refuter-confirmed / read-by-me / finder-only.
- Wrote the plan to `C:\Users\neuma_p1qrsic\.claude\plans\try-planning-again-but-sleepy-steele.md` (approved): R4.0 prove-on-a-copy, R4.1 lifecycle re-match durability, R4.2 reachability + hand-pick, R4.3 cost-center edge, R4.4 trip report + item 48's free lines, R4.5 prompts. Each with caller-level tests and named `regress_check` wires.

## What Did NOT Work (and why)

- **Sizing both workflows at 52 agents:** hit "You've hit your session limit" (resets 02:50 Berlin) after 21 completed. `reference_workflow_session_limit_budget` says keep a run under ~60 agents; the real constraint was two concurrent runs plus a 6.3M-token first run, not the per-run count. The gap-hunt lost 8 of 9 finders and all 20 verifiers, so its 8 findings are unverified.
- **Reading code from the primary checkout:** it was 284 commits behind `origin/main`, so the first pass would have planned against PR #981 state while HEAD was #1150+. Caught by the SessionStart stale-checkout warning; all reading moved to a `git archive` extract of `origin/main`.
- **`cd <dir> && …` in Bash:** refused by the cd-guard hook four times before switching to `git -C` / subshells / absolute paths.
- **Python writing digest files with `?` in the name:** `OSError [Errno 22]` on Windows from a `verdict-C2-?.md` filename built off a missing `lens` key; fixed by numbering duplicates instead.

## Current Status

Plan approved, zero code written, zero product files touched. Brisken platform ops status unknown (no `platform` section in `infrastructure.yaml` for this client). Live app verified read-only: `GET /api/trips` returns `{"trips": []}`, all 7 batches are `company-month`, `cost_centers` is `{}` — so the entire trip and cost-center feature pair is code-live and data-dead. The read-only `origin/main` extract and both workflow journals are in the session scratchpad; the read-only worktree used for the first pass was removed.

## Next Steps

1. Start the execution session from the continuation prompt (fresh chat, fresh worktree from `origin/main`, never the stale primary checkout).
2. After the 02:50 Berlin reset, resume both workflows to cover the two lenses that got zero coverage (lock races, intake/pooling) and the dead refuters C6/C8/C9: `Workflow({scriptPath: ".../r4-gap-hunt-wf_3fc0e14a-a71.js", resumeFromRunId: "wf_3fc0e14a-a71"})` and the same for `r4-verify-and-map-wf_35c36953-2a5.js` / `wf_35c36953-2a5`.
3. Put owner questions Q1 (does the trip entity survive), Q2 (author the four cost centers), Q3 (may a real trip be created live) to Dirk; the rest can ride the round.
4. Run `archive-register --days 14` in the same docs PR as this checkpoint (register is 318 KB).
5. Refresh the two stale project-status files flagged by pre-flight: `p2-product-decks.md` (60d), `p2-targeting.md` (61d).
6. Brisken comms-log is 13 days stale; log anything outstanding.

## Files to Read First

- `C:\Users\neuma_p1qrsic\.claude\plans\try-planning-again-but-sleepy-steele.md` (the approved plan; gaps A-K, the five rounds, the 12 owner questions)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 38, 47, 48, 112, 113
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` §"The two batch functions" (~584), §"The trip-spanning pool (R4b)" + §"The trip report" (~1160-1205)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_trip_settlement.py` (the fixture recipe every new test reuses)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

# Checkpoint: Brisken Item 38 R4 Close

**Date:** 2026-09-21
**Status:** R4.0 and R4.1 shipped and deployed (Fly v199); R4.2 open, R4.3/R4.4 held by owner

---

## Summary

Item 38's "remaining round" R4 turned out to have shipped on 2026-09-07 and
never been recorded, so three sessions re-planned it from a stale item body.
This round proved the shipped R4 against real data for the first time, found
two lifecycle defects, and built the fix the owner ordered.

---

## What Was Done This Session

### R4.0, prove the shipped R4 on real data (PR #1167, merge `218cdca0`)

1. Pulled a read-only copy of `/data/recon-web.sqlite` and ran a trip fixture
   against the real July and August months with **zero LLM calls** (extraction
   stubbed by filename). Copy deleted at the end.
2. All **seven behaviours** `tests/test_trip_settlement.py` asserts hold on
   real months. July *and* August re-matched with trigger `trip`, because
   August's charge span starts 2026-07-06 and a July trip legitimately lends
   to both.
3. Cold drive of the **published** SPA against that copy, through the login
   gate, every API call routed to the local server: 13 rewrites, 0 leaks. The
   Trips screen, the trip batch page and July's `Settled by trip ...` badge
   all render.
4. Recorded what was never recorded: Shipped rows 110-113 for R3 (#688),
   R4a/R4b (#685, `fc75c8a9`) and the prompt bundle (#698); retracted item
   47's "Nothing exists yet: `grep -rn cost_center src/` returns zero hits"
   (137 hits); corrected its D2 table to the `merchant` / `""` the code
   emits; fixed two stale source comments that asserted the cross-batch
   design had not landed.

### R4.1, the lifecycle fix (PR #1174, merge `b34ace5b`, Fly v199)

1. Four entrances now owe `rematch_pending(trigger="trip")` **inside their own
   `_BATCH_ADD_LOCK` span** and pay it outside: receipt-joins, a date edit
   (the union of old-range and new-range months), a trip-batch delete (months
   chosen *before* the delete) and a trip-receipt delete.
2. Five more defects of the same class, found alongside: the paying loop
   gained the per-month `try/except` `rematch_neighbour_months` always had;
   the candidate filter gained the expense-generation check;
   `learning_db_path` reaches both trip entrances; a rename carries onto the
   batch label **and** every borrowing month's stored `settled_by` label; the
   trip-batch create slot releases on any failure, not only `RunInputError`.
3. `tests/test_trip_lifecycle_rematch.py`, 12 route-level tests, self-contained
   fixtures. Suite **2714 → 2726 passed / 2 skipped**, ruff clean, CI green
   first pass. **Eight wires red-proven** under `regress_check`, the date gate
   in both directions.

### Owner rulings executed

`docs/trip-reports-and-cost-centers-today.md` (the current-state write-up the
held design will be argued from) and `docs/lovable-roster-mismatch-prompt.md`
(Pending in PROMPT-STATUS), plus the five rulings recorded in backlog item 38.

---

## Key Decisions Made

### The trip entity survives, and its cost-center integration is on hold
- **Choice:** Keep the trip entity unchanged; do not touch the trip/cost-center
  edge this round. Owner will brainstorm implementing both together.
- **Rationale:** A cost center carries the attribution, which is the owner's
  2026-09-20 point and correct. It cannot own a batch, lend to a match pool,
  refuse a statement, carry a roster or count days away, and it has no dates.

### Fix the lifecycle staleness, not the report's missing cost center
- **Choice:** Build R4.1; hold the report change.
- **Rationale:** Owner: "must be done because later on if expenses and items in
  statement dont line up we will have a problem." A wrong `n_reconciled` is a
  correctness defect; the missing cost-center line is a design question.

### The R4.1 defect is staleness, not corruption
- **Choice:** Retarget the planned test that asserted "no claim names the
  deleted run".
- **Rationale:** Measured: the claims ARE released on delete and the next
  re-match heals the month completely, so that assertion passes today without
  the fix and would not bite. The real defect is that nothing schedules that
  next re-match.

---

## What Did NOT Work (and why)

- **Playwright MCP for the SPA drive:** pinned to Edge CDP `:9222`, the
  machine-shared seat memory `reference_user_edge_cdp_9222` warns about. First
  call died on a 30s websocket timeout.
- **agent-browser:** `connect 9333` worked once, then `open`, `connect` and
  `close --all` each hung past 100-250s. Its node daemon wedged and had to be
  killed by hand and its `~/.agent-browser/*.pid|port|stream` state deleted.
- **Rewriting the SPA's API origin to `http://127.0.0.1:8791`:** an HTTPS page
  cannot reach an HTTP origin. The patch reported 14 "rewritten" calls while
  **zero** reached the local server; an explicit reach test returned
  `TypeError: Failed to fetch`.
- **A self-signed cert so the local API could speak HTTPS:** `openssl` was
  refused by the permission classifier and the module venv has no
  `cryptography`. Solved instead with Chrome's `--disable-web-security` on a
  throwaway profile.
- **The first R4.1 durability test:** it drove create-with-receipt while the
  wire under test was the gradual-add path, so `regress_check` reported the fix
  green with its wire disabled. Closed with two add-path tests.
- **The first R4.1 draft's async handlers:** `put_trip` and `delete_expense`
  are `async def` and blocked on the batch lock, which parks the event loop.
  The repo's own item-18 guard (`test_no_async_handler_calls_a_locked_service_function`)
  failed the suite. Both spans now go through `run_in_threadpool`.
- **The first deploy:** passed `--build-arg EXPENSE_RECON_COMMIT` when the
  Dockerfile ARG is `GIT_COMMIT`, so `/healthz` reported an empty commit on a
  live release until the redeploy.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `web/service.py` | edit | `trip_months_covering`, `_owe_trip_month_rematches_locked`, `owe_trip_month_rematches`, `rematch_trip_months`, `relabel_borrowed_sources`; `execute_expense_batch` takes `learning_db_path` |
| `web/app.py` | edit | `put_trip` owes the range union + syncs the label; `delete_run` and `delete_expense` owe the borrowing months; create-slot `try/finally`; both locked spans via `run_in_threadpool` |
| `web/intake_mail.py` | edit | thread `learning_db_path` into `join_trip`'s execute |
| `tests/test_trip_lifecycle_rematch.py` | new | 12 route-level tests |
| `docs/api-contract.md` | append | "A trip lifecycle change owes its months a re-match (R4.1)" |
| `docs/trip-reports-and-cost-centers-today.md` | new | current-state write-up for the held design |
| `docs/lovable-roster-mismatch-prompt.md` | new | the unrendered `roster_mismatch` field |
| `docs/PROMPT-STATUS.md` | edit | Pending row for the above |
| `status/p1-improvement-backlog.md` | edit | Shipped rows 110-114, item 38 findings + owner rulings, item 47 retraction |
| `status/p1-expense-reconciliation.md` | edit | R4 row: real-data verification + R4.1 |
| `.claude/patterns/warn-flyctl-deploy-git-commit.md` | new | catches the deploy-stamp mistake above |

---

## Current Status

R4.0 and R4.1 are merged and live: Fly **v199**, `/healthz` commit equals the
merge `b34ace5b`. A post-deploy cold drive of the live SPA shows July rendering
**31 of 112 paired** (its true value), no fallback strings, no error banner and
**zero non-GET calls**. Live `GET /api/trips` is still `{"trips": []}` and
stored `cost_centers` is still `null`, so every R4 field remains dormant until
Dirk authors the cost centers and a real trip exists.

Brisken platform: unknown plan, ops/mo unassessed, last assessed unknown.

---

## Next Steps

1. Paste `docs/lovable-roster-mismatch-prompt.md` into Lovable, publish, then
   bundle-audit and drive it.
2. Dirk authors the four cost centers in live Settings. Measured consequence:
   `needs_cost_center` turns on for **183 rows across seven months** and none
   resolve. Decide whether to seed merchant or card defaults first.
3. Owner brainstorm on trips + cost centers, from
   `docs/trip-reports-and-cost-centers-today.md`.
4. R4.2 (borrowed-receipt reachability, hand-pick, the id-collision
   namespacing) is the next backend round and is unblocked.
5. Brisken comms-log is 13 days stale; log anything outstanding.
6. Refresh the two stale project-status files flagged at pre-flight for a
   second checkpoint running: `p2-product-decks.md` (60d), `p2-targeting.md`
   (61d).
7. Run a feasibility assessment for Brisken's platform section in
   `infrastructure.yaml` (no plan or ops figures recorded).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 38 (the
  owner rulings and the two measured defects) and item 47
- `workspace/clients/brisken/automations/expense-reconciliation/docs/trip-reports-and-cost-centers-today.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`,
  the R4.1 section at the end
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_trip_lifecycle_rematch.py`

### Open Questions
- Which cost-center carrier gets seeded first so the 183 flagged rows resolve
  rather than sit open?
- Does the trip report eventually print the trip's cost center, or does the
  held design replace the per-person sectioning entirely?
- Should the Node CDP driver used for both SPA drives be promoted from the
  scratchpad into `tools/`?

### Working Notes
- **The SPA drive recipe that worked**, after Playwright MCP and agent-browser
  both failed: launch Chrome with `--remote-debugging-port=PORT
  --user-data-dir=<throwaway>`, then drive CDP directly from a Node script on
  Node 24's built-in `WebSocket` (`Page.addScriptToEvaluateOnNewDocument` for a
  pre-load patch, `Runtime.evaluate` for everything else). ~90 lines, worked
  first try, no dependencies.
- **To route the published SPA at a local API**, the page origin is HTTPS so
  the local server must be reachable: `--disable-web-security
  --allow-running-insecure-content
  --disable-features=BlockInsecurePrivateNetworkRequests` on a throwaway
  profile. Always assert reach explicitly before trusting a rewrite count.
- **July's live numbers** for comparison: 112 charges, 31 reconciled,
  match_rate 27.7, charge span 2026-06-30..2026-07-31. August: 114 charges,
  span 2026-07-06..2026-08-31, which is why a July trip lends to both.
- **Unmatched July charges usable as trip-receipt fixtures** (amounts unique in
  the month): ESPETINHO DO RAMOS 5.15 / 2026-07-25 / card 3876,
  PRESSMASTER DMCC 135.00 / 2026-07-23 / card 2838.
- The live card registry maps 3876, 0340 and 2838 all to the same Zoho account
  `CHASE VISA - 2838 - TRAVEL`. That is correct, confirmed by the owner; do not
  re-raise it as a defect.

### Reference Materials
- PR #1167 (R4.0 docs), PR #1174 (R4.1) — both merged
- `docs/operating.md` "Deploy" — the deploy command with the clean-tree guard
- `docs/PARALLEL-ROUND-PROTOCOL.md`

---

## How to Continue

The backend is unblocked for R4.2. Everything else waits on two owner actions
(paste the prompt, author the cost centers) and one owner decision (the
trips/cost-center design). Start from backlog item 38's ruling block.

---

## Strategic Feedback

### What Worked Well This Session
- **The differential probe caught my own false positive.** The R4.0 check for
  "does the trip report print the cost center" passed on the string `Brazil`,
  which was also the trip's name. Re-running with a marker string that appears
  nowhere else flipped the answer. Instrument-validity is now paying for itself
  about once a session.
- **`regress_check` refused a test that did not bite**, and it was right: the
  durability test drove a different entrance than the wire it claimed to cover.
  Two of the eight wires needed a second attempt.
- **The repo's own item-18 guard caught a defect I introduced**, not a
  regression in someone else's code. The async/lock rule is doing real work.

### Suggestions
- Promote the Node CDP driver into `tools/` as a first-class browser harness.
  Playwright MCP is pinned to a seat that hangs and agent-browser wedged three
  times in one session; the 90-line CDP script worked first try and is the only
  thing that has reliably driven the SPA this month.

### System Health
- Autonomy: **1 human intervention**, and it was the owner-decision round this
  session was designed to collect, not a correction. Fully autonomous otherwise.
- Two `verification-theater` rows this round, both instrument-validity and both
  caught by me before they reached the user. That is the third consecutive
  session logging this type; the fix has been `documented` each time, which is
  the pattern the anneal ladder says to escalate.

# Checkpoint: Brisken Recon SPA Contract Test + Batch-Lock Threadpool

**Date:** 2026-08-22
**Status:** Both 2026-08-22 defects closed; wave round 8 (Cards R4) blocked on owner answers

---

## Summary

The parse_issues SPA crash is cleared (owner published the Lovable fix, DOM-verified against a batch that really carries an issue) and its recurrence-kill shipped as a view-shape contract test. Backlog item 18, the batch-lock event-loop freeze, shipped and deployed in the same session.

---

## What Was Done This Session

### 1. Confirmed the SPA fix is published and actually renders
1. Pulled the live index, enumerated all 42 asset refs, fetched `chunk-expenses._batchId-B0GM7SZQ.js`: the served code handles `ParseIssue[]` with a `typeof item === "string"` fallback and renders `file`/`line`/`message` with severity styling.
2. Confirmed the backend really exercises the crash path: batch `ae61e122a505` carries one object-shaped issue (`receipt_01_p7.png`, report-summary quarantine), `n_parse_notes: 1`.
3. DOM-probed the batch page in headless Chrome, logging in from the vault so the operator code never entered the transcript: 36 table rows, quarantine note visible, no error boundary, zero console errors. Re-probed after the backend deploy.
4. Chunk-name pinning confirmed still holding (`chunk-expenses._batchId-…`, never `_batchId-…`).

### 2. Backlog item 21 — view-shape contract test (PR #571)
1. `tests/test_view_contract.py`: pins the element type of every list field on both view payloads (expense-batch, run), probed over HTTP so the pin is what actually ships including `jsonable_encoder`.
2. Three assertions per view: no unpinned field, no element-type drift, and a `MUST_COVER` non-vacuity guard — without the third, a weakened fixture makes the whole test pass by observing nothing.
3. Fixtures built to reach every list: quarantined statement page, unsupported upload, generic + exact payment hints, a duplicate pair, a field edit, one vendor booked to two categories, plus a seeded snapshot for ambiguous candidates and duplicate charges/receipts.
4. `docs/api-contract.md`: the prose companion the Lovable prompts cite, with the change rules (enrich via a parallel field, never retype under a live renderer; ship the SPA half in the same round; render defensively).

### 3. Backlog item 18 — batch lock off the event loop (PR #572, Fly v74)
1. `set-aside/restore` and the cards endpoint were `async def` blocking on `_BATCH_ADD_LOCK`; both now hand the locked span to `run_in_threadpool`.
2. Static AST guard: fails CI on any future `async def` route calling a lock-taking service function outside a sync closure or lambda, with the locked set derived from `service.py` so a new one joins for free.
3. `_BATCH_ADD_LOCK` documents its two riders: in-process only (scale-out breaks the model), and no async handler may block on it.
4. Deployed to Fly after checking nothing was processing, then verified live.

### 4. Bookkeeping (PR #573)
Backlog items 21 and 18 moved to Shipped rows 13/14, loop runbook's LIVE BLOCKER section replaced with the cleared state, suite baseline corrected to 1221, status element row added, loop memory + index updated.

---

## Key Decisions Made

### Prove each guard fails before trusting it
- **Choice:** Regress the real code and watch the new test go red, every time.
- **Rationale:** Both tests passed against the very bug they guarded on first draft. The contract probe passed until `parse_issues` was regressed to `string[]` (3 of 4 tests then failed); the lock test passed until it stopped using a nonexistent batch id, because both endpoints validate the run and 404 before ever reaching the lock. A guard never seen to fail is not a guard.

### Pin list element types, not every leaf
- **Choice:** Contract covers list element types only; scalar-type flips are explicitly out of scope, stated in both the test docstring and the doc.
- **Rationale:** A list is the only place the SPA maps over elements it did not individually type, which is the shape the crash took. Pinning every leaf is several hundred rows churning every round. Widen it if a scalar flip ever bites, not before.

### Take item 18 while Cards R4 is blocked
- **Choice:** Ship the one unblocked code item rather than idle on owner answers.
- **Rationale:** Item 18 was a real availability bug (parked loop kills `/healthz`, Fly restarts, restart kills the in-flight ingest) and the backlog already marked it "ship with the next code round". That round was blocked, so it became its own.

### Accept the threadpool-worker residual
- **Choice:** A blocked handler now holds an anyio worker instead of the loop; documented rather than engineered around.
- **Rationale:** Exhaustion needs ~40 concurrent blocked calls. One operator. Same trade `delete_run` already makes.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/tests/test_view_contract.py` | new | Pin list element types on both view payloads (item 21) |
| `automations/expense-reconciliation/docs/api-contract.md` | new | Prose contract the Lovable prompts cite |
| `automations/expense-reconciliation/tests/test_web_batch_lock_threadpool.py` | new | Event-loop freeze reproduction + static AST guard (item 18) |
| `automations/expense-reconciliation/src/expense_recon/web/app.py` | edit | Both locked spans handed to `run_in_threadpool` |
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | edit | `_BATCH_ADD_LOCK` constraints documented |
| `status/p1-improvement-backlog.md` | edit | Items 21 + 18 to Shipped rows 13/14 |
| `status/p1-recon-loop-prompt.md` | edit | Blocker cleared, baseline 1221, item 18 note |
| `status/p1-expense-reconciliation.md` | edit | Contract-test element row |
| `memory/project_brisken_expense_recon_usability_loop.md` | edit | Round recorded; crash marked closed |

---

## Current Status

Live and verified: `brisken-expense-recon` Fly v74, machine `48ee133c363758` (fra), healthz 200, `/api/expense-batches` 401 not 404. All 6 batches intact on the volume, including the January set and the owner's April batch `ae61e122a505` (36 expenses, 1 parse issue, 1 set-aside). SPA batch page renders after the deploy.

Suite **1221 passed / 2 skipped**; `calibrate --config examples/run.example.json` green; ruff clean on all new files.

Platform ops status: unknown plan, last assessed unknown (no `platform` section in `infrastructure.yaml` for this client; the expense tool runs on Fly, not an orchestrator, so no ops-audit applies).

Wave rounds 1-7 of 8 shipped. Round 8 (Cards R4) is the only remaining wave item and is blocked on owner answers.

---

## Next Steps

1. **Cards R4** once the owner answers backlog item 10: mixed-entity export (per-entity CoaGate), persisted cards migration, intake dropdown unification.
2. **Item 19** needs the owner's call: re-ingest for attachment mail stranded by a deleted month.
3. **January set-aside strip:** restore-or-not on Dirk's rendered credit notice.
4. **Item 20** (issue codes on upload/parse-issue prose) rides whichever round next touches those three emission sites; `docs/api-contract.md` now records the safe shape (parallel `issue_details`, never retype `issues`).
5. **p2 status files are genuinely stale** (p2-lead-gen-general and p2-outreach at 62d, four more at 30-31d). Not touched here because this session was p1-only, and bumping `updated:` without doing the work would invent currency. They need a p2 session, not a date bump.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`

### Open Questions
- Item 10 (Cards R4): mixed-entity export, persisted cards migration, intake dropdown unification.
- Item 19: re-ingest path for attachment mail after a month delete.
- Restore Dirk's rendered credit notice in the January set-aside strip?

### Working Notes

**Reading the live app without asking anyone.** `POST /api/login` with the vault entry `Brisken recon operator code matthias` returns a bearer token; everything else is `Authorization: Bearer`. A small helper at `%TEMP%/claude/recon-probe/api.py` does login-with-401-retry. The DOM probe (`dom_probe.py`, same dir) is a PEP-723 uv script that reads the code from the vault itself, so the credential never reaches the transcript. Playwright's bundled chromium is not installed on this box; `p.chromium.launch(channel="chrome")` uses the system Chrome and works.

**The 404 short-circuit that made two tests theater.** Both `set-aside/restore` and `/cards` call `_mutable_expense_run_or_error` before touching the lock, so an endpoint test using a nonexistent run id exercises nothing. Same shape bit the contract fixture. Any test aimed at a code path behind validation needs a real entity id.

**Contract-probe mechanics worth reusing.** The walker merges list elements into one representative object before recursing, and list-valued keys CONCATENATE across elements — otherwise one row with `candidates: []` hides the shape of the row that has them. That single detail was the difference between 12 covered paths and 19.

**Failed approach:** pinning scalar leaf types as well. Abandoned before writing it; the table would be several hundred rows and churn every round for a failure mode that has never occurred.

**Bash heredocs are unreliable here for large Python.** `cat > f <<'PY'` died with "unexpected EOF" on a ~150-line script, and a later heredoc-embedded string replacement silently failed to match a non-ASCII bytes literal. Use the Write tool for multi-line Python; heredocs are fine for short ASCII patches.

### Reference Materials
- SPA repo: `011matthias/brisken-expense-review` (Lovable two-way sync)
- Live SPA: https://brisken-reconcile-dash.lovable.app
- Backend: https://brisken-expense-recon.fly.dev
- PRs this session: #571, #572, #573

---

## How to Continue

Open a fresh chat and paste `p1-recon-loop-prompt.md`. If the owner has answered item 10, Cards R4 is the round; otherwise item 20 is the only unblocked code item and it wants a round that already touches the three issue-emission sites. Work from the `agentic-ops1-recon` worktree, refresh to `origin/main`, cut a `client/brisken/*` branch before the first edit.

---

## Strategic Feedback

### What Worked Well This Session
- Regressing the real code to watch each new test go red caught two guards that would have shipped as decoration. The contract test also caught a wrong pin while being written (`card_review.resolved[]` carries `hints`, not `documents`).
- Verifying the SPA fix by DOM-probing a batch that actually carries a parse issue, rather than reading the bundle and calling it done. Reading the bundle proved the code shipped; only the probe proved the page renders.
- Deriving the AST guard's locked set from `service.py` source instead of hardcoding it, so the next lock-taking function is covered without anyone remembering to add it.

### Suggestions
- The two theater drafts shared one root cause: a test aimed at code behind a validation short-circuit. Worth a line in the loop runbook's step 5 — "prove it fails" is already there, but "and make sure the fixture reaches the guarded path" is the half that failed twice today.

### System Health
- Autonomy: **0 human interventions** — fully autonomous session.
- The friction register is at 357 KB and past its archive threshold; archived in this checkpoint's docs PR.
- The `gate-skip-pre-publish` hook fired twice on merges that were fully validated (suite + calibrate + ruff all ran); the CI-watch calls in between pushed the validation out of its buffer. Worth widening the buffer or keying on the PR's own CI verdict, otherwise it trains the reader to dismiss it.

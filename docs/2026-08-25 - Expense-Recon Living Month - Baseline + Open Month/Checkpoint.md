# Checkpoint: Expense-Recon Living Month - Baseline + Open Month

**Date:** 2026-08-25
**Status:** 2b-2a shipped and deployed (Fly v95). 2b-2b (gradual statement uploads) is next and unblocked.

---

## Summary

The 2b-2 guard triage refuted the plan's stated risk and found a worse one
underneath it, which became a prerequisite PR of its own. Two PRs shipped,
merged and deployed: the extraction baseline now survives the bake (#628,
v94) and the month stays open once its statement is loaded (#629, v95).

---

## What Was Done This Session

### The guard triage (the requested first step)

1. Enumerated the nine `has_statement` route guards and mapped each to its
   route, confirming the brief's three classes.
2. Probed the overlay-after-bake behavior by driving the real HTTP routes
   rather than reading the code. Two findings, both contradicting the plan:
   - **Double-application is not the risk.** The overlay is idempotent by
     construction: `add` is guarded by an `existing_ids` check written for
     exactly this case, `delete` is set membership, every header edit is an
     absolute assignment.
   - **The bake destroys the audit baseline.** Measured on a batch whose
     reviewer corrected vendor and total, then attached: snapshot went
     `{'OriginalVendor', '42.50'}` to `{'EDITED-BY-REVIEWER', '99.99'}`.
3. Found the guard is TWO layers, not nine call sites: those nine are routes
   through one gate, and beneath five of them sat five more refusals inside
   the service functions themselves.

### PR #628 - the extraction baseline survives the bake

1. `extracted_receipts`, a parallel snapshot key, first-write-wins PER
   document (a second re-match reads an already-baked snapshot, so
   refreshing would capture the baked values; growing per document is what
   lets later arrivals join).
2. Overlay-composing reads (grid, export, learning harvest, batch-list
   counts) start from it via `service.baseline_receipts`; matching, reports
   and reconciliation views keep the baked pool.
3. Three harms fixed: `raw` echoing the reviewer's own edit, clearing an edit
   being a silent no-op, and the learning harvest keying corrections on the
   corrected vendor instead of the original.
4. Four tests, each proven red first, driving real HTTP routes.

### PR #629 - the month stays open

1. Removed four service-layer refusals and opened four routes: receipts,
   set-aside restore, cards, refresh-master-data.
2. `service.rematch_after_change` after each, OUTSIDE the caller's lock span
   (`_BATCH_ADD_LOCK` is not reentrant and `rematch_month` takes it to
   commit); skipped when an upload added nothing.
3. A re-match failure is REPORTED, not raised (`_rematch_or_error`).
4. Pool: a statement-bearing month claims its mail; `pool_month_state`
   reports `reconciling` where it said `closed`. No SPA change needed
   (`status_label` already composes the prose).
5. Nine tests; both halves proven by mutation via `regress_check.py`.

### The adversarial find (and its recurrence-kill)

The item-18 AST guard that stops an `async def` route from parking the event
loop derived its locked set by scanning for `with _BATCH_ADD_LOCK` in a
function's OWN body. Every lock-taker held it that way until
`rematch_after_change`, which takes it one call deeper, so the guard reported
my new function as safe. A future async route calling it directly would have
frozen every endpoint including `/healthz` for the minutes a re-match runs.
The locked set is now a transitive closure, proven by mutation.

---

## Key Decisions Made

### The four expense-edit overlay routes stay closed

- **Choice:** they do not open in 2b-2.
- **Rationale:** the plan's reason (double-application) was refuted by
  measurement. The real reason is that a re-match BAKES the overlay into the
  pool, so an edit surface is worth reopening only once every edit stays
  reversible and honestly attributed. #628 restored the baseline both rest
  on; reopening them needs the re-match an edit must trigger, its own round.

### A re-match failure is reported, not raised

- **Choice:** `_rematch_or_error` returns `{"error": ...}` instead of
  propagating.
- **Rationale:** the caller's change is already committed when the re-match
  runs. A throw would mark a receipt that safely landed as `held_failed` and
  replay it; an OpenAI outage would do that to every receipt Dirk sends. A
  truthful stale beats a wrong fresh, and the next trigger retries.

### Split into prerequisite PRs rather than one 2b-2

- **Choice:** #628 (baseline) then #629 (open month), with append deferred.
- **Rationale:** the house rhythm. #628 is provably neutral (1312 to 1316,
  the +4 being its own tests, no pre-existing test moved), so "did the
  refactor move behavior?" never tangles with "does the guard lift work?".

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/service.py` | edit | `baseline_receipts`, `_extended_baseline`, `rematch_after_change`, `_rematch_or_error`; four service guards removed; baseline write in `rematch_month` |
| `src/expense_recon/web/app.py` | edit | four routes moved off `_mutable_expense_run_or_error`; guard docstring narrowed to the overlay |
| `src/expense_recon/web/intake_mail.py` | edit | reconciling months claim pooled mail; `pool_month_state` gains `reconciling`; label |
| `tests/test_extraction_baseline.py` | new | four tests, red-first |
| `tests/test_living_month.py` | new | nine tests, red-first |
| `tests/test_web_batch_lock_threadpool.py` | edit | locked set is now a transitive closure |
| `tests/test_intake_mail.py`, `tests/test_web_expense_lifecycle.py` | edit | re-pinned to the new behavior |
| `docs/api-contract.md` | edit | `pool_month_state` enum growth |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 29 (2b-1b + 2b-2a shipped; 2b-2b next) |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | two shipped-element rows (PR #630) |

---

## Current Status

Backend live on Fly **v95**, health check passing. Suite **1325 passed / 2
skipped** (was 1312 at session start), calibrate exit 0, ruff (E9,F) clean on
every diff. PRs #628 and #629 merged and deployed; #630 (status rows) open.

Live-verified after each deploy: healthz 200, the attached January batch
renders 13 expenses through the baseline's fallback path, April renders 40
with 37 categorized, both export paths answer 200, intake log reads 30 rows /
10 pooled.

Two honest gaps in the live check: no pooled mail is currently addressed to a
statement-bearing month, so the `reconciling` state is exercised only by
tests; and no POST was fired into a real client month, since that would put a
TEST receipt into Criss's January without an ask.

brisken platform: unknown plan, ops/mo unrecorded, last assessed unknown.

---

## Next Steps

1. **2b-2b: gradual statement uploads.** `POST .../statement` becomes
   append-capable and repeatable (per card, several times a month), parsing
   and content-id deduping against the existing set, with a `statements[]`
   parallel field. The one-shot attach is the degenerate case of the same
   path. `prepare_statement_attach` keeps its refusal until then, pinned by
   a test.
2. **Decide the sign-inference warning** (2a's pinned interaction): a file
   whose SIGN inference differs between a partial and a full upload yields
   different ids for the same printed row. Surfacing two rows beats silently
   deduping a contradiction; whether it also wants a visible warning is open.
3. **PR 3: coverage surface** (per-card statements/periods/matched counts in
   the batch view, the month page's statement panel prompt).
4. Merge #630 on green.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 29 -
  the authority on what is next)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`rematch_month`, `rematch_after_change`, `baseline_receipts`)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
- `C:\Users\neuma_p1qrsic\.claude\plans\fizzy-seeking-lagoon.md` (the plan;
  its 2b-2 guard analysis is superseded by this session's triage)

### Open Questions

- Does the sign-inference divergence want a visible warning, or is surfacing
  two rows enough on its own?
- Should `next_open_batch` (the LEGACY selector behind delete-month and
  re-ingest) also treat a reconciling month as open? Left alone deliberately;
  it answers a different question and changing it would route legacy mail
  into an attached month.

### Working Notes

Findings that were expensive to derive and should not be re-derived:

- **The overlay routes are idempotent** - measured, not assumed.
  `apply_expense_edits` guards manual adds with `existing_ids` precisely
  because the bake persists, and `_apply_header_overrides` is absolute
  assignment. They stay closed for reversibility and attribution, not for
  double-application.
- **The service layer refuses independently of the routes.** Five service
  guards existed; four are gone, `prepare_statement_attach` remains. A route
  lift alone does nothing.
- **`_BATCH_ADD_LOCK` is `threading.Lock`, not RLock.** Any re-match must run
  outside a lock span or it deadlocks.
- **The expense grid's summary is receipt-centric** and carries no match
  counts; `n_receipts_matched` / `n_unmatched_rec` live on the STORED run
  summary. A test proving a re-match ran must read the store, not the grid.
- **Vault shape:** `~/.passwords.json` is a flat top-level dict keyed by entry
  name; the operator entry's field is `code` (not `password`/`value`).
  `vault.py get` prints a formatted record, not a bare secret.
- **Operator auth is a signed bearer token**, not a header code: `POST
  /api/login` with `{"code": ...}` returns `token`, then
  `Authorization: Bearer`.
- Pre-2b runs (January) have no baseline and exercise the fallback path;
  live-verified as rendering correctly.
- A checkpoint topic containing `:` cannot become a Windows folder.

### Reference Materials

- PR #628 (baseline), #629 (open month), #630 (status rows) on
  `011matthias/agentic-ops1.01`
- App: https://brisken-expense-recon.fly.dev ; SPA:
  https://brisken-reconcile-dash.lovable.app

---

## How to Continue

Work in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-recon` on a fresh branch off
`origin/main`. Read backlog item 29 first; it is the authority. Start 2b-2b by
reading `prepare_statement_attach` and `execute_statement_attach`, then split
the append work so the parse/dedupe foundation lands before the `statements[]`
surface.

---

## Strategic Feedback

### What Worked Well This Session

- **The triage was run as measurement, not reading.** Probing the real routes
  turned a plan assumption ("risks double-application") into a refutation plus
  a live defect nobody had noticed. Reading the code would have reproduced the
  plan's belief and shipped the wrong PR.
- **Mutation testing caught a hole in a guard, not just in the code.** The
  transitive-closure fix came from asking "does the existing guard still see
  my new indirection?" - worth asking only because the guard was run and then
  doubted.

### Suggestions

- The plan file's 2b-2 section is now partly wrong (the guard analysis and the
  overlay rationale). A stale plan that reads authoritative is the same
  failure class as a stale status file. Annotate it in place or point it at
  backlog item 29 as the authority.

### System Health

- **Autonomy: 2 human interventions**, both "continue" after work stalled at a
  boundary, one caused by a B1 deferral the stop gate had to catch. The rest
  ran unattended through two full ship chains including deploys.
- `agent-deferred` is now four rows in three days (08-23, 08-24, 08-25 x2).
  The stop gate catches it every time, but always post-hoc, and each catch
  costs a redone turn. The `[B1 PRIMER]` pre-generation path fired this
  session and the deferral still happened on a later turn, which is worth
  knowing before the next attempt to strengthen it.

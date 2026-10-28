# Checkpoint: Expense-Recon Case 9 Build 3

**Date:** 2026-09-25
**Status:** Build 3 shipped and live (PR #1364, Fly v232); its two open findings logged as backlog items 211 and 212 (PR #1381)

---

## Summary
Backlog item 204, step 3. A receipt that a neighbour month's statement settled now carries that charge's card, company and person on the grid, CSV, month PDF and the learner. No live row moves today. The build surfaced two gaps that could not be built within its scope: the borrow window under calendar-month statements, and FX that does not follow the claim. Both are now backlog items.

---

## What Was Done This Session

### Build 3 (PR #1364, squash `1a78c1ae`, Fly v232, `/healthz` = `1a78c1ae`)
1. **The flow-back.** `settled_charge_cards` merges `cards_settled_elsewhere`, a new function at the end of `web/service.py`. It reads the claims other runs hold on this run's receipts and re-checks each one against the holder's effective verdict:
   - the holder's charge is reconciled,
   - it still holds this document,
   - `receipt_source_run` is this run.

   The card comes from `_charge_card_identity`, resolved in the receipt's own batch registry. The card chain's existing `settled` link consumes the result unchanged.
2. **The store access.** `store.open_read_only` (end of `web/store.py`) opens a `RunStore` over a `mode=ro` connection and skips the schema pass.
3. **Tests.** `tests/test_card_flows_back_c9.py` holds 8 route-level tests. `regress_check` on the wiring line took them green → 6 red → green.
4. **Merges from main.** Main was merged in three times: builds 1 and 2 of the case 9 round, item 208, and checkpoints. The Shipped row renumbered 123 → 124 → 125 → 126.
5. **Final head `9ea024a3`.**
   - CI: full `test` job green, plus every other check.
   - Locally: 153 focused tests passed, and the accuracy check showed no diff.
   - Earlier head: 3484 passed / 2 skipped locally.

### Logging (PR #1381, `df939029`)
6. **Item 211:** the borrow-window gap. It needs an owner decision; its live count is TBD until the first calendar-month statement is loaded.
7. **Item 212:** FX conversion does not follow the claim. 0 live rows, because both cross-month receipts are USD, the base currency.
8. Both findings were re-verified on main after builds 4 and 5 had merged.

### Live reads (read-only)
9. **Before and after deploy:** 2 rows carry `settled_by`, August's OpenAI 80.12 and 80.04, borrowed by September. Both show `hint` 9693 and are unchanged.
10. **July's one borrowed receipt:** June's SUPERMERCADO FENIX 10.82 is in July's review bucket, so it has no claim and gets no card.

---

## Key Decisions Made

### Read the claims store from the run, not from the callers
- **Choice:** `cards_settled_elsewhere` derives the database from `run.work_dir` (`data_root/runs/{id}` → `data_root/recon-web.sqlite`) and opens it read-only.
- **Rationale:** The prompt fixed the callers' signatures (build 4 owns `resolve_batch_row_cards`, and the CSV, PDF and learner call lines were out of scope). A read-only connection cannot wait on the caller's write lock, and any failure lends nothing. The cost is a layout coupling, documented in the docstring.

### Re-check claims against the holder's effective verdict
- **Choice:** A claim lends a card only while the holder's charge is still reconciled and holds this document.
- **Rationale:** The item-111 same-month rule reads effective state. A stale claim must lend nothing rather than a card that the holder's own page no longer shows.

### Merge on CI green rather than re-run the 15-minute local suite on every sibling merge
- **Choice:** For each merge from main: focused tests plus the accuracy check locally, then CI's full `test` job on that head.
- **Rationale:** Three sibling merges landed during two local full runs, and both runs were superseded.

### No SPA drive
- **Choice:** Verification was API-only. The app was not driven in a browser.
- **Rationale:** The round prompt drives the SPA only if a live row moved, and none did.

---

## What Did NOT Work (and why)
- **`pytest -n auto ... | tail || pytest ...`:** pytest-xdist is not installed, so pytest refused `-n` with a usage error. `tail` masked that exit code, so the `||` fallback never ran. This repeats a same-day sibling row.
- **Forcing a review-bucket borrow through amount or FX confidence:**
  - USD receipts at 71.00, 68.00, 65.00 and 60.00 against a 71.64 USD charge still match deterministically at 0.85. At 55.00 there is no candidate.
  - Lowering the mocked FX confidence changes nothing, because USD/USD never takes the FX-judgment path.
  - A EUR receipt yields no candidate, because there is no reference rate.
  - What works: a tie, i.e. an identical receipt in the borrowing month.
- **Edit tool and `Path.read_text` on the backlog and api-contract:** these files mix CRLF and LF, and `read_text` folds CRLF, so the anchors never matched. What works: byte-wise edits with per-anchor line-ending detection.
- **Two local full suites between sibling merges:** both were superseded mid-run and stopped. About 25 minutes of wall clock were lost.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` | edit + append | `settled_charge_cards` body; `cards_settled_elsewhere` |
| `.../src/expense_recon/web/store.py` | append | `open_read_only` |
| `.../tests/test_card_flows_back_c9.py` | new | 8 route-level tests |
| `.../docs/api-contract.md` | append | build 3 section |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | append | build 3 paragraph under item 204, Shipped row 126, items 211 and 212 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | top paragraph | build 3 status, pointers to items 211 and 212 |
| `.claude/patterns/warn-pytest-xdist-not-installed.md` | new | warns on `pytest -n` / `--numprocesses`; tested 3 match / 4 silent |

---

## Current Status
- Case 9 round: builds 1, 2 and 3 are merged. Builds 4 and 5 run in their own sessions (build 5 is already in the Shipped table as row 127).
- Live: Fly v232 at `1a78c1ae` at the time of deploy. Later sibling deploys carry this change too.
- Brisken ops status in `infrastructure.yaml`: unknown plan, never assessed.

---

## Next Steps
1. **Owner decision on item 211:** widen the adjacent borrow window for calendar-month statements, or accept hand-matching for a month-end receipt paid on the 1st. Measure the count on the first calendar-month statement.
2. **Build item 212** (small, no decision needed): `settled_charge_amounts` reads the same claim, returning the charge's amount and currency.
3. **Waiting on the owner or Criss:** D2 (weekly Chase export with view access to 9693 / 1176) and D3 (loading the 9693 history and the April to June 3876 / 0340 sheets). The previous checkpoint's title suggests D2/D3 were granted on 2026-09-25; confirm there before acting.
4. **Feasibility assessment for Brisken's hosting:** `infrastructure.yaml` has no assessed platform plan.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`: item 204's "Build 3 (step 3)" paragraph, and items 211 and 212
- `.../web/service.py`: `settled_charge_cards`, `cards_settled_elsewhere`, `statement_period_for_month`, `settled_charge_amounts`

### Open Questions
- Item 211: how wide can the window get before wrong pairings outweigh the receipts it recovers? This can only be measured once a calendar-month statement exists.

### Working Notes
- **A route-level review bucket** needs a tie. Deterministic USD pairs tolerate about 15% amount drift at 0.85 confidence.
- **The claim map is live-exercised on August**, whose two receipts September holds. The reader ran without error on Fly (the page returned 200), but the printed hint masks its output on both rows.
- **Shipped-row numbers in a parallel round** get taken while CI runs. Renumber on every merge from main. `resolve4.py` in this session's scratchpad was the reusable shape: keep both sides; ours on top with the next free number.

### Reference Materials
- PR #1364 (build 3), PR #1381 (items 211 and 212), PR #1374 (build 3 mini-checkpoint)
- `docs/2026-09-25 - Expense-Recon Case 9 Build 3/Mini-Checkpoint-1.md`

---

## How to Continue
Resume Brisken with `/comd_resume brisken`. Item 211 waits on the owner. Item 212 can be built directly: extend `cards_settled_elsewhere`'s read to return `(amount, currency)` and feed `settled_charge_amounts`. Regress through `GET /runs/{id}/expenses.csv`'s `Exchange Rate` on a BRL receipt settled by a neighbour month's USD charge.

---

## Strategic Feedback

### What Worked Well This Session
- **Measuring before building turned an assumed payoff into a precise one.** The prompt expected "0 to 1 rows" plus a July receipt to identify. The read found FENIX in review (no claim) and that both borrowed rows were already hinted, so the PR claims 0 moved rather than an invented number. The same read exposed the item 211 gap.
- **Keep-both conflict resolution** ran three times on shared status files with no lost sibling lines. It checked ordering (sibling first where it merged first; ours on top in the Shipped table), not just marker removal.

### Suggestions
- **Promote `warn-stop-merge-left-pending` from warn to block on the Stop event.** It has fired after the fact three times in two days (rows 2026-09-24, 2026-09-25, and this session). Each time the turn had already ended with a PR mid-chain. A Stop block honouring `stop_hook_active` costs one turn and keeps the chain inside it.

### System Health
- **Case 9 round workflow:** five parallel builds merged into one `service.py` with only status-file conflicts. The append-only protocol is holding. Its remaining cost is wall clock spent re-merging while CI runs.
- **Autonomy:** 1 human intervention. The owner had to ask for the two findings to be logged as backlog items.

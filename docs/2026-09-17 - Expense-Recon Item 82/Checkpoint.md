# Checkpoint: Expense-Recon Item 82

**Date:** 2026-09-17
**Status:** Item 82 live (Fly v144) and inert on July/August by design; all pending SPA prompts applied; item 90 queued

---

## Summary
Item 82 was simulated, then built as ruled and verified: ECB monthly rates are more accurate but gain no correct pair on the live months at today's 3% band. The owner ruled to tighten the band first and remove the Settings rates after, and the three waiting SPA prompts (82, 87, 89) are published and verified.

---

## What Was Done This Session

### Simulation, before any code
1. DB + learning copies and 103 receipt files pulled off the Fly volume at v143; a driver imported `tools/recon-match-attribution.py`'s own loaders. Instrument proved first: both months replayed at the Settings rates with parity 0 and 0 judgment-cache misses.
2. Four rate variants on both live months and the six bundles, plus a 2% band measurement. Numbers are in backlog item 82's simulation block (not repeated here).

### Build and ship (PR #951, merge `17e1501c`, Fly v144)
1. `web/ecb_rates.py` (one wildcard request for all 29 ECB currencies, fail-open 4 s, env kill switch); `MatchingConfig.fx_ecb_monthly_rates` + `ecb_monthly_rate`; `_reference_rate_for(..., on=)` with rungs typed > statement > receipts > `ecb_month`; fetch at company-month creation and statement attach; `fx.reference_rate_period`; advisory copy; conftest stub so no test reaches the network.
2. Suite 1983 -> 1998 / 2 skipped. Four regress proofs red then green. Scorer 70/95 SCORE 76.0, guard 4/4.
3. Live: the machine reaches the ECB; July/August FX blocks and summaries identical to pre-deploy, `updated_at` unchanged; SPA driven cold.

### Decisions recorded and prompts verified
1. PR #952 mini-checkpoint; PR #953 backlog item 90 (owner ruling); PR #954 PROMPT-STATUS: bundle audit (48 chunks, 1,050 KB, controls hit, 11 names present, old FX copy absent in EN and PT) and a cold EN + PT drive (`rv82b`) of Settings, the months badge + tooltip, the July card-fix select (opened, Escape, nothing picked) and the FX panel.
2. This checkpoint: p1 status rows for items 73/74/77/80/81 corrected from "pending owner paste" to applied (PROMPT-STATUS since PR #924), and 82/87/89 to applied (PR #954).

---

## Key Decisions Made

### ECB rung sits below the self-derived rates
- **Choice:** typed Settings rate > statement FX lines > receipts' booked rates > ECB month.
- **Rationale:** a statement's FX line is the rate the card charged; on the bundles the receipts' own rates beat the ECB 70 to 68. Hosted months have neither, so the ECB is what fires there.

### Key the rate by the charge's month, store the ECB table as published
- **Choice:** units per EUR by month, cross computed at lookup, nearest month when absent.
- **Rationale:** card networks lock the rate at authorization; the raw table covers any currency (a 2024 bundle is DKK) and a month created before its average is published.

### Ship inert rather than re-match
- **Choice:** leave July/August on their frozen Settings rates; no live write.
- **Rationale:** the no-live-writes rule, and the simulation showed the ECB at 3% would cost July one right pair and add two coincidental auto-matches.

### Owner ruling: band first, then remove the Settings rates (item 90)
- **Choice:** tighten the ECB clean band as its own item, then remove EUR:USD 1.162275 and BRL:USD 0.192448 on a per-action yes.
- **Rationale:** a 2% band under ECB rates measured July 32 right (vs 30) with the six bundles held at 70.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/web/ecb_rates.py` | created | ECB fetch + CSV parse, fail-open |
| `.../src/expense_recon/matching/deterministic.py` | edited | table field, `ecb_monthly_rate`, rung, reason phrase |
| `.../src/expense_recon/web/service.py` | edited | fetch at create/attach, lookup `on=`, `reference_rate_period`, advisory |
| `.../tests/test_ecb_month_rates.py` | created | 14 route + unit tests |
| `.../tests/conftest.py`, `test_view_contract.py`, `test_fx_breakdown.py` | edited | network stub, period contract, stub signature |
| `.../docs/api-contract.md`, `lovable-ecb-rates-prompt.md`, `PROMPT-STATUS.md` | edited/created | contract, SPA prompt, applied ledger |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edited | item 82 simulation + shipped, Shipped row 56, item 90 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edited | item 82 row; eight stale "pending paste" labels corrected |

---

## Current Status
Backend v144 live. The ECB table reaches a month at creation and statement attach, but the two typed Settings rates win for EUR and BRL on every month, so no live FX block reads `ecb_month` yet and the SPA's ECB label has no live case. PROMPT-STATUS Not-applied table is empty. brisken ops status: platform unknown (no infrastructure assessment); comms-log none.

---

## Next Steps
1. Item 90 in a fresh session (backlog item 90 carries the build order).
2. After item 90 ships: per-action owner yes, then remove the two Settings rates; first new month matched on the ECB is the live case for the SPA label.
3. Triage feedback notes #52-54 (2026-09-16 22:23-22:27 UTC) into the backlog.
4. PT wording for the months badge ("Comparado com o extrato") and the Matching card ("Conciliadas") to Criss via the owner.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 82 and 90)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `docs/optimize/brisken-recon-tuning-v1/SUMMARY.md` (refuted levers, before touching `fx_reference_match_pct`)

### Open Questions
- Item 90: an ECB-only knob (leaves the scorer asset and the shared band untouched) or the shared `fx_reference_match_pct`?

### Working Notes
- Simulate a rate change by rewriting `runs.config.matching` in a DB copy, then `load_live` from the attribution tool; to simulate the charge-month keying before building, wrap `deterministic.match_one` (match_month calls it by module global). The shipped code with Settings rates removed and the ECB table in config reproduced that simulation exactly, so the same DB-copy method is valid for item 90.
- A rate that moves pairs into the band also moves RIVALS in: the uniqueness gate, not the deviation, decided every July change (`0067` lost to JoseliMariaDos 8.40; `0034` gained when its rival MP *24HBEBIDAS 24.88 fell out). Read `trace_candidates(...)["cands"][(tx, doc)]["rivals"]` before explaining a move.
- `0034` Erste Fracht vs HOTEL AM TIERGARTEN 24.02 sits at +0.2% under the ECB rate: no band fixes it.
- Windows traps this session: Windows Python needs `C:/...` paths; extract archives under a short path (`.scratch/` in a worktree), not the scratchpad (MAX_PATH); `pytest -n` is unavailable (no xdist); the first `agent-browser open` of a new named session can hang, a retry with `timeout 90` works; `wait --text` loses its daemon connection on this SPA, read state with `eval` on a `setTimeout` promise; Radix tooltips open only on dispatched pointer events, not `hover`.

### Reference Materials
- ECB Data API wildcard: `https://data-api.ecb.europa.eu/service/data/EXR/M..EUR.SP00.A?startPeriod=YYYY-MM&endPeriod=YYYY-MM&format=csvdata&detail=dataonly`
- PRs #951, #952, #953, #954

---

## How to Continue
Fresh session, own worktree off origin/main per the round protocol, then item 90: pull a fresh DB copy, rebuild the driver (the scratch copy was deleted with the worktree; the method is in Working Notes), measure 3% / 2.5% / 2%, report, build.

---

## Strategic Feedback

### What Worked Well This Session
- Proving the instrument before trusting its result: the replay reproduced the hosted outcome (parity 0) before any variant was read, and the shipped code was re-run against the simulation afterwards (empty diff). The negative finding (no right pair gained) was therefore reportable with confidence rather than suspected as a harness bug.

### Suggestions
- Keep the simulation driver as a tool: `tools/recon-rate-sim.py` (variants: stored config, rates replaced, rates keyed by charge month, band override) would make item 90 and any later matcher-input change a one-command before/after instead of a rebuilt scratch script.

### System Health
- Hooks caught every shell trap (heredoc, cd-guard, MSYS) but the same traps recur across same-day sessions; the unresolved register row is now a triple recurrence.
- Autonomy: 2 human interventions (the Settings-rates ruling and the Lovable publish, both owner-only).

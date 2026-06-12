# Checkpoint: Brisken Reconciliation Parameters

**Date:** 2026-06-12
**Status:** Matcher core calibrated + parameters locked (LD-5). All ungated/un-blocked matcher work done. Remaining work gated on a reconciled ground-truth month from Chris + Dirk data exports.

---

## Summary

Continuous session that took the Brisken expense-recon matcher from "3b
calibration blocked on bank data" to a fully calibrated, parameter-locked
matching engine. The Chase 6-card activity export (2026-06-11) and three
real travel months WITH receipt scans (2026-06-12) unblocked the
calibration; shipped the FX emission gate, bipartite assignment,
vendor/reference signal, the transaction-centric Summary fix, a calibrate
subcommand, and the locked pairing parameters (LD-5). Owner confirmed
all-USD cards + standalone architecture.

---

## What Was Done This Session

### Matcher build + calibration (8 PRs, all merged CI-green; main 96e6412)
1. **PR #122** — slice 3b calibration record (first run on 3 real months).
2. **PR #123** — slice 3.7: FX_JUDGMENT emission gate (date + implied-rate band). Cut Needs-Review pair-rows 19–21x.
3. **PR #124** — A9: report Summary made transaction-centric (was rendering $8.8K month as $1.26M + false "invariant BROKEN").
4. **PR #125** — restored the rich 2026-06-11 session log over an EOD auto-stub (process race, no data lost).
5. **PR #127** — slice 3.8 + 3.9: bipartite receipt assignment (no double-binding) + vendor/reference tie-break signal (stdlib difflib). Hit the ≤2x FX-multiplicity acceptance criterion.
6. **PR #128** — E8: `expense-recon calibrate` subcommand (metrics + regression gate) + dry-run review-count fix.
7. **PR #129** — Session 5 log final update.
8. **PR #130** — LD-5: monthly reconciliation pairing parameters (all-USD-card model); DKK band added, EUR/BRL bands widened for DCC+tip; A6 closed; infrastructure.yaml STANDALONE + ALL-USD.

### Decisions recorded
- Architecture = **standalone** (Dirk confirmed Path A, 2026-06-12).
- Currency model = **all-USD cards** (no EU/UK card ever).

---

## Key Decisions Made

### Standalone architecture (Path A) confirmed
- **Choice:** Tool stays a standalone pipeline — ingests Zoho Expense CSV + bank CSV, matches/classifies in its own tables, pushes journal-entry export to Books carrying receipt URLs. Books API is the one write boundary only.
- **Rationale:** Path B (automate inside Zoho) optimizes the system Brisken plans to leave; standalone survives the Zoho switch-off and is mostly already built. See `context/2026-06-11-path-recommendation.md`.

### All cards settle in USD
- **Choice:** Layer-2 account-card currency is always USD; every non-USD receipt (BRL/EUR/DKK) is an FX pair. No per-region card profile.
- **Rationale:** Owner-confirmed. Closes ANNEALING A6 (its premise — EU tips 0–12.5% — is also wrong: the US cardholder tips up to 16.7% in the EU).

### FX band shape: tight-low, generous-high
- **Choice:** EUR→USD [1.00, 1.45], BRL→USD [0.15, 0.26], DKK→USD [0.13, 0.18].
- **Rationale:** DCC markup (measured +3.5%/+5%/+12.8%) compounds with a card tip (to +16.7%); both only push the charge up. Widening cost zero precision — bipartite caps each receipt to one tx, vendor signal picks. Verified: FX multiplicity unchanged at 0.95–0.98x.

### DCC receipts match same-currency exact
- **Choice:** Dirk's rule "prefer the receipt's printed USD" is upstream of the band: OCR captures the DCC USD amount, the pair becomes same-currency USD, matches exact, never reaches the FX band. Never trust Zoho's internal per-line rate (off up to 12.8%).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| automations/expense-reconciliation/src/expense_recon/matching/deterministic.py | Modified | FX emission gate (3.7), bipartite match_month (3.8), vendor/reference signal (3.9), LD-5 bands (DKK + widened EUR/BRL) |
| automations/expense-reconciliation/src/expense_recon/output/report_xlsx.py | Modified | A9: transaction-centric Summary (`_Row.transaction_id`, Spend from statement) |
| automations/expense-reconciliation/src/expense_recon/calibrate.py | Created | E8 `calibrate` subcommand (metrics + regression gate) |
| automations/expense-reconciliation/src/expense_recon/cli.py | Modified | route `calibrate`; dry-run review-count fix |
| automations/expense-reconciliation/tests/test_deterministic_matching.py | Modified | FX-gate, bipartite, vendor-signal, DKK/tip+DCC band tests |
| automations/expense-reconciliation/tests/test_report_xlsx.py | Modified | A9 regression test |
| automations/expense-reconciliation/tests/test_calibrate.py | Created | 6 calibrate tests |
| automations/expense-reconciliation/BLUEPRINT.md | Modified | 3b calibration block; 3.7/3.8/3.9 shipped; LD-5 pairing parameters |
| automations/expense-reconciliation/ANNEALING.md | Modified | A1/A2/A3 resolved, A4 status, A9 resolved, A6 closed, E8 partial |
| automations/expense-reconciliation/README.md | Modified | `calibrate` subcommand docs |
| infrastructure.yaml | Modified | platform_decision STANDALONE, currency_model ALL-USD |
| context/2026-06-11-expense-report-samples.md | Modified (git-ignored) | DCC/tip calibration evidence; mode→card revision (1672 = primary travel card) |

---

## Current Status

Matcher core is calibrated and parameter-locked. Test suite **189 passed / 2 skipped**. Acceptance criteria MET on real data: FX ≤2x cross-currency-receipt count, no double-bound receipts, zero stack traces/parse errors, Summary Spend reconciles to the statement to the cent. main at `96e6412`.

No `platform` section in infrastructure.yaml (it's a standalone Python CLI, not a workflow engine) — no ops-audit applicable.

---

## Next Steps

1. **Highest-value unblocker — one reconciled month from Chris.** Turns the calibrate subcommand's coverage numbers into real accuracy numbers and lets the bands be tuned against ground truth instead of receipt-inferred values. This is the single thing gating real accuracy validation. (Parked: outbound to Chris/Dirk needs explicit user ask — do not draft unprompted.)
2. **Chart-of-accounts export + one Zoho Expense CSV** from Dirk — settles the receipt-URL field question for the standalone receipt-hosting design and feeds the Expense-CSV ingest adapter.
3. **BLUEPRINT slice-map realignment for standalone** (now that Path A is confirmed): Expense-CSV ingest adapter, bank-statement table w/ dedup, reports table (4–5 fields), receipt-URL hosting. See path-recommendation doc §"What Path A changes".
4. **Extended calibration (optional cross-check)** — the Chase xlsx contains the bank side for the 3 new travel months (Oct-24/Nov-24/Jun-25); slice them + the ER lines for a DKK/EUR DCC cross-check when wanted.
5. **Remaining 3b items, all data-gated:** 3.10 refunds (no refund-side receipts yet), 3.11 per-bank profiles (needs 2+ cards/run — but all-USD simplifies), 3.13 A4 window-tightening (needs reconciled month).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` — LD-5 (pairing parameters), slice 3b calibration block, slice map.
- `workspace/clients/brisken/automations/expense-reconciliation/ANNEALING.md` — resolved/closed items + remaining backlog.
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py` — MatchingConfig (param source of truth) + match_month bipartite.
- `workspace/clients/brisken/context/2026-06-11-expense-report-samples.md` (git-ignored) — all real-data calibration evidence (DCC/tip table, mode→card, missing-counterpart lines).
- `workspace/clients/brisken/context/2026-06-11-path-recommendation.md` — standalone rationale + Path A slice-map changes.
- `workspace/clients/brisken/infrastructure.yaml` — STANDALONE / ALL-USD decisions.

### Open Questions
- Does the Zoho Expense CSV export carry a receipt-URL field? Dirk-stated, docs-silent — one real export's header settles it (folds into the data request, not a separate ask).
- The 3 expense lines with no statement counterpart in any of the 6 cards (Ventilador BRL 3,099.99; an Apr fuel; a May Routex) — need Chris (other account, or non-card payment?).
- Payment-mode↔card mapping: now mostly resolved from receipt slips (mode1→1672, mode3→1672 on slips, mode5→3645, mode6→0340); confirm with Chris.

### Working Notes
- `%TEMP%\brisken_3b_calibration.py` is the matching-calibration harness (parses ER PDFs from `context/expense-reports/`, slices the Chase xlsx, runs the engine). `%TEMP%\brisken-3b\` holds the generated run configs/CSVs/reports. Not committed; the matching half is now also a real subcommand (`expense-recon calibrate --config X`).
- To re-run calibration: `uv run "%TEMP%\brisken_3b_calibration.py"` then `uv run --directory <pkg> expense-recon calibrate --config %TEMP%\brisken-3b\run-2026-03.json`.
- Matcher results on the 3 admin months are honest-low (Matched 1/0/1) because ~97% of admin-bucket lines are foreign-currency → FX_JUDGMENT (LLM territory), and many USD subscriptions have no receipt in the ER sample. This is correct, not a bug; real accuracy needs Chris's reconciled month.
- 1672 finding: it's Dirk's PRIMARY travel card (all over 2024–25 EU slips), not retired — it just had no charges in the 2026 admin export window. Revises the earlier "likely reissued" note.

### Reference Materials
- PRs: #122, #123, #124, #125, #127, #128, #129, #130 (all merged).
- Repo: 011matthias/agentic-ops1.01, main `96e6412`.

---

## How to Continue

The matcher is done pending real ground truth. Two paths for the next session:
(a) If Chris/Dirk data has arrived: ingest the reconciled month, run `expense-recon calibrate`, tune bands against true accuracy, then start the standalone slice-map realignment (Expense-CSV adapter, bank-statement table, reports table, receipt-URL hosting).
(b) If no new data: pick up the standalone realignment design (BLUEPRINT slice map) which doesn't need the reconciled month, OR run the optional extended calibration on the 3 new travel months.
Do NOT draft outbound to Chris/Dirk without an explicit user ask.

---

## Strategic Feedback

### What Worked Well This Session
- Dropping the real ER PDFs *with receipt scans* was the unlock — every band value now traces to a measured DCC markup or tip, not a guess. The "give me the real artifact" pattern beats describing the data.
- "Do what needs to be done" + the CI-gated auto-merge let the full 8-PR chain run without per-step approval; each piece was verified on real data before shipping.

### Suggestions
- The single highest-leverage next input is one reconciled month from Chris (her past receipt↔transaction pairings). It costs her nothing beyond a standard export and converts every "coverage" number in the tool into a real "accuracy" number.

### System Health
- The `expense-recon calibrate` subcommand now operationalizes what was a recurring %TEMP% script (E8 friction retired for the matching half; OCR-coverage half still a temp script).
- Autonomy score: 0 — fully autonomous session (the one B1 stop-hook deferral on 2026-06-11 was already logged in Session 5; the LD-5 portion had zero corrective interventions). The A12-reference slip was self-caught via grep before ship.

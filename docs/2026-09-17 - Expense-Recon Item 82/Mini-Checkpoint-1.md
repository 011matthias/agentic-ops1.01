# Mini-Checkpoint: Expense-Recon Item 82

**Date:** 2026-09-17
**Status:** Item 82 shipped and live (PR #951, merge `17e1501c`, Fly v144), inert on July and August by design; SPA prompt and one owner decision pending
**Type:** mini

---

## Summary
Item 82 was simulated before it was built. ECB monthly rates are more accurate but buy no correct pair on the live months. It was then built as ruled, so a month with no typed rate matches on the ECB average for each charge's month; July and August keep their frozen Settings rates.

## What Was Done
- **Live read.** Feedback store holds 54 notes, not the handoff's 51: #52-54 (owner, 2026-09-16 22:23-22:27 UTC) ask to view set-aside PDFs, whether dropped receipts sort into months, and that a receipt arriving in a matched month gets the full process. None concerns FX; not triaged. Settings rates BRL:USD 0.192448, EUR:USD 1.162275; July 25 and August 3 FX candidates, all `settings`.
- **Simulation** (DB + learning copies and 103 receipt files off the volume at v143; driver imports `tools/recon-match-attribution.py`'s own `load_live` / `attribute`). Instrument first: parity 0 and 0 cache misses at Settings rates. ECB July 1.141748 / 0.195341, August 1.159310 / 0.194241. July's 22 labelled FX pairs: mean deviation 1.78% -> 0.44%. Buckets: August unchanged; July `0067` MARINHO clean -> review (rival JoseliMariaDos 8.40 enters the 3% band), `0034` Erste Fracht and `0066` Mega Center (labelled excluded, notes name other merchants) become auto-matches (`0034` lost its rival MP *24HBEBIDAS 24.88, traced). Bundles (determ-correct / wrong / composite): shipped self-derived 70 / 0 / 76.0, one Settings rate 64 / 3 / 65.2, ECB 68 / 0 / 74.3. Label-month and charge-month keying identical. ECB + 2% clean band: July 32 right, bundles 70 / 0 / 75.7 (measured only).
- **Build (PR #951).** `matching.fx_ecb_monthly_rates` (ECB table as published, units per EUR, 29 currencies, one wildcard request `EXR/M..EUR.SP00.A`) fetched fail-open (4 s) at company-month creation and statement attach / re-read, never for trips. `MatchingConfig.ecb_monthly_rate` crosses through EUR for the charge's month, nearest month when absent. Rungs: typed > statement > receipts > `ecb_month`. `fx.reference_rate_period`; advisory no longer asks for a hand-typed rate. conftest stubs the fetch suite-wide. Prompt `docs/lovable-ecb-rates-prompt.md`, PROMPT-STATUS Not applied.
- **Proof.** Suite 1983 -> 1998 / 2 skipped; CI green incl. `test`. Regress: matcher call site (4 red), view lookup (4 red), attach fetch (outage test red), creation fetch (created test red). Scorer 70/95, SCORE 76.0; guard 4/4. On the shipped code: July/August parity 0 with frozen rates; with Settings rates removed it reproduces the simulated charge-month result exactly.
- **Live (v144).** The machine reaches the ECB (0.51 s, 29 currencies). Both months: 0 FX-block and 0 summary diffs vs the pre-deploy payloads, `updated_at` unchanged. Cold drive `recon-item82`: July AMAZON panel reads `Reference rate 1.162275 (USD per EUR) · Settings`, Receipt in USD 320.88, -5.32 (-1.66%); `0034` and `0066` still under Receipts without a charge; August 111 charges, no fallback; Settings shows the old copy.

## Current Status
Backend live at v144; nothing on Criss's months moved. The two Settings rates also win for every new month, so the ECB fires today only for a currency Settings does not hold. brisken ops status: platform unknown (no infrastructure assessment); comms-log none.

## Next Steps
1. Owner decision: remove the two Settings FX rates so new months use the ECB (July and August stay frozen either way).
2. After the owner pastes `lovable-ecb-rates-prompt.md`: bundle audit for `reference_rate_period`, `wb.fx.source.ecbMonth`, the new `set.fx.desc`.
3. Owner call: a 2% clean band under ECB rates as its own item (July +2 right, `0067` kept, bundles 70).
4. Triage feedback notes #52-54 into the backlog.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 82 simulation block; Shipped row 56)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-ecb-rates-prompt.md`

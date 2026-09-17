# Mini-Checkpoint: Expense-Recon Item 87

**Date:** 2026-09-17
**Status:** Four published prompts verified applied; item 87 shipped and live (Fly v143); item 89 prompt written; item 82 not started
**Type:** mini

---

## Summary
The owner's four 2026-09-16 prompts are applied in production and render as specified. A receipt that prints no usable card now gets a card picked on its own row, remembered for the vendor at Publish.

## What Was Done
- Feedback store still 51 notes (last 2026-09-16 16:16:06 UTC). Payloads matched the handoff exactly; memory 103 categories, nothing published.
- **Prompts verified (PR #943, merge `b417a9f3`).** Bundle 48 chunks / 1,047 KB, controls hit, 15 of 15 names. Cold drive `rv917`, EN + PT on both months, 236 GET / 7 OPTIONS / 0 writes. August reason lines 1 / 4 / 4 / 1 with "Why:" adding to 10, 11 copies in the fold; July GOOGLE Workspace "paired with another charge"; July tiles list exactly 49 / 3 / 14 / 33 / 24; "Show 48 booked rows" with the yellow / grey tooltip, no underline classes. Matched's fold reads "31 decided" (3 grey rows), correct by the prompt's own rule. Item 88's toast is bundle-only.
- **Item 87 read.** The "month only" notice is true where it shows (generic tenders). Two strip assignments said `learned: true` and never resolved again: "Paid via Corp Services card" (four cards alias "Corp") and "42463153XXXXXX38" (masked BIN taught as a digit `_card_keys` skips). 24 of July's 33 no-company rows had no path but Confirm private: 16 tender words, and 8 with no card, which sit outside the strip.
- **Item 87 build (PR #947, merge `08a240cc`, Fly v143).** `card_key` header field (active registry card, copied into the month snapshot when defined later; off the event loop), `expenses[].card_source` hint / override / learned / none, `Receipt.card_key` filled from a vendor field correction learned at Publish and applied only when the hint carries no card digits. `resolve_card`: a unique whole-string alias beats shared word aliases (the first draft broke on a card holding both; its unit test caught it). `learnable_hint_tokens` skips mask-followed runs. Suite 1974 -> 1983 / 2 skipped. Seven regress proofs bite; the route one printed no pytest summary and was reproduced by hand (unknown card 200 instead of 400).
- **Live after deploy.** The only payload change is `card_source`: July 19 hint / 33 none, August 18 / 13; summaries, card strip and memory unchanged. Cold drive `rv87`: July Expenses 52 rows, same tiles, 19 card chips, no fallback, 0 writes.
- **Item 89 (owner mid-session, screenshot).** The green "Reconciled" badge is `/months`' Statement column, shown whenever `has_statement`. Prompt `lovable-matched-with-statement-prompt.md`: "Matched with statement" + tooltip.

## Current Status
Backend live at v143. Pending the owner's paste (PROMPT-STATUS Not applied): `lovable-card-fix-prompt.md` (87), `lovable-matched-with-statement-prompt.md` (89). No card fix exists on Criss's months, so nothing moves until someone picks a card and publishes. brisken ops status: platform unknown (no infrastructure assessment); comms-log none.

## Next Steps
1. Item 82 in a fresh session: sftp a copy of `recon-web.sqlite`, replay July and August plus the six bundles with `tools/recon-match-attribution.py` at the Settings rate vs ECB monthly rates (EXR/M.USD.EUR.SP00.A, EXR/M.BRL.EUR.SP00.A, BRL:USD cross), report bucket changes against `labels.csv` before building. Owner ruling (do not re-ask): per month, ECB, typed rate wins.
2. After the owner publishes the two prompts: bundle audit on `card_source`, `expx.cardFix.pick`, `expx.cardFix.source.learned`, `expx.cardFix.boxHint`, `months.state.matchedStatement`, `months.state.matchedStatement.tip`; cold drive (open a card select and Escape it, never pick on Criss's month).
3. Ask Criss (via the owner) for the PT badge wording and whether the Matching card's PT "Conciliadas" should also change.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 87, 89, 82; Shipped row 55)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (the 2026-09-17 re-audit, Not applied)

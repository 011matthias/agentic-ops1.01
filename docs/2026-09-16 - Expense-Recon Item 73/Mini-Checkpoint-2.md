# Mini-Checkpoint: Expense-Recon Item 73

**Date:** 2026-09-16
**Status:** Backend shipped and live (PR #905, merge `f07adcf3`, Fly v136); SPA prompt pending owner paste
**Type:** mini

---

## Summary
Backlog item 73 (note #42) shipped: every run row now carries `row_type` (purchase / payment / refund / reversal / fee / interest) and `entity_source` (card / batch / none), so the Chase card payoff reads `payment` instead of printing under "Refund". Matching, buckets and counts are unchanged.

## What Was Done
- Live read first. Both months hold exactly one credit, the "Payment Thank You-Mobile" payoff (July -9,664.81, August -7,823.16). Both workbooks carry a Type column (July 111 Sale + 1 Payment, August 109 Sale + 1 Payment + 1 Fee). All 9 runs on the volume were read read-only: no other `is_credit` row exists.
- The item's secondary claim did not reproduce. The payoff row printed card 2838 (`card_last4: "2838"` on the stored charge), and "Corporate Services" came from the registry via item 59, not from the upload. `entity_source` shipped anyway; it reads `card` on every live row.
- Parsers (xlsx + csv) stamp `Transaction.row_type` from a recognised Type label. `ingest/_common.row_type_of` falls back to the sign. Snapshots stored before the field read the Type cell back out of `raw_text` with `ast`, never evaluated. This was checked against the exact stored raw text of both live payoff rows before deploy, so no re-read was needed.
- `month_health` skips card payments. The reconciliation PDF prints "card payment". The report workbook's credits section gains a Type column, and CLI `--explain` labels PAYMENT / REFUND / REVERSAL.
- Tests: `tests/test_row_type.py` (11, route-level) plus a contract pin. Suite: 1832 before; 1887 passed / 2 skipped after merging items 79, 80 and 81. Eight `regress_check.py` proofs all went red first: view wiring, entity_source, raw_text read-back, xlsx label, csv label, health skip, PDF label, workbook Type cell.
- Post-deploy diff of both live payloads against pre-deploy copies: the only change is the two new keys on every row (July 111 purchase + 1 payment; August 109 purchase + 1 fee + 1 payment). Live reconciliation PDFs print "Payment Thank You-Mobile -9,664.81 USD card payment" (and the August equivalent). The SPA was driven cold through the login gate (`agent-browser --session recon-item73`): the "Credits on the statement" view renders the payoff row with no error and no fallback string. There is no type chip yet, because the renderer is the pending prompt.
- Merge conflicts with items 79, 80 and 81 were all append-vs-append, and both sides were kept. Item 81 took Shipped row 47, so item 73 is row 48.

## Current Status
Live on v136. Lovable half `docs/lovable-row-type-prompt.md` is in PROMPT-STATUS Not applied. Until it is pasted, the page shows the payoff under "Credits on the statement" with no "Card payment" chip. brisken ops: platform plan unknown in `infrastructure.yaml`.

## Next Steps
1. The owner pastes `lovable-row-type-prompt.md`. Then run `uv run tools/lovable-bundle-audit.py` for `row_type` / `entity_source` / `wb.rowType.payment`, and browser-drive July (payoff shows "Card payment", company tooltip names card 2838) and August (the ANNUAL MEMBERSHIP FEE row shows "Card fee").
2. Continue the wave in the ruled order: 74, 75, 77, then 82.
3. Open, not built: the payoff row still shows category "ASSIGN" and a disabled "Confirm match" (a card payment needs no category). Raise this with item 76/79's row handling rather than widening 73.
4. Open, not built: a PDF statement has no Type label, so a payoff there still reads `refund`. No live PDF month exists.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (section "What a statement line is ... (item 73)")
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-row-type-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 73 + Shipped row 48

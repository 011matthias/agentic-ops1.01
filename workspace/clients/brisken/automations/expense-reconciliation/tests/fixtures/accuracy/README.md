# Accuracy fixtures (backlog item 127)

Synthetic labelled bundles for `tools/recon_accuracy_check.py ci`, replayed
by the pinned scorer (`tools/scorers/recon-match-accuracy.py`) under
`config/match-tuning.json` and pinned field by field in `expected.json`.
Every vendor, amount, date and card is invented; nothing here comes from
Brisken data. Labels were produced with `expense-recon label propose` /
`accept` / `check` (the `human` rows are the decisions a reviewer would
take), so the transaction ids are the content-derived ids the parsers assign.

| bundle | readers | row classes |
|---|---|---|
| `usd-card-2026-05` | statement CSV with a Type column; receipts `csv` source | E2 same-currency exact (r-01). E4 reference hit with a tip, resolved PROBABLE (r-02: the statement text carries `INV-77812`, charge 36.20 vs receipt 31.50). no_charge receipt 3.3% off a different merchant's charge, held off by the vendor floor (r-03 vs GRANITE PEAK HOTEL). Two identical charges either side of one receipt (r-04, `excluded`: Post Date blank on both ORBIT rows so each sits one day away; the matcher binds it to the first charge in statement order, which is why a confirmed label here would be a guess). One charge with two identical receipts, the matcher's own ambiguous bucket (r-05 confirmed, r-06 `excluded`). Refund row (NORTHWIND STATIONERY, Type `Return`). Unmatched purchase (METRO TRANSIT). Plain no_charge (r-07). EUR receipt on the USD card through the profiled EUR:USD band, deferred, hand-confirmed with no evidence tier (r-08). |
| `eur-card-fx-2026-06` | statement CSV with original-amount columns; receipts `expense_csv` source with `amount_base` | E1 original-amount pairs in USD and GBP (f-01, f-02). E3 base-amount inside the 1% band (f-03, 0.54%). E3 base-amount in the review zone, deferred (f-04, 1.55%: the row that moves when `fx_base_amount_match_pct` is widened to 2%). Unprofiled USD:EUR band pair, deferred, hand-confirmed (f-05). no_charge receipt whose base is 4.6% off a nearby charge, deferred and not matched (f-06). E2 same-currency EUR pair (f-07). Refund row (Type `Return`). |

Absent on purpose: a `determ_wrong` row (a confirmed label the matcher
mis-files; the gate proves that axis by mis-pointing a label in a scratch
copy), a card-scoped pair (no payment mode or card column), a configured or
ECB reference rate, and a self-derived rate (no `exchange_rate` column, so
the receipt-median path never fires). To add a class: add rows, re-run the
label flow, then `ci --write-expected`, and review the `expected.json` diff.

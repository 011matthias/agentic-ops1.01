# Examples — copy-paste starting point

Three files that work as a self-contained run, so a first-time user
can verify the tool works on their machine in under a minute.

```bash
cd workspace/clients/brisken/automations/expense-reconciliation

uv sync                                            # one-time install
uv run expense-recon --config examples/run.example.json
# Wrote report: examples/report.xlsx
```

Open `examples/report.xlsx` to see the 5+N sheet structure:

- **Summary** — totals, source breakdown (LINE / VENDOR ⚠ / REVIEW), by-card and by-category × by-card matrix
- **amex-9001** — chronological per-card tab with per-line-item rows + category subtotals + card total
- **Needs Review** — Tier 2 (vendor fallback) + Tier 3 (review) rows pulled together
- **Unmatched** — `STAPLES NYC` (no receipt provided)
- **Errors** — empty (clean run)

## Dry-run preview before writing xlsx

```bash
uv run expense-recon --config examples/run.example.json --dry-run
```

Prints counts to stdout, skips the xlsx write. Useful when onboarding
a new bank format to confirm the column map is right before committing
to a full run.

## Guessing the column_map for a new bank

```bash
uv run expense-recon-inspect path/to/your-new-bank.csv
```

Reads the header row and prints a suggested `column_map` block ready
to paste into your `run.json`. If a required field can't be guessed,
the output lists the available headers so you know what to map by
hand. Heuristics cover common English + DE bank exports today; if
your bank's headers aren't recognised, the inspect output still lists
them so you can map manually.

## What to change for your own run

Edit `run.example.json`:

1. `statement.path` → your bank export file (`.csv` or `.xlsx`)
2. `statement.column_map` → match your bank's actual header names
3. `statement.account_id` → identifier for this card (drives the tab name)
4. `statement.account_card_currency` → currency of the card
5. `receipts.path` → your receipts CSV (slice-1 bridge until OCR lands)

## Receipts CSV column reference

| Column | Required | Notes |
|---|---|---|
| `document_id` | yes | unique across the run; duplicates land in Errors sheet |
| `detected_date` | yes | ISO `YYYY-MM-DD` or `MM/DD/YYYY` / `DD/MM/YYYY` / `YYYY/MM/DD` |
| `detected_total` | yes | accepts `$`, `,`, `(50.00)` accounting negative |
| `detected_vendor` | yes | matched against statement's Description/Vendor column |
| `detected_currency` | no | uppercased; falls back to `receipts.default_currency` from config |
| `detected_reference` | no | reservation number, order id, etc.; surfaces in the report |
| `line_items` | no | JSON array string. Each item: `{"description": "...", "line_total": "...", "quantity"?: ..., "unit_price"?: ...}`. Empty/missing triggers the BLUEPRINT LD-2 Tier 2 vendor-fallback categorization |

## Errors sheet behavior (BLUEPRINT B1)

A single malformed row no longer aborts the run. The bad row lands in
the Errors sheet (file + line number + message), and surrounding rows
still parse and reconcile. Example:

```text
Errors
File          Line  Error
receipts.csv  3     Unrecognized date format: 'not-a-date'
receipts.csv  7     duplicate document_id 'rcpt-001' (also on row 2)
statement.csv 12    Not a number: 'see attached'
```

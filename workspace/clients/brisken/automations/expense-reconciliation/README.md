# Brisken Expense Reconciliation Platform — Build

Project ID: `p1`. Functional spec (binding):
[`../../specs/1-spec/p1-expense-reconciliation-functional-spec.md`](../../specs/1-spec/p1-expense-reconciliation-functional-spec.md).

## What this is

The build of the multi-tenant AI-assisted expense reconciliation SaaS
described in the v2 functional spec.

**North star (Dirk, 2026-05-25):** reduce Chris's monthly reconciliation
grind from days to minutes. The matching engine is the single
highest-leverage piece for that goal, so the build starts there even
though it sits at Phase 4 in the v2 spec §32 phase ordering. Phase 4
is pure logic — no stack dependencies — so it can ship ahead of the
Phase 0 foundation that still waits on the §38 stack decision.

## Where the build is right now

**Phase 4 — Deterministic matching engine: shipped, tested green.**

- [x] Domain types ([`src/expense_recon/matching/types.py`](src/expense_recon/matching/types.py))
  - `Transaction`, `Receipt`, `Match`, `MatchOutcome`, `MatchType` enum.
  - Three-currency-layer fields (transaction / account-card per v2 spec §20).
  - Legal-entity + tenant scope fields wired in (v2 spec §4.2, §23).
- [x] Deterministic matcher ([`src/expense_recon/matching/deterministic.py`](src/expense_recon/matching/deterministic.py))
  - USD-on-USD common case returns `EXACT` match at 0.99 confidence
    (Dirk's call baseline).
  - Purchase-date vs posting-date tolerance (weekend / bank-delay window).
  - Restaurant-tip tolerance configurable; default 20% (probable, requires review).
  - EUR-on-USD-card short-circuits to `FX_JUDGMENT` for the LLM layer
    (v2 spec §15.2).
  - Ambiguous (tied candidates) surfaced, never auto-picked.
  - Legal-entity scope enforced at the candidate-pair level.
  - Reconciliation guarantee invariant (v2 spec §25.5) covered by test:
    every transaction lands in exactly one bucket; no silent drops.

**Phase 2 — Statement ingest (CSV + Excel): shipped, tested green.**

- [x] Shared helpers ([`src/expense_recon/ingest/_common.py`](src/expense_recon/ingest/_common.py))
  - `StatementParseError(line_number=...)` — same row-numbering convention
    across formats (header is row 1, first data row is row 2).
  - `parse_date` (ISO / MM-DD / DD-MM / YYYY-slash), `parse_amount`
    (tolerates `$`, `,`, `(50.00)` accounting negatives),
    `validate_required_map`.
- [x] CSV parser ([`src/expense_recon/ingest/statement_csv.py`](src/expense_recon/ingest/statement_csv.py))
  - `parse_statement_csv(path, column_map, account_id, legal_entity_id, account_card_currency) -> list[Transaction]`.
  - UTF-8-with-BOM tolerant (handles Windows-exported files).
  - Blank rows skipped (common at EOF); malformed rows raise with row number.
- [x] Excel parser ([`src/expense_recon/ingest/statement_xlsx.py`](src/expense_recon/ingest/statement_xlsx.py))
  - `parse_statement_xlsx(path, column_map, account_id, legal_entity_id, account_card_currency, sheet_name=None) -> list[Transaction]`.
  - Native datetime cells used directly; native float cells routed
    through `Decimal(str(value))` (avoids IEEE-754 binary noise on
    `Decimal(5.75)`).
  - String-typed cells fall back to the shared `parse_date` /
    `parse_amount` helpers (covers banks that export dates / amounts
    as text).
  - Optional `sheet_name` for multi-sheet workbooks; default reads
    the active sheet.
  - Bool cells in the amount column rejected explicitly (defends
    against the `bool` ⊂ `int` Python quirk).

**Tests:** 32 passing across the matching engine + both parsers
(see `tests/`). Both parsers have an end-to-end integration test that
runs CSV/xlsx → `parse_statement_*` → `match_month` and asserts the
reconciliation invariant.

**Still to do:**
- [ ] LLM judgment layer (stubbed pending Anthropic API access; v2 spec §38.2).
- [ ] Real-data validation against a Chris-supplied month.

**Phase 0 — Foundation:** waits on the §38.1 stack decision (Cloud SQL
+ Firebase services vs alternative). Code that depends on it (data
model migrations, multi-tenant middleware, RBAC enforcement layer)
starts when Dirk signs off on §38.1.

## Run the tests

```bash
cd workspace/clients/brisken/automations/expense-reconciliation
uv run --with 'pytest>=8.0' --with 'openpyxl>=3.1' pytest -v
```

Expected: 32 passed.

## Data we need from Chris (smallest viable set)

To validate the matching engine against a real Brisken month and tune
the tolerances away from synthetic defaults:

1. **One credit-card statement** in the exact CSV / Excel format she
   downloads today (any month with non-trivial volume).
2. **The folder of receipts** for that month, in whatever shape she
   stores them (images / PDFs / mixed).
3. **The chart of accounts / expense categories** she classifies
   against in Zoho today (export from Zoho is fine).
4. **Last month's reconciled output** if she's willing to share it.
   Her manual matches become the ground-truth benchmark for the
   engine's match rate and false-positive rate.

Receipts can be redacted (account number / address) before sharing.
No customer data is needed at this stage.

## Why start with the matching engine before Phase 0

The v2 spec §32 phase ordering is a clean theoretical decomposition,
but in practice three things make matching the right first move:

1. **It is the value prop.** Dirk's 99% claim and the ~15-min-from-days
   north-star both live or die in this code.
2. **It is stack-independent.** Pure Python logic; survives any §38
   decision unchanged.
3. **It de-risks the rest.** Running this against Chris's real month
   tells us whether the 99% baseline holds in the wild, which informs
   the size of the LLM judgment layer (§15.2) and the auto-approval
   policy progression (§14). Building Phase 0 foundations before knowing
   this would be premature optimization.

When Chris's data lands, the next session adds a CSV statement parser
(Phase 2 piece, also stack-independent), feeds the real month through
the matcher, and reports the actual match rate. That number drives
the next set of decisions.

## File layout

```
expense-reconciliation/
├── README.md                        # this file
├── pyproject.toml                   # uv project, Python >= 3.12
├── .gitignore
├── src/
│   └── expense_recon/
│       ├── __init__.py
│       ├── matching/
│       │   ├── __init__.py
│       │   ├── types.py             # domain types (Transaction, Receipt, Match, …)
│       │   └── deterministic.py     # v2 spec §15.1 engine
│       └── ingest/
│           ├── __init__.py
│           ├── _common.py           # shared StatementParseError + parse_date/amount
│           ├── statement_csv.py     # v2 spec §7.1 CSV parser
│           └── statement_xlsx.py    # v2 spec §7.1 Excel sibling
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   └── sample_amex_export.csv   # synthetic 7-row Amex shape
    ├── test_deterministic_matching.py  #  9 tests
    ├── test_statement_csv.py           #  9 tests
    └── test_statement_xlsx.py          # 14 tests, openpyxl fixtures in-memory
```

## References

- v2 spec: [`../../specs/1-spec/p1-expense-reconciliation-functional-spec.md`](../../specs/1-spec/p1-expense-reconciliation-functional-spec.md)
- Boundaries: [`../../PROJECT-BOUNDARIES.md`](../../PROJECT-BOUNDARIES.md)
- Call outcomes (decision extraction): [`../../context/2026-05-20-call-outcomes.md`](../../context/2026-05-20-call-outcomes.md)
- Call transcript: [`../../reference/2026-05-20-call-transcript.md`](../../reference/2026-05-20-call-transcript.md)
- Dirk's v1 functional doc: [`../../reference/2026-05-14-functional-spec-original.md`](../../reference/2026-05-14-functional-spec-original.md)

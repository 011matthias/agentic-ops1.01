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

**Slice 2 part 1 — LLM categorizer (OpenAI gpt-4o-mini): shipped 2026-06-01.**

Per the 2026-06-01 stack pivot, the LLM provider is OpenAI (was
Anthropic per §38.2). The `LLMClient` protocol in `src/expense_recon/llm/`
is provider-agnostic; swap class to swap provider.

- [x] `LLMClient` Protocol + `OpenAIClient` + `MockLLMClient`
      ([`src/expense_recon/llm/client.py`](src/expense_recon/llm/client.py))
- [x] `TokenUsage` + `CostTracker` per-run cost aggregation
      ([`src/expense_recon/llm/cost.py`](src/expense_recon/llm/cost.py))
- [x] Categorizer (`categorize_receipts(receipts, client=...)`) routes
      through the LLM when wired; falls back to keyword stub otherwise.
- [x] CLI reads `llm:` block from config, instantiates `OpenAIClient`
      with `OPENAI_API_KEY` env var.
- [x] Summary sheet displays "Estimated cost (USD)".
- [x] Bug fix in `_is_vague`: word-boundary matching (was substring;
      `"fee" in "coffee"` was silently flagging "coffee beans" as vague).
- [x] Live OpenAI smoke run: 4-receipt example reconciled for
      $0.00029 USD; "Coffee beans 2kg" correctly classified as
      Office Supplies & Consumables (keyword stub returned Meals due
      to the substring quirk).

**Still to do in Slice 2:**

- [ ] Slice 2 part 2: Receipt OCR / vision extraction (swap
      `parse_receipts_csv` for `parse_receipts_vision`). Real OpenAI
      gpt-4o vision call on receipt images → structured `Receipt`
      with line_items. Deferred until Chris's first receipt folder
      lands so the vision prompt can be tuned against real shapes.
- [x] Real LLM swap for FX judgment (`judge_fx_match`) — **done
      (D1b, 2026-06-06).** `LLMClient.judge_fx_match` + OpenAI and Mock
      implementations; the model FX-converts the receipt into the
      transaction currency and returns a same-purchase confidence +
      implied rate. Always routes to review; no-client path keeps the
      `[STUB]` Match. 8 tests in `test_fx_judgment_llm.py`. Not yet run
      against a live FX receipt (gated on Chris's data via Slice 2 part
      2).

---

**Slice 1 — End-to-end CLI tool: shipped, tested green.**

Wires the existing parsers and matcher into a runnable CLI that
produces an Excel review report. North-star posture (Dirk 2026-05-27):
"we just need a working tool — anneal quality through real-data use,
not architecture up front." The multi-tenant SaaS scaffolding is
deferred; this is one Python process per reconciliation run.

- [x] Receipts CSV ingest ([`src/expense_recon/ingest/receipts_csv.py`](src/expense_recon/ingest/receipts_csv.py))
  - `parse_receipts_csv(path, legal_entity_id, default_currency) -> list[Receipt]`.
  - Bridge for slice 1: receipts arrive already-extracted from CSV.
    Real OCR / Claude-vision extraction lands in slice 2; matcher
    contract stays identical, only this function gets swapped.
- [x] LLM judgment layer ([`src/expense_recon/matching/judgment.py`](src/expense_recon/matching/judgment.py))
  - **`judge_fx_match`: wired (D1b).** With an `LLMClient` it returns a
    real model verdict (same-purchase confidence + implied rate +
    converted amount). With no client it returns the `[STUB]` Match.
    `judge_ambiguous` is now wired too: the LLM breaks ties among
    candidates, the pick is annotated and promoted to the front, but
    every candidate stays in the bucket (no receipt dropped).
  - Reconciliation guarantee preserved: FX entries always carry
    `requires_review=True` and stay in `judgment_required` whatever the
    verdict; nothing is auto-resolved or silently dropped.
- [x] Excel report writer ([`src/expense_recon/output/report_xlsx.py`](src/expense_recon/output/report_xlsx.py))
  - Four sheets, fixed order: **Summary** (counts, % match rate,
    invariant check), **Matches** (EXACT green / PROBABLE yellow),
    **Needs Review** (FX / ambiguous / possible — orange),
    **Unmatched** (transactions + receipts — red).
  - Per-row PatternFill (no Excel CF rules engine) — file opens
    cleanly in any viewer.
- [x] CLI entry point ([`src/expense_recon/cli.py`](src/expense_recon/cli.py))
  - `expense-recon --config run.json [--out alt-report.xlsx]`.
  - JSON config (stdlib only — no YAML dep). Paths in the config
    resolve relative to the config file's directory.
- [x] `pyproject.toml` build system (hatchling) so `uv sync`
  installs the `expense-recon` script.

**Slice-1 annealing items (matcher quality, surfaced by integration testing):**

1. **FX cross-product noise.** The deterministic matcher generates
   an `FX_JUDGMENT` candidate for every (USD tx, non-USD receipt)
   pair regardless of amount or date — see the early-return in
   [`deterministic.py`](src/expense_recon/matching/deterministic.py)
   `match_one`. In real use this means one EUR receipt in the pool
   floods Needs Review with one entry per USD transaction. Fix
   direction: require date proximity AND amount-after-rough-FX
   plausibility before emitting `FX_JUDGMENT`.
2. **One receipt can match multiple transactions.** The matcher tracks
   `matched_receipts` for the unmatched-receipts residual but does
   not prevent the same receipt from being the best match for two
   different transactions. Slice-1 integration fixture avoids this
   by design; real data will hit it. Fix direction: bipartite
   assignment (e.g., Hungarian algorithm on the confidence matrix)
   so each receipt lands at most once.
3. **No vendor / reference signal in matching.** Amount + date +
   currency are the only inputs today. A $100 Amazon receipt and a
   $100 Uber receipt on the same day are equally good candidates
   for a $100 transaction. Vendor fuzzy match + reference-number
   check would tip the scoring.

These are matcher-behavior changes, not slice-1 plumbing. Defer
until real Chris data shows which one bites first.

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

**Tests:** 98 passing across the matching engine, both parsers, the
keyword + LLM categorizers, the FX + ambiguous judgment layers, the
inspect heuristic, the report writer (incl. the `--explain` sheet),
the Zoho export skeleton, the cost tracker, and the end-to-end CLI
both in-process and via subprocess (see `tests/`).
The CLI tests write inline statement + receipts fixtures into
`tmp_path`, run the full pipeline, open the resulting xlsx, and
assert the LD-2/LD-3/LD-4 contracts (per-line categorization,
5+N sheet structure, three-tier source coloring, Amazon multi-line
receipt → 3 distinct rows, vendor-fallback marking, FX always
routed to review) AND the B1 tolerant-parsing flow (bad rows land in
the Errors sheet without aborting the run, surrounding good rows
still reconcile) AND the B4 dry-run flow (Summary to stdout, no
xlsx written).

**Still to do:**

- [ ] Slice 2: receipt OCR / vision extraction (swap
      `parse_receipts_csv` for vision pipeline).
- [x] Slice 2: real `judge_ambiguous` LLM call — done (2026-06-07). FX
      (`judge_fx_match`, D1b) and ambiguous tie-break both wired.
- [ ] Real-data validation against a Chris-supplied month.
- [ ] Annealing items #1–#3 above (matcher quality), prioritized by
      what bites first on Chris's real data.

**Phase 0 — Foundation:** waits on the §38.1 stack decision (Cloud
SQL with Firebase services vs alternative). Code that depends on it
(data model migrations, multi-tenant middleware, RBAC enforcement
layer) starts when Dirk signs off on §38.1.

## Run the tool

```bash
cd workspace/clients/brisken/automations/expense-reconciliation
uv sync                                       # installs the CLI entry point
uv run expense-recon --config /path/to/run.json
uv run expense-recon --config run.json --out alt-report.xlsx   # output override
uv run expense-recon --config run.json --dry-run               # counts only, no xlsx
uv run expense-recon doctor --config run.json                  # pre-flight config check
uv run expense-recon calibrate --config run.json               # matcher metrics, no xlsx
```

## Testing mode (hosted, 2026-07-15)

While the tool is in testing, the hosted app (`brisken-expense-recon.fly.dev`)
runs a **role-split intake model** so Chris can use it without triggering
the pipeline:

- **User (Chris)** logs in with `EXPENSE_RECON_ACCESS_CODE` and only
  *uploads* documents (statement + optional receipts + a card picker).
  Nothing runs; the upload is saved and appears as "Received".
- **Operator (dev)** logs in with `EXPENSE_RECON_OPERATOR_CODE`, runs the
  pipeline from the intake queue, reviews, and **Publishes** the run back;
  the user then sees it as "Ready to review" and reviews it (no LLM
  involved in review). Operator-only surface: intake queue, run, Compare,
  Memory, publish.
- The server stays **API-free**: `tools/brisken-recon-notify.py` (run
  dev-side, `--once` after a publish or on a scheduled task) polls
  `/api/operator/state` and sends the Graph mails (new upload -> matthias;
  run ready -> Chris + matthias; new feedback -> matthias). No Graph creds
  on the box.
- **Anchored feedback**: every logged-in page carries the double-click
  widget (same pattern as the OnePilot prototype). A reviewer double-clicks
  any spot, or uses the floating Feedback button, and the note lands in
  `/data/feedback.jsonl` attributed to the session role, page, and run id.
  Operators read it at `/feedback-log` (nav tab) or `/feedback.jsonl`.

Card presets for the simplified upload live in `/data/cards.json` (env
`EXPENSE_RECON_CARDS`; shape in `examples/cards.example.json`); unset =>
a plain card-name text box (fail-open).

**Deploy** (Band-3, explicit order only):

```bash
fly secrets set EXPENSE_RECON_OPERATOR_CODE=<op> EXPENSE_RECON_ACCESS_CODE=<user> --stage
# author + upload /data/cards.json (real card list), then:
flyctl deploy   # from this module dir; the DB self-migrates on first open
```

Notifier env (dev-side, gitignored `../../context/.env`):
`BRISKEN_TENANT_ID`, `BRISKEN_GRAPH_CLIENT_ID`, `BRISKEN_GRAPH_CLIENT_SECRET`,
`EXPENSE_RECON_OPERATOR_CODE`, and `EXPENSE_RECON_NOTIFY_USER` (Chris's
email; the ready-ping is dev-copy-only until set).

## Browser UI (review workbench)

Chris does not have to hand-edit a JSON config or read the xlsx. The
same pipeline is wrapped in a web app (hosted per "Testing mode" above,
or run locally on loopback):

```bash
cd workspace/clients/brisken/automations/expense-reconciliation
uv sync --extra web                     # installs the web dependencies
uv run expense-recon-web                # opens http://127.0.0.1:8000
uv run expense-recon-web --port 9000 --data ./runs   # alternate port + data dir
```

It binds to loopback (127.0.0.1) only, so it is reachable from the
browser on that machine and nowhere else; every statement, receipt, and
generated report stays on the machine running the server. To turn on AI
categorization and FX judgment, set `OPENAI_API_KEY` in the server's
environment before launching (the keyword fallback runs without it).

What it does:

1. Upload one card statement (`.csv` / `.xlsx`) and the receipts CSV.
   The statement column map is auto-detected (the `inspect` heuristic);
   override a field only if the guess is wrong.
2. The run goes through the exact CLI pipeline (`cli.reconcile`): ingest,
   categorize, deterministic match, LLM judgment for FX / ambiguous.
3. The review workbench shows every transaction with its candidate
   receipt(s), match type, confidence, and per-line category. Chris can
   confirm a match, reject it, pick the right receipt among candidates,
   and reclassify a line's category. Each edit persists (SQLite) and the
   summary updates live.
4. Download the xlsx report with her decisions and reclassifications
   applied.

Runs persist under the data dir (`recon-web-data/` by default): the
SQLite db plus a per-run folder with the uploads and the generated
report. Journal POSTING to Zoho (4b) stays gated, same as the CLI.

`calibrate` runs the matcher and prints calibration metrics — the
distinct-transaction outcome split, the reconciliation invariant, the
receipt double-binding check, the FX-pair-vs-foreign-receipt
multiplicity (the `<= 2x` slice-3 target), and per-card spend. It exits
non-zero if the invariant breaks or a receipt is double-bound, so it
doubles as a regression gate on a known-good month.

Config shape (JSON, stdlib only — no YAML dep). Paths resolve relative
to the config file's directory:

```json
{
  "statement": {
    "path": "amex-may.csv",
    "account_id": "amex-9001",
    "legal_entity_id": "brisken-llc",
    "account_card_currency": "USD",
    "column_map": {
      "transaction_date": "Date",
      "amount": "Amount",
      "vendor": "Description"
    },
    "sheet_name": null
  },
  "receipts": {
    "path": "receipts-may.csv",
    "default_currency": "USD"
  },
  "output": { "path": "report-may.xlsx" }
}
```

Receipts CSV columns (header row):

```text
document_id, detected_date, detected_total, detected_vendor
  (required)
detected_currency, detected_reference, line_items
  (optional)
```

`line_items` is a JSON array string (per BLUEPRINT LD-2). Each item:
`{"description": "...", "line_total": "...", "quantity"?: ..., "unit_price"?: ...}`.
Empty / missing → vendor-fallback (Tier 2) categorization path triggers.
Real OCR (slice 2) populates this directly; CSV is the slice-1 bridge.

## Run the tests

```bash
cd workspace/clients/brisken/automations/expense-reconciliation
uv run --with 'pytest>=8.0' pytest -v
```

Expected: 98 passed.

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

```text
expense-reconciliation/
├── README.md                        # this file
├── pyproject.toml                   # uv project, Python >= 3.12, hatchling build
├── .gitignore
├── src/
│   └── expense_recon/
│       ├── __init__.py
│       ├── cli.py                   # entry point (expense-recon script; routes doctor/history/diff/calibrate)
│       ├── calibrate.py             # `calibrate` subcommand — matcher metrics + regression gate (E8/3b)
│       ├── categorize.py            # BLUEPRINT LD-1/LD-2 — LLM + keyword-stub classifier
│       ├── matching/
│       │   ├── __init__.py
│       │   ├── types.py             # Transaction, Receipt, LineItem, Categorization, …
│       │   ├── deterministic.py     # v2 spec §15.1 engine
│       │   └── judgment.py          # v2 spec §15.2 — FX judgment via LLM (D1b); ambiguous still stub
│       ├── ingest/
│       │   ├── __init__.py
│       │   ├── _common.py           # shared StatementParseError + parse_date/amount
│       │   ├── statement_csv.py     # v2 spec §7.1 CSV parser
│       │   ├── statement_xlsx.py    # v2 spec §7.1 Excel sibling
│       │   └── receipts_csv.py      # slice-1 bridge (+ line_items JSON column)
│       └── output/
│           ├── __init__.py
│           ├── report_xlsx.py       # Excel review report (5+N sheets, LD-3/LD-4, --explain)
│           └── zoho_export.py       # Zoho journal-entry CSV skeleton (slice 4.6)
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   └── sample_amex_export.csv   # synthetic 7-row Amex shape (parser tests)
    ├── test_deterministic_matching.py  #  9 tests
    ├── test_statement_csv.py           #  9 tests
    ├── test_statement_xlsx.py          # 14 tests, openpyxl fixtures in-memory
    ├── test_cli_integration.py         # 16 tests, inline fixtures + LD-2/LD-3 assertions
    ├── test_categorize_llm.py          # 14 tests, LLM-path categorizer + cost tracker
    ├── test_inspect.py                 # 12 tests, column-map heuristic guesser
    ├── test_fx_judgment_llm.py         # 13 tests, FX (D1b) + ambiguous judgment + guarantee
    ├── test_report_xlsx.py             #  4 tests, report writer + --explain sheet (E1/A8)
    ├── test_zoho_export.py             #  4 tests, Zoho journal-entry CSV (slice 4.6)
    └── test_cli_subprocess.py          #  3 tests, entry point via subprocess (E2)
```

## References

- v2 spec: [`../../specs/1-spec/p1-expense-reconciliation-functional-spec.md`](../../specs/1-spec/p1-expense-reconciliation-functional-spec.md)
- Boundaries: [`../../PROJECT-BOUNDARIES.md`](../../PROJECT-BOUNDARIES.md)
- Call outcomes (decision extraction): [`../../context/2026-05-20-call-outcomes.md`](../../context/2026-05-20-call-outcomes.md)
- Call transcript: [`../../reference/2026-05-20-call-transcript.md`](../../reference/2026-05-20-call-transcript.md)
- Dirk's v1 functional doc: [`../../reference/2026-05-14-functional-spec-original.md`](../../reference/2026-05-14-functional-spec-original.md)

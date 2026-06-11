# Annealing Register — Expense Reconciliation Build

Single coherent list of quality items noticed during the slice-1
working-tool build (session 2026-05-27) that were deferred to keep
the ship lean. Re-read this when Chris's first real month lands or
when starting slice 2.

**Posture (Dirk 2026-05-27):** "We just need a working tool. Anneal
quality through real-data use, not architecture up front."
This register is the deferred-quality backlog that posture creates.
Nothing here is a slice-1 bug — slice 1 ships intentionally narrow.

**Legend.** Effort: S (~hours), M (~day), L (~week+).
Trigger = the moment this becomes urgent enough to revisit.

---

## Resolved 2026-06-07 — hardening + plumbing batch (no client input)

Shipped without real data, all mock-tested (98/98 suite green). These
items below are now done; their individual entries are superseded by
this note.

- **judge_ambiguous wired** (was BLUEPRINT 2.4 stub). LLM breaks ties
  among candidate receipts; the pick is annotated + promoted to the
  front, every candidate stays in the bucket (guarantee asserted in
  `test_apply_ambiguous_judgment_promotes_pick_but_keeps_all`).
  `LLMClient.judge_ambiguous` + OpenAI/Mock impls; `_apply_ambiguous_judgment`
  in the CLI.
- **C3 — structured logging.** `logging` across the CLI pipeline +
  `--verbose` flag (DEBUG to stderr; quiet by default).
- **A8 — `--explain` sheet.** Per-transaction outcome + confidence +
  reason trail in the report. FX / ambiguous LLM reasoning now also
  surfaces in the per-row Note.
- **Zoho export skeleton (slice 4.6).** `output/zoho_export.py` —
  journal-entry CSV in Zoho's column shape, N debits + 1 balancing
  credit per matched tx, matches-only. Account names are placeholders
  until chart-of-accounts ingest (4.1).
- **E1 — report-writer unit tests** (`test_report_xlsx.py`).
- **E2 — subprocess CLI test** (`test_cli_subprocess.py`).
- **E5 — CI** (`.github/workflows/expense-recon-tests.yml`).
- **E6 — `MatchOutcome` frozen.** Rebinding a bucket now raises; lists
  still mutated in place (`outcome.judgment_required[:] = ...`).
- **E7 — currency-layer clarity.** Docstrings on the three layers
  (transaction / account-card / book) on `Transaction` + `Receipt`.
- **E3 — README accuracy pass** (test counts, file layout, slice
  status all current).

Still gated on Chris's data / Zoho access: D2 vision OCR, the A-series
matcher calibration (A1–A7), real-data validation, slice 4 posting.

---

## What already works (do not regress)

Brief deliberate list so annealing changes don't break what's clean.

- **Deterministic-first split.** The matcher is pure logic; LLM is
  invoked only at the judgment boundary. Dirk-aligned and slice-2-ready.
- **Reconciliation invariant.** Every tx lands in exactly one of
  `matches` / `judgment_required` / `ambiguous` / `unmatched_transactions`.
  No silent drops. Verified by `test_reconciliation_guarantee_invariant_holds`
  and the integration-test Summary assertion.
- **Shared parser helpers.** `_common.py` keeps CSV / XLSX / receipts
  CSV on a single source of truth for date/amount tolerance + error
  type. Avoided silent divergence when the XLSX sibling landed.
- **Stub LLM doesn't auto-resolve.** `judge_fx_match` returns
  `requires_review=True` with `[STUB]` reason. Slice 2 swaps the body
  without breaking the slice-1 contract.
- **Build system + entry point.** `uv sync && uv run expense-recon`
  works end-to-end on a clean clone. Hatchling configured.
- **40/40 tests green in <1s.** Fast suite = cheap regression catch.

---

## A. Matcher quality (the noise that bites real data first)

### A1. FX cross-product noise *(README annealing #1)*

**Where:** [`src/expense_recon/matching/deterministic.py`](src/expense_recon/matching/deterministic.py) `match_one`, lines 60-75
**Symptom:** Every USD transaction generates an `FX_JUDGMENT`
candidate against every non-USD receipt in the pool, regardless of
amount or date proximity. One EUR receipt in a 30-row month produces
30 spurious "needs review" entries.
**Why it happens:** The currency-mismatch branch returns immediately
without checking amount or date plausibility — design comment says
"vendor / reference / mock-FX is the LLM's job" but in practice this
floods the LLM (and the review sheet) with junk pairs.
**Fix direction:** Require BOTH date proximity (within ±N days) AND
rough amount plausibility (e.g., within ±50% after a 0.8–1.4 FX-band
sanity check) before emitting `FX_JUDGMENT`. Tighter band = less LLM
spend, less Chris review.
**Effort:** M
**Trigger:** First real Brisken month with ≥1 non-USD receipt
(near-certain on month 1 — UK / EU presence).
**Real-data evidence (2026-06-11 3b calibration):** measured at
5,064 / 3,312 / 1,639 FX pair-rows on the three real months
(119/92/91 transactions) — ~50× the BLUEPRINT ≤2×-receipts target,
a 10,124-row Needs-Review sheet for one month. ~97% of the expense
lines are foreign-currency, so this branch carries nearly all
volume: the fix must be a deterministic FX band (daily-rate
conversion + band match: ≤3% high-confidence, 3–13% DCC-suspect
review, >13% reject — bands measured from 98 aligned real pairs,
max observed DCC gap 12.8%), not just a plausibility gate in front
of the LLM. See the BLUEPRINT slice 3b calibration block.

### A2. Receipt double-binding *(README annealing #2)*

**Where:** [`src/expense_recon/matching/deterministic.py`](src/expense_recon/matching/deterministic.py) `match_month`, the `by_tx` loop
**Symptom:** The same receipt can be the "best" match for two
different transactions when amounts are close. Confirmed in the
slice-1 fixture-design phase: Hotel Paris ($112.30) probable-matched
the Amazon receipt ($89.99) because it sat within the 20% / 5-day
window, AND Amazon's own transaction also matched that receipt as
EXACT. Both go into `matches`.
**Why it happens:** `matched_receipts: set[str]` tracks receipts only
for the unmatched-receipts residual calculation; it does not feed
back into candidate filtering.
**Fix direction:** Bipartite assignment over the candidate matrix
(Hungarian algorithm or greedy-by-confidence with consumption). Each
receipt lands at most once. Drop the second-best candidate to the
next outcome tier instead.
**Effort:** M
**Trigger:** First real month — guaranteed to hit this on any month
with 20+ transactions of similar amounts (Uber, coffee, lunch).
**Real-data evidence (2026-06-11 3b calibration):** confirmed on
month 1, worse than the fixture predicted. Each month's single
same-currency receipt was claimed by 4–5 different transactions
inside the 20%/5-day window (March: one receipt → 4 MATCHED rows;
May: one receipt → 5 MATCHED rows, only its exact pair true). 7–8
of the quarter's 9 deterministic matches are false double-bindings.

### A3. No vendor / reference signal in matching *(README annealing #3)*

**Where:** [`src/expense_recon/matching/deterministic.py`](src/expense_recon/matching/deterministic.py) `match_one`
**Symptom:** A $100 Amazon receipt and a $100 Uber receipt on the
same day are equally good candidates for a $100 transaction. Scoring
ignores `vendor_from_statement` ↔ `detected_vendor` and
`detected_reference`.
**Fix direction:** Add a vendor fuzzy-match score (RapidFuzz / Jaro-
Winkler) and a reference-number exact-match bonus to the confidence
calculation. Tip the ties; do not gate the whole match (some banks
strip vendor names to gibberish).
**Effort:** M (with rapidfuzz dep) / S (with stdlib `difflib`)
**Trigger:** First real month — same-amount-same-day collisions will
otherwise produce ambiguous-bucket noise.
**Real-data evidence (2026-06-11 OCR calibration):** two design
inputs for the fuzzy scorer confirmed on the 13 real receipts.
(1) OCR vendor strings carry single-character misreads on
low-quality photos, so the vendor score must be fuzzy, never exact.
(2) 12/13 receipts carried an extracted reference (ride-share UUIDs,
rail booking numbers), so the reference-number exact-match bonus has
real signal to bind on, likely stronger than vendor for ticket-type
receipts.

### A4. Probable-match window may double-bind even with bipartite assignment

**Where:** `match_one` — 20% amount / 5-day date probable window
**Symptom:** Even after A2's bipartite fix, the probable window is
loose enough that one tx can claim a receipt the user would have
intuitively assigned elsewhere. Confirmed by slice-1 fixture: Hotel
matched Amazon's receipt at 19.9% / 5-day.
**Fix direction:** Tighten probable window OR break ties on vendor
similarity (depends on A3). Likely both. Per-bank profiles (A7) may
also help.
**Effort:** S (window tuning) — but tune AGAINST Chris's real data,
never against synthetic.
**Trigger:** After A2 + A3 land; tune empirically on month-2 data.
**Real-data evidence (2026-06-11 3b calibration):** the false
double-bindings under A2 all entered through this window (amount
diffs of 16–21% accepted at up to 5 days' distance). On the
same-currency aligned pairs, true matches sit ≤3% (non-DCC) —
the 20% default is an order of magnitude looser than the data
needs once A3's vendor/reference signal exists to break ties.

### A5. Negative-amount (refund) matching gap

**Where:** `match_one` — the `tx.amount > 0` guard on the probable branch
**Symptom:** Refund transactions ($-15 Amazon return) cannot
probable-match anything; they only match if EXACT to a negative
receipt. The synthetic Amazon-return test left it correctly in
`unmatched_transactions`, but real refund flows (Amazon return →
return-confirmation receipt) need pair matching.
**Fix direction:** Either (a) add an explicit refund-matching path
that pairs negative-tx to negative-receipt with relaxed amount/date
tolerance, or (b) accept that refunds always go through human review
(simplest; Chris probably wants to confirm refunds anyway).
**Effort:** S (option b: a single explanatory comment + a separate
"refunds" outcome bucket).
**Trigger:** First month with any return / refund. Likely month 1.

### A6. Default tip tolerance assumes US

**Where:** `MatchingConfig.amount_probable_tolerance_pct = Decimal("0.20")`
**Symptom:** 20% tolerance is US-restaurant-tip shaped. Brisken
has UK / EU presence where tips are typically 0–12.5%. A 20% pad
there is over-loose and lets unrelated charges into probable.
**Fix direction:** Per-card or per-region tolerance profile passed
via the run config. Default stays 20% (US); per-card override sets
0.12 (UK) or 0.00 (strict).
**Effort:** S
**Trigger:** First reconciliation of a UK / EU card.

### A7. Per-bank tolerance profiles

**Where:** `MatchingConfig` (today a single shared config)
**Symptom:** Some banks post 2 days after purchase consistently
(Amex US), some post next-day (Chase), some same-day (most EU
debit). One global `date_exact_window_days` over-pads tighter
banks and under-pads looser ones.
**Fix direction:** `MatchingConfig` keyed by `account_id` (or by
bank profile name). Config is per-run; per-account overrides
specified in `run.json`.
**Effort:** M
**Trigger:** Second card added to the same run (multi-card
reconciliation, A11 below) — not before, no point.

### A8. Matcher emits no explanation trail

**Where:** `match_one` returns a `reason` string; no structured
breakdown of why this beat that.
**Symptom:** When Chris asks "why was this matched and not that?",
all we have is the reason string. For debugging A2 / A3 / A4
behavior we need per-tx scoring breakdowns.
**Fix direction:** Optional `--explain` flag → write a per-tx
decision log as a 5th sheet (or a separate JSON). Off by default.
**Effort:** S
**Trigger:** First time we need to debug a "why did this match"
question from Chris.

### A9. Summary sheet counts pair-rows, not transactions (2026-06-11)

**Where:** [`src/expense_recon/output/report_xlsx.py`](src/expense_recon/output/report_xlsx.py) — `by_card_total` / needs-review counting and the invariant line
**Symptom:** Found by the 3b calibration: a month whose statement
sums to $8.8K displays "Spend $1,258,996" because every
judgment/review PAIR contributes the transaction amount again
(5,064 pair-rows in that month). The Summary "Reconciliation
invariant" line also false-alarms BROKEN while the engine-level
invariant actually holds (per-transaction outcomes sum exactly,
e.g. 115 FX + 4 matched = 119).
**Why it happens:** the report flattens outcome buckets to one row
per pair; Summary aggregates over rows where it means transactions.
**Fix direction:** aggregate Spend and the invariant over unique
`transaction_id`s; keep pair-rows for the review sheets only. A1's
fix shrinks the blast radius but the unit confusion is wrong
independently.
**Effort:** S
**Trigger:** With A1, before Chris sees any report (a $1.2M Spend
line on an $8.8K month is an instant-credibility kill).

---

## B. Tool / UX ergonomics

### ~~B1. No error-output sheet for malformed rows~~

**Resolved 2026-06-01** — slice 3a defensive pass. All three
parsers expose tolerant variants (`parse_statement_csv_tolerant`,
`parse_statement_xlsx_tolerant`, `parse_receipts_csv_tolerant`)
returning `(rows, list[ParseIssue])`. Header errors still raise
(config-class). CLI uses tolerant mode by default; issues land in
the Errors sheet with file basename + line number + message. Good
rows continue to parse + reconcile. Verified by
`test_bad_row_in_receipts_collects_to_errors_continues_with_good_rows`,
`test_bad_row_in_statement_collects_to_errors_continues`,
`test_duplicate_receipt_document_id_lands_in_errors_sheet`.

### ~~B2. No column auto-detection / preview~~

**Resolved 2026-06-01** — slice 3a defensive pass.
`expense-recon-inspect <statement>` ships as a second console
script. Heuristic library: regex against English + DE bank-export
header conventions (Date / Description / Amount / Posting Date /
Currency, plus DE Amex: Buchungsdatum / Beschreibung / Betrag /
Währung). Posting-date doesn't steal transaction-date (greedy
assignment in priority order). Outputs a copy-paste-able
`column_map` JSON block; when a required field can't be guessed,
lists the available headers under `// MISSING ... TBD` markers.
Verified by 12 tests in `tests/test_inspect.py` covering: Amex US
+ Chase + DE Amex headers, posting-date priority, unknown
headers, partial match, CSV + xlsx end-to-end, unsupported
extension, BOM handling. Real CLI smoke run produces clean JSON
on the example fixture.

### B3. Single statement per run

**Where:** `_load_statement` accepts one file
**Symptom:** Brisken has multiple cards and accounts per legal
entity per call-outcomes. Today Chris must run the CLI N times
and concat the reports manually.
**Fix direction:** `statements: [...]` array in config, each with
its own `account_id` / `column_map`. Pipeline reconciles all
statements against the shared receipts pool. Report Summary sheet
breaks down by account.
**Effort:** M (also surfaces A2 / A7 sooner)
**Trigger:** First month where Chris reconciles ≥2 cards in one
session.

### ~~B4. No `--dry-run` / `--preview`~~

**Resolved 2026-06-01** — slice 3a defensive pass. CLI accepts
`--dry-run`; `run(..., dry_run=True)` returns None, prints
`DRY RUN` header + counts (Transactions, Receipts, Matched, Needs
review, Unmatched tx, Parse errors) + first 5 parse errors to
stdout. No xlsx written. Verified by
`test_dry_run_skips_xlsx_and_prints_summary`.

### ~~B5. Receipts CSV row de-duplication~~

**Resolved 2026-05-31** (slice 1.5) — receipts_csv tracks `seen_ids`,
raises on duplicate `document_id` with both row numbers. Now under
the B1 tolerant umbrella: duplicates land in the Errors sheet
instead of aborting the run. Verified by
`test_duplicate_receipt_document_id_lands_in_errors_sheet`.

**Historical fix direction:** Raise `StatementParseError` on duplicate
`document_id` with both line numbers. Cheap, prevents a confusing
class of "why is this ambiguous" question.
**Effort:** S
**Trigger:** Anytime — defensive, low ROI now, free to add.

### B6. CSV / JSON alternative outputs

**Where:** [`src/expense_recon/output/report_xlsx.py`](src/expense_recon/output/report_xlsx.py) — single writer
**Symptom:** Only xlsx today. A future review UI wants JSON.
**Half resolved 2026-06-07 by PR #80:** the "Zoho import wants CSV"
half shipped as a dedicated artifact (`output/zoho_export.py`,
journal-entry CSV per LD-2), not a `--format` flag — better shape,
since the Zoho CSV is a different document from the review report,
not an alternative rendering of it.
**Remaining:** JSON output of the review report itself.
**Effort:** M (structured JSON schema)
**Trigger:** Slice 6 review UI — it would be the JSON consumer.
Don't build before then.

### ~~B7. No example `run.json` committed~~

**Resolved 2026-06-01** — slice 3a defensive pass.
`examples/run.example.json` + `examples/statement.example.csv` +
`examples/receipts.example.csv` + `examples/README.md` committed.
Smoke-tested end-to-end: `uv run expense-recon --config
examples/run.example.json` writes a 9272-byte report.xlsx with the
expected 5+N sheet structure. JSON `_*_help` fields used for inline
comments (sibling fields, not inside `column_map` since the parser
iterates that literally). `.gitignore` updated to skip
`examples/report.xlsx`.

### ~~B8. No command runner shortcuts~~

**Resolved 2026-06-01** — slice 3a defensive pass. `justfile`
committed at the automation root with targets: `sync`, `recon
CONFIG`, `dry-run CONFIG`, `inspect FILE`, `example`, `test`,
`test-x`, `clean`. Works on any machine with [just](https://github.com/casey/just)
installed. README still shows the raw `uv run ...` commands so the
tool works without `just` too.

---

## C. Output completeness

### ~~C1. No idempotency / run-log~~

**Resolved (run-log half) 2026-06-11 by PR #109** — `runlog.py`
opt-in SQLite run-log (`run_log:` config block; no block = no file,
no behaviour change). One row per run + one row per tx-decision incl.
unmatched (guarantee carried into the log); audit columns only, never
account/vendor/amount data. `expense-recon history` +
`expense-recon diff` subcommands. 11 tests (`tests/test_runlog.py`).
The IDEMPOTENCY half (don't double-post a line item) is deliberately
NOT built: it guards 4b live Zoho posting, which stays gated — tracked
as BLUEPRINT 4.8, no surface until 4b lands. Review-edit write-back
(the C5 dependency) remains slice-6 territory.

### ~~C2. No vendor / category enrichment from chart-of-accounts~~

**Resolved 2026-06-09 by PR #87** (chart-of-accounts ingest,
`ingest/chart_of_accounts.py`, wired in `cli.py`
`_build_chart_of_accounts`) on top of the per-line LLM categorizer
from PR #68 (`categorize.py`). Shipped better than the original fix
direction: per-LINE-item categorization (LD-2, not vendor→category
mapping), suggested Zoho account in the report's "Zoho A/C" column,
confidence-gated REVIEW tier. Live-verified 2026-06-09 against
Brisken's real sandbox chart (BLUEPRINT 4.6).

### ~~C3. No structured logging~~

**Resolved 2026-06-07 by PR #80** (slice 3a hardening; strike
missed in that PR, recorded 2026-06-11). Python `logging` wired in
`cli.py` (`--verbose`/`-v` → DEBUG, default WARNING) and used by the
ingest pipeline (`receipts_folder.py` logs per-file extraction).
The optional `--log-file` JSON output was not built — no demand
signal yet; re-raise only if a real debugging session wants it.

### C4. Excel report uses float for amounts at display boundary

**Where:** [`src/expense_recon/output/report_xlsx.py`](src/expense_recon/output/report_xlsx.py) `_decimal_to_float`
**Symptom:** Amounts converted Decimal → float for the xlsx
cell. Source of truth stays Decimal upstream, but the displayed
value loses precision below 0.01 if it ever existed.
**Why deferred:** Real bank statements never use sub-cent
precision; in practice this is fine.
**Fix direction:** If Brisken ever shows sub-cent (FX-conversion
fractional rounding), switch to writing strings with explicit
formatting and a numeric format string on the cell.
**Effort:** S (only if symptom appears)
**Trigger:** Only if real-data inspection shows precision loss.

### C5. No telemetry on Chris's review decisions

**Where:** Nothing — slice 1 is fire-and-forget
**Symptom:** No signal to anneal tolerances on. Tip-tolerance
should be calibrated from "Chris confirmed this probable match
N% of the time," but that data doesn't exist.
**Fix direction:** Tied to C1's run-log. When Chris edits a
review row (slice 3+), persist the edit. After N months we have
a real distribution to retune `MatchingConfig` against.
**Effort:** L (needs review UI to exist)
**Trigger:** Slice 3 (review UI). Don't build before that — no
data source.

---

## D. Slice-2 prep (LLM wiring)

### ~~D1. LLM client abstraction~~

**Resolved 2026-06-01** (provider pivoted to OpenAI per BLUEPRINT
"Provider Pivot" block). `src/expense_recon/llm/client.py` ships
the `LLMClient` Protocol + `OpenAIClient` (production, gpt-4o-mini
by default) + `MockLLMClient` (tests). Cost tracking in
`llm/cost.py` (`TokenUsage` + `CostTracker`). Categorizer wired
via `categorize_receipts(receipts, client=...)`; CLI reads `llm:`
block from config and instantiates client (or falls back to
keyword stub when block absent). Verified by 14 tests in
`tests/test_categorize_llm.py` + live smoke run against real
OpenAI API ($0.0003 / 4-receipt run). Provider swap (e.g., back
to Anthropic Vertex / Bedrock) = one new class implementing the
same protocol; no other code changes.

### ~~D1b. FX judgment LLM call~~

**Resolved 2026-06-06.** `judge_fx_match` now calls the LLM when a
client is wired. Added `LLMClient.judge_fx_match` (provider-agnostic,
primitive in / `FxJudgmentResult` out) + `OpenAIClient` impl
(`_FX_JUDGMENT_PROMPT_TEMPLATE` + strict json_schema) +
`MockLLMClient` impl (`fx_responses` queue + vendor-overlap default
heuristic). The model FX-converts the receipt into the transaction
currency and returns a same-purchase confidence + implied rate +
converted amount; the Match surfaces all of it. Two invariants held:
FX always `requires_review=True` (rate is approximate, §38-TBD; D2
"review everything for the first months"), and the entry stays in
`judgment_required` whatever the verdict (reconciliation guarantee).
No-client path still returns the `[STUB]` Match (slice-1 contract
preserved). CLI helper `_apply_judgment_stub` renamed
`_apply_judgment` and threads the client. Verified by 8 tests in
`tests/test_fx_judgment_llm.py` (82/82 suite green). NOT yet run
against a live FX receipt — vision OCR (D2) is gated on Chris's data,
so no real foreign-currency receipt has reached the matcher; the live
prompt should be re-checked against the first real FX case.
`judge_ambiguous` shipped in the same PR (#80) — LLM tie-break with
pick annotated + promoted, all candidates kept; BLUEPRINT 2.4 done
2026-06-07. (This sentence originally said "remains a stub" — stale
at write time; corrected 2026-06-11.)

### ~~D2. Receipt OCR pipeline replaces receipts_csv~~

**Resolved 2026-06-10 by PR #107** (slice 2.2) — landed as
`ingest/receipts_folder.py` (not `receipts_vision.py`): vision OCR
for images, PDF text-layer via pypdf for digital receipts, pypdfium2
render fallback for scans. Same `(receipts, issues)` return shape as
the CSV path; matcher contract untouched. CSV path NOT removed —
`receipts.source: "csv" | "folder"` (inferred from path), so both
coexist. Per-file tolerant; unsupported files land in the Errors
sheet. Never invents line items (LD-2). 14 mocked tests + env-gated
live test (2.9). **Live-calibrated 2026-06-11** against the 13 real
Brisken receipts: 13/13 extracted, 100% header coverage, three
currencies detected, $0.0204 total — see BLUEPRINT slice-2
calibration block. `max_concurrent` batch parallelism was not built
(13 sequential calls were fast enough); re-raise only if a real
month's wall-clock hurts.

### ~~D3. Cost / token tracking per run~~

**Resolved 2026-06-01** — `src/expense_recon/llm/cost.py` ships
`TokenUsage` (per-call) + `CostTracker` (per-run aggregate).
OpenAIClient records each call's `prompt_tokens` + `completion_tokens`;
cost computed against `_PRICING_PER_MILLION` table (gpt-4o-mini:
$0.15/M input + $0.60/M output). CLI passes `cost_tracker.total_cost_usd`
to the report writer; Summary sheet shows "Estimated cost (USD)".
Persisted to run-log: deferred to slice 5b (C1). Verified by
`test_cost_tracker_accumulates_one_per_call` +
`test_token_usage_cost_calculation_matches_published_pricing` +
real LLM smoke (live $0.00029 cost displayed on Summary).

---

## E. Code health / tests / project meta

### ~~E1. Unit-test coverage for report writer~~

**Resolved 2026-06-07 by PR #80** (strike missed in that PR,
recorded 2026-06-11). `tests/test_report_xlsx.py` covers the
canonical 5+N sheet set, matched-line row expansion, parse errors
landing in the Errors sheet, and the `--explain` sheet's
presence/absence.

### ~~E2. Subprocess-based CLI test~~

**Resolved 2026-06-07 by PR #80** (strike missed in that PR,
recorded 2026-06-11). `tests/test_cli_subprocess.py` exercises the
installed `expense-recon` entry point end-to-end, catching packaging
/ `__main__` regressions the in-process tests can't see.

### ~~E3. README ordering implies slice 1 is older than Phase 2/4~~

**Resolved 2026-06-07 by PR #80** (strike missed in that PR,
recorded 2026-06-11). README restructured around what the tool does:
"What this is" → "Where the build is right now" → "Run the tool" →
"Run the tests" → data-needs / rationale / layout. The slice-vs-phase
chronology inversion is gone.

### E4. Spec divorced from build state

**Where:** v2 spec §32 phase ordering says Phase 0 first
**Symptom:** We did Phase 4 (matching), then Phase 2 (ingest),
then a CLI tool that isn't really one of the spec's phases.
The spec doesn't reflect the "tool-first" pivot.
**Fix direction:** Add a `## §32.1 Tool-first build path` block
to the v2 spec acknowledging Dirk's 2026-05-27 directive and the
slice-numbered roadmap. Spec phases remain the long-term map;
slices are the path through them.
**Effort:** S
**Trigger:** Next spec update OR before any new joint-call with
Dirk where build sequencing comes up.

### ~~E5. No CI~~

**Resolved 2026-06-07 by PR #80** (strike missed in that PR,
recorded 2026-06-11). `.github/workflows/expense-recon-tests.yml`
runs the suite on every PR; it is the "test" check that gates
auto-merge (Band 2) — e.g. it ran green on PRs #107/#108/#109/#110.

### ~~E6. `MatchOutcome` mutability subtlety~~

**Resolved 2026-06-07 by PR #80** (strike missed in that PR,
recorded 2026-06-11). `MatchOutcome` is now `frozen=True`
(`matching/types.py`) — the stronger of the two proposed fixes;
consumers must construct new outcomes rather than mutate.

### E7. Per-account currency confusion

**Where:** Receipt's `detected_currency` vs Transaction's
`transaction_currency` vs `account_card_currency`
**Symptom:** Three currency fields per the spec's 3-layer
design. Slice 1 collapses some of this in defaults
(`default_currency` for receipts). Real data with mixed-currency
cards (Wise multi-currency, Revolut) may surface bugs.
**Fix direction:** Document the 3-layer convention explicitly
at the top of `types.py` (already partially there, expand).
Add a test for the 3-layer case (Wise card in USD, transaction
posted in EUR, receipt in EUR).
**Effort:** S
**Trigger:** First multi-currency card.
**Note (2026-06-11):** no longer hypothetical — the real receipt set
spans three currencies (USD/EUR/BRL), so the first full real-month
run WILL exercise this. Re-check before slice 3b tuning.

### E8. OCR calibration script lives in %TEMP%, breaks between sessions

**Where:** `%TEMP%\brisken_ocr_calibration.py` (uncommitted, staged
2026-06-10, re-staged 2026-06-11)
**Symptom:** The script hard-codes a `SRC` path; it already broke
once when the worktree it pointed at was removed, and needed a
session spent re-verifying the API surface before it could re-run.
%TEMP% is also subject to OS cleanup. Calibration WILL re-run (new
receipt batches, slice 3b tuning, post-prompt-change regression), so
this is repeat-use tooling kept in a throwaway location —
`infrastructure-deferred` territory if it recurs unbuilt.
**Fix direction:** Promote to an `expense-recon calibrate <folder>`
subcommand (or `tools/`-committed script): folder-mode ingest +
per-file field table + coverage summary + cost, key from
`OPENAI_API_KEY` or the local vault. The temp script IS the spec;
~1 hour to port. Real receipt data stays git-ignored either way.
**Effort:** S
**Trigger:** Next calibration ask, or 2 more checkpoints staging the
temp script (whichever first).

---

## Anneal order (when build lands and you re-read this)

Not strict — depends on which item Chris's data hits hardest. But a
reasonable default ordering for the first session after this lands:

1. ~~**B1 (error-output sheet)**~~ done 2026-06-01.
2. **A1 (FX cross-product noise)** — first real month with EU
   receipts floods Needs Review. ~1 day. (2026-06-11: real set spans
   USD/EUR/BRL, so this fires on month one.)
3. **A2 + A3 together (bipartite + vendor signal)** — fix the
   double-binding properly with vendor as the tie-breaker. ~1 day.
4. **A5 (refund handling)** — explicit refund bucket, document
   the design choice. ~few hours.
5. ~~**D1 (client abstraction)**~~ done 2026-06-01 (OpenAI pivot).
6. **B3 (multi-statement input)** — when Chris adds her second card.
7. ~~**C1 (run-log)**~~ done 2026-06-11 (PR #109; idempotency half
   deferred to 4b).
8. The rest as need surfaces — most are S-effort and can land
   opportunistically.

---

## How this register updates

- **New items go in.** Add to the right category (A/B/C/D/E),
  number sequentially, include Where / Symptom / Fix / Effort /
  Trigger.
- **Items completed → strike through with `~~text~~`** and a
  dated line: `Resolved 2026-XX-XX by {commit / PR / session}`.
- **Items that turn out to be wrong → just delete with a note in
  the next session checkpoint** so the deletion is traceable.
- **This file replaces the inline annealing notes in README.md.**
  README annealing items #1-3 are the same as A1, A2, A3 below
  and should be removed from README when this file is committed
  (deferred to keep slice 1 ship lean).

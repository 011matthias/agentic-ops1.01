# Checkpoint: Brisken Expense Recon Excel Parser

**Date:** 2026-05-26
**Status:** Phase 2 Excel sibling parser shipped; 32/32 tests green. Further build work still gated on §38 stack sign-off OR Chris's first real-data sample, unchanged from the 2026-05-25 checkpoint.

---

## Summary

Resumed Brisken with the three-branch tree from the 2026-05-25 checkpoint. Verified that neither Dirk's §38 sign-off nor Chris's real-data sample has moved since (no new files in `context/` / `reference/` / `drafts/`, no Brisken session log between 2026-05-25 and now). Branch 3 fired: built the next stack-independent piece. Picked Excel parser over the synthetic-receipt generator because v2 spec §7.1 already says "CSV **or** Excel — whichever Brisken already downloads", so Excel parity preempts a concrete unknown the moment Chris's data lands, while synthetic-OCR-noise generation is speculative until the §38.5 OCR engine is picked.

---

## What Was Done This Session

### Pre-flight resume checks
1. Read `PROJECT-BOUNDARIES.md`, prior `Checkpoint.md`, `2026-05-20-call-outcomes.md`, `automations/expense-reconciliation/README.md` — the user-mandated order.
2. Verified Branch 1 not fired: no new file in `context/` or `reference/` from Dirk.
3. Verified Branch 2 not fired: no Chris CSV in `tests/fixtures/`; only the synthetic `sample_amex_export.csv` from 2026-05-25 sits there.
4. Verified no Brisken session log entry between 2026-05-25 and 2026-05-26.

### Shared-helper refactor (no behavior change)
5. Created [`src/expense_recon/ingest/_common.py`](../../workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py) — lifted `StatementParseError(line_number=...)`, `parse_date`, `parse_amount`, `validate_required_map`, `REQUIRED_KEYS`, `OPTIONAL_KEYS` out of `statement_csv.py`. Row-number convention (header is row 1, data starts row 2) now documented as cross-format.
6. Refactored [`src/expense_recon/ingest/statement_csv.py`](../../workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/statement_csv.py) to import from `_common`. All 9 prior CSV tests still pass — refactor proven non-breaking.

### Excel sibling parser (new)
7. Created [`src/expense_recon/ingest/statement_xlsx.py`](../../workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/statement_xlsx.py) — `parse_statement_xlsx(path, column_map, account_id, legal_entity_id, account_card_currency, sheet_name=None) -> list[Transaction]`. Same interface as CSV, plus the optional `sheet_name`. Cell-type handling:
   - Native `datetime.datetime` / `datetime.date` → `.date()` directly (no string parsing).
   - Native `int` / `float` → `Decimal(str(value))` to avoid IEEE-754 binary noise (`Decimal(5.75)` would round-trip badly; `Decimal(str(5.75)) == Decimal("5.75")`).
   - `str` → shared `parse_date` / `parse_amount` (so `$`, `,`, `(50.00)` tolerances apply).
   - `bool` rejected explicitly — `bool ⊂ int` in Python; without the guard a stray TRUE cell would become `Decimal(1)`.
   - `None` / blank → empty (row-blank → skip, mapped-cell-blank with optional key → `None` posting_date).
8. Added `openpyxl>=3.1` as runtime dep in [`pyproject.toml`](../../workspace/clients/brisken/automations/expense-reconciliation/pyproject.toml).
9. Updated [`ingest/__init__.py`](../../workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/__init__.py) to point readers at the three modules and the shared helpers.

### Tests
10. Created [`tests/test_statement_xlsx.py`](../../workspace/clients/brisken/automations/expense-reconciliation/tests/test_statement_xlsx.py) — 14 tests. Fixtures generated in-memory via `openpyxl.Workbook` to `tmp_path` (no binary committed to git). Mirrors the CSV test surface where shared, plus Excel-only cases: native float Decimal-noise guard, string-typed date cell fallback, string-typed amount cell fallback, named-sheet selection on a multi-sheet workbook, bool-in-amount rejection, per-row currency override, end-to-end xlsx → matcher integration.
11. Full suite run: **32/32 passed in 0.89s** (9 matcher + 9 csv + 14 xlsx). Used the documented `(cd ... && uv run --with 'pytest>=8.0' --with 'openpyxl>=3.1' pytest -v)` subshell pattern.

### Docs
12. Updated [`README.md`](../../workspace/clients/brisken/automations/expense-reconciliation/README.md) — added the Phase 2 ingest section with both parsers + shared helpers, bumped expected test count to 32, refreshed file-layout tree.
13. Updated [`infrastructure.yaml`](../../workspace/clients/brisken/infrastructure.yaml) — `build_artifacts` block now lists 32 tests passing and enumerates the four ingest/matching modules; added a 2026-05-26 entry to the notes block.

---

## Key Decisions Made

### Pick Excel over synthetic-receipt generator for Branch 3
- **Choice:** Excel parser, defer synthetic receipts.
- **Rationale:** Excel parity is required by v2 spec §7.1 — Chris uses whichever format her bank exports, and we don't know which yet. Building both formats now means zero scramble when her data lands. Synthetic OCR-noise is more speculative: real OCR errors depend on the engine, which is gated on §38.5, and the matcher already handles missing/malformed fields at the type level (returns FX_JUDGMENT / UNMATCHED) so the test gap isn't urgent.

### Refactor shared helpers before adding the sibling, not after
- **Choice:** Move `StatementParseError` + parsers into `_common.py` first, refactor CSV, then build XLSX importing the same module.
- **Rationale:** Two parsers diverging on date-format set or accounting-negative tolerance would be a silent footgun. Single source of truth from day one is cheaper than reconciling later. The refactor is verified non-breaking by running all 9 CSV tests through the new import path before adding any XLSX code.

### Generate xlsx fixtures in-memory per test, don't commit a binary
- **Choice:** Use a `_write_xlsx(path, rows, headers)` helper that builds the workbook in `tmp_path` inside each test.
- **Rationale:** Binary fixtures don't diff in git, are easy to break silently, and would need a regeneration script. openpyxl is already a runtime dep so any test runner can produce the file. The cost is one helper function and a few lines per test; the benefit is full reproducibility and visible test data.

### Reject `bool` explicitly in `_coerce_amount`
- **Choice:** Special-case `isinstance(value, bool)` before the `isinstance(value, (int, float))` branch.
- **Rationale:** `bool` is a subclass of `int` in Python — without the guard, a stray `TRUE` cell in the amount column would silently become `Decimal(1)`. The reconciliation-guarantee posture (v2 spec §25.5) says no silent acceptance of garbage. Backed by `test_bool_amount_rejected`.

### Default tip tolerance and `_parse_amount` defaults untouched
- **Choice:** Did not change any matcher constants or CSV parsing behavior this session.
- **Rationale:** All real tuning waits for Chris's data. Touching defaults now would be guesswork; touching them after Chris's first month gives a calibrated signal.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py` | Created | Shared `StatementParseError`, `parse_date`, `parse_amount`, `validate_required_map` (lifted from `statement_csv.py`). |
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/statement_csv.py` | Modified | Refactored to import shared helpers from `_common`. No behavior change — verified by all 9 prior CSV tests still green. |
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/statement_xlsx.py` | Created | New `parse_statement_xlsx` Excel sibling — same interface as CSV, plus optional `sheet_name`. Native datetime / float / string cell handling. |
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/__init__.py` | Modified | Module docstring now points at both parsers + shared helpers. |
| `workspace/clients/brisken/automations/expense-reconciliation/pyproject.toml` | Modified | Added `openpyxl>=3.1` as runtime dep. |
| `workspace/clients/brisken/automations/expense-reconciliation/tests/test_statement_xlsx.py` | Created | 14 tests; in-memory openpyxl fixtures (no binary in git); end-to-end xlsx → matcher integration. |
| `workspace/clients/brisken/automations/expense-reconciliation/README.md` | Modified | Added Phase 2 ingest section, bumped expected test count to 32, refreshed file-layout tree. |
| `workspace/clients/brisken/infrastructure.yaml` | Modified | `build_artifacts` enumerates four modules + 32 tests; new 2026-05-26 notes entry. |

---

## Current Status

**Phases shipped:**
- §32 Phase 4 (deterministic matching engine, 9 tests).
- §32 Phase 2 (statement ingest, CSV + Excel siblings sharing helpers, 18 tests).
- 32/32 total green in 0.89s.

**Still gated, unchanged from 2026-05-25:**
- §38.1 stack sign-off (Cloud SQL + Firebase candidate vs alternative) → Phase 0 foundation, persistence, RBAC middleware.
- §38.2 sign-off + Brisken Anthropic Pro API access → Phase 5 LLM judgment layer code.
- §38.5 mobile-scanning approach → Phase 3 OCR + mobile capture page.
- Chris's real CSV/xlsx + receipt folder + chart-of-accounts → real-data match-rate measurement, tip-tolerance tuning, FX_JUDGMENT volume estimate.

**Brisken is not a Make/n8n/Trigger.dev client; ops-status line not applicable** (`infrastructure.yaml` tier is `"unknown"` by design: custom SaaS build).

**No comms-log exists for brisken yet** — staleness check skipped. Same observation as the 2026-05-25 checkpoint's Suggestions section; still worth creating when the next Dirk or Chris contact lands.

---

## Next Steps

1. **Send v2.1 to Dirk** (unchanged from 2026-05-25 next steps) — three sign-off points still pending: §38.1 (Cloud SQL + Cloud Storage split or single-store-via-Cloud-SQL-files), §38.2 (Vertex EU vs Bedrock eu-central-1 vs Brisken-Pro-direct), §38.5 (directive locked; tech pick deferred). The Excel parser landing today doesn't change this gate.
2. **Request Chris's first data sample** (unchanged) — one statement file (CSV or .xlsx, both work now), one receipt folder, one Zoho chart-of-accounts export.
3. **Get API access to Brisken's existing Anthropic Pro subscription** (unchanged Dirk task-list item).
4. **Schedule joint call with Chris** once Dirk briefs her.
5. **When Chris's data lands:** add column-map for her actual headers; run `parse_statement_csv` or `parse_statement_xlsx` against her real month; feed into `match_month`; report (a) deterministic match-rate vs Dirk's ~99% baseline, (b) FX_JUDGMENT volume to inform LLM-layer sizing, (c) tip-tolerance signal (current default 20% may need re-tuning).
6. **If neither §38 nor Chris's data has moved by the next session:** build the synthetic-receipt OCR-noise generator (the Branch-3 alternative deferred today), so the matcher can be exercised at scale on Chris-shaped data before real OCR lands.
7. **Create `workspace/clients/brisken/context/comms-log.md`** at the next inbound Dirk/Chris contact — same suggestion as 2026-05-25.

---

## Context for Next Session

### Files to Read First
- [PROJECT-BOUNDARIES.md](../../workspace/clients/brisken/PROJECT-BOUNDARIES.md) — binding scope ledger.
- [v2 functional spec (v2.1)](../../workspace/clients/brisken/specs/1-spec/p1-expense-reconciliation-functional-spec.md) — binding for build decisions, especially §7.1, §15, §32, §38.
- [2026-05-25 Checkpoint](../2026-05-25%20-%20Brisken%20Functional%20Spec%20v2%20and%20Build%20Start/Checkpoint.md) — prior session's three-branch resume tree, still the controlling decision tree.
- [2026-05-20 call outcomes](../../workspace/clients/brisken/context/2026-05-20-call-outcomes.md) — Dirk's authoritative decisions.
- [automations/expense-reconciliation/README.md](../../workspace/clients/brisken/automations/expense-reconciliation/README.md) — current build state, now lists Phase 2 + Phase 4.
- [ingest/_common.py](../../workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py) — shared parser contract surface.

### Open Questions
- Will Chris's actual statement export be CSV or .xlsx? (Both supported now; her bank choice will pick the active parser.)
- What are Chris's actual column headers? (Drives the `column_map` for her real month.)
- Does her bank export include a `posting_date` column, or just a transaction date? (Affects matcher's weekend/bank-delay tolerance.)
- Multi-sheet workbook concern: do any real bank exports put data in a non-default sheet? The `sheet_name` arg is in place, but the default (active sheet) handles the common single-sheet case.

### Working Notes
- The Excel parser uses `openpyxl.load_workbook(filename, read_only=True, data_only=True)`. `data_only=True` returns cached cell values for formulas — if Chris's export has formulas evaluating to her numbers, this avoids us seeing the raw formula string. Worth verifying once we have a real export.
- The integration test (`test_integration_parser_to_matcher_happy_path`) is the smallest demo proving xlsx → matcher composes correctly; use it as a copy-template when Chris's real .xlsx lands.
- All amount values round-trip cleanly through `Decimal(str(value))`. Verified for 0.1, 0.2, 1.05 (classic IEEE-754 binary noise traps). If a Brisken export ever shows fractional cents (sub-0.01 precision), Decimal preserves them — no quantization done in the parser.
- The `bool` rejection guards against a real Excel footgun: spreadsheet users sometimes type `TRUE`/`FALSE` in error and Excel auto-coerces to bool. Without the guard, that becomes `Decimal(1)` silently.
- Session pressure was low this session (~25 tool calls, single client, single feature). No checkpoint mid-session needed; this is the end-of-session checkpoint.

### Reference Materials
- v2 spec §7.1 (statement intake), §15 (matcher), §32 (phase order), §38 (open research items / candidate stack answers).
- 2026-05-25 checkpoint Working Notes (carries the cd-in-Bash workaround + brisken comms-log absence).
- openpyxl docs (Workbook, iter_rows, data_only): https://openpyxl.readthedocs.io/

---

## How to Continue

`/resume brisken`. The 2026-05-26 context YAML carries brisken so resume takes the fast path. The 2026-05-25 three-branch resume tree still controls — re-evaluate which has moved:

- **If Dirk has reviewed v2.1:** lock §38 picks into the spec, advance candidate → decided; if §38.1 picks GCP+Cloud-SQL, begin Phase 0 foundation.
- **If Chris's data has arrived:** add column-map, parse her file (CSV or .xlsx — both work now), run the matcher, report the actual match-rate.
- **If neither has moved:** build the synthetic-receipt OCR-noise generator (the Branch-3 alternative deferred today).

---

## Strategic Feedback

### What Worked Well This Session
- **The resume tree from the prior checkpoint was directly executable.** Reading the three branches, doing the four lightweight checks (context/, reference/, fixtures/, sessions log) to determine which branch fired, and proceeding — that whole front-of-session decision took ~5 tool calls. Cheap, structural, no user input needed.
- **Single-feature focus.** Picked Excel over the synthetic-receipt alternative early and stuck with it; no scope creep into a second feature even though the test infrastructure made it tempting. The result is a tight, testable, end-to-end-verified addition rather than two half-built things.
- **Behavioral verification language at B2.** The pytest hook fired after the test run, and the response named specific tests proving real behavior (binary-noise guard, line-number on real malformed file, multi-sheet routing, end-to-end matcher integration) rather than handwaving "tests pass". That format is reusable for any future B2 declaration.

### Suggestions
- **Lift the CSV-fixture pattern out of `tests/fixtures/`.** The existing `sample_amex_export.csv` is committed as a file; the new xlsx tests generate fixtures in-memory. The in-memory pattern is cleaner (no binary, fully reproducible, easy to vary per test). Worth considering deleting the static CSV fixture and switching `test_statement_csv.py` to the same `_write_csv(path, rows, headers)` helper pattern — would unify both test files and remove a committed fixture. Defer until the next CSV-side change.
- **Consider lifting `ingest/_common.py` further** if a third statement format ever lands (PDF? Bank MT/CAMT per v2 spec §7.1 "Statement intake (future)"). The current shape (`parse_date`, `parse_amount`, `StatementParseError`, `validate_required_map`) is the right surface for any tabular ingest — no premature abstraction, just well-placed sharing.

### System Health
- **Test infrastructure stayed friction-free.** `uv run --with 'pytest>=8.0' --with 'openpyxl>=3.1' pytest -v` worked first try; no virtualenv plumbing the user managed. The 2026-05-25 suggestion to lift this pyproject shape into `templates/` for the next stack-independent client build still stands.
- **Autonomy score: 0 user interventions this session.** No corrections, no redirects, no user-performed tasks. The resume directive from the user was clear enough that no clarifying questions were needed; the four pre-flight checks were enough to confirm Branch 3.
- **cd-in-compound-Bash workaround held.** Used the documented `(cd ... && uv run ...)` subshell pattern; PreToolUse hooks did not fire on it. This is the 4th session using the workaround successfully — the 2026-05-25 checkpoint's "PreToolUse:Bash hook overdue" suggestion still stands but the workaround is reliable enough that this is no longer urgent friction. Worth a system-dev round when convenient, not today.
- **Gates: B1:5 B2:3 B3:0 B4:2 skipped:0.** Clean B1 application on the four pre-flight checks. B2 fired correctly after each major edit cluster. No diagnostic situations so B3 didn't apply. B4 fired on every infrastructure.yaml / README value (test counts, file paths, dates all traced to verified sources).

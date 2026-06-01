# Checkpoint: Brisken Expense Recon Slice 2 LLM Categorizer

**Date:** 2026-06-01
**Status:** Slice 2 part 1 (OpenAI LLM categorizer) shipped locally, verified end-to-end against real API. Slices 1 + 1.5 + 3a + 3a-part-2 + 2-part-1 all sit uncommitted pending explicit ship order (B6).

---

## Summary

Built the entire working brisken expense-reconciliation tool across this thread, then pivoted slice 2 from Anthropic to OpenAI when the user supplied an OpenAI service-account key and said "just use it". Working state today: 74/74 tests passing, real `expense-recon --config examples/run.with-llm.example.json` produces a 5+N sheet xlsx with line-item-level LLM categorization for $0.00029 per run. Output proves the LLM path beats the keyword stub on the canonical "Coffee beans 2kg" case (LLM correctly classifies as Office Supplies; stub returns Meals because `"coffee"` is in `_LINE_KEYWORDS`).

---

## What Was Done This Session

This thread spans three calendar days due to system-clock changes; work is grouped by slice not by date because the slices were built sequentially across the session, not on isolated days.

### Slice 1 — End-to-end CLI tool (originally shipped earlier in the thread)
1. Created `judgment.py` LLM-judgment stub (FX cases return `[STUB]` reason, never auto-resolve).
2. Created `output/report_xlsx.py` (initial 4-sheet structure, rewritten in slice 1.5).
3. Created `ingest/receipts_csv.py` (slice-1 bridge for pre-extracted receipt fields).
4. Created `cli.py` (config-driven entry point: `expense-recon --config run.json`).
5. Updated `pyproject.toml` with hatchling build-system + `expense-recon` console script.
6. 8 integration tests covering end-to-end pipeline + FX-stub contract.
7. Authored `BLUEPRINT.md` (full remaining-build plan, gates, slice map, risk register, done-state checklist).
8. Authored `ANNEALING.md` (30 deferred-quality items across 5 categories, ranked by trigger).

### Slice 1.5 — Line-item categorization design (LD-1/2/3/4)
1. User-locked design decisions: 8 expense categories (LD-1), strict line-item-only classification rule with vendor-fallback marked `VENDOR ⚠` (LD-2), 5+N sheet output structure (LD-3), three-tier row coloring (LD-4).
2. Added `LineItem` + `Categorization` + `ClassificationSource` to `matching/types.py`; extended `Receipt` with `line_items`.
3. Updated `ingest/receipts_csv.py` to accept a `line_items` JSON-in-CSV column.
4. Created `categorize.py` with deterministic keyword stub (signatures match the eventual LLM swap).
5. Rewrote `output/report_xlsx.py` for the 5+N structure: Summary + per-card tabs + Needs Review + Unmatched + Errors.
6. Rewrote integration tests for the new structure (~13 tests).

### Slice 3a defensive items (no gate dependencies)
1. **B1** — All three parsers now expose tolerant variants (`parse_X_tolerant`) returning `(rows, list[ParseIssue])`. Header errors still raise; row errors collect. CLI uses tolerant mode; parse errors land in the Errors sheet without aborting the run.
2. **B4** — `--dry-run` flag prints Summary counts to stdout, skips xlsx write.
3. **B5** — Receipt CSV `document_id` dedup with explicit error (now lands in Errors sheet under the B1 tolerant umbrella).
4. **B7** — `examples/run.example.json` + `examples/statement.example.csv` + `examples/receipts.example.csv` + `examples/README.md` committed (in the local tree); `.gitignore` skips generated `report*.xlsx`.

### Slice 3a part 2
1. **B2** — `expense-recon-inspect` second console script. Regex heuristic library covers EN headers + DE Amex (Buchungsdatum / Beschreibung / Betrag / Währung). Posting-date doesn't steal transaction-date (greedy priority order). 12 unit tests.
2. **B8** — `justfile` with targets: `sync`, `recon CONFIG`, `dry-run CONFIG`, `inspect FILE`, `example`, `test`, `test-x`, `clean`.

### Slice 2 part 1 — OpenAI LLM categorizer (today's headline ship)
1. **Provider pivot**: Anthropic → OpenAI after user supplied an `sk-svcacct-...` key and said "just use it". `LLMClient` Protocol is provider-agnostic; swap class to swap provider.
2. Created `llm/client.py` — `LLMClient` Protocol + `OpenAIClient` (production, `gpt-4o-mini`) + `MockLLMClient` (tests).
3. Created `llm/cost.py` — `TokenUsage` + `CostTracker`; pricing table for gpt-4o-mini / gpt-4o / gpt-4.1 family.
4. Updated `categorize.py`: `categorize_receipts(receipts, client=...)`. When `client` provided, uses LLM batched call per receipt's line items (or vendor-fallback call when items absent/vague). When `client=None`, falls back to keyword stub (slice 1.5 behavior preserved).
5. Updated `cli.py`: reads optional `llm:` block from config, instantiates `OpenAIClient` from `OPENAI_API_KEY` env var. Missing env var raises clean `ConfigError`. Cost surfaced on Summary sheet.
6. Real bug fix in `_is_vague`: substring match (`"fee" in "coffee"`) was silently flagging "coffee beans" as vague. Now uses word-boundary regex.
7. 14 LLM-path tests in `test_categorize_llm.py` covering: per-line categorization, batched call cost discipline, REVIEW threshold, invalid-category routing, vendor fallback, cost tracker math, CLI llm-block loading, env-var missing case, no-llm-block fallback.
8. Live OpenAI smoke run: `OPENAI_API_KEY=... uv run expense-recon --config examples/run.with-llm.example.json` produced 9272-byte report.xlsx for **$0.00029**. Coffee beans → Office Supplies (correct), chair → Equipment, HDMI → Equipment, Uber / Delancey → vendor-fallback marked `VENDOR ⚠`. Card total $328.05 matches statement sum.
9. Updated BLUEPRINT.md (Provider Pivot block), ANNEALING.md (D1 + D2 + D3 strikethrough), README.md (test count + Slice 2 section).

### Hours tracker logging + new feedback memory
1. Logged 7.5h of brisken work today as 2 rows in `workspace/hours-tracker.xlsx` (10:00-13:00 + 14:00-18:30).
2. User rejected first version of task strings for AI tells (em-dashes, parenthetical laundry-lists, formal class names mid-sentence, slash-joined filenames).
3. Rewrote rows in human voice ("openai client wrapper, hooked categorizer up to it, added cost tracking" / "llm tests, live api smoke, fixed vague-check bug, doc updates").
4. Cleared all other rows from the sheet on user request; left `_meta` sheet intact so sync-hours dedup state is preserved.
5. Saved `feedback_human_voice_in_deliverables.md` + indexed in MEMORY.md so future ghost-written spreadsheet/ticket/log fragments stay human-voiced.

---

## Key Decisions Made

### Provider pivot from Anthropic to OpenAI
- **Choice:** Slice 2 LLM provider is OpenAI gpt-4o-mini (text) with gpt-4o reserved for vision in part 2. Reverses §38.2 stack decision.
- **Rationale:** User supplied an `sk-svcacct-...` OpenAI service-account key and directed "just use it. if its an open ai key or not". The `LLMClient` protocol is provider-agnostic, so this is one file's worth of swap if Brisken later moves to Anthropic / Vertex Claude / Bedrock.

### Eight expense categories, locked
- **Choice:** Travel & Transport, Meals & Entertainment, Software & Subscriptions, Office Supplies & Consumables, Equipment & Hardware, Marketing & Advertising, Professional Services, Utilities & Premises.
- **Rationale:** Built for a small-business SaaS-era P&L. New categories are added explicitly (`EXPENSE_CATEGORIES` constant) — never inferred. Two intentional omissions: no Bank Fees (lands on statement as direct debit, no receipt to categorize) and no Cost of Goods Sold (Brisken is services, not stocked goods). Add a 9th explicitly if Brisken ever sells physical products.

### Strict line-item-only categorization (LD-2 hard rule)
- **Choice:** Vendor name is NEVER an input to the Tier 1 classifier. Receipts with line items get per-line categorization from the line text alone. Receipts without line items fall back to a vendor-based call marked `VENDOR ⚠`. Sub-threshold confidence routes to `REVIEW`.
- **Rationale:** User caught the design gap directly: "Alot of times for example the vendor isnt direct proof for the specific vendors most common product/service. Therefor the exact details on the receipt should be looked at to see what exactly was bought." The Amazon case proves the value: chair + coffee beans + HDMI all need different categories that vendor name can't disambiguate.

### One receipt → N journal entries
- **Choice:** Multi-line receipts produce one Excel row + one Zoho journal entry per line item, all tied to the same source transaction via Reference#.
- **Rationale:** Matches Zoho's native support for split expenses; preserves the categorization accuracy of LD-2 all the way to the posting system.

### 5+N sheet output structure
- **Choice:** Summary + one tab per credit card (chronological within, with category subtotals at bottom) + Needs Review (Tier 2 + Tier 3 aggregated) + Unmatched + Errors.
- **Rationale:** User-chosen after design back-and-forth. Per-card tab matches how Chris reviews (one bank statement at a time); Summary's by-card × by-category matrix gives the cross-card overview. Three-tier row coloring (green/yellow/orange/red) lets her eye scan for what needs touching.

### Tolerant parsing (B1) instead of strict
- **Choice:** CLI uses tolerant parser variants; row errors land in the Errors sheet, surrounding rows still reconcile. Header errors still raise (config-class).
- **Rationale:** First real Brisken month is near-certain to have at least one malformed row; abort-on-first-bad-row would lose all the good data. Tolerant mode means Chris sees the bad row called out and the good 99 still get processed.

### Hours tracker entries in human voice
- **Choice:** Spreadsheet cell content must read as human-to-human. No em-dashes, parenthetical laundry-lists, formal class names mid-sentence, fake-precision counts, or slash-joined filename runs.
- **Rationale:** User flagged it directly. The tracker is billing-visible; AI fingerprints in cells are inappropriate context. Generalized into `feedback_human_voice_in_deliverables.md` so it covers tickets, log notes, ghost-written fragments, error strings too.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` | Created + Provider Pivot block + Slice 2/4 deliverable revisions | Full remaining-build roadmap with gates, slices, risks, done-state |
| `workspace/clients/brisken/automations/expense-reconciliation/ANNEALING.md` | Created + 8 items struck through (B1, B2, B4, B5, B7, B8, D1, D3) | Rolling punch-list of deferred quality items |
| `workspace/clients/brisken/automations/expense-reconciliation/README.md` | Multiple updates (test count, layouts, Slice 2 section, run/inspect docs) | Onboarding doc + test count + file layout |
| `workspace/clients/brisken/automations/expense-reconciliation/pyproject.toml` | Added `openai>=1.50`, `expense-recon-inspect` script, hatchling build | Dep + console scripts + build backend |
| `workspace/clients/brisken/automations/expense-reconciliation/.gitignore` | Extended | Skip generated `examples/report*.xlsx` |
| `workspace/clients/brisken/automations/expense-reconciliation/justfile` | Created | `sync`, `recon`, `dry-run`, `inspect`, `example`, `test`, `clean` shortcuts |
| `src/expense_recon/cli.py` | Multiple (tolerant parsers, --dry-run, llm: block, cost tracker) | Single CLI entry; reads `llm:` config; surfaces cost |
| `src/expense_recon/categorize.py` | Created + LLM path + word-boundary `_is_vague` bug fix | LD-2 categorizer (LLM and keyword-stub paths share signature) |
| `src/expense_recon/inspect.py` | Created | `expense-recon-inspect` heuristic column-map guesser |
| `src/expense_recon/llm/__init__.py` | Created | `llm` package surface |
| `src/expense_recon/llm/client.py` | Created | `LLMClient` Protocol + `OpenAIClient` + `MockLLMClient` |
| `src/expense_recon/llm/cost.py` | Created | `TokenUsage` + `CostTracker` per-run aggregator |
| `src/expense_recon/matching/types.py` | Extended | `LineItem`, `Categorization`, `ClassificationSource`, `EXPENSE_CATEGORIES`; `Receipt.line_items` added |
| `src/expense_recon/matching/judgment.py` | Created | FX-judgment stub (slice 1; still STUB; deferred under D1b) |
| `src/expense_recon/ingest/_common.py` | Extended with `ParseIssue` | Shared header-vs-row error model |
| `src/expense_recon/ingest/receipts_csv.py` | Multiple (line_items column, dedup, tolerant) | Slice-1 bridge for pre-extracted receipts |
| `src/expense_recon/ingest/statement_csv.py` | Tolerant variant added | Header errors still raise; row errors collect |
| `src/expense_recon/ingest/statement_xlsx.py` | Tolerant variant added | Same posture as CSV |
| `src/expense_recon/output/__init__.py` | Created | `output` package surface |
| `src/expense_recon/output/report_xlsx.py` | Created + LD-3 5+N rewrite | Excel review report with Summary + per-card tabs + Needs Review + Unmatched + Errors |
| `tests/test_cli_integration.py` | Multiple (16 tests including LD-2/3/4 assertions + B1 tolerant flow + B4 dry-run) | End-to-end pipeline assertions |
| `tests/test_inspect.py` | Created (12 tests) | Heuristic column-map guesser unit tests |
| `tests/test_categorize_llm.py` | Created (14 tests) | LLM-path categorizer + cost tracker + CLI llm-block integration |
| `workspace/clients/brisken/automations/expense-reconciliation/examples/run.example.json` | Created | Copy-paste-able config for keyword-stub path |
| `workspace/clients/brisken/automations/expense-reconciliation/examples/run.with-llm.example.json` | Created | Same shape with `llm:` block to exercise the OpenAI path |
| `workspace/clients/brisken/automations/expense-reconciliation/examples/statement.example.csv` | Created | Synthetic 5-row Amex shape |
| `workspace/clients/brisken/automations/expense-reconciliation/examples/receipts.example.csv` | Created | Synthetic 4-receipt set including Amazon multi-line case |
| `workspace/clients/brisken/automations/expense-reconciliation/examples/README.md` | Created | Onboarding doc for a new bank format |
| `workspace/hours-tracker.xlsx` | 2 brisken rows added + all other rows cleared | 7.5h logged today as Row 2 + Row 3 |
| `~/.claude/projects/.../memory/feedback_human_voice_in_deliverables.md` | Created | Generalizes voice-pass rule to spreadsheet cells, tickets, ghost-written fragments |
| `~/.claude/projects/.../memory/MEMORY.md` | Index pointer added | Memory index |

Test count trajectory across the thread: 9 (slice 1 start) → 32 (Phase 2 + 4) → 40 (slice 1 CLI) → 45 (slice 1.5) → 48 (slice 3a) → 60 (slice 3a part 2) → **74/74 passing** (slice 2 part 1).

---

## Current Status

**Brisken is not a Make / n8n / Trigger.dev client; ops-status line not applicable.** `infrastructure.yaml` tier is `unknown` by design; this is a custom Python SaaS tool, not a workflow engine.

**Uncommitted ship-pile.** Slices 1, 1.5, 3a, 3a-part-2, and 2-part-1 all sit local. No commit, no PR, no merge. Ship boundary is the user's call per `rule_no_auto_commit.md` B6.

**Slice 2 part 1 verified end-to-end.**
- `uv sync && uv run expense-recon --config examples/run.example.json` (keyword-stub path) works.
- `OPENAI_API_KEY=... uv run expense-recon --config examples/run.with-llm.example.json` (LLM path) works.
- Live OpenAI cost for the 4-receipt example: $0.00029. Projects to ~$0.015-0.06/month for Brisken's expected receipt volume.
- 74/74 tests green in <2s. `uv run --with 'pytest>=8.0' pytest` is the canonical command.

**OpenAI key exposure pending rotation.** User's `sk-svcacct-yQtFt...` key is now in this transcript permanently. Used for one live test ($0.00029). Standard practice is to rotate; cost is zero. Not yet done.

**Brisken comms.** No `comms-log.md` exists for brisken (noted in 3 prior brisken checkpoints; the suggestion to create one is now stale enough to be an `infrastructure-deferred` candidate).

---

## Next Steps

1. **Rotate the exposed OpenAI key.** Revoke `sk-svcacct-yQtFt...` in OpenAI Platform → API keys, generate fresh service-account key, store in `.env.brisken` outside the repo. Cost: 30 seconds. Closes the exposure.
2. **User decides ship strategy.** Options: one big commit for slices 1 + 1.5 + 3a + 3a-part-2 + 2-part-1; OR split per slice (5 commits / 5 PRs); OR a hybrid. Once ordered, the auto-tracker `tools/sync-hours.py` will pick up the brisken commits and populate hours-tracker rows going forward.
3. **Send Dirk a "working tool" update.** Slice 2 part 1 verifies the categorization pipeline against the 4-receipt synthetic example. The next gate-resolution items remain unchanged: Chris's first real-data sample (statement + receipt folder + chart-of-accounts), API access to Brisken's existing Anthropic Pro subscription (now MOOT given the OpenAI pivot — surface that explicitly), Zoho Books API access vs file-export decision.
4. **When Chris's data lands** (real bank statement + real receipt folder): build slice 2 part 2 (vision OCR replacing `parse_receipts_csv` with `parse_receipts_vision`). Tune the vision prompt against actual receipt shapes (PDF, photo, email-attachment, OCR-noisy). Land matcher-quality items A1/A2/A3/A5 from ANNEALING calibrated to whatever Chris's data actually breaks.
5. **When Zoho access lands**: build slice 4 (chart-of-accounts ingestion + Zoho export CSV). One row per categorized line item per LD-2.
6. **Optional bite-sized work that's unblocked now**: C3 (structured logging), D1b (FX judgment LLM call swap when first FX case hits — currently still STUB), E5 (CI workflow on `.github/workflows/`).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` — full remaining-build plan; Provider Pivot block at top notes the OpenAI swap
- `workspace/clients/brisken/automations/expense-reconciliation/ANNEALING.md` — rolling punch list; 8 items struck through this session
- `workspace/clients/brisken/automations/expense-reconciliation/README.md` — current Slice 2 section + run instructions + file layout
- `workspace/clients/brisken/PROJECT-BOUNDARIES.md` — binding scope ledger (still active = expense-reconciliation p1; lead-nurturing remains paused)
- `workspace/clients/brisken/infrastructure.yaml` — note the `platform.tier` is still `unknown` and `build_artifacts` doesn't yet reflect slice 2 part 1 (worth updating when the ship lands)
- `src/expense_recon/llm/client.py` — the provider-agnostic surface; slice 2 part 2 vision OCR will add `extract_receipt(image_bytes, media_type)` to the protocol
- `src/expense_recon/categorize.py` — LD-2 strict rule lives here; the keyword stub fallback is intentional and tested

### Open Questions
- Ship strategy: one big commit or split per slice? (Pending user decision; B6 gate.)
- Has the OpenAI key been rotated? (Pending; should be done before next session uses the key.)
- When will Chris's first real-data sample land? (Unchanged from prior brisken checkpoints; Dirk-to-Chris brief is the unblocker.)
- Has Dirk reviewed BLUEPRINT? (Authored this session; not surfaced to him yet via comms.)
- §38 stack decision is now MOOT for the MVP-for-Brisken scope (OpenAI selected, custom Python platform, no multi-tenant DB needed). Worth a one-line note to Dirk that §38.1 / §38.2 research can stop.

### Working Notes
- **Coffee-beans test case.** `examples/receipts.example.csv` Amazon receipt has `Herman Miller chair $150 / Coffee beans 2kg $30 / HDMI cable $20`. The LLM correctly classifies coffee beans as Office Supplies; the keyword stub returns Meals because `"coffee"` is in `_LINE_KEYWORDS`. This is the demo case for any "is the LLM actually better than the stub" question.
- **CWD violation recovery.** Mid-session I ran `cd workspace/clients/brisken/...` which persisted across bash invocations, breaking the relative `.claude/hooks/*.py` lookups. Recovery cost a PowerShell `Set-Location` round trip. The `cd-guard.py` hook fired on subsequent attempts but couldn't undo the initial drift. CLAUDE.md rule says use absolute paths or subshells. This is the second `cd`-drift slow-path in the friction register (prior: 2026-05-20).
- **`_is_vague` substring bug.** Slice 1.5's vagueness check used `any(token in desc for token in _VAGUE_DESCRIPTION_TOKENS)`. `"fee"` matched `"coffee"` as a substring, silently triggering vendor-fallback whenever a receipt had a single line item containing such a substring. Real bug, real fix (word-boundary regex), found via running an integration test by hand to isolate.
- **Mock client + cost discipline.** `MockLLMClient.cost_tracker` records a fixed $0.001 per call; tests that assert cost accumulation use this nominal value. Production `OpenAIClient` records actual `response.usage` from the OpenAI SDK against the `_PRICING_PER_MILLION` table.
- **Vision OCR deferral rationale.** Slice 2 part 2 is intentionally deferred until Chris's first receipt folder lands because the vision prompt needs tuning against actual receipt shapes (PDF, photo, screenshot, email-attachment, OCR-noisy). Building it against synthetic examples first and then re-tuning against real shapes would be wasted work.

### Reference Materials
- Provider docs: https://platform.openai.com/docs/api-reference/chat/create (structured outputs / json_schema)
- OpenAI pricing: https://openai.com/api/pricing/ (gpt-4o-mini $0.15/M input + $0.60/M output)
- `feedback_human_voice_in_deliverables.md` — new memory authored this session
- `rule_deliverables.md` — em-dash ban that the new memory generalizes from HTML to spreadsheet cells

---

## How to Continue

`/resume brisken`. The 2026-06-01 context YAML has a brisken block now, so resume takes the fast path. The 4-branch resume tree from prior brisken checkpoints still controls:

- **If Dirk has signed off on something or sent comms:** check `workspace/clients/brisken/context/` and `workspace/clients/brisken/reference/` for new files; check Gmail for inbound. Brisken still has no `comms-log.md` (track-this).
- **If Chris's first data has arrived:** drop her statement file + receipt folder into the run config, run the CLI, see what the real data breaks. Slice 3b matcher-quality items A1/A2/A3/A5 are pre-staged in ANNEALING.
- **If the user wants to ship**: explicit order, then commit + push + PR + merge per B6. Auto-tracker picks up entries on next sync-hours run.
- **If neither moved**: bite-sized unblocked items — C3 (structured logging via Python `logging`), D1b (FX-judgment LLM call swap, ~30 min), E5 (CI workflow). Don't pre-build slice 2 part 2 (vision OCR) before Chris's data — vision-prompt tuning needs real receipts to anchor against.

---

## Strategic Feedback

### What Worked Well This Session

- **The "STOP — that prefix is OpenAI, not Anthropic" surfacing.** When the user pasted an `sk-svcacct-...` key labeled as Anthropic, the correct move was to flag the prefix mismatch + ask which provider before building. User's directive to use it anyway was a clear redirect, but the surface was the right pattern: high-blast-radius forks (provider choice changes the entire slice 2 SDK) deserve confirmation, even when the user is moving fast.
- **Provider-agnostic protocol.** `LLMClient` Protocol with `OpenAIClient` + `MockLLMClient` implementations made the provider pivot mechanical. The day the user supplied an OpenAI key instead of an Anthropic key, the only file that actually needed to know about OpenAI was `llm/client.py`. Categorizer, CLI, tests, output writer all stayed identical.
- **Smoke + named tests as the B2 evidence.** Every "shipped" claim this session named specific tests + a real CLI smoke result. The "Coffee beans → Office Supplies" demonstration is reusable: it's the simplest case that proves the LLM beats the keyword stub on real-world ambiguity.

### Suggestions

- **The `cd workspace/...` violation is now a 2-strike slow-path** (2026-05-20 platform + 2026-06-01 brisken). CLAUDE.md documents the rule; agents keep violating it. Structural fix worth building: `cd-guard.py` (which already exists) could be extended to detect `cd <relative-path>` patterns even on the FIRST invocation, not just subsequent ones, and refuse — forcing the agent to either use absolute paths or `(subshell && cmd)`.
- **The hour-tracker AI-tells incident was a missed B4 gate** — the data-into-deliverable boundary should have triggered a voice-pass before writing, but I didn't notice that timesheet cell content counts as a deliverable. The new `feedback_human_voice_in_deliverables.md` covers this going forward, but it's memory-class fix. Structural alternative: extend `tools/validate-output.py` (the post-write linter) to scan committed Excel/CSV/YAML cell content against the same banned-construction list it applies to markdown.

### System Health

- **Autonomy score: 3 human interventions this session (elevated — run /system-dev to close gaps).** Tally: (1) user caught AI tells in hours-tracker entries → fix=memory (B4 skipped); (2) stop-b1-gate hook caught two B1 deferral patterns ("If you want, I'll loop" / "close excel and tell me to retry") → fix=structural (hook held); (3) slow-path on CWD recovery after `cd workspace/...` violation → fix=needs-structural (cd-guard exists but didn't catch the initial violation).
- **The agentic-ops voice-pass story is still scattered.** `rule_deliverables.md` covers HTML em-dashes + PDF voice-pass + video scripts. `feedback_no_em_dashes` covers em-dashes specifically. The new `feedback_human_voice_in_deliverables.md` covers spreadsheet cells + ghost-written fragments. There's no single "deliverable voice" rule; each artifact class has its own subset. Worth a `/system-dev` round to consolidate into one Layer 1 rule with per-artifact subsections.
- **Brisken `comms-log.md` is a 3-checkpoint stale-suggestion.** Suggested on 2026-05-25, 2026-05-26, 2026-06-01. None of those sessions had inbound comms to trigger creation, but the recurrence pattern itself is `infrastructure-deferred` material — every brisken checkpoint surfaces the suggestion, no checkpoint acts. Tool fix: auto-create the file on first brisken checkpoint that touches `context/` if it doesn't exist.
- **Tests-not-committed risk.** 74 passing tests sit locally with no CI gate to catch regressions. Slice 2 part 2 will add receipt-vision tests that need a mock-vs-real-OpenAI gate; building the CI workflow now would prevent a class of "I broke the existing tests while building the next thing" friction. ANNEALING E5 is staged.

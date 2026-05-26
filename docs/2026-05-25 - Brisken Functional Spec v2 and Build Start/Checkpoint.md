# Checkpoint: Brisken Functional Spec v2 and Build Start

**Date:** 2026-05-25
**Status:** Active. v2 functional spec (with v2.1 candidate addendum for Dirk approval) shipped; build began with the deterministic matching engine (Phase 4) and CSV statement parser (Phase 2). 18/18 tests green. Further code blocked on §38 stack sign-off OR Chris's real data sample.

---

## Summary

Took the Brisken expense-reconciliation project from "v1 functional doc not in repo" to "v2 spec in repo, Dirk's three candidate stack answers folded in as v2.1 with tensions flagged, and two stack-independent code layers shipped with full test coverage." Dirk's mid-session directive ("north star is reducing Chris's grind days->minutes; begin the build now") promoted Phase 4 ahead of the §32 phase order because it's the value-prop core and is stack-independent.

---

## What Was Done This Session

### Spec landing (v1 + v2)
1. User provided Dirk's 2026-05-14 functional doc. Preserved verbatim to `reference/2026-05-14-functional-spec-original.md` (primary source, do not edit).
2. Read v1 line-by-line per Dirk's directive (call-outcomes Part 2 "Comprehension directive"); wrote v2 functional spec to `specs/1-spec/p1-expense-reconciliation-functional-spec.md` (39 sections, every delta traced inline to call-outcomes file).
3. Added v2.1 same-day addendum for Dirk's three candidate stack answers (GCP + Cloud SQL + Firebase services; Vertex AI EU OR Bedrock eu-central-1; "simplest mobile scanning" directive). Three flagged reversals of explicit call decisions noted inline so Dirk approves the proposal AND the reversal together: single-store reversed by Cloud Storage; Brisken-Pro Anthropic subscription reversed by Vertex/Bedrock; "no AWS as provider" reversed specifically by Bedrock.

### Supporting docs updated
4. `PROJECT-BOUNDARIES.md` — added v1/v2/automations live artifacts; 2026-05-24 swap entry for spec landing + 2026-05-25 swap entry for build start.
5. `specs/README.md` — restructured into Active (p1) vs Paused (a0-a4) sections; added Phase 4 build artifact pointer.
6. `infrastructure.yaml` — captured v2.1 candidates with reversal flags; added `build_artifacts:` block; added 2026-05-25 build-started note.

### Build began (stack-independent code)
7. Scaffolded `automations/expense-reconciliation/` per PROJECT-BOUNDARIES path (pyproject, src layout, gitignore).
8. **Phase 4 deterministic matching engine** shipped (`src/expense_recon/matching/`):
   - Domain types (Transaction, Receipt, Match, MatchOutcome, MatchType enum) with three-currency-layer fields + tenant/entity scope.
   - Hybrid matcher: USD-on-USD same-day → `EXACT` at 0.99 confidence (Dirk's baseline); FX (EUR-on-USD card) short-circuits to `FX_JUDGMENT` for the LLM layer; tip tolerance 20% (tunable, comment explains); ambiguous detection; entity scope enforced at candidate-pair level; reconciliation-guarantee invariant covered by a dedicated test.
   - 9 tests, all green.
9. Plan mode interlude — wrote plan file, presented via ExitPlanMode, approved.
10. **Phase 2 CSV statement parser** shipped (`src/expense_recon/ingest/`):
    - `parse_statement_csv(path, column_map, account_id, legal_entity_id, account_card_currency) -> list[Transaction]`.
    - `StatementParseError` with `.line_number` for row-specific failures.
    - Date parsing tries ISO + MM/DD/YYYY + DD/MM/YYYY + YYYY/MM/DD; amounts as `Decimal`; accounting-style `(50.00)` negatives accepted; whitespace stripped; blank EOF rows skipped silently; malformed rows raise (reconciliation-guarantee posture).
    - Synthetic Amex-shaped fixture, 9 tests including end-to-end CSV → matcher integration.
11. **Final test run: 18/18 green in 0.11s.**

---

## Key Decisions Made

### Promote Phase 4 ahead of Phase 0
- **Choice:** Build the deterministic matching engine first, even though §32 lists it as Phase 4.
- **Rationale:** Dirk's directive made Chris's grind the north star; the matcher IS the value-prop core; it's stack-independent (survives any §38 outcome); de-risks the LLM judgment layer sizing once it runs against real data. Phase 0 multi-tenant foundations are stack-locked and a premature optimization until Dirk picks the stack.

### Add Phase 2 (CSV parser) in the same session
- **Choice:** Add the CSV statement parser immediately after the matcher.
- **Rationale:** The matcher needs Transactions to match against. The parser is the smallest piece that bridges "Chris's real CSV" to "list[Transaction]." Together they form a working vertical slice that can run against any real-world Brisken month without code changes — only column-map tweaks.

### Record v2.1 candidates as proposals, not overrides
- **Choice:** Fold user's three candidate stack answers (Cloud SQL/Firebase shape; Vertex AI EU vs Bedrock Frankfurt; "simplest mobile scanning" directive) into v2.1 with tensions flagged, not as locked decisions.
- **Rationale:** Two of the three candidates reverse explicit 2026-05-20 call decisions (single-store; Brisken-Pro Anthropic). Bedrock specifically reverses Dirk's "no AWS as provider." Dirk needs to approve the proposal AND the reversal in one pass, so the doc has to surface that nuance for him.

### Single-store posture on the Cloud SQL question
- **Choice:** Note in §26.3 that the GCP-native answer (Cloud Storage for receipts) splits the store, contradicting §9. Offer an alternative inline: keep single-store by having Cloud SQL hold the receipt files (workable but not GCP-native at scale).
- **Rationale:** Don't silently override Dirk's call decision. Surface the choice; let him pick.

### Default tip tolerance 20%
- **Choice:** `amount_probable_tolerance_pct = Decimal("0.20")` (was 0.10 initially; failed the tip test).
- **Rationale:** US tip range is 15-20%. Probable matches require review anyway, so being slightly loose costs only "Chris glances at extras"; being too tight costs "valid tip cases fall to unmatched, Chris hunts manually." The latter is worse. Comment notes this is a starting default to tune with Chris's real data.

---

## Files Modified

### Spec + supporting docs
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/reference/2026-05-14-functional-spec-original.md` | Created | Dirk's v1, preserved verbatim as primary source |
| `workspace/clients/brisken/specs/1-spec/p1-expense-reconciliation-functional-spec.md` | Created (then v2.1 edits) | v2 functional spec; binding for build decisions |
| `workspace/clients/brisken/PROJECT-BOUNDARIES.md` | Modified | v1/v2/automations artifacts + 2 swap-history entries |
| `workspace/clients/brisken/specs/README.md` | Modified | Restructured: Active (p1) vs Paused (a0-a4); Phase 4 artifact pointer |
| `workspace/clients/brisken/infrastructure.yaml` | Modified | v2.1 candidates with reversal flags; `build_artifacts` block; build-started note |

### Build code (`automations/expense-reconciliation/`)
| File | Action | Purpose |
|------|--------|---------|
| `README.md` | Created | Build entry: where we are, how to run, what we need from Chris |
| `pyproject.toml` | Created | uv project, Python >=3.12, pytest dev dep |
| `.gitignore` | Created | Python standard ignores + `.venv` |
| `src/expense_recon/__init__.py` | Created | Package init |
| `src/expense_recon/matching/__init__.py` | Created | Matching module overview (deterministic vs judgment separation) |
| `src/expense_recon/matching/types.py` | Created | Transaction, Receipt, Match, MatchOutcome, MatchType |
| `src/expense_recon/matching/deterministic.py` | Created (1 tolerance bump) | v2 §15.1 engine |
| `src/expense_recon/ingest/__init__.py` | Created | Ingest module overview |
| `src/expense_recon/ingest/statement_csv.py` | Created | v2 §7.1 CSV parser + StatementParseError |
| `tests/__init__.py` | Created | Test package init |
| `tests/test_deterministic_matching.py` | Created | 9 tests, all green |
| `tests/test_statement_csv.py` | Created | 9 tests including end-to-end integration, all green |
| `tests/fixtures/sample_amex_export.csv` | Created | Synthetic Amex-shaped CSV (7 rows, includes refund + whitespace edge) |

### Other
| File | Action | Purpose |
|------|--------|---------|
| `C:\Users\neuma_p1qrsic\.claude\plans\jaunty-coalescing-trinket.md` | Created (plan-mode interlude) | Approved before Phase 2 work |

---

## Current Status

**Phases shipped:** §32 Phase 4 (deterministic matching) + Phase 2 (CSV statement ingest). Both pure Python, both stack-independent, both green (18/18 tests). The integration test proves they compose: CSV → Transactions → MatchOutcome with the reconciliation-guarantee invariant preserved.

**Phases gated:**
- Phase 0 (foundation: multi-tenant, multi-entity, RBAC, storage) — gated on §38.1 stack sign-off.
- Phase 3 (OCR + mobile capture page) — gated on §38.1 stack pick + §38.5 mobile-scanning approach pick.
- Phase 5 (LLM judgment layer code) — gated on §38.2 sign-off + API access to Brisken's Anthropic Pro subscription.
- Phases 6/7 (review UI, Zoho posting) — gated on §38.1.

**What unblocks more code without §38 sign-off:** Chris's real Brisken month (one CSV statement + receipt folder + chart-of-accounts export). With that, the matcher runs against real data and produces the actual match-rate number that informs both the auto-approval policy default and the LLM-layer sizing.

**Brisken is not a Make/n8n/Trigger.dev client; ops-status line not applicable** (infrastructure.yaml tier is `"unknown"` by design: custom SaaS build, not a workflow-engine op count).

---

## Next Steps

1. **Send v2.1 to Dirk for review.** Three sign-off points: §38.1 (Cloud-SQL + accept-Cloud-Storage-split OR keep-single-store-on-Cloud-SQL); §38.2 (Vertex EU vs Bedrock-eu-central-1 vs hold-Brisken-Pro-direct); §38.5 (directive locked; tech pick deferred).
2. **Request Chris's first data sample** (one CSV statement + matching receipt folder + Zoho chart-of-accounts export). Quickest unblock for real-data validation of the matcher; runs against §38-independent code.
3. **Get API access to Brisken's existing Anthropic Pro subscription** (Dirk task-list item; do NOT create a new account). Unblocks Phase 5 LLM judgment layer code the moment §38.2 is signed off.
4. **Schedule joint call with Chris** once Dirk briefs her. Confirms split-cases scope (v2 §19), confidence thresholds (v2 §15.5), and the chart-of-accounts shape.
5. **Once Chris's data is in:** add the column-map for her actual CSV headers; run the matcher; report the actual deterministic match rate + the LLM-judgment volume estimate.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/PROJECT-BOUNDARIES.md` — binding scope ledger
- `workspace/clients/brisken/specs/1-spec/p1-expense-reconciliation-functional-spec.md` — v2 spec (v2.1) — binding for build
- `workspace/clients/brisken/context/2026-05-20-call-outcomes.md` — call source of truth
- `workspace/clients/brisken/automations/expense-reconciliation/README.md` — current build state
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py` — heart of the value prop

### Open Questions
- Will Dirk approve the Cloud-SQL-with-Cloud-Storage split, or insist on single-store-via-Cloud-SQL-files?
- Will Dirk reverse "no AWS as provider" for Bedrock-eu-central-1, or land on Vertex AI EU?
- What is Chris's actual CSV statement format (column names, date format, currency column presence)?
- What is Brisken's real legal-entity count (German GmbH out of scope per call; US count TBD)?
- Legal retention period — unchanged; awaits Brisken accountant.

### Working Notes
- The deterministic matcher's default tip tolerance was bumped 10%→20% on the first failing test. Real Brisken data may reveal whether 20% gives false positives at scale; revisit with Chris.
- The `StatementParseError(line_number=N)` posture is built so a future ingest UI can highlight the offending row to the user. The reconciliation guarantee invariant test asserts no silent drops.
- The integration test (`test_integration_parser_to_matcher_happy_path`) is the smallest demo that proves the end-to-end shape works. Useful as a copy-template once Chris's real CSV lands.
- For pytest runs from project root: use a subshell `(cd ... && uv run pytest)` to avoid leaking cwd into the persistent Bash session (which breaks PreToolUse hooks that resolve `.claude/hooks/` from cwd).
- The v2 spec uses several US-shaped financial assumptions (USD primary currency, eu-central-1 = Frankfurt = German enterprise sales). Confirm with Chris whether any other entities (UK, etc.) need first-class support sooner than v2 currently implies.

### Reference Materials
- Plan file from this session: `C:\Users\neuma_p1qrsic\.claude\plans\jaunty-coalescing-trinket.md`
- v2 spec §32 — implementation phase order
- v2 spec §38 — open research items + candidate answers
- v2 spec §26 — architecture (decided / rejected / candidate)

---

## How to Continue

`/resume brisken`. The 2026-05-25 context YAML carries brisken so resume takes the fast path. First substantive next move depends on which unblock fires first:

- **If Dirk has reviewed v2.1:** lock the §38 picks into the spec, advance from "candidate" to "decided"; if §38.1 picks GCP+Cloud-SQL, begin Phase 0 foundation (multi-tenant data model, RBAC middleware, audit-log scaffold).
- **If Chris's data has arrived:** add column-map, parse her CSV, run the matcher, report the actual match-rate. This is the highest-information experiment available.
- **If neither has moved:** continue with the next stack-independent piece — likely an Excel reader sibling to `statement_csv.py`, OR a synthetic-receipt OCR-stub generator that lets the matcher be exercised on Chris-shaped data without waiting on real OCR.

---

## Strategic Feedback

### What Worked Well This Session
- **The "preserve v1 verbatim before revising" pattern.** Dirk's directive to read line-by-line is now structurally enforced: v1 sits read-only in `reference/`, v2 cites it inline. Future sessions can't accidentally drift v1 because it's a primary-source artifact.
- **Vertical-slice-before-foundation choice.** Promoting Phase 4 ahead of Phase 0 when the foundation is stack-blocked is a clean pattern. The matcher + parser combination is a working pipeline that already serves the north-star metric; everything else is enabling infrastructure for production scale.
- **Plan-mode interlude.** User-activated plan mode mid-session caught me about to extend scope further; presenting a focused plan + ExitPlanMode produced clean approval and a tighter second half. The flow felt collaborative, not interrupted.

### Suggestions
- **Comms-log doesn't exist for brisken yet.** Worth creating `workspace/clients/brisken/context/comms-log.md` next session — multiple Dirk conversations (2026-04-10, 2026-04-13, 2026-04-22, 2026-05-14, 2026-05-17, 2026-05-20, 2026-05-25) are scattered across transcripts and prior checkpoints. A real log would give /resume a clean staleness signal and prevent the current "infer last contact from infrastructure.yaml" approximation.
- **Consider an `infrastructure-deferred` cleanup pass.** The cd-in-compound-Bash issue has now been logged at least three times (2026-05-18 local-web, 2026-05-20 platform Regression=Yes, 2026-05-25 this session). The documented-only fix has not held; a PreToolUse:Bash hook that detects `cd ... &&` patterns and rewrites/refuses them is overdue.

### System Health
- **Test infrastructure is friction-free.** `uv run --with 'pytest>=8.0' pytest` worked first try; no setup script, no virtualenv plumbing the user needed to manage. The pyproject `pythonpath = ["src"]` + `testpaths = ["tests"]` combo is the right minimal config for a uv-driven Python project — worth lifting into `templates/` as a starter for the next stack-independent client build.
- **B4 (reference-anchor) gate fired ~8 times this session and held without slowing the work.** Every flagged edit had its values traced (Dirk's call sections, Write-call file paths, system date, pytest output). The post-write reflex of "trace each value source" is now habitual, which is what the gate was designed to produce.
- **Autonomy score: 0 user-detected interventions; 2 hook-detected events** (B1 closing-offer pattern; Bash cd cwd persistence — 3rd recurrence). The user did not have to correct a single agent action this session; both events were caught by structural backstops before they reached the user.

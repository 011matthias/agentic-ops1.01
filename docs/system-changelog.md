# System Changelog

Historical record of infrastructure development. Moved from MEMORY.md to reduce always-loaded context.

---

## System Development Infrastructure (2026-02-25, updated 2026-02-26)

- **`/system-dev [client] [--audit-only]`** — Structured friction audit → prioritize → build cycle. The invocable self-annealing loop.
- **`build-test-fix` skill** — Autonomous build→test→classify→fix loop **with outcome verification**. 3 iterations before escalation. Modules: ITERATION-LOOP, OUTCOME-VERIFICATION, FAILURE-TAXONOMY, FIX-PATTERNS.
- **Outcome verification** — Mandatory gate: after execution succeeds, verify outputs are correct (not just that it ran). New `OUTCOME_MISMATCH` failure category with 4 sub-types (EMPTY_OUTPUT, WRONG_VALUES, MISSING_FIELDS, STRUCTURAL_MISMATCH). Injected into build-orchestrator Phase 3.5 and Phase 6.
- **Operationalization loop** — Now fires after builds too (not just fixes). "After Building" section asks: did I verify output? what couldn't I verify? what did the user do manually?
- **`blueprint-reconciler` skill** — Cross-validates blueprints against data stores, sheets, IML refs, templates, and handover format. 5 modules: DATA-STORE, SHEETS-COLUMN, IML-REFERENCE, TEMPLATE-PLACEHOLDER, HANDOVER-FORMAT-CHECKER.
- **New make-mcp-tools-expert modules:** WEBHOOK-PAYLOAD-INSPECTOR (discover actual payload structure), SCHEMA-EVOLUTION (full add/modify/remove field chain).
- **Escalation policy** in `testing-philosophy.md`: 3 autonomous iterations → escalate; novel errors → escalate immediately; never retry same fix.
- **Rules budget:** Started at 141/250 lines across 5 rules. Consolidated to 2 rules in 2026-03 overhaul.
- **Unified decision framework (2026-02-26):** DECISION-TREE.md is now the single canonical source for "what primitive to create." The operationalization-loop rule and `/system-dev` command both defer to it. New "Agentic Ops Decision Criteria" section includes: rule-vs-skill litmus test, rules budget reminder, agent sub-types, extend-vs-create preference, and friction-to-primitive mapping table.
- **S0 post-mortem improvements (2026-02-26):** FIX-PATTERNS.md now has OM-1 through OM-4 (OUTCOME_MISMATCH fixes). `validate_blueprint_schema` API-only limitation surfaced in make-mcp-tools-expert SKILL.md + BLUEPRINT-FORMAT.md. MAKE-BUILD.md Step 4 split into Option A (start from export, for handover) / Option B (generate from spec). `/system-dev` Phase 1 now reads MEMORY.md. Escalation wording aligned between SKILL.md and ITERATION-LOOP.md.

## n8n Infrastructure (2026-03-02)

n8n tooling now has parity with Make.com for testing, diagnostics, and client readiness. Key difference: n8n's execution history is fully readable via MCP (unlike Make.com), so the infrastructure is intentionally leaner.

**New modules created:**
- `n8n-mcp-tools-expert/modules/N8N-RUNTIME-GOTCHAS.md` — 10 catalogued gotchas (G1-G10), lookup format: symptom → cause → fix
- `n8n-mcp-tools-expert/modules/AUTONOMOUS-DIAGNOSTICS.md` — 6-level diagnostic ladder (vs Make's 16)
- `n8n-mcp-tools-expert/modules/POST-EXECUTION-VERIFICATION.md` — verifiable vs unverifiable outputs, verification fixture pattern
- `n8n-mcp-tools-expert/modules/PRE-CLIENT-REVIEW.md` — pre-handover checklist (workflow hygiene, Config node, credentials, testing, docs)
- `n8n-workflow-patterns/modules/WEBHOOK-PAYLOAD-INSPECTOR.md` — payload discovery procedure + provider expression translation table

**Updated files:**
- `build-test-fix/modules/FIX-PATTERNS.md` — 5 n8n-specific entries: ER-4, EX-4, EX-5, SM-4, AE-3
- `build/modules/N8N-BUILD.md` — fixed 2 broken rule references

**What n8n does NOT need (vs Make.com):** No blueprint reconciler, no handover format checker, no schema evolution, no debug taps, no S0 utility template.

## Client Comms Infrastructure (2026-03-03)

Evolved from outbound-only message formatter to bidirectional project development interface.

**Two entry points:** `/draft` (outbound) and `/comms` (inbound/log/status)
**Shared state:** `context/comms-log.md` per client — persistent conversation record with open items tracking

**New modules (2026-03-03):**
- `COMMS-LOG.md` — Log format spec, read/write procedures, entry types
- `INBOUND-PROCESSING.md` — Paste deduplication, gap detection, decision/fact extraction
- `FEASIBILITY-CHECK.md` — Quality gates + complexity flags

**Key design decisions:**
- `/comms` is separate from `/draft` (clean concern separation)
- Always ask before logging (user stays in control)
- Feasibility includes complexity flags + effort estimates
- Temporal awareness drives opener style

## Logging System (2026-03-03)

Three-layer logging infrastructure for cross-session pattern detection.

**Three log types:**
- Session logs (`docs/sessions/YYYY-MM-DD.md`) — written by `/checkpoint`, per-day aggregation with frontmatter counters
- Build logs (`workspace/clients/{client}/context/build-log.md`) — written by build-orchestrator Phase 7, per-client iteration history
- Friction register (`docs/friction-register.md`) — global accumulator, written by build-test-fix on escalation + checkpoint on friction events

**New command:** `/review [--save]` — reads all three log types, surfaces patterns (frequency >= 3, error categories >30%), scores by ROI, recommends `/system-dev` targets.

**Modified primitives:**
- `/checkpoint` — appends session log entry after writing checkpoint
- `build-orchestrator` Phase 7 — appends build log entry after session summary
- `ITERATION-LOOP.md` — logs friction events on escalation (ESCALATION) and novel errors (KNOWLEDGE_GAP)
- `/resume` — shows build history from build-log.md when available
- `/system-dev` Phase 1 — reads friction register + session logs as primary data sources (faster than scanning checkpoints)

**Design principles:** Zero always-loaded token impact. All hooks piggybacked on existing habits. Markdown tables for easy append/grep.

## Token Efficiency Overhaul (2026-03-03)

- Consolidated 5 rules (141 lines) → 2 rules (~30 lines): `detection.md` + `behaviors.md`
- Compressed CLAUDE.md from 130 → ~45 lines (removed tables, env vars, self-annealing section)
- Compressed MEMORY.md from 99 → ~30 lines (moved history to this changelog, replaced content with pointers)
- Created orchestrator packs: n8n-pack, make-pack, trigger-pack (consolidating 16 individual skills)
- Designed three-layer context loading: always-loaded → session-scoped → phase-scoped → reference-only

# Mini-Checkpoint: Agent Teams Phase 2

**Date:** 2026-05-26
**Status:** Gap #2 partially closed — Make.com builder specialist shipped (n8n builder + per-orchestrator testers still deferred)
**Type:** mini
**Prior:** [Agent Teams Phase 1](../2026-05-26%20-%20Agent%20Teams%20Phase%201/Mini-Checkpoint-1.md)

---

## Summary

Built [.claude/agents/agnt_make-builder.md](../../.claude/agents/agnt_make-builder.md), the first orchestrator-specific build specialist. Closes the Make-half of diagnostic gap #2 (per-orchestrator builder/tester teams). The generic `agnt_implementation-agent` continues to handle Trigger.dev + FastAPI; Make.com specs now route to the new specialist. Smoke-tested both BLOCKED output shapes against persistent fixtures. n8n-builder and per-orchestrator testers deferred per the scope-creep watch in the Phase-2 prompt — earn each one.

## What Was Done

- Read the four prerequisite files from the Phase-1 handoff prompt before writing anything: [agnt_implementation-agent.md](../../.claude/agents/agnt_implementation-agent.md) (what's already generic), [agnt_comms-critic.md](../../.claude/agents/agnt_comms-critic.md) + [agnt_done-verifier.md](../../.claude/agents/agnt_done-verifier.md) (the structural pattern to match), [skil_make-pack/SKILL.md](../../.claude/skills/skil_make-pack/SKILL.md) (knowledge layer to embody), and [comd_build-automation.md](../../.claude/commands/comd_build-automation.md) (where routing happens). Also pulled the friction register's full Make-relevant history (entries on ops feasibility, sheet 429, MCP execution-detail limitation, iteration breach, SQL injection in UTIL 8974201, email-batch enumeration).
- Built [.claude/agents/agnt_make-builder.md](../../.claude/agents/agnt_make-builder.md) — Make.com specialist. v1 scope: one scenario per invocation, against one client. Workflow: read spec → resolve instance → run 7 pre-build gates (G1 ops estimation, G2 API impossibilities, G3 connection enumeration, G4 module-casing audit, G5 SQL parameterization, G6 sheet-op ordering, G7 email-module batch manifest) → generate blueprint → validate → deploy via MCP with REST fallback → post-deploy binding check → update infrastructure.yaml → emit build report. Each gate cites the specific friction-register entry it structurally enforces (G1 → #49 ops feasibility, G5 → #77 SQL injection, G6 → #40 sheet 429, G7 → #71 BCC scope gap). Hard rules baked in: 3-iteration cap, mandatory ops gate, UI requirements in the FIRST response (resolves #56's 6+ retry loop), no SQL string concat ever, modify-scenario gate compliance, no spec edits (BLOCK upstream instead).
- Strict two-shape output contract matching the Phase-1 pattern: `## Build report — {id}: {name}` (success or partial) OR `## Build BLOCKED — {id}: {name}` (any pre-build gate failed). First characters are the `##` header, no preamble. The build report's section skeleton is fixed so the orchestrator can parse it; the BLOCKED shape always includes "what's needed to unblock" plus the failing gate name.
- Wired into [.claude/commands/comd_build-automation.md](../../.claude/commands/comd_build-automation.md) Phase 2 routing: Make.com → agnt_make-builder; Trigger.dev/FastAPI → agnt_implementation-agent; n8n → agnt_implementation-agent (flagged as specialist-TBD). Added a Quick Reference table row for each orchestrator.
- Created persistent test fixtures at [tools/fixtures/agnt_make-builder/](../../tools/fixtures/agnt_make-builder/): a fixture infrastructure.yaml (synthetic `_fixture-make-builder` client with a 10k-ops/month plan), `spec-blocked-no-trigger.md` (missing `trigger:` frontmatter → Step 1 fail-fast), `spec-blocked-ops.md` (5-second cron × 6 modules = 3.1M ops/month vs 10k plan → Gate G1 BLOCK), and a README explaining how to re-run.
- Smoke-tested via `general-purpose` agent role-playing the spec (the new agent file isn't picked up by the runtime registry mid-session; this is the same workaround Phase-1 used).
  - **Test 1 (spec-blocked-no-trigger):** Clean BLOCKED shape. Gate `spec`, blocker verbatim-matches the agent's Step 1 fail-fast text. Pre-build gates section correctly says "none" (failed before any gate). Cited register #49 + hard rule #9. No preamble.
  - **Test 2 (spec-blocked-ops):** Clean BLOCKED shape. Gate G1. Ops math shown end-to-end: `(2,592,000 / 5) × 6 = 3,110,400` projected ops/month vs `0.8 × 10,000 = 8,000` threshold → 388x. Three remedial options listed (reduce frequency, upgrade plan, refactor flow). G2–G7 correctly noted as not-run (G1 is a hard stop). Cited register #49 + hard rules #4 + #9. No preamble.

## Current Status

- One new agent live in [.claude/agents/agnt_make-builder.md](../../.claude/agents/agnt_make-builder.md), wired into the build-orchestrator's Phase 2 routing, behaviorally validated on both BLOCKED output shapes via fixtures.
- Repo not committed yet — left for user review per the `feedback_no_auto_commit` memory.
- Phase-1 agents (agnt_comms-critic, agnt_done-verifier) still uncommitted from the previous session per the Phase-1 next-step #1. This session's work can be bundled into the same review commit, or split — user's call.
- The "BUILT" output shape (full happy-path build report) was NOT smoke-tested this session because it requires either a real Make MCP server connection or a willingness to actually deploy a no-op scenario. The two BLOCKED-shape tests validate the strict output contract; full-path validation will happen on the first real Make build the orchestrator routes through.

## Gaps remaining (from Phase-1 diagnostic)

- **#3 per-orchestrator n8n builder** — natural Phase 3 candidate; mirror the Make pattern. n8n knowledge layer (skil_n8n-pack) already exists; need an agnt_n8n-builder that enforces n8n-specific gotchas (typeVersion 3 for Split-In-Batches done output, Cloud Code sandbox restrictions, etc.).
- **#3b per-orchestrator testers** — deferred per the original Phase-2 recommendation ("if after 2-3 real builds the testing-agent is missing something Make-specific, then add agnt_make-tester. Don't pre-build both."). Re-evaluate after 2-3 real Make builds route through the new agent.
- **#4 strategic intent-reviewer** — narrow-scope agent that flags `over-literal` / `intent-misalignment` / `strategic-gap` patterns before execution. Distinct from comms-critic; this one runs on planning, not on drafts.
- **#5 proposal parallel research** — concurrent research fan-out for proposal drafting.
- **#6 memory-recall enforcer** — blocked on real-use data from comms-critic. Don't build until 3-5 real `/draft` runs show what the critic catches vs misses.

## Next Steps

1. **Review the agent prompt + the wiring edit + the fixtures.** Either bundle this commit with the Phase-1 work (one batch for both phases), or split.
2. **First real Make build.** When the next Make spec hits `/comd_build-automation`, the orchestrator will route it through the new builder. Watch the build report carefully — that's the real validation; the smoke-tests only proved the BLOCKED shape.
3. **Phase 3 candidate: agnt_n8n-builder.** Mirror the Make pattern. The friction register has n8n-specific entries (#35, #37, #38, #39 — Cloud Code sandbox, typeVersion, f-string expression interpolation) that mirror the Make-specific ones; the gate set will be different but the structural shape is the same.
4. **Don't build #3b testers, #4, #5, #6 yet.** Earn each one. Phase 2's scope-creep watch (cited in the Phase-1 prompt) applies recursively.

## Files to Read First

- [.claude/agents/agnt_make-builder.md](../../.claude/agents/agnt_make-builder.md) — the new agent spec
- [.claude/commands/comd_build-automation.md](../../.claude/commands/comd_build-automation.md) — see Phase 2 routing block + Quick Reference table
- [tools/fixtures/agnt_make-builder/README.md](../../tools/fixtures/agnt_make-builder/README.md) — how to re-run the smoke tests
- [docs/2026-05-26 - Agent Teams Phase 1/Mini-Checkpoint-1.md](../2026-05-26%20-%20Agent%20Teams%20Phase%201/Mini-Checkpoint-1.md) — Phase-1 context (the two agents shipped last session, also still uncommitted)

## Friction events

None this session. The scope-creep watch held (did not build n8n-builder, did not build testers, did not generalize). The two-shape output contract was followed end-to-end. The "agent registry doesn't refresh mid-session" constraint is a known harness behavior, not a new friction — same workaround as Phase 1.

## What worked well

- Reading the four prerequisite files in parallel up-front (per the resume prompt's "read these BEFORE writing any code" instruction) meant the agent spec was internally consistent on the first write — no rework cycles.
- Grounding each Gate in a specific register entry made the hard-rules section self-justifying (the user can audit any rule by reading the cited friction event).
- Persistent fixtures with the "expected behavior" written into the spec file's body (not just the README) means future smoke-tests are reproducible from any session — the test passes/fails against an explicit contract, not a vibe.

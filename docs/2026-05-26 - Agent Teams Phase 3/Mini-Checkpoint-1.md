# Mini-Checkpoint: Agent Teams Phase 3

**Date:** 2026-05-26
**Status:** Gap #2 fully closed for orchestrator builders — n8n specialist shipped; the per-orchestrator builder column is now complete (Make.com, n8n, Trigger.dev/FastAPI all have specialists).
**Type:** mini
**Prior:** [Phase 1](../2026-05-26%20-%20Agent%20Teams%20Phase%201/Mini-Checkpoint-1.md) · [Phase 2](../2026-05-26%20-%20Agent%20Teams%20Phase%202/Mini-Checkpoint-1.md)

---

## Summary

Built [.claude/agents/agnt_n8n-builder.md](../../.claude/agents/agnt_n8n-builder.md), the second orchestrator-specific build specialist this day. Same structural pattern as agnt_make-builder, adapted for n8n's distinct gotchas (Code-node sandbox restrictions, typeVersion compatibility, nodeType naming discipline, double-brace expression syntax, n8n Cloud execution-budget billing). The build-orchestrator's Phase 2 routing now has zero generic fallbacks — Make, n8n, Trigger.dev, and FastAPI each have their own specialist. Smoke-tested both BLOCKED output shapes.

## What Was Done

- Read the n8n-specific prerequisites in parallel: [skil_n8n-pack/SKILL.md](../../.claude/skills/skil_n8n-pack/SKILL.md) (knowledge layer), n8n-relevant friction register entries (#35, #37 sandbox; #38 f-string brace collapse; #39 splitInBatches typeVersion; #40 sheets 429), [comd_n8n-instances.md](../../.claude/commands/comd_n8n-instances.md) (per-client MCP server provisioning pattern).
- Built [.claude/agents/agnt_n8n-builder.md](../../.claude/agents/agnt_n8n-builder.md) — n8n specialist with 7 pre-build gates:
  - **N1 nodeType-format discipline** — `nodes-base.*` for validation tools, `n8n-nodes-base.*` for workflow body (skil_n8n-pack §"Critical Rules"); inline fixes on mismatches
  - **N2 typeVersion compatibility** — hard-coded table starting with splitInBatches `>= 3` (resolves #39); extensible as new incidents log
  - **N3 Code-node sandbox check** — greps Code-node bodies for banned patterns: `fetch()`, `$helpers.httpRequest()`, `this.helpers.httpRequestWithAuthentication()` (resolves #35 + #37); refactor to HTTP Request node
  - **N4 expression-syntax integrity** — flags single-brace `{ $json.field }` references that should be `{{ $json.field }}` (resolves the #38 Python f-string brace-collapse class)
  - **N5 sheet-op ordering** — same shape as Make's G6: Clear/Delete/Update sheet ops must NOT receive multi-item input (resolves #40)
  - **N6 credential enumeration** — n8n credential IDs are instance-specific; verify each `systems` entry maps to a registered credential in infrastructure.yaml
  - **N7 execution-budget** — n8n Cloud only (self-hosted is N-A). Different billing model from Make.com (executions, not module-ops). Cites #49 as transferable precedent.
- Wired into [.claude/commands/comd_build-automation.md](../../.claude/commands/comd_build-automation.md) Phase 2 routing — n8n now goes to `agnt_n8n-builder` instead of falling back to the generic implementation-agent. Quick Reference table updated.
- Created persistent fixtures at [tools/fixtures/agnt_n8n-builder/](../../tools/fixtures/agnt_n8n-builder/): synthetic infrastructure.yaml + `spec-blocked-code-sandbox.md` (Code-node `fetch()` → Gate N3 BLOCK) + `spec-blocked-typeversion.md` (splitInBatches typeVersion 1 → Gate N2 BLOCK) + README.
- Smoke-tested via `general-purpose` agent role-playing (registry doesn't refresh mid-session; same workaround as Phase 1 + 2).
  - **Test 1 (Code sandbox):** Clean BLOCKED shape. Gate N3. Verbatim quote of the offending `await fetch(...)` line. Cited register #37 + #35. Gates correctly listed (N1 PASS, N2 N-A, N3 BLOCK, N4–N7 not run).
  - **Test 2 (typeVersion):** Clean BLOCKED shape. Gate N2. Node name + bad version (1) + required version (`>= 3`) + register #39 citation. Gates correctly listed (N1 PASS, N2 BLOCK, N3–N7 not run).

## Current Status

- Three specialists now live and routed (Phase 1: comms-critic + done-verifier; Phase 2: make-builder; Phase 3: n8n-builder), all uncommitted per `feedback_no_auto_commit`.
- The orchestrator's Phase 2 routing has no remaining "specialist TBD" entries: Make → make-builder, n8n → n8n-builder, Trigger.dev/FastAPI → implementation-agent.
- The output-shape contract is consistent across both builder specialists (same `## Build report` / `## Build BLOCKED` shape, same section names), so the orchestrator can parse Make and n8n build reports with one schema.

## Gaps remaining (from Phase-1 diagnostic)

- **#3b per-orchestrator testers** — STILL deferred. Same reason as Phase 2: don't build until 2-3 real Make or n8n builds prove the generic testing-agent is missing something orchestrator-specific.
- **#4 strategic intent-reviewer** — narrow-scope agent for `over-literal` / `intent-misalignment` / `strategic-gap` patterns at planning time. Ready to build; not done this session (scope-creep watch — one specialist per session is the disciplined cadence).
- **#5 proposal parallel research** — concurrent research fan-out for `/comd_new-proposal`. Ready to build.
- **#6 memory-recall enforcer** — STILL blocked on real-use data from comms-critic (need 3-5 real `/draft` runs first).

## Next Steps

1. **Review.** Three uncommitted phases now (comms-critic + done-verifier + their wiring; make-builder + its wiring + fixtures; n8n-builder + its wiring + fixtures). When you're ready to commit, pick the bundle vs split shape and say so.
2. **First real n8n build.** Same as Phase 2's next-step #2: when the next n8n spec hits `/comd_build-automation`, the orchestrator will route it through the new builder. The BUILT shape only gets exercised on a real build (smoke tests only proved the BLOCKED shape).
3. **Phase 4 candidate: agnt_intent-reviewer.** Different shape from the builders — runs at planning time, not build time. The closest analog is agnt_comms-critic (semantic audit, narrow scope, structured findings) but applied to plans instead of drafts. Earn it: only build when you feel the absence (the next time a session opens a plan you'd want a second opinion on, that's the trigger).
4. **Phase 5 candidate: agnt_proposal-research.** Parallel research fan-out for `/comd_new-proposal`. Lower priority than #4 because the proposal flow already works; speed/quality marginal.

## Files to Read First

- [.claude/agents/agnt_n8n-builder.md](../../.claude/agents/agnt_n8n-builder.md) — the new agent
- [.claude/commands/comd_build-automation.md](../../.claude/commands/comd_build-automation.md) — Phase 2 routing block + Quick Reference table
- [tools/fixtures/agnt_n8n-builder/README.md](../../tools/fixtures/agnt_n8n-builder/README.md) — how to re-run the smoke tests
- [docs/2026-05-26 - Agent Teams Phase 2/Mini-Checkpoint-1.md](../2026-05-26%20-%20Agent%20Teams%20Phase%202/Mini-Checkpoint-1.md) — sibling structure (Make-builder)

## Friction events

None this session. The mirror-the-Make-pattern approach kept the build tight (no rework cycles on the agent spec). Scope-creep watch held — did not build testers, did not build intent-reviewer, did not build proposal-research. The n8n-builder's gate set is genuinely different from Make's (sandbox restrictions, typeVersion compat, double-brace expressions don't exist in Make), which validates the per-orchestrator split as the right structural choice.

## What worked well

- **Mirroring the Make-builder structural skeleton** meant the n8n-builder was internally consistent on the first write, with only the gate semantics needing original thought. Same output-shape, same section names, same hard-rules format. The orchestrator's parser stays simple.
- **Grounding each gate in a specific friction-register entry** (and labeling them `N{n}` analogously to Make's `G{n}`) means the orchestrator + the user can audit any rule by reading the cited friction event. Self-justifying gates.
- **Two BLOCKED-shape smoke tests instead of trying to test the BUILT shape** kept the fixture work proportional. The BUILT path will get its real test on the first n8n spec that hits `/comd_build-automation`.
- **One agent per session** is holding as the disciplined cadence. Three phases shipped this day with zero scope-creep events.

## Session pressure

Moderate-to-high. Three phases in one day, accumulating reads and tool calls. If you want Phase 4 (intent-reviewer) or Phase 5 (proposal-research) next, a fresh `/comd_resume` would give cleaner context. The deferred-gap punch list is documented above so a new session can pick up from any item.

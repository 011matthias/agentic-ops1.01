# Fresh-session prompt — Agent Teams Phase 2: per-orchestrator teams

Copy-paste the prompt below into a new Claude Code session in this repo (`agentic-ops1`). It is self-contained and references the files the previous session left for you.

---

## PROMPT

I want to continue building agent teams in agentic-ops. Last session shipped two specialists (agnt_comms-critic + agnt_done-verifier — see [docs/2026-05-26 - Agent Teams Phase 1/Mini-Checkpoint-1.md](docs/2026-05-26%20-%20Agent%20Teams%20Phase%201/Mini-Checkpoint-1.md) for the full context, and the underlying gap diagnostic).

This session, build **gap #2 from the diagnostic: per-orchestrator builder + tester teams**, starting with Make.com.

### Why this gap

The diagnostic last session found 4+ Make-specific friction events in 2026-03 (#39 typeVersion gotcha, #40 sheet 429, #42 phpMyAdmin defer, #50 ops-feasibility miss), plus #75 SQL-injection in a UTIL scenario built without security review. The current `agnt_implementation-agent` is generic — its frontmatter only mentions Trigger.dev and FastAPI; Make and n8n are second-class even though `skil_make-pack` and `skil_n8n-pack` already hold the deep domain knowledge as skills. Skills are knowledge; agents are specialists who can ACT on it. That gap is structural.

### What to build (decision needed first)

The previous session left this open question:

> Should per-orchestrator teams be 2 agents per orchestrator (builder + tester) or 1 combined agent?

Resolve it before coding. The trade-off:
- **2 agents per orchestrator (builder + tester, 4 agents total for Make + n8n).** Cleaner separation; mirrors the existing implementation-agent + testing-agent split. More agents to maintain.
- **1 combined agent per orchestrator (2 agents total).** Less ceremony, faster to ship, but loses the critic-pair quality lift that worked well for /draft.

My recommendation, but redirect me if you disagree: start with `agnt_make-builder` ALONE (no tester yet) as the v1. The testing-agent that already exists handles execution verification at the MCP layer; what's missing is the BUILD specialist who knows Make's gotchas. If after 2-3 real builds the testing-agent is missing something Make-specific, then add `agnt_make-tester`. Don't pre-build both.

### Scope ceiling for this session

ONE agent: `agnt_make-builder`. Wire it into `comd_build-automation.md` so the build-orchestrator routes Make.com specs to it. Smoke-test against the existing fixture pattern at `tools/fixtures/agnt_comms-critic/`. Same pace as last session — checkpoint and stop after one agent ships green. Don't build n8n-builder, don't build testers. Earn each one.

### What to read first

Read these BEFORE writing any code:

1. [.claude/agents/agnt_implementation-agent.md](.claude/agents/agnt_implementation-agent.md) — the existing generic agent. Understand what already works and what specifically you're specializing.
2. [.claude/skills/skil_make-pack/SKILL.md](.claude/skills/skil_make-pack/SKILL.md) — the knowledge layer the new agent will embody.
3. [.claude/agents/agnt_comms-critic.md](.claude/agents/agnt_comms-critic.md) AND [.claude/agents/agnt_done-verifier.md](.claude/agents/agnt_done-verifier.md) — the two agents shipped last session. Match their structural pattern: strict output shape contract, hard rules section, scope-bounded v1, source-list footer.
4. [.claude/commands/comd_build-automation.md](.claude/commands/comd_build-automation.md) — where the routing happens.
5. [docs/friction-register.md](docs/friction-register.md) — search for `make` entries to ground the agent's "gotchas to enforce" list in real incidents (#39, #40, #42, #50, #75 cited above).

### Constraints from last session that apply here

- **Self-annealing layer 1 ladder** — escalate from memory → structural. A new agent IS structural.
- **Strict output shape contract.** Both shipped agents have a strict OK/fail-list (or VERIFIED/fail-list) shape. The builder agent doesn't have the same fit (it produces code, not audits) but it MUST emit a structured "build report" the build-orchestrator can parse — don't let it ramble.
- **Scope-creep watch.** Last session's only friction event was scope-creep (polishing a working agent). After smoke-test passes, STOP. Do not also build the tester. Do not also generalize to n8n. One agent, ship green, checkpoint.
- **Test fixtures pattern.** Persistent fixtures in `tools/fixtures/{agent-name}/`. Re-runnable for next iteration.

### Output by end of session

- `.claude/agents/agnt_make-builder.md` — the new agent, following the structural pattern of the two existing critic agents
- Wiring edit in `.claude/commands/comd_build-automation.md` so Make specs route to it
- `tools/fixtures/agnt_make-builder/` — at least one test fixture (a minimal Make spec) the agent can be smoke-tested against
- Smoke-test results (the agent's output on the fixture, evaluated against expected behavior)
- Mini-checkpoint at `docs/{TODAY}` - Agent Teams Phase 2/Mini-Checkpoint-1.md`
- Updated INDEX.md

Don't commit until I review.

---

## Notes for me (Matthias) when picking up

- The 4 remaining gaps after this session are documented in [docs/sessions/2026-05-26-context.yaml](docs/sessions/2026-05-26-context.yaml) under `deferred_gaps`.
- After this session ships `agnt_make-builder`, the natural Phase 3 candidate is `agnt_n8n-builder` (mirror the Make build). Phase 4 candidates are gap #5 (proposal parallel research) and gap #4 (strategic intent-reviewer narrow-scope).
- Gap #6 (memory-recall enforcer) is blocked on real-use data from the comms-critic. Don't build it until I've done 3-5 real `/draft` runs and seen what the critic catches vs. misses.
